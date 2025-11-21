#!/usr/bin/env python3
"""
SQL Runner Script

Reads SQL statements from sqlline.sql, executes them against PostgreSQL,
measures execution time, and displays results with proper formatting.
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

# Add parent directory to path to import default module
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from scripts.data.default import get_default
except ImportError:
    print("Error: Could not import default module. Make sure scripts/data/default.py exists.")
    sys.exit(1)

try:
    from tabulate import tabulate
except ImportError:
    print("Warning: tabulate not installed. Install with: pip install tabulate")
    print("Falling back to simple table formatting.")
    tabulate = None


# Configuration
SQL_FILE = Path(__file__).parent / "sqlline.sql"
RESULT_DIR = Path(__file__).parent / "result"
ERROR_DIR = Path(__file__).parent / "error"
SMALL_RESULT_THRESHOLD = 100
SUMMARY_SAMPLE_ROWS = 10


class SQLError:
    """Container for SQL execution errors."""
    def __init__(self, query_num: int, sql: str, error: Exception):
        self.query_num = query_num
        self.sql = sql.strip()[:200]  # First 200 chars
        self.error = error


class SQLRunner:
    """Main SQL runner class."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.errors: List[SQLError] = []
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_time": 0.0,
        }
        # Generate timestamp for file names
        self.timestamp = self._generate_timestamp()
        self.result_file = RESULT_DIR / f"result_{self.timestamp}.txt"
        self.error_file = ERROR_DIR / f"error_{self.timestamp}.txt"
        # Ensure directories exist
        self._ensure_directories()
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp in format hh_mm_ss_dd_mm_yy."""
        now = datetime.now()
        return now.strftime("%H_%M_%S_%d_%m_%y")
    
    def _ensure_directories(self) -> None:
        """Ensure result and error directories exist."""
        RESULT_DIR.mkdir(exist_ok=True)
        ERROR_DIR.mkdir(exist_ok=True)
    
    def setup_database_connection(self) -> None:
        """Set up database connection using config from scripts/data/default.py"""
        try:
            postgres_user = get_default("postgres.user")
            postgres_pass = get_default("postgres.password")
            postgres_host = get_default("postgres.host")
            postgres_port = get_default("postgres.port")
            postgres_db = get_default("postgres.database")
            
            database_url = (
                f"postgresql://{postgres_user}:{postgres_pass}@"
                f"{postgres_host}:{postgres_port}/{postgres_db}"
            )
            
            self.engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            
            print(f"✓ Connected to database: {postgres_host}:{postgres_port}/{postgres_db}")
        except Exception as e:
            print(f"✗ Error connecting to database: {e}")
            sys.exit(1)
    
    def read_sql_file(self) -> str:
        """Read SQL statements from sqlline.sql file."""
        if not SQL_FILE.exists():
            print(f"✗ Error: SQL file not found: {SQL_FILE}")
            sys.exit(1)
        
        try:
            with open(SQL_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"✗ Error reading SQL file: {e}")
            sys.exit(1)
    
    def parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL content by semicolons, handling multi-line statements."""
        statements = []
        
        # Split by semicolons
        parts = sql_content.split(';')
        
        for part in parts:
            # Strip whitespace
            cleaned = part.strip()
            
            # Skip empty statements
            if not cleaned or cleaned.isspace():
                continue
            
            statements.append(cleaned)
        
        return statements
    
    def format_value(self, value: Any) -> str:
        """Format a value for display in table."""
        if value is None:
            return "NULL"
        elif isinstance(value, (datetime,)):
            return str(value)
        elif isinstance(value, (list, dict)):
            return str(value)
        else:
            return str(value)
    
    def format_results_table(self, rows: List[Tuple], headers: List[str]) -> str:
        """Format results as a table."""
        if tabulate:
            # Use tabulate for nice formatting
            formatted_rows = [[self.format_value(val) for val in row] for row in rows]
            return tabulate(formatted_rows, headers=headers, tablefmt="grid")
        else:
            # Fallback simple formatting
            lines = []
            # Header
            header_line = " | ".join(f"{h:20}" for h in headers)
            lines.append(header_line)
            lines.append("-" * len(header_line))
            # Rows
            for row in rows:
                row_line = " | ".join(f"{self.format_value(val):20}" for val in row)
                lines.append(row_line)
            return "\n".join(lines)
    
    def write_result_to_file(self, query_num: int, sql: str, execution_time: float,
                            result: Optional[Any] = None, rowcount: Optional[int] = None,
                            query_type: Optional[str] = None) -> None:
        """Write query result to result file."""
        try:
            with open(self.result_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Query #{query_num}\n")
                if query_type:
                    f.write(f"Query Type: {query_type}\n")
                f.write(f"{'='*80}\n")
                f.write(f"SQL: {sql}\n")
                f.write(f"Execution Time: {execution_time:.4f} seconds\n")
                f.write(f"{'-'*80}\n")
                
                if result is not None:
                    # Query returned result set
                    if isinstance(result, list) and len(result) > 0:
                        rows = result
                        row_count = len(rows)
                        
                        # Get column names from first row keys if it's a dict, or use indices
                        if isinstance(rows[0], dict):
                            headers = list(rows[0].keys())
                            rows_data = [tuple(row.values()) for row in rows]
                        elif isinstance(rows[0], tuple):
                            headers = [f"Column_{i+1}" for i in range(len(rows[0]))]
                            rows_data = rows
                        else:
                            headers = ["Result"]
                            rows_data = [(row,) for row in rows]
                        
                        # Special handling for EXPLAIN queries
                        if query_type == 'EXPLAIN':
                            f.write(f"Query Plan ({row_count} lines):\n\n")
                            # For EXPLAIN, write as text lines
                            for row in rows_data:
                                if isinstance(row, tuple) and len(row) > 0:
                                    f.write(f"{str(row[0])}\n")
                                else:
                                    f.write(f"{str(row)}\n")
                        else:
                            f.write(f"Rows returned: {row_count}\n\n")
                            # Write all rows to file (no threshold for file output)
                            f.write(self.format_results_table(rows_data, headers))
                            f.write("\n")
                    elif isinstance(result, list) and len(result) == 0:
                        f.write("Rows returned: 0 (empty result set)\n")
                    else:
                        f.write(f"Result: {result}\n")
                elif rowcount is not None:
                    # DML query
                    f.write(f"Rows affected: {rowcount}\n")
                else:
                    # DDL or other query type
                    if query_type in ('CREATE', 'DROP', 'ALTER', 'TRUNCATE'):
                        f.write(f"Query executed successfully ({query_type})\n")
                    else:
                        f.write("Query executed successfully\n")
        except Exception as e:
            print(f"Warning: Could not write to result file: {e}")
    
    def write_error_to_file(self, query_num: int, sql: str, error: Exception, execution_time: float) -> None:
        """Write error information to error file."""
        try:
            with open(self.error_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Query #{query_num} - ERROR\n")
                f.write(f"{'='*80}\n")
                f.write(f"SQL: {sql}\n")
                f.write(f"Execution Time: {execution_time:.4f} seconds (failed)\n")
                f.write(f"Error Type: {type(error).__name__}\n")
                f.write(f"Error Message: {str(error)}\n")
        except Exception as e:
            print(f"Warning: Could not write to error file: {e}")
    
    def display_results(self, query_num: int, sql: str, execution_time: float, 
                       result: Optional[Any] = None, rowcount: Optional[int] = None,
                       query_type: Optional[str] = None) -> None:
        """Display query results in appropriate format and write to file."""
        print(f"\n{'='*80}")
        print(f"Query #{query_num}")
        if query_type:
            print(f"Query Type: {query_type}")
        print(f"{'='*80}")
        print(f"SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
        print(f"Execution Time: {execution_time:.4f} seconds")
        print(f"{'-'*80}")
        
        if result is not None:
            # Query returned result set (SELECT, EXPLAIN, SHOW, RETURNING, etc.)
            if isinstance(result, list) and len(result) > 0:
                rows = result
                row_count = len(rows)
                
                # Get column names from first row keys if it's a dict, or use indices
                if isinstance(rows[0], dict):
                    headers = list(rows[0].keys())
                    rows_data = [tuple(row.values()) for row in rows]
                elif isinstance(rows[0], tuple):
                    # Try to get column names from result keys if available
                    # For now, use generic column names
                    if hasattr(result, 'keys'):
                        headers = list(result.keys())
                    else:
                        headers = [f"Column_{i+1}" for i in range(len(rows[0]))]
                    rows_data = rows
                else:
                    headers = ["Result"]
                    rows_data = [(row,) for row in rows]
                
                # Special handling for EXPLAIN queries - show full output
                if query_type == 'EXPLAIN':
                    print(f"Query Plan ({row_count} lines):")
                    print()
                    # For EXPLAIN, format as text lines
                    for row in rows_data:
                        if isinstance(row, tuple) and len(row) > 0:
                            print(str(row[0]))
                        else:
                            print(str(row))
                elif row_count <= SMALL_RESULT_THRESHOLD:
                    # Show full table
                    print(f"Rows returned: {row_count}")
                    print()
                    print(self.format_results_table(rows_data, headers))
                else:
                    # Show summary with sample
                    print(f"Rows returned: {row_count} (showing first {SUMMARY_SAMPLE_ROWS} rows)")
                    print()
                    sample_rows = rows_data[:SUMMARY_SAMPLE_ROWS]
                    print(self.format_results_table(sample_rows, headers))
                    print(f"\n... ({row_count - SUMMARY_SAMPLE_ROWS} more rows)")
            elif isinstance(result, list) and len(result) == 0:
                print("Rows returned: 0 (empty result set)")
            else:
                print(f"Result: {result}")
        elif rowcount is not None:
            # DML query (INSERT, UPDATE, DELETE) - show rows affected
            print(f"Rows affected: {rowcount}")
        else:
            # DDL or other query type
            if query_type in ('CREATE', 'DROP', 'ALTER', 'TRUNCATE'):
                print(f"Query executed successfully ({query_type})")
            else:
                print("Query executed successfully")
        
        # Write to result file
        self.write_result_to_file(query_num, sql, execution_time, result, rowcount, query_type)
    
    def _detect_query_type(self, sql: str) -> str:
        """Detect the type of SQL query."""
        sql_upper = sql.strip().upper()
        
        # Remove leading comments and whitespace
        sql_clean = sql_upper.lstrip()
        
        # Check for query types that return result sets
        if sql_clean.startswith('SELECT') or sql_clean.startswith('WITH'):
            return 'SELECT'
        elif sql_clean.startswith('EXPLAIN'):
            return 'EXPLAIN'
        elif sql_clean.startswith('SHOW') or sql_clean.startswith('DESCRIBE') or sql_clean.startswith('DESC'):
            return 'SHOW'
        elif sql_clean.startswith('INSERT'):
            return 'INSERT'
        elif sql_clean.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_clean.startswith('DELETE'):
            return 'DELETE'
        elif sql_clean.startswith('CREATE'):
            return 'CREATE'
        elif sql_clean.startswith('DROP'):
            return 'DROP'
        elif sql_clean.startswith('ALTER'):
            return 'ALTER'
        elif sql_clean.startswith('TRUNCATE'):
            return 'TRUNCATE'
        elif sql_clean.startswith('GRANT') or sql_clean.startswith('REVOKE'):
            return 'PERMISSION'
        else:
            return 'OTHER'
    
    def _has_returning_clause(self, sql: str) -> bool:
        """Check if query has RETURNING clause."""
        sql_upper = sql.upper()
        # Look for RETURNING keyword that's not in a comment or string
        return 'RETURNING' in sql_upper
    
    def execute_query(self, query_num: int, sql: str) -> Tuple[float, Optional[Any], Optional[int], Optional[str]]:
        """Execute a single SQL query and return execution time, results, rowcount, and query type."""
        start_time = time.perf_counter()
        result = None
        rowcount = None
        query_type = self._detect_query_type(sql)
        has_returning = self._has_returning_clause(sql)
        
        try:
            with self.engine.connect() as conn:
                # Execute the query
                result_proxy = conn.execute(text(sql))
                
                # Try to fetch results - many query types return result sets
                # (SELECT, EXPLAIN, SHOW, INSERT/UPDATE/DELETE with RETURNING, etc.)
                try:
                    # Try to get column names first (this will fail if query doesn't return rows)
                    columns = list(result_proxy.keys())
                    rows = result_proxy.fetchall()
                    
                    # Convert to list of dicts for better formatting
                    if columns and rows:
                        result = [dict(zip(columns, row)) for row in rows]
                    elif rows:
                        # Fallback to tuples if no column names
                        result = rows
                    else:
                        result = []
                except (AttributeError, Exception):
                    # Some queries don't return rows (pure DML/DDL without RETURNING)
                    # AttributeError: result proxy doesn't have keys() method
                    # Other exceptions: query doesn't support fetching
                    result = None
                
                # Get rowcount for DML queries (INSERT, UPDATE, DELETE)
                # Note: rowcount is -1 for DDL and queries that don't affect rows
                if query_type in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
                    rowcount = result_proxy.rowcount
                    # If rowcount is -1, it might be a DDL-like operation, set to None
                    if rowcount == -1:
                        rowcount = None
                
                # Commit for DML/DDL queries
                if query_type in ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE'):
                    conn.commit()
                
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                return execution_time, result, rowcount, query_type
                
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Store error
            self.errors.append(SQLError(query_num, sql, e))
            self.stats["failed_queries"] += 1
            
            print(f"\n{'='*80}")
            print(f"Query #{query_num} - ERROR")
            print(f"{'='*80}")
            print(f"SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
            print(f"Execution Time: {execution_time:.4f} seconds (failed)")
            print(f"Error: {type(e).__name__}: {str(e)}")
            
            # Write error to file
            self.write_error_to_file(query_num, sql, e, execution_time)
            
            return execution_time, None, None, query_type
    
    def run(self) -> None:
        """Main execution flow."""
        print("SQL Runner")
        print("="*80)
        
        # Initialize result file with header
        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                f.write("SQL Runner - Query Results\n")
                f.write("="*80 + "\n")
                f.write(f"Execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"SQL file: {SQL_FILE}\n")
                f.write("="*80 + "\n")
        except Exception as e:
            print(f"Warning: Could not initialize result file: {e}")
        
        # Initialize error file with header
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                f.write("SQL Runner - Error Report\n")
                f.write("="*80 + "\n")
                f.write(f"Execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"SQL file: {SQL_FILE}\n")
                f.write("="*80 + "\n")
        except Exception as e:
            print(f"Warning: Could not initialize error file: {e}")
        
        # Setup database connection
        self.setup_database_connection()
        
        # Read and parse SQL file
        print(f"\nReading SQL from: {SQL_FILE}")
        sql_content = self.read_sql_file()
        statements = self.parse_sql_statements(sql_content)
        
        if not statements:
            print("✗ No SQL statements found in sqlline.sql")
            sys.exit(1)
        
        self.stats["total_queries"] = len(statements)
        print(f"✓ Found {len(statements)} SQL statement(s) to execute\n")
        
        # Execute each statement
        for idx, sql in enumerate(statements, 1):
            execution_time, result, rowcount, query_type = self.execute_query(idx, sql)
            
            # Update stats
            self.stats["total_time"] += execution_time
            
            # Display results if successful (not in errors list)
            query_failed = any(err.query_num == idx for err in self.errors)
            if not query_failed:
                self.stats["successful_queries"] += 1
                self.display_results(idx, sql, execution_time, result, rowcount, query_type)
        
        # Display summary
        print(f"\n{'='*80}")
        print("EXECUTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total queries: {self.stats['total_queries']}")
        print(f"Successful: {self.stats['successful_queries']}")
        print(f"Failed: {self.stats['failed_queries']}")
        print(f"Total execution time: {self.stats['total_time']:.4f} seconds")
        if self.stats['total_queries'] > 0:
            avg_time = self.stats['total_time'] / self.stats['total_queries']
            print(f"Average execution time: {avg_time:.4f} seconds")
        
        # Write summary to result file
        try:
            with open(self.result_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*80}\n")
                f.write("EXECUTION SUMMARY\n")
                f.write(f"{'='*80}\n")
                f.write(f"Total queries: {self.stats['total_queries']}\n")
                f.write(f"Successful: {self.stats['successful_queries']}\n")
                f.write(f"Failed: {self.stats['failed_queries']}\n")
                f.write(f"Total execution time: {self.stats['total_time']:.4f} seconds\n")
                if self.stats['total_queries'] > 0:
                    avg_time = self.stats['total_time'] / self.stats['total_queries']
                    f.write(f"Average execution time: {avg_time:.4f} seconds\n")
                f.write(f"Execution completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            print(f"Warning: Could not write summary to result file: {e}")
        
        # Display errors if any
        if self.errors:
            print(f"\n{'='*80}")
            print("ERRORS REPORT")
            print(f"{'='*80}")
            for error in self.errors:
                print(f"\nQuery #{error.query_num}:")
                print(f"  SQL: {error.sql}")
                print(f"  Error: {type(error.error).__name__}: {str(error.error)}")
            
            # Write errors summary to error file
            try:
                with open(self.error_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n{'='*80}\n")
                    f.write("ERRORS SUMMARY\n")
                    f.write(f"{'='*80}\n")
                    f.write(f"Total errors: {len(self.errors)}\n\n")
                    for error in self.errors:
                        f.write(f"Query #{error.query_num}:\n")
                        f.write(f"  SQL: {error.sql}\n")
                        f.write(f"  Error: {type(error.error).__name__}: {str(error.error)}\n\n")
            except Exception as e:
                print(f"Warning: Could not write errors summary to file: {e}")
        
        # Print file locations
        print(f"\n{'='*80}")
        print("OUTPUT FILES")
        print(f"{'='*80}")
        print(f"Results saved to: {self.result_file}")
        if self.errors:
            print(f"Errors saved to: {self.error_file}")
        print(f"{'='*80}")


def main():
    """Entry point."""
    runner = SQLRunner()
    runner.run()


if __name__ == "__main__":
    main()

