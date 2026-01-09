# src/db/create_tables.py (SIMPLIFIED VERSION)
import psycopg2
from connect import get_db_connection


def create_tables():
    connection = None
    cursor = None
    try:
        # Use the same connection as everywhere else
        connection = get_db_connection()
        cursor = connection.cursor()
        

        # CREATE ONLY THE TABLES YOU NEED
        print("Creating skills_analysis table...")
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
        
        print("Creating detailed_skills table...")
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
        
        cursor.execute(create_skills_analysis_table)
        cursor.execute(create_detailed_skills_table)

        # Create indexes for better performance
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

        # Commit all changes
        connection.commit()
        print("✅ Tables created successfully!")
        print("   - skills_analysis")
        print("   - detailed_skills")

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