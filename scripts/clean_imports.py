#!/usr/bin/env python3
"""
Analyze and clean Python imports across the codebase.

Features:
- Find imports inside functions/methods
- Move them to module top
- Organize per PEP 8 (using ruff)
- Smart categorization (keeps try/except, TYPE_CHECKING)
- Dry-run mode for safety
"""

import argparse
import ast
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ImportLocation(Enum):
    """Location types for import statements."""
    MODULE_TOP = "top"              # Correct location
    FUNCTION_BODY = "function"      # Needs moving
    CLASS_BODY = "class"            # Needs moving
    TRY_EXCEPT = "try_except"       # Keep (optional dependency)
    TYPE_CHECKING = "type_checking" # Keep (forward reference)
    DOCSTRING = "docstring"         # Ignore (example code)


@dataclass
class ImportInfo:
    """Information about an import statement."""
    line: int
    column: int
    location: ImportLocation
    scope: str  # Function/class name or "module"
    import_type: str  # "import" or "from"
    module: str  # Module name
    names: List[str] = field(default_factory=list)  # Imported names
    alias: Optional[str] = None  # Import alias
    parent_node_type: str = ""  # Type of parent AST node
    is_legitimate: bool = False  # Should this import stay in place?
    reason: str = ""  # Reason for keeping/moving


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    file_path: Path
    imports: List[ImportInfo] = field(default_factory=list)
    imports_to_move: List[ImportInfo] = field(default_factory=list)
    imports_to_keep: List[ImportInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    modified: bool = False


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to find and categorize all imports."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.imports: List[ImportInfo] = []
        self.current_scope: List[str] = ["module"]
        self.in_try_except = False
        self.in_type_checking = False
        self.depth = 0
        self.parent_stack: List[ast.AST] = []
        
    def visit(self, node: ast.AST):
        """Override visit to track parent nodes."""
        if node:
            self.parent_stack.append(node)
        try:
            super().visit(node)
        finally:
            if node and self.parent_stack and self.parent_stack[-1] == node:
                self.parent_stack.pop()
    
    def visit_Import(self, node: ast.Import):
        """Visit an import statement."""
        location = self._determine_location()
        scope = "::".join(self.current_scope)
        parent_type = type(self.parent_stack[-2]).__name__ if len(self.parent_stack) > 1 else "Module"
        
        for alias in node.names:
            import_info = ImportInfo(
                line=node.lineno,
                column=node.col_offset,
                location=location,
                scope=scope,
                import_type="import",
                module=alias.name,
                alias=alias.asname,
                parent_node_type=parent_type,
                is_legitimate=self._is_legitimate(location),
                reason=self._get_reason(location)
            )
            self.imports.append(import_info)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit a from...import statement."""
        location = self._determine_location()
        scope = "::".join(self.current_scope)
        parent_type = type(self.parent_stack[-2]).__name__ if len(self.parent_stack) > 1 else "Module"
        
        module = node.module or ""
        names = [alias.name for alias in node.names]
        aliases = {alias.name: alias.asname for alias in node.names if alias.asname}
        
        # Group imports from same module
        import_info = ImportInfo(
            line=node.lineno,
            column=node.col_offset,
            location=location,
            scope=scope,
            import_type="from",
            module=module,
            names=names,
            alias=None,  # Will handle aliases separately if needed
            parent_node_type=parent_type,
            is_legitimate=self._is_legitimate(location),
            reason=self._get_reason(location)
        )
        # Store aliases in a way we can reconstruct
        import_info.alias = json.dumps(aliases) if aliases else None
        self.imports.append(import_info)
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function scope."""
        self.current_scope.append(f"function:{node.name}")
        self.depth += 1
        self.generic_visit(node)
        self.current_scope.pop()
        self.depth -= 1
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function scope."""
        self.current_scope.append(f"async_function:{node.name}")
        self.depth += 1
        self.generic_visit(node)
        self.current_scope.pop()
        self.depth -= 1
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class scope."""
        self.current_scope.append(f"class:{node.name}")
        self.depth += 1
        self.generic_visit(node)
        self.current_scope.pop()
        self.depth -= 1
    
    def visit_Try(self, node: ast.Try):
        """Track try/except blocks."""
        old_state = self.in_try_except
        self.in_try_except = True
        self.generic_visit(node)
        self.in_try_except = old_state
    
    def visit_If(self, node: ast.If):
        """Check for TYPE_CHECKING blocks."""
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            old_state = self.in_type_checking
            self.in_type_checking = True
            self.generic_visit(node)
            self.in_type_checking = old_state
        else:
            self.generic_visit(node)
    
    def _determine_location(self) -> ImportLocation:
        """Determine the location type of the current import."""
        if self.in_type_checking:
            return ImportLocation.TYPE_CHECKING
        if self.in_try_except:
            return ImportLocation.TRY_EXCEPT
        if len(self.current_scope) == 1:  # Module level
            return ImportLocation.MODULE_TOP
        if any("function" in scope for scope in self.current_scope):
            return ImportLocation.FUNCTION_BODY
        if any("class" in scope for scope in self.current_scope):
            return ImportLocation.CLASS_BODY
        return ImportLocation.MODULE_TOP
    
    def _is_legitimate(self, location: ImportLocation) -> bool:
        """Check if import should stay in place."""
        return location in (
            ImportLocation.MODULE_TOP,
            ImportLocation.TRY_EXCEPT,
            ImportLocation.TYPE_CHECKING
        )
    
    def _get_reason(self, location: ImportLocation) -> str:
        """Get reason for keeping or moving the import."""
        reasons = {
            ImportLocation.MODULE_TOP: "Already at module top",
            ImportLocation.FUNCTION_BODY: "Inside function - should move to top",
            ImportLocation.CLASS_BODY: "Inside class - should move to top",
            ImportLocation.TRY_EXCEPT: "Optional dependency - keep in try/except",
            ImportLocation.TYPE_CHECKING: "Forward reference - keep in TYPE_CHECKING",
            ImportLocation.DOCSTRING: "In docstring - ignore"
        }
        return reasons.get(location, "Unknown")
    
    def _get_parent_context(self):
        """Get parent context (simplified - returns current scope info)."""
        return self.current_scope[-1] if self.current_scope else "module"
    
    def _is_in_docstring(self, node: ast.AST) -> bool:
        """Check if node is inside a docstring (simplified check)."""
        # This is a simplified check - in practice, docstrings are string literals
        # at the start of modules/classes/functions, not where imports would be
        return False


def analyze_file(file_path: Path) -> FileAnalysis:
    """Analyze a Python file for imports."""
    analysis = FileAnalysis(file_path=file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.splitlines()
        
        # Parse AST
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            analysis.errors.append(f"Syntax error: {e}")
            return analysis
        
        # Analyze imports
        analyzer = ImportAnalyzer(source_lines)
        analyzer.visit(tree)
        analysis.imports = analyzer.imports
        
        # Categorize imports
        for imp in analysis.imports:
            if imp.is_legitimate:
                analysis.imports_to_keep.append(imp)
            else:
                analysis.imports_to_move.append(imp)
    
    except Exception as e:
        analysis.errors.append(f"Error analyzing file: {e}")
    
    return analysis


class ImportMover:
    """Logic to extract imports and move them to top."""
    
    @staticmethod
    def build_import_statements(imports: List[ImportInfo]) -> List[str]:
        """Build import statements from ImportInfo objects."""
        import_lines = []
        
        # Group by module for 'from' imports
        from_imports: Dict[str, List[Tuple[str, Optional[str]]]] = {}
        regular_imports: List[Tuple[str, Optional[str]]] = []
        
        for imp in imports:
            if imp.import_type == "from":
                if imp.module not in from_imports:
                    from_imports[imp.module] = []
                # Handle aliases stored as JSON
                aliases = {}
                if imp.alias:
                    try:
                        aliases = json.loads(imp.alias)
                    except:
                        pass
                
                for name in imp.names:
                    alias = aliases.get(name)
                    from_imports[imp.module].append((name, alias))
            else:
                alias = imp.alias
                regular_imports.append((imp.module, alias))
        
        # Build 'from' import statements
        for module, items in sorted(from_imports.items()):
            if len(items) == 1:
                name, alias = items[0]
                if alias:
                    import_lines.append(f"from {module} import {name} as {alias}")
                else:
                    import_lines.append(f"from {module} import {name}")
            else:
                # Multi-line import
                parts = []
                for name, alias in items:
                    if alias:
                        parts.append(f"{name} as {alias}")
                    else:
                        parts.append(name)
                import_lines.append(f"from {module} import {', '.join(parts)}")
        
        # Build regular import statements
        for module, alias in sorted(regular_imports):
            if alias:
                import_lines.append(f"import {module} as {alias}")
            else:
                import_lines.append(f"import {module}")
        
        return import_lines
    
    @staticmethod
    def remove_import_lines(source_lines: List[str], imports_to_remove: List[ImportInfo]) -> List[str]:
        """Remove import lines from source code using AST-based approach."""
        # Group imports by line number (multiple imports can be on same line in AST)
        lines_to_remove = set()
        for imp in imports_to_remove:
            lines_to_remove.add(imp.line - 1)  # Convert to 0-based index
        
        # Parse the source to understand structure better
        try:
            source = '\n'.join(source_lines)
            tree = ast.parse(source)
            
            # Build a set of line numbers that contain imports to remove
            import_lines_to_remove = set()
            
            class ImportRemover(ast.NodeVisitor):
                def __init__(self, lines_to_remove):
                    self.lines_to_remove = lines_to_remove
                    self.import_lines = set()
                
                def visit_Import(self, node):
                    if (node.lineno - 1) in self.lines_to_remove:
                        self.import_lines.add(node.lineno - 1)
                
                def visit_ImportFrom(self, node):
                    if (node.lineno - 1) in self.lines_to_remove:
                        self.import_lines.add(node.lineno - 1)
            
            remover = ImportRemover(lines_to_remove)
            remover.visit(tree)
            lines_to_remove = remover.import_lines
            
        except:
            # Fallback to simple line removal if AST parsing fails
            pass
        
        # Remove lines
        result = []
        for i, line in enumerate(source_lines):
            if i not in lines_to_remove:
                result.append(line)
        
        return result
    
    @staticmethod
    def insert_imports_at_top(source_lines: List[str], new_imports: List[str]) -> List[str]:
        """Insert new imports at the top of the file, after docstring and __future__ imports."""
        result = []
        docstring_end = 0
        future_imports_end = 0
        
        # Find end of docstring
        i = 0
        if source_lines and source_lines[0].strip().startswith('"""') or source_lines[0].strip().startswith("'''"):
            # Multi-line docstring
            i = 1
            while i < len(source_lines):
                if '"""' in source_lines[i] or "'''" in source_lines[i]:
                    docstring_end = i + 1
                    break
                i += 1
        elif source_lines and (source_lines[0].strip().startswith('#') or not source_lines[0].strip()):
            # Skip shebang and empty lines
            i = 0
            while i < len(source_lines) and (source_lines[i].strip().startswith('#') or not source_lines[i].strip()):
                i += 1
            docstring_end = i
        
        # Find __future__ imports
        i = docstring_end
        while i < len(source_lines):
            line = source_lines[i].strip()
            if line.startswith('from __future__ import'):
                future_imports_end = i + 1
                i += 1
                # Continue if there are more __future__ imports
                while i < len(source_lines) and (source_lines[i].strip().startswith('from __future__') or not source_lines[i].strip()):
                    if source_lines[i].strip().startswith('from __future__'):
                        future_imports_end = i + 1
                    i += 1
                break
            elif line and not line.startswith('#'):
                break
            i += 1
        
        insert_position = max(docstring_end, future_imports_end)
        
        # Build result
        result.extend(source_lines[:insert_position])
        
        # Add blank line if needed
        if result and result[-1].strip():
            result.append("")
        
        # Add new imports
        result.extend(new_imports)
        
        # Add blank line after imports
        if new_imports:
            result.append("")
        
        # Add rest of file
        result.extend(source_lines[insert_position:])
        
        return result


def run_ruff_fix(file_path: Path) -> Tuple[bool, List[str]]:
    """Run ruff --fix on a file to organize imports."""
    errors = []
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "--select", "I001", "--fix", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0 and result.stderr:
            errors.append(f"Ruff warning: {result.stderr}")
        return True, errors
    except subprocess.TimeoutExpired:
        errors.append("Ruff timeout")
        return False, errors
    except FileNotFoundError:
        errors.append("Ruff not found - install with: pip install ruff")
        return False, errors
    except Exception as e:
        errors.append(f"Ruff error: {e}")
        return False, errors


def verify_syntax(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Verify that a file has valid Python syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source, filename=str(file_path))
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def create_backup(file_path: Path) -> Optional[Path]:
    """Create a backup of a file."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        return None


class ImportRemover(ast.NodeTransformer):
    """AST transformer to remove specific import nodes."""
    
    def __init__(self, lines_to_remove: Set[int]):
        self.lines_to_remove = lines_to_remove
    
    def visit_Import(self, node: ast.Import):
        """Remove import if it's in the removal set."""
        if (node.lineno - 1) in self.lines_to_remove:
            return None
        return node
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Remove import from if it's in the removal set."""
        if (node.lineno - 1) in self.lines_to_remove:
            return None
        return node


def modify_file(analysis: FileAnalysis, dry_run: bool = False, use_ruff: bool = True, verbose: bool = False) -> bool:
    """Modify a file to move imports to top."""
    if not analysis.imports_to_move:
        return False
    
    try:
        with open(analysis.file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            source_lines = source.splitlines()
        
        # Parse AST
        try:
            tree = ast.parse(source, filename=str(analysis.file_path))
        except SyntaxError as e:
            analysis.errors.append(f"Cannot parse file: {e}")
            return False
        
        # Get lines to remove
        lines_to_remove = {imp.line - 1 for imp in analysis.imports_to_move}
        
        # Remove import nodes from AST
        remover = ImportRemover(lines_to_remove)
        new_tree = remover.visit(tree)
        
        # Convert AST back to source
        # Use Python's built-in ast.unparse if available (Python 3.9+)
        try:
            modified_source = ast.unparse(new_tree)
        except AttributeError:
            # Fallback for older Python: use line-based approach
            # Build new import statements
            new_imports = ImportMover.build_import_statements(analysis.imports_to_move)
            
            # Remove old import lines carefully
            modified_lines = []
            for i, line in enumerate(source_lines):
                if i not in lines_to_remove:
                    modified_lines.append(line)
            
            # Insert new imports at top
            final_lines = ImportMover.insert_imports_at_top(modified_lines, new_imports)
            modified_source = '\n'.join(final_lines)
        
        if not dry_run:
            # Create backup
            backup_path = create_backup(analysis.file_path)
            if backup_path and verbose:
                print(f"    Backup created: {backup_path}")
            
            # Write modified content
            with open(analysis.file_path, 'w', encoding='utf-8') as f:
                if not modified_source.endswith('\n'):
                    modified_source += '\n'
                f.write(modified_source)
            
            # Verify syntax
            is_valid, error = verify_syntax(analysis.file_path)
            if not is_valid:
                # Restore backup if syntax is invalid
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, analysis.file_path)
                    analysis.errors.append(f"Syntax error detected - restored from backup: {error}")
                    return False
                else:
                    analysis.errors.append(f"Syntax error: {error}")
                    return False
            
            # Run ruff for final formatting
            if use_ruff:
                ruff_success, ruff_errors = run_ruff_fix(analysis.file_path)
                if ruff_errors:
                    analysis.errors.extend(ruff_errors)
            
            # Final syntax check
            is_valid, error = verify_syntax(analysis.file_path)
            if not is_valid:
                analysis.errors.append(f"Syntax error after ruff: {error}")
                return False
            
            analysis.modified = True
            return True
        else:
            # Just return that we would modify
            return True
    
    except Exception as e:
        analysis.errors.append(f"Error modifying file: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze and clean Python imports across the codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run analysis
  python clean_imports.py --dry-run backend/app
  
  # Fix imports in specific directory
  python clean_imports.py --fix backend/app/services
  
  # Verbose output
  python clean_imports.py --verbose backend/app
  
  # JSON output
  python clean_imports.py --json backend/app
        """
    )
    
    parser.add_argument(
        "path",
        nargs="?",
        default="backend/app",
        help="Path to analyze (file or directory, default: backend/app)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only analyze, don't modify files"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix imports (requires --dry-run to be False)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--exclude",
        help="Comma-separated patterns to exclude (e.g., 'tests/*,migrations/*')"
    )
    
    args = parser.parse_args()
    
    # Find Python files
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.py"))
    
    # Filter excluded patterns
    if args.exclude:
        exclude_patterns = [p.strip() for p in args.exclude.split(",")]
        files = [
            f for f in files
            if not any(f.match(pattern) for pattern in exclude_patterns)
        ]
    
    # Analyze files
    analyses = []
    for file_path in files:
        if args.verbose:
            print(f"Analyzing: {file_path}", file=sys.stderr)
        analysis = analyze_file(file_path)
        analyses.append(analysis)
    
    # Modify files if requested
    files_modified = 0
    if args.fix and not args.dry_run:
        print("\nModifying files...")
        for analysis in analyses:
            if analysis.imports_to_move:
                if args.verbose:
                    print(f"  Modifying: {analysis.file_path}")
                if modify_file(analysis, dry_run=False, use_ruff=True, verbose=args.verbose):
                    files_modified += 1
                if analysis.errors:
                    print(f"    Errors: {'; '.join(analysis.errors)}", file=sys.stderr)
    
    # Report results
    total_to_move = sum(len(a.imports_to_move) for a in analyses)
    files_with_issues = [a for a in analyses if a.imports_to_move]
    total_errors = sum(len(a.errors) for a in analyses)
    
    if args.json:
        output = {
            "files_analyzed": len(analyses),
            "files_with_issues": len(files_with_issues),
            "files_modified": files_modified,
            "total_imports_to_move": total_to_move,
            "total_errors": total_errors,
            "files": [
                {
                    "path": str(a.file_path),
                    "imports_to_move": len(a.imports_to_move),
                    "imports_to_keep": len(a.imports_to_keep),
                    "modified": a.modified,
                    "errors": a.errors
                }
                for a in analyses
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        # Print summary
        print(f"\n{'='*60}")
        print("Import Analysis Summary")
        print(f"{'='*60}")
        print(f"Files analyzed: {len(analyses)}")
        print(f"Files with imports to move: {len(files_with_issues)}")
        if args.fix and not args.dry_run:
            print(f"Files modified: {files_modified}")
        print(f"Total imports to move: {total_to_move}")
        if total_errors > 0:
            print(f"Total errors: {total_errors}")
        print(f"{'='*60}\n")
        
        if files_with_issues:
            if args.verbose:
                print("Files with imports to move:")
                for analysis in files_with_issues:
                    status = "✓ Modified" if analysis.modified else "⚠ Needs fixing"
                    print(f"\n  {status}: {analysis.file_path}")
                    for imp in analysis.imports_to_move:
                        print(f"    Line {imp.line}: {imp.import_type} {imp.module} "
                              f"({imp.reason})")
                    if analysis.errors:
                        for error in analysis.errors:
                            print(f"    ⚠ Error: {error}")
            else:
                print("Files with imports to move (use --verbose for details):")
                for analysis in files_with_issues:
                    status = "✓" if analysis.modified else "⚠"
                    print(f"  {status} {analysis.file_path} ({len(analysis.imports_to_move)} imports)")
        
        if args.fix and not args.dry_run and files_modified > 0:
            print(f"\n✓ Successfully modified {files_modified} file(s)")
            print("  Note: Backups were created with .bak extension")
    
    # Exit with appropriate code
    exit_code = 0
    if total_errors > 0:
        exit_code = 2
    elif total_to_move > 0 and not (args.fix and not args.dry_run):
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

