"""
Resume builder tables and init (team-3 style: multiple named resumes per user,
with RESUME, RESUME_PROJECT, RESUME_SKILLS).
PostgreSQL; project_id = uploaded_files.id.
"""
from config.db_config import with_db_cursor


def init_resume_builder_tables():
    """Create resumes, resume_projects, resume_skills tables if they don't exist."""
    with with_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                user_name VARCHAR(255) NOT NULL,
                name VARCHAR(500) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_resumes_user_name ON resumes(user_name);
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_projects (
                resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
                project_id INTEGER NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
                display_order INTEGER NOT NULL DEFAULT 1,
                project_name VARCHAR(500),
                start_date VARCHAR(50),
                end_date VARCHAR(50),
                skills JSONB,
                bullets JSONB,
                PRIMARY KEY (resume_id, project_id)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_skills (
                resume_id INTEGER PRIMARY KEY REFERENCES resumes(id) ON DELETE CASCADE,
                skills JSONB NOT NULL DEFAULT '[]'::jsonb,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
