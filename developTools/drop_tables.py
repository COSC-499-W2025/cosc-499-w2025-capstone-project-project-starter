"""
Database Table Management Tool - Development Utility Script

This script detects all data tables in the local database and allows developers to selectively drop tables.
Note: This tool is for development environments only. Do NOT use in production!
"""

import os
import sys
import random
import string
from typing import List, Tuple

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.db_config import get_connection


def check_environment_safety() -> bool:
    """
    Verify that the script is running in a safe development environment.
    This includes multiple safety checks to prevent accidental production use.
    """
    print("=" * 80)
    print("ENVIRONMENT SAFETY CHECKS".center(80))
    print("=" * 80)
    
    # Check 1: Ensure running in interactive terminal (not automated script)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("\nX ERROR: This script must be run in an interactive terminal.")
        print("  It cannot be executed in automated scripts or pipelines.")
        return False
    print("✓ Check 1: Running in interactive terminal")
    
    # Check 2: Verify environment variable indicates development environment
    env_mode = os.getenv("ENVIRONMENT", "").lower()
    postgres_host = os.getenv("POSTGRES_HOST", "").lower()
    
    # Reject if explicitly production
    if env_mode in ["production", "prod", "live"]:
        print("\nX ERROR: ENVIRONMENT is set to PRODUCTION.")
        print("  This script is FORBIDDEN in production environments!")
        return False
    
    # Reject if production database host detected
    production_indicators = ["prod", "production", "live", "aws", "azure", "cloud"]
    if any(indicator in postgres_host for indicator in production_indicators):
        print("\nX ERROR: Production database host detected.")
        print(f"  POSTGRES_HOST contains production indicator: {postgres_host}")
        return False
    
    # Warn if not explicitly development
    if env_mode not in ["development", "dev", "local"]:
        print(f"\n  WARNING: ENVIRONMENT is '{env_mode}' (not explicitly 'development').")
        print("  This script should only run in development environments.")
        confirm = input("  Are you SURE you're in a development environment? (type 'I AM SURE'): ")
        if confirm != "I AM SURE":
            print("\nX Safety check failed.")
            return False
    else:
        print(f"V Check 2: Environment is '{env_mode}' (development mode)")
    
    # Check 3: Database host safety check
    if postgres_host in ["localhost", "127.0.0.1", "db", ""]:
        print(f"V Check 3: Database host is '{postgres_host or 'localhost'}' (local)")
    else:
        print(f"\n  WARNING: Database host is '{postgres_host}' (non-standard local host).")
        confirm = input("  Confirm this is a DEVELOPMENT database (type 'DEV DATABASE'): ")
        if confirm != "DEV DATABASE":
            print("\nX Safety check failed.")
            return False
    
    # Check 4: Generate random confirmation code
    confirmation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    print(f"\nV All automated checks passed.")
    print("\n" + "=" * 80)
    print("MANUAL CONFIRMATION REQUIRED".center(80))
    print("=" * 80)
    print(f"\nTo proceed, type this confirmation code: {confirmation_code}")
    user_input = input("Confirmation code: ").strip()
    
    if user_input != confirmation_code:
        print("\nX Incorrect confirmation code. Aborting.")
        return False
    
    print("\nV Confirmation code accepted.\n")
    return True


