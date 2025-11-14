from datetime import datetime
from config.db_config import with_db_cursor
from analysis.project_ranking import rank_all_projects, calculate_project_score
from project_summarizer import ProjectSummarizer
import json


class ResumeManager:
    """Manages user resume data model and storage operations."""
    
    @staticmethod
    def init_resume_table():
        """
        Initialize the generated_resumes table in the database.
        Creates table structure for storing user-aggregated resume data.
        Uses JSONB for flexible resume content storage across different resume types.
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS generated_resumes (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL UNIQUE,
                        resume_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_generated_resumes_user_id 
                    ON generated_resumes(user_id);
                """)
            
            print("[SUCCESS] Resume table initialized successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error initializing resume table: {e}")
            return False
    
    @staticmethod
    def store_user_resume(user_id, resume_data):
        """
        Store or update a user-aggregated resume.
        
        Uses UPSERT logic (ON CONFLICT) to ensure only the latest version is stored.
        The resume_data parameter should contain aggregated information from top user projects
        including top projects, skills, portfolio metrics, and experience duration.
        
        Args:
            user_id (str): Unique user identifier
            resume_data (dict): Aggregated resume data containing top projects and skills
            
        Returns:
            bool: True if storage successful, False otherwise
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
            print(f"[ERROR] Error storing user resume: {e}")
            return False
    
    @staticmethod
    def get_user_resume(user_id):
        """
        Retrieve the aggregated user resume.
        
        Fetches the most recent user resume from the database.
        Returns resume data along with creation and last update timestamps
        for tracking resume generation history.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            dict: Dictionary containing resume_data, created_at, and updated_at
                  Returns None if no resume exists for the user
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
            print(f"[ERROR] Error retrieving user resume: {e}")
            return None
    
    @staticmethod
    def delete_user_resume(user_id):
        """
        Delete a user's resume.
        
        Removes the user's resume from the database. This operation is typically
        triggered when a user withdraws consent (per requirement #1) or requests
        data deletion for privacy compliance.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM generated_resumes
                    WHERE user_id = %s
                """, (user_id,))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error deleting user resume: {e}")
            return False
    
    @staticmethod
    def resume_exists(user_id):
        """
        Check if a resume exists for the given user.
        
        Useful for determining whether to generate a new resume
        or retrieve an existing one.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            bool: True if resume exists, False otherwise
        """
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM generated_resumes WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            print(f"[ERROR] Error checking resume existence: {e}")
            return False
    
    @staticmethod
    def generate_user_resume(user_id, top_projects_count=5):
        """
        Generate a user-aggregated resume from top ranked projects.
        
        Leverages existing ranking system to identify top projects by score.
        Uses ProjectSummarizer to extract summary data from each top project.
        Aggregates skills, metrics, and project information for portfolio building.
        
        Args:
            user_id (str): Unique user identifier
            top_projects_count (int): Number of top projects to include (default: 5)
            
        Returns:
            dict: Generated resume data containing top projects and aggregated skills
                  Returns None if generation fails or no projects exist
        """
        try:
            ranked_projects = rank_all_projects()
            
            if not ranked_projects:
                return None
            
            top_projects = ranked_projects[:top_projects_count]
            summarizer = ProjectSummarizer()
            
            all_skills = set()
            project_summaries = []
            
            for project in top_projects:
                try:
                    summary = summarizer.generate_project_summary(project['project_id'])
                    
                    if summary and 'error' not in summary:
                        project_skills = summary.get('languages', {}).get('languages', [])
                        all_skills.update(project_skills)
                        
                        project_summaries.append({
                            'project_name': project['filename'],
                            'score': project['score'],
                            'primary_language': summary.get('languages', {}).get('primary_language', 'Unknown'),
                            'skills': project_skills[:3]
                        })
                
                except Exception as e:
                    print(f"[ERROR] Failed to summarize project {project['project_id']}: {e}")
                    continue
            
            resume_data = {
                'user_id': user_id,
                'total_projects_analyzed': len(ranked_projects),
                'top_projects_displayed': len(project_summaries),
                'all_skills': sorted(list(all_skills)),
                'top_projects': project_summaries,
                'generated_at': datetime.now().isoformat()
            }
            
            return resume_data
            
        except Exception as e:
            print(f"[ERROR] Error generating user resume: {e}")
            return None