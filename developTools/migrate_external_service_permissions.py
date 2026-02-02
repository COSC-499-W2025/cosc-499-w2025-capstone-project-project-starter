"""
Migration script to update external_service_permissions table.
Changes user_id column to user_name and adds foreign key constraint.

Usage:
    python developTools/migrate_external_service_permissions.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.db_config import get_connection


def migrate_external_service_permissions():
    """
    Migrate external_service_permissions table from user_id to user_name.
    
    Steps:
    1. Check if table exists
    2. Check if user_name column already exists (migration already done)
    3. If user_id column exists, rename it to user_name
    4. Drop old index and create new one
    5. Add foreign key constraint to user_informations table
    """
    
    print("Starting migration of external_service_permissions table...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.tables 
                        WHERE table_name = 'external_service_permissions'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(" Table does not exist yet. It will be created with the new schema.")
                    return
                
                # Check if user_name column already exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'external_service_permissions' 
                    AND column_name IN ('user_id', 'user_name');
                """)
                columns = [row[0] for row in cursor.fetchall()]
                
                if 'user_name' in columns and 'user_id' not in columns:
                    print(" Migration already completed. Table uses user_name.")
                    return
                
                if 'user_id' not in columns:
                    print(" Warning: Neither user_id nor user_name column found. Table may be corrupted.")
                    return
                
                print("→ Found user_id column. Beginning migration...")
                
                # Step 1: Drop existing index
                print("  - Dropping old index...")
                cursor.execute("""
                    DROP INDEX IF EXISTS idx_service_permissions_user_service;
                """)
                
                # Step 2: Drop existing UNIQUE constraint if it exists
                print("  - Dropping old unique constraint...")
                cursor.execute("""
                    DO $$ 
                    BEGIN
                        IF EXISTS (
                            SELECT 1 
                            FROM information_schema.table_constraints 
                            WHERE constraint_name = 'external_service_permissions_user_id_service_name_key'
                            AND table_name = 'external_service_permissions'
                        ) THEN
                            ALTER TABLE external_service_permissions 
                            DROP CONSTRAINT external_service_permissions_user_id_service_name_key;
                        END IF;
                    END $$;
                """)
                
                # Step 3: Rename user_id column to user_name
                print("  - Renaming user_id to user_name...")
                cursor.execute("""
                    ALTER TABLE external_service_permissions 
                    RENAME COLUMN user_id TO user_name;
                """)
                
                # Step 4: Add new unique constraint
                print("  - Adding new unique constraint...")
                cursor.execute("""
                    ALTER TABLE external_service_permissions 
                    ADD CONSTRAINT external_service_permissions_user_name_service_name_key 
                    UNIQUE (user_name, service_name);
                """)
                
                # Step 5: Create new index
                print("  - Creating new index...")
                cursor.execute("""
                    CREATE INDEX idx_service_permissions_user_service 
                    ON external_service_permissions(user_name, service_name);
                """)
                
                # Step 6: Add foreign key constraint (if user_informations table exists)
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.tables 
                        WHERE table_name = 'user_informations'
                    );
                """)
                user_table_exists = cursor.fetchone()[0]
                
                if user_table_exists:
                    print("  - Adding foreign key constraint to user_informations...")
                    cursor.execute("""
                        ALTER TABLE external_service_permissions 
                        ADD CONSTRAINT fk_external_service_permissions_user 
                        FOREIGN KEY (user_name) 
                        REFERENCES user_informations(user_name) 
                        ON DELETE CASCADE;
                    """)
                else:
                    print(" Warning: user_informations table not found. Skipping foreign key constraint.")
                
                conn.commit()
                print("Migration completed successfully!")
                
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = migrate_external_service_permissions()
    sys.exit(0 if success else 1)