class TableManager:
    """Database table manager"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self) -> bool:
        """Connect to the database"""
        try:
            self.conn = get_connection()
            if self.conn:
                self.cursor = self.conn.cursor()
                print("V Database connection successful!\n")
                return True
            else:
                print("X Database connection failed!")
                return False
        except Exception as e:
            print(f"X Error connecting to database: {e}")
            return False
    
    def get_all_tables(self) -> List[Tuple[str, str]]:
        """Get all user-created tables in the database"""
        try:
            query = """
                SELECT 
                    schemaname,
                    tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename;
            """
            self.cursor.execute(query)
            tables = self.cursor.fetchall()
            return tables
        except Exception as e:
            print(f"X Error getting table list: {e}")
            return []
    
    def get_table_info(self, schema: str, table: str) -> dict:
        """Get detailed information about a table"""
        try:
            # Get row count
            count_query = f'SELECT COUNT(*) FROM "{schema}"."{table}";'
            self.cursor.execute(count_query)
            row_count = self.cursor.fetchone()[0]
            
            # Get column count
            columns_query = """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s;
            """
            self.cursor.execute(columns_query, (schema, table))
            column_count = self.cursor.fetchone()[0]
            
            return {
                'rows': row_count,
                'columns': column_count
            }
        except Exception as e:
            return {
                'rows': 'Unknown',
                'columns': 'Unknown',
                'error': str(e)
            }
    
    def drop_table(self, schema: str, table: str, cascade: bool = False) -> bool:
        """Drop the specified table"""
        try:
            cascade_clause = " CASCADE" if cascade else ""
            query = f'DROP TABLE "{schema}"."{table}"{cascade_clause};'
            self.cursor.execute(query)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"  X Drop failed: {e}")
            self.conn.rollback()
            return False
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def display_tables(tables: List[Tuple[str, str]], manager: TableManager):
    """Display all tables and their information"""
    if not tables:
        print("No user-created tables found in the database.")
        return
    
    print(f"Found {len(tables)} data table(s):\n")
    print("=" * 80)
    
    for idx, (schema, table) in enumerate(tables, 1):
        info = manager.get_table_info(schema, table)
        print(f"{idx}. {schema}.{table}")
        print(f"   - Rows: {info['rows']}")
        print(f"   - Columns: {info['columns']}")
        if 'error' in info:
            print(f"   - Note: {info['error']}")
        print("-" * 80)


def get_user_choice(max_choice: int) -> str:
    """Get user choice"""
    print("\nPlease select an option:")
    print("  [a] Drop all tables")
    print("  [s] Select specific tables (enter table numbers separated by commas, e.g.: 1,3,5)")
    print("  [q] Quit without making any changes")
    
    choice = input("\nYour choice: ").strip().lower()
    return choice


def confirm_deletion(tables_to_delete: List[Tuple[str, str]]) -> bool:
    """Confirm deletion operation"""
    print("\n" + "=" * 80)
    print("WARNING! The following tables will be permanently deleted:")
    print("=" * 80)
    
    for schema, table in tables_to_delete:
        print(f"  - {schema}.{table}")
    
    print("\nThis operation is irreversible! All data will be permanently lost!")
    
    confirm = input("\nConfirm deletion? Type 'YES' to continue, any other input will cancel: ").strip()
    return confirm == "YES"


def main():
    """Main function"""
    print("=" * 80)
    print("Database Table Management Tool".center(80))
    print("=" * 80)
    print("\n WARNING: This tool is for development environments only!")
    print(" Dropping tables will permanently delete all data - this cannot be undone!\n")    
    # Run environment safety checks first
    if not check_environment_safety():
        print("\n" + "=" * 80)
        print("Script execution blocked for safety reasons.")
        print("=" * 80)
        sys.exit(1)    
    # Connect to database
    manager = TableManager()
    if not manager.connect():
        return
    
    try:
        # Get all tables
        tables = manager.get_all_tables()
        
        if not tables:
            print("No user-created tables found in the database.")
            return
        
        # Display table information
        display_tables(tables, manager)
        
        # Get user choice
        choice = get_user_choice(len(tables))
        
        tables_to_delete = []
        
        if choice == 'q':
            print("\nOperation cancelled.")
            return
        elif choice == 'a':
            # Drop all tables
            tables_to_delete = tables
        elif choice == 's':
            # Select specific tables
            indices_input = input("Enter table numbers to drop (comma-separated): ").strip()
            try:
                indices = [int(x.strip()) for x in indices_input.split(',')]
                for idx in indices:
                    if 1 <= idx <= len(tables):
                        tables_to_delete.append(tables[idx - 1])
                    else:
                        print(f"Warning: Number {idx} is out of range, ignored.")
            except ValueError:
                print("X Invalid input format!")
                return
        else:
            print("X Invalid choice!")
            return
        
        if not tables_to_delete:
            print("\nNo tables selected for deletion.")
            return
        
        # Confirm deletion
        if not confirm_deletion(tables_to_delete):
            print("\nDeletion cancelled.")
            return
        
        # Ask about CASCADE option
        cascade_input = input("\nUse CASCADE when dropping (will also drop dependent objects)? [y/N]: ").strip().lower()
        use_cascade = cascade_input == 'y'
        
        # Execute deletion
        print("\nStarting to drop tables...")
        print("=" * 80)
        
        success_count = 0
        fail_count = 0
        
        for schema, table in tables_to_delete:
            print(f"Dropping {schema}.{table}...", end=" ")
            if manager.drop_table(schema, table, use_cascade):
                print("V Success")
                success_count += 1
            else:
                fail_count += 1
        
        print("=" * 80)
        print(f"\nDeletion complete! Success: {success_count}, Failed: {fail_count}")
        
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nX Error occurred: {e}")
    finally:
        manager.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
