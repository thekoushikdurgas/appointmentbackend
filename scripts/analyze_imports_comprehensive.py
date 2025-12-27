#!/usr/bin/env python3
"""
Comprehensive import analysis script for backend codebase.
Analyzes all Python files to identify import placement and organization issues.
"""

import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ImportLocation(Enum):
    """Location types for import statements."""
    MODULE_TOP = "module_top"
    FUNCTION_BODY = "function_body"
    CLASS_BODY = "class_body"
    TRY_EXCEPT = "try_except"
    TYPE_CHECKING = "type_checking"
    METHOD_BODY = "method_body"


@dataclass
class ImportInfo:
    """Information about an import statement."""
    line: int
    column: int
    location: str
    scope: str  # Function/class name or "module"
    import_type: str  # "import" or "from"
    module: str  # Module name
    names: List[str] = field(default_factory=list)  # Imported names (for from imports)
    alias: Optional[str] = None  # Import alias
    parent_node_type: str = ""  # Type of parent AST node
    is_legitimate: bool = False  # Should this import stay in place?
    reason: str = ""  # Reason for keeping/moving
    code_context: str = ""  # Surrounding code for context


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    file_path: str
    imports: List[ImportInfo] = field(default_factory=list)
    imports_at_top: List[ImportInfo] = field(default_factory=list)
    imports_to_move: List[ImportInfo] = field(default_factory=list)
    imports_to_keep: List[ImportInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_imports: int = 0
    imports_in_functions: int = 0
    imports_in_classes: int = 0


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to find and categorize all imports."""
    
    def __init__(self, source_lines: List[str], file_path: Path):
        self.source_lines = source_lines
        self.file_path = file_path
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
        
        # Get code context (3 lines before and after)
        context_start = max(0, node.lineno - 4)
        context_end = min(len(self.source_lines), node.lineno + 3)
        code_context = "\n".join(self.source_lines[context_start:context_end])
        
        for alias in node.names:
            import_info = ImportInfo(
                line=node.lineno,
                column=node.col_offset,
                location=location.value,
                scope=scope,
                import_type="import",
                module=alias.name,
                alias=alias.asname,
                parent_node_type=parent_type,
                is_legitimate=self._is_legitimate(location),
                reason=self._get_reason(location),
                code_context=code_context
            )
            self.imports.append(import_info)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit a from...import statement."""
        location = self._determine_location()
        scope = "::".join(self.current_scope)
        parent_type = type(self.parent_stack[-2]).__name__ if len(self.parent_stack) > 1 else "Module"
        
        # Get code context (3 lines before and after)
        context_start = max(0, node.lineno - 4)
        context_end = min(len(self.source_lines), node.lineno + 3)
        code_context = "\n".join(self.source_lines[context_start:context_end])
        
        module = node.module or ""
        names = [alias.name for alias in node.names]
        aliases = {alias.name: alias.asname for alias in node.names if alias.asname}
        
        import_info = ImportInfo(
            line=node.lineno,
            column=node.col_offset,
            location=location.value,
            scope=scope,
            import_type="from",
            module=module,
            names=names,
            alias=json.dumps(aliases) if aliases else None,
            parent_node_type=parent_type,
            is_legitimate=self._is_legitimate(location),
            reason=self._get_reason(location),
            code_context=code_context
        )
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
        if any("function" in scope or "async_function" in scope for scope in self.current_scope):
            if any("class" in scope for scope in self.current_scope):
                return ImportLocation.METHOD_BODY
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
            ImportLocation.METHOD_BODY: "Inside method - should move to top",
            ImportLocation.TRY_EXCEPT: "Optional dependency - keep in try/except",
            ImportLocation.TYPE_CHECKING: "Forward reference - keep in TYPE_CHECKING",
        }
        return reasons.get(location, "Unknown")


def classify_import_type(module: str) -> str:
    """Classify import as stdlib, third-party, or local."""
    if not module:
        return "local"
    
    # Standard library modules (common ones)
    stdlib_modules = {
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'base64',
        'bisect', 'builtins', 'bz2', 'calendar', 'collections', 'concurrent',
        'configparser', 'contextlib', 'copy', 'csv', 'dataclasses', 'datetime',
        'dbm', 'decimal', 'difflib', 'dis', 'doctest', 'email', 'encodings',
        'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput',
        'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass',
        'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html',
        'http', 'imaplib', 'imghdr', 'importlib', 'inspect', 'io', 'ipaddress',
        'itertools', 'json', 'keyword', 'lib2to3', 'linecache', 'locale',
        'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
        'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing', 'netrc',
        'nis', 'nntplib', 'ntpath', 'numbers', 'operator', 'optparse', 'os',
        'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pipes', 'pkgutil',
        'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile',
        'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
        'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
        'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex',
        'shutil', 'signal', 'site', 'smtplib', 'sndhdr', 'socket', 'socketserver',
        'spwd', 'sqlite3', 'sre_compile', 'sre_constants', 'sre_parse', 'ssl',
        'stat', 'statistics', 'string', 'stringprep', 'struct', 'subprocess',
        'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog', 'tarfile',
        'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading',
        'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback',
        'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing',
        'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings',
        'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
        'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib'
    }
    
    # Check if it's a standard library module
    root_module = module.split('.')[0]
    if root_module in stdlib_modules:
        return "stdlib"
    
    # Check if it's a local app import
    if module.startswith('app.'):
        return "local"
    
    # Otherwise it's third-party
    return "third_party"


