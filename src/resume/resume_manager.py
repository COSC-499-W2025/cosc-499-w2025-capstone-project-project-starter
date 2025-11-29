from datetime import datetime
from config.db_config import with_db_cursor
from analysis.project_ranking import rank_all_projects, calculate_project_score
from analysis.key_metrics import analyze_project_from_db
from project_summarizer import ProjectSummarizer
from parsing.file_contents_manager import get_file_contents_by_upload_id, get_file_statistics
from portfolio.skill_mapper import SkillMapper
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
    def _detect_frameworks_from_files(file_contents):
        """
        Detect frameworks from file contents.
        
        Args:
            file_contents: List of file content dictionaries
            
        Returns:
            list: Detected frameworks
        """
        file_names = [f.get('file_name', '').lower() for f in file_contents]
        framework_indicators = {
            'React': ['package.json', 'react', '.jsx', '.tsx'],
            'Vue': ['vue.config.js', 'vue'],
            'Angular': ['angular.json'],
            'Django': ['manage.py', 'settings.py'],
            'Flask': ['flask'],
            'Express': ['express'],
            'Spring': ['pom.xml', 'build.gradle'],
            'Node.js': ['package.json', 'node_modules'],
            'Docker': ['dockerfile', 'docker-compose.yml'],
            'PostgreSQL': ['psycopg', 'postgresql'],
            'MongoDB': ['mongoose', 'mongodb'],
            'FastAPI': ['fastapi'],
        }
        detected_frameworks = set()
        for framework, indicators in framework_indicators.items():
            for indicator in indicators:
                for name in file_names:
                    if indicator.lower() in name:
                        detected_frameworks.add(framework)
                        break
        return sorted(list(detected_frameworks))
    
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
            skill_mapper = SkillMapper()
            
            all_skills = set()
            all_languages = set()
            all_frameworks = set()
            project_summaries = []
            total_lines_of_code = 0
            total_files = 0
            
            for project in top_projects:
                try:
                    project_id = project['project_id']
                    
                    # Get comprehensive summary
                    summary = summarizer.generate_project_summary(project_id)
                    
                    if summary and 'error' not in summary:
                        # Extract languages
                        languages_data = summary.get('languages', {})
                        project_languages = languages_data.get('languages', [])
                        primary_language = languages_data.get('primary_language', 'Unknown')
                        all_languages.update(project_languages)
                        
                        # Get key metrics
                        key_metrics = analyze_project_from_db(project_id, silent=True)
                        totals = key_metrics.get('totals', {})
                        file_count = totals.get('files', 0)
                        lines_of_code = totals.get('lines', 0)
                        total_lines_of_code += lines_of_code
                        total_files += file_count
                        
                        # Get timeline info
                        time_analysis = summary.get('time_analysis', {})
                        duration_days = time_analysis.get('duration_days', 0)
                        intensity = time_analysis.get('intensity', 'Unknown')
                        
                        # Get collaboration info
                        collab_analysis = summary.get('collaboration_analysis', {})
                        collaboration_level = collab_analysis.get('collaboration_level', 'Unknown')
                        
                        # Get code analysis
                        code_analysis = summary.get('code_analysis', {})
                        quality_summary = code_analysis.get('code_quality_summary', {})
                        code_quality_score = quality_summary.get('average_quality_score', 0)
                        
                        # Count OOP principles
                        oop_summary = code_analysis.get('oop_principles_summary', {})
                        oop_count = 0
                        for principle in ['abstraction', 'encapsulation', 'polymorphism', 'inheritance']:
                            principle_data = oop_summary.get(principle, {})
                            if isinstance(principle_data, dict):
                                oop_count += principle_data.get('count', 0)
                        
                        # Count optimizations
                        optimization_count = len(code_analysis.get('optimization_summary', []))
                        
                        # Get file contents for framework detection
                        file_contents = get_file_contents_by_upload_id(project_id)
                        frameworks = ResumeManager._detect_frameworks_from_files(file_contents)
                        all_frameworks.update(frameworks)
                        
                        # Detect if project has tests and docs
                        has_tests = False
                        has_docs = False
                        for f in file_contents:
                            file_path = f.get('file_path', '').lower()
                            file_name = f.get('file_name', '').lower()
                            if 'test' in file_path or file_name.startswith('test_'):
                                has_tests = True
                            if 'readme' in file_name or file_name.endswith('.md'):
                                has_docs = True
                        
                        # Extract skills from deep analysis
                        deep_analysis_skills = skill_mapper.extract_skills_from_deep_analysis(code_analysis)
                        
                        # Combine all skills for this project
                        project_skills = set(project_languages)
                        project_skills.update(frameworks)
                        project_skills.update(deep_analysis_skills)
                        all_skills.update(project_skills)
                        
                        # Build enriched project summary
                        project_summaries.append({
                            'project_name': project['filename'],
                            'project_id': project_id,
                            'score': project['score'],
                            'primary_language': primary_language,
                            'languages': project_languages,
                            'frameworks': frameworks,
                            'skills': sorted(list(project_skills))[:10],
                            'file_count': file_count,
                            'lines_of_code': lines_of_code,
                            'duration_days': duration_days,
                            'intensity': intensity,
                            'collaboration_level': collaboration_level,
                            'code_quality_score': round(code_quality_score, 1),
                            'oop_principles_count': oop_count,
                            'optimization_count': optimization_count,
                            'has_tests': has_tests,
                            'has_docs': has_docs
                        })
                
                except Exception as e:
                    print(f"[ERROR] Failed to summarize project {project['project_id']}: {e}")
                    continue
            
            # Categorize skills
            categorized_skills = skill_mapper.categorize_skills(all_skills)
            
            # Build comprehensive resume data
            resume_data = {
                'user_id': user_id,
                'total_projects_analyzed': len(ranked_projects),
                'top_projects_displayed': len(project_summaries),
                'summary_stats': {
                    'total_lines_of_code': total_lines_of_code,
                    'total_files': total_files,
                    'unique_languages': len(all_languages),
                    'unique_frameworks': len(all_frameworks),
                    'unique_skills': len(all_skills)
                },
                'all_skills': sorted(list(all_skills)),
                'categorized_skills': categorized_skills,
                'languages': sorted(list(all_languages)),
                'frameworks': sorted(list(all_frameworks)),
                'top_projects': project_summaries,
                'generated_at': datetime.now().isoformat()
            }
            
            return resume_data
            
        except Exception as e:
            print(f"[ERROR] Error generating user resume: {e}")
            return None