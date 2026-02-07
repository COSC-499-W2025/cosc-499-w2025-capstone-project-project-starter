"""
Database migration script to convert user_preferences table from user_id to user_name.

This script:
1. Backs up existing user_preferences data
2. Drops the old table
3. Creates new table with user_name as foreign key
4. Migrates data if possible (user_id=1 can be mapped to a specific user)

Usage:
    python developTools/migrate_user_preferences_to_username.py [--default-user <username>]
    
Options:
    --default-user: Username to assign to user_id=1 records (default: first user in database)
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config.db_config import get_connection


def backup_old_data(cursor):
    """Backup existing user_preferences data."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'user_preferences'
        );
    """)
    table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        print("[OK] No existing user_preferences table to backup")
        return None
    
    cursor.execute("SELECT * FROM user_preferences;")
    backup = cursor.fetchall()
    
    if backup:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_preferences'
            ORDER BY ordinal_position;
        """)
        columns = [row[0] for row in cursor.fetchall()]
        print(f"[OK] Backed up {len(backup)} record(s) from old table")
        print(f"  Columns: {columns}")
        return {'data': backup, 'columns': columns}
    
    print("[OK] No data to backup")
    return None


def get_default_user(cursor, specified_user=None):
    """Get the username to use for migrating user_id=1 data."""
    if specified_user:
        cursor.execute("SELECT user_name FROM user_informations WHERE user_name = %s;", (specified_user,))
        result = cursor.fetchone()
        if result:
            print(f"[OK] Using specified user: {specified_user}")
            return specified_user
        else:
            print(f"[WARNING] Specified user '{specified_user}' not found")
    
    # Get first user from database
    cursor.execute("SELECT user_name FROM user_informations ORDER BY user_id LIMIT 1;")
    result = cursor.fetchone()
    if result:
        username = result[0]
        print(f"[OK] Using first database user: {username}")
        return username
    
    print("[WARNING] No users found in user_informations table")
    return None


def drop_old_table(cursor):
    """Drop the old user_preferences table."""
    cursor.execute("DROP TABLE IF EXISTS user_preferences CASCADE;")
    print("[OK] Dropped old user_preferences table")


def create_new_table(cursor):
    """Create new user_preferences table with user_name foreign key."""
    cursor.execute("""
        CREATE TABLE user_preferences (
            user_name VARCHAR(255) PRIMARY KEY,
            consent BOOLEAN DEFAULT FALSE,
            collaborative BOOLEAN DEFAULT FALSE,
            git_username VARCHAR(255),
            last_updated TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_name) REFERENCES user_informations(user_name) ON DELETE CASCADE
        );
    """)
    print("[OK] Created new user_preferences table with user_name as foreign key")


def migrate_data(cursor, backup, default_user):
    """Migrate data from backup to new table structure."""
    if not backup or not default_user:
        print("[OK] No data to migrate or no default user available")
        return
    
    data = backup['data']
    columns = backup['columns']
    
    # Map old columns to new structure
    for record in data:
        record_dict = dict(zip(columns, record))
        
        # Extract values
        consent = record_dict.get('consent', False)
        collaborative = record_dict.get('collaborative', False)
        git_username = record_dict.get('git_username')
        last_updated = record_dict.get('last_updated', datetime.now())
        
        # Insert with new structure
        cursor.execute("""
            INSERT INTO user_preferences (user_name, consent, collaborative, git_username, last_updated)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_name) DO UPDATE SET
                consent = EXCLUDED.consent,
                collaborative = EXCLUDED.collaborative,
                git_username = EXCLUDED.git_username,
                last_updated = EXCLUDED.last_updated;
        """, (default_user, consent, collaborative, git_username, last_updated))
    
    print(f"[OK] Migrated {len(data)} record(s) to user: {default_user}")


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate user_preferences table to use user_name')
    parser.add_argument('--default-user', type=str, help='Username to assign to user_id=1 records')
    args = parser.parse_args()
    
    print("=" * 60)
    print("User Preferences Table Migration")
    print("From: user_id (integer) to user_name (VARCHAR foreign key)")
    print("=" * 60)
    print()
    
    try:
        with get_connection() as conn, conn.cursor() as cursor:
            # Step 1: Backup old data
            print("[1/5] Backing up existing data...")
            backup = backup_old_data(cursor)
            print()
            
            # Step 2: Determine default user
            print("[2/5] Determining default user for migration...")
            default_user = get_default_user(cursor, args.default_user)
            print()
            
            # Step 3: Drop old table
            print("[3/5] Dropping old table...")
            drop_old_table(cursor)
            print()
            
            # Step 4: Create new table
            print("[4/5] Creating new table structure...")
            create_new_table(cursor)
            print()
            
            # Step 5: Migrate data
            print("[5/5] Migrating data...")
            migrate_data(cursor, backup, default_user)
            print()
            
            # Commit transaction
            conn.commit()
            
            print("=" * 60)
            print("[OK] Migration completed successfully!")
            print("=" * 60)
            print()
            print("Summary:")
            print(f"  - Old table backed up: {'Yes' if backup else 'No'}")
            print(f"  - Records migrated: {len(backup['data']) if backup else 0}")
            print(f"  - Default user: {default_user if default_user else 'N/A'}")
            print()
            print("Next steps:")
            print("  1. Update all code that calls user_preferences functions")
            print("  2. Ensure user_name is passed to all functions")
            print("  3. Test the application thoroughly")
            
    except Exception as e:
        print()
        print("=" * 60)
        print(f"[ERROR] Migration failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