def analyze_file(file_path: Path) -> FileAnalysis:
    """Analyze a Python file for imports."""
    analysis = FileAnalysis(file_path=str(file_path))
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
            source_lines = source.splitlines()
        
        # Parse AST
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            analysis.errors.append(f"Syntax error: {e}")
            return analysis
        
        # Analyze imports
        analyzer = ImportAnalyzer(source_lines, file_path)
        analyzer.visit(tree)
        analysis.imports = analyzer.imports
        analysis.total_imports = len(analysis.imports)
        
        # Categorize imports
        for imp in analysis.imports:
            if imp.is_legitimate:
                analysis.imports_at_top.append(imp)
                analysis.imports_to_keep.append(imp)
            else:
                analysis.imports_to_move.append(imp)
                if "function" in imp.location:
                    analysis.imports_in_functions += 1
                elif "class" in imp.location or "method" in imp.location:
                    analysis.imports_in_classes += 1
    
    except Exception as e:
        analysis.errors.append(f"Error analyzing file: {e}")
    
    return analysis


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Comprehensive import analysis for backend codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "path",
        nargs="?",
        default="app",
        help="Path to analyze (default: app)"
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
            if not any(str(f).replace('\\', '/').match(pattern) for pattern in exclude_patterns)
        ]
    
    # Exclude __pycache__ and .pyc files
    files = [f for f in files if '__pycache__' not in str(f) and not f.name.endswith('.pyc')]
    
    # Analyze files
    analyses = []
    for file_path in sorted(files):
        analysis = analyze_file(file_path)
        analyses.append(analysis)
    
    # Generate summary statistics
    total_files = len(analyses)
    files_with_issues = [a for a in analyses if a.imports_to_move]
    total_imports_to_move = sum(len(a.imports_to_move) for a in analyses)
    total_errors = sum(len(a.errors) for a in analyses)
    
    if args.json:
        output = {
            "summary": {
                "total_files": total_files,
                "files_with_issues": len(files_with_issues),
                "total_imports_to_move": total_imports_to_move,
                "total_errors": total_errors
            },
            "files": [
                {
                    "file_path": a.file_path,
                    "total_imports": a.total_imports,
                    "imports_at_top": len(a.imports_at_top),
                    "imports_to_move": len(a.imports_to_move),
                    "imports_in_functions": a.imports_in_functions,
                    "imports_in_classes": a.imports_in_classes,
                    "errors": a.errors,
                    "imports_to_move_details": [
                        {
                            "line": imp.line,
                            "column": imp.column,
                            "location": imp.location,
                            "scope": imp.scope,
                            "import_type": imp.import_type,
                            "module": imp.module,
                            "names": imp.names,
                            "alias": imp.alias,
                            "reason": imp.reason,
                            "code_context": imp.code_context
                        }
                        for imp in a.imports_to_move
                    ]
                }
                for a in analyses if a.imports_to_move or a.errors
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        # Print summary
        print(f"\n{'='*80}")
        print("Import Analysis Summary")
        print(f"{'='*80}")
        print(f"Total files analyzed: {total_files}")
        print(f"Files with imports to move: {len(files_with_issues)}")
        print(f"Total imports to move: {total_imports_to_move}")
        if total_errors > 0:
            print(f"Total errors: {total_errors}")
        print(f"{'='*80}\n")
        
        if files_with_issues:
            print("Files with imports to move:")
            print("-" * 80)
            for analysis in files_with_issues:
                print(f"\n{analysis.file_path}")
                print(f"  Total imports: {analysis.total_imports}")
                print(f"  Imports to move: {len(analysis.imports_to_move)}")
                print(f"  Imports in functions: {analysis.imports_in_functions}")
                print(f"  Imports in classes: {analysis.imports_in_classes}")
                if analysis.errors:
                    print(f"  Errors: {', '.join(analysis.errors)}")
                print(f"  Details:")
                for imp in analysis.imports_to_move:
                    module_str = imp.module
                    if imp.names:
                        names_str = ", ".join(imp.names[:3])
                        if len(imp.names) > 3:
                            names_str += f", ... ({len(imp.names)} total)"
                        module_str = f"{imp.module}.{names_str}"
                    print(f"    Line {imp.line}: {imp.import_type} {module_str}")
                    print(f"      Location: {imp.location} ({imp.scope})")
                    print(f"      Reason: {imp.reason}")
    
    # Exit with appropriate code
    sys.exit(0 if total_imports_to_move == 0 and total_errors == 0 else 1)


if __name__ == "__main__":
    main()

