# src/db/create_tables.py
import psycopg2
from connect import get_db_connection  # Use the same connection function


def create_tables():
    connection = None
    cursor = None
    try:
        # Use the same connection as everywhere else
        connection = get_db_connection()
        cursor = connection.cursor()

        # Drop existing tables in correct order (to avoid foreign key constraints)
        cursor.execute("DROP TABLE IF EXISTS artifacts CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS detailed_skills CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS skills_analysis CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS category CASCADE;")

        # Create users table (keep if you need it)
        create_users_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        '''

        # Create category table (keep if you need it)
        create_category_table = '''
        CREATE TABLE IF NOT EXISTS category (
            id SERIAL PRIMARY KEY,
            main_category VARCHAR(100) UNIQUE NOT NULL
        );
        '''

        # Create artifacts table (keep if you need it)
        create_artifacts_table = '''
        CREATE TABLE IF NOT EXISTS artifacts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            category_id INTEGER REFERENCES category(id) ON DELETE SET NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_type VARCHAR(50)
        );
        '''

        # CREATE THE SKILLS TABLES THAT YOUR skills_repository.py EXPECTS
        create_skills_analysis_table = '''
        CREATE TABLE IF NOT EXISTS skills_analysis (
            id SERIAL PRIMARY KEY,
            project_id VARCHAR(255) NOT NULL,
            analysis_type VARCHAR(100) NOT NULL,
            source VARCHAR(50) NOT NULL,
            skills_data JSONB NOT NULL,
            file_path TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''

        create_detailed_skills_table = '''
        CREATE TABLE IF NOT EXISTS detailed_skills (
            id SERIAL PRIMARY KEY,
            project_id VARCHAR(255) NOT NULL,
            skill_name VARCHAR(100) NOT NULL,
            source VARCHAR(50) NOT NULL,
            confidence FLOAT DEFAULT 1.0,
            file_path TEXT,
            context TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''

        # Execute all table creation
        print("Creating users table...")
        cursor.execute(create_users_table)
        
        print("Creating category table...")
        cursor.execute(create_category_table)
        
        print("Creating artifacts table...")
        cursor.execute(create_artifacts_table)
        
        print("Creating skills_analysis table...")
        cursor.execute(create_skills_analysis_table)
        
        print("Creating detailed_skills table...")
        cursor.execute(create_detailed_skills_table)

        # Create indexes for skills tables
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_analysis_project 
            ON skills_analysis(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_analysis_source 
            ON skills_analysis(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detailed_skills_project 
            ON detailed_skills(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detailed_skills_name 
            ON detailed_skills(skill_name)
        """)

        # Insert 10 default categories (only if empty) - OPTIONAL
        cursor.execute("SELECT COUNT(*) FROM category;")
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.executemany(
                "INSERT INTO category (main_category) VALUES (%s);",
                [
                   ("General Cat 1",), 
                   ("General Cat 2",), 
                   ("General Cat 3",), 
                   ("General Cat 4",), 
                   ("General Cat 5",), 
                   ("General Cat 6",), 
                   ("General Cat 7",), 
                   ("General Cat 8",), 
                   ("General Cat 9",), 
                   ("General Cat 10",)
                ]
            )
            print("Inserted 10 default categories into 'category' table.")

        # Commit all changes
        connection.commit()
        print("✅ All tables created successfully!")
        print("   - users")
        print("   - category") 
        print("   - artifacts")
        print("   - skills_analysis (for your skills storage)")
        print("   - detailed_skills (for your skills storage)")

    except Exception as e:
        print("❌ Failed to create tables:", e)
        if connection:
            connection.rollback()
        raise e

    finally:
        try:
            if cursor:
                cursor.close()
        except NameError:
            pass
        try:
            if connection:
                connection.close()
        except NameError:
            pass


if __name__ == "__main__":
    create_tables()