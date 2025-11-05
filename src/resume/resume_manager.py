from datetime import datetime
from config.db_config import with_db_cursor
from analysis.project_ranking import calculate_project_score
from analysis.key_metrics import analyze_project_from_db
import json


class ResumeManager:
    """Manages resume data model and storage operations."""
    
    @staticmethod
    def init_resume_tables():
        """Create resume tables if they don't exist."""
        try:
            with with_db_cursor() as cursor:
                # Table for user-aggregated resumes
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS generated_resumes (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL UNIQUE,
                        resume_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Table for project-specific resume items
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_resumes (
                        id SERIAL PRIMARY KEY,
                        project_id INTEGER NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
                        user_id VARCHAR(255) NOT NULL,
                        resume_item_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(project_id, user_id)
                    );
                """)
                
                # Index for faster retrieval
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_project_resumes_user_id 
                    ON project_resumes(user_id);
                """)
            
            print("✓ Resume tables initialized successfully")
            return True
            
        except Exception as e:
            print(f"✗ Error initializing resume tables: {e}")
            return False
    
    @staticmethod
    def store_project_resume(project_id, user_id, resume_item_data):
        """
        Store or update a project-specific resume item.
        
        Args:
            project_id (int): ID of the uploaded project
            user_id (str): User identifier
            resume_item_data (dict): Resume data for the project
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO project_resumes (project_id, user_id, resume_item_data)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (project_id, user_id)
                    DO UPDATE SET 
                        resume_item_data = EXCLUDED.resume_item_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (project_id, user_id, json.dumps(resume_item_data)))
            
            return True
            
        except Exception as e:
            print(f"✗ Error storing project resume: {e}")
            return False
    
    @staticmethod
    def get_project_resume(project_id, user_id):
        """
        Retrieve a project-specific resume item.
        
        Args:
            project_id (int): ID of the uploaded project
            user_id (str): User identifier
            
        Returns:
            dict: Resume item data or None if not found
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT resume_item_data, created_at, updated_at
                    FROM project_resumes
                    WHERE project_id = %s AND user_id = %s
                """, (project_id, user_id))
                
                result = cursor.fetchone()
                
            if result:
                return {
                    'resume_item_data': result[0],
                    'created_at': result[1],
                    'updated_at': result[2]
                }
            return None
            
        except Exception as e:
            print(f"✗ Error retrieving project resume: {e}")
            return None
    
    @staticmethod
    def get_all_project_resumes(user_id):
        """
        Retrieve all project-specific resume items for a user.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            list: List of resume items or empty list if none found
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, project_id, resume_item_data, created_at, updated_at
                    FROM project_resumes
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                """, (user_id,))
                
                results = cursor.fetchall()
            
            resumes = []
            for row in results:
                resumes.append({
                    'id': row[0],
                    'project_id': row[1],
                    'resume_item_data': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            
            return resumes
            
        except Exception as e:
            print(f"✗ Error retrieving project resumes: {e}")
            return []
    
    @staticmethod
    def store_user_resume(user_id, resume_data):
        """
        Store or update an aggregated user resume.
        
        Args:
            user_id (str): User identifier
            resume_data (dict): Aggregated resume data for user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO generated_resumes (user_id, resume_data)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        resume_data = EXCLUDED.resume_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, json.dumps(resume_data)))
            
            return True
            
        except Exception as e:
            print(f"✗ Error storing user resume: {e}")
            return False
    
    @staticmethod
    def get_user_resume(user_id):
        """
        Retrieve the aggregated user resume.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            dict: User resume data or None if not found
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT resume_data, created_at, updated_at
                    FROM generated_resumes
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
            
            if result:
                return {
                    'resume_data': result[0],
                    'created_at': result[1],
                    'updated_at': result[2]
                }
            return None
            
        except Exception as e:
            print(f"✗ Error retrieving user resume: {e}")
            return None
    
    @staticmethod
    def delete_project_resume(project_id, user_id):
        """
        Delete a project-specific resume item.
        Automatically called when project is deleted.
        
        Args:
            project_id (int): ID of the uploaded project
            user_id (str): User identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM project_resumes
                    WHERE project_id = %s AND user_id = %s
                """, (project_id, user_id))
            
            return True
            
        except Exception as e:
            print(f"✗ Error deleting project resume: {e}")
            return False
    
    @staticmethod
    def generate_project_resume_item(project_id, user_id):
        """
        Generate a project-specific resume item from project analysis.
        
        Args:
            project_id (int): ID of the uploaded project
            user_id (str): User identifier
            
        Returns:
            dict: Generated resume item data or None if generation fails
        """
        try:
            # Get project info
            from project_manager import get_project_by_id
            project_info = get_project_by_id(project_id)
            
            if not project_info:
                return None
            
            # Get project analysis
            analysis = analyze_project_from_db(project_id)
            
            if not analysis or 'error' in analysis:
                return None
            
            # Calculate project score
            score = calculate_project_score(analysis)
            
            # Extract key information for resume
            languages = analysis.get('by_language', [])
            activities = analysis.get('by_activity', {})
            totals = analysis.get('totals', {})
            
            resume_item = {
                'project_id': project_id,
                'project_name': project_info['filename'],
                'description': f"Analyzed project with {totals.get('files', 0)} files and {totals.get('lines', 0)} lines of code",
                'duration': project_info['created_at'].strftime("%Y-%m-%d") if project_info['created_at'] else "Unknown",
                'key_contributions': [],
                'skills_demonstrated': [lang['language'] for lang in languages[:5]],
                'metrics': {
                    'total_files': totals.get('files', 0),
                    'total_lines': totals.get('lines', 0),
                    'project_score': score
                },
                'activity_breakdown': {activity: data.get('count', 0) for activity, data in activities.items()}
            }
            
            return resume_item
            
        except Exception as e:
            print(f"✗ Error generating project resume item: {e}")
            return None