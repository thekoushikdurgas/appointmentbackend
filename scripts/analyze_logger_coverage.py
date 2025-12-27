#!/usr/bin/env python3
"""
Analyze codebase for logger statement coverage.
Identifies files that need logger initialization.
"""

import ast
import sys
from pathlib import Path
from typing import List, Optional, Set


class LoggerAnalyzer(ast.NodeVisitor):
    """AST visitor to find logger initialization statements."""
    
    def __init__(self):
        self.has_logger = False
        self.logger_patterns = {
            "get_logger",
            "logging.getLogger",
            "logger =",
        }
        self.imports_logger = False
        self.uses_logger_utils = False
        
    def visit_Import(self, node: ast.Import):
        """Check for logging imports."""
        for alias in node.names:
            if alias.name == "logging":
                self.imports_logger = True
            if "logger" in alias.name.lower():
                self.uses_logger_utils = True
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check for logger utility imports."""
        if node.module and "logger" in node.module.lower():
            self.uses_logger_utils = True
        if node.module == "app.utils.logger":
            self.uses_logger_utils = True
        for alias in node.names:
            if "logger" in alias.name.lower() or alias.name == "get_logger":
                self.uses_logger_utils = True
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Check for logger assignment."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "logger":
                self.has_logger = True
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Check for get_logger calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "get_logger":
            self.has_logger = True
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Attribute):
                if (isinstance(node.func.value.value, ast.Name) and 
                    node.func.value.value.id == "logging" and
                    node.func.value.attr == "getLogger"):
                    self.has_logger = True
            elif isinstance(node.func.value, ast.Name):
                if node.func.value.id == "logging" and node.func.attr == "getLogger":
                    self.has_logger = True
        self.generic_visit(node)


def analyze_file(file_path: Path) -> dict:
    """Analyze a Python file for logger usage."""
    result = {
        "file_path": str(file_path),
        "has_logger": False,
        "imports_logging": False,
        "uses_logger_utils": False,
        "needs_logger": True,
        "errors": []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            result["errors"].append(f"Syntax error: {e}")
            return result
        
        analyzer = LoggerAnalyzer()
        analyzer.visit(tree)
        
        result["has_logger"] = analyzer.has_logger
        result["imports_logging"] = analyzer.imports_logger
        result["uses_logger_utils"] = analyzer.uses_logger_utils
        
        # Files that don't need loggers:
        # - __init__.py files (unless they have significant logic)
        # - Test files (usually don't need loggers, they use pytest logging)
        # - Schema/model files (data structures)
        # - Config files (simple configuration)
        file_name = file_path.name
        
        if file_name == "__init__.py":
            # Check if __init__.py has actual code or just imports
            has_significant_code = any(
                isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                for node in ast.walk(tree)
                if hasattr(node, 'body') and node.body
            )
            result["needs_logger"] = has_significant_code
        elif file_name.startswith("test_") or "tests" in str(file_path):
            result["needs_logger"] = False  # Tests use pytest's logging
        elif "schemas" in str(file_path) or "models" in str(file_path):
            # Schema/model files typically don't need loggers unless they have business logic
            has_business_logic = any(
                isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                for node in ast.walk(tree)
            )
            result["needs_logger"] = has_business_logic and not file_name.startswith("__")
        else:
            # Service, repository, endpoint, utility files should have loggers
            result["needs_logger"] = True
    
    except Exception as e:
        result["errors"].append(f"Error analyzing file: {e}")
    
    return result


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze logger coverage in backend codebase"
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
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.py"))
    
    # Exclude __pycache__
    files = [f for f in files if "__pycache__" not in str(f)]
    
    analyses = []
    for file_path in sorted(files):
        analysis = analyze_file(file_path)
        analyses.append(analysis)
    
    # Categorize files
    files_with_logger = [a for a in analyses if a["has_logger"]]
    files_needing_logger = [a for a in analyses if a["needs_logger"] and not a["has_logger"]]
    files_with_errors = [a for a in analyses if a["errors"]]
    
    if args.json:
        import json
        output = {
            "summary": {
                "total_files": len(analyses),
                "files_with_logger": len(files_with_logger),
                "files_needing_logger": len(files_needing_logger),
                "files_with_errors": len(files_with_errors)
            },
            "files_needing_logger": [
                {
                    "file_path": a["file_path"],
                    "imports_logging": a["imports_logging"],
                    "uses_logger_utils": a["uses_logger_utils"],
                    "errors": a["errors"]
                }
                for a in files_needing_logger
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*80}")
        print("Logger Coverage Analysis")
        print(f"{'='*80}")
        print(f"Total files analyzed: {len(analyses)}")
        print(f"Files with logger: {len(files_with_logger)}")
        print(f"Files needing logger: {len(files_needing_logger)}")
        print(f"Files with errors: {len(files_with_errors)}")
        print(f"{'='*80}\n")
        
        if files_needing_logger:
            print("Files needing logger initialization:")
            print("-" * 80)
            for analysis in files_needing_logger:
                print(f"\n{analysis['file_path']}")
                if analysis['errors']:
                    print(f"  Errors: {', '.join(analysis['errors'])}")
    
    sys.exit(0 if len(files_needing_logger) == 0 else 1)


if __name__ == "__main__":
    main()

