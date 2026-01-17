from datetime import datetime
from config.db_config import with_db_cursor, get_connection
from analysis.project_ranking import rank_all_projects, calculate_project_score
from analysis.key_metrics import analyze_project_from_db
from analysis.ranking_storage import get_stored_ranking_by_project_id
from project_summarizer import ProjectSummarizer, summarize_project
from parsing.file_contents_manager import get_file_contents_by_upload_id, get_file_statistics
from portfolio.skill_mapper import SkillMapper
from account.user_manager import AuthManager
from collaborative.identify_projects import _identify_authors_from_zip, _extract_common_names_from_filenames
from database.user_preferences import get_user_git_username
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
                resume_data = result[0]
                # Parse JSON if it's a string (PostgreSQL JSONB might return as dict or string depending on driver)
                if isinstance(resume_data, str):
                    resume_data = json.loads(resume_data)
                elif isinstance(resume_data, dict):
                    # Already parsed, use as is
                    pass
                else:
                    # Try to parse anyway
                    try:
                        resume_data = json.loads(str(resume_data))
                    except:
                        resume_data = result[0]
                
                return {
                    'resume_data': resume_data,
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
            # Data Isolation: Rank only projects belonging to this user
            ranked_projects = rank_all_projects(user_name=user_id)
            
            if not ranked_projects:
                return None
            
            top_projects = ranked_projects[:top_projects_count]
            
            # Collect all authors from top projects to let user select their name
            all_authors = set()
            for project in top_projects:
                try:
                    project_id = project['project_id']
                    file_contents = get_file_contents_by_upload_id(project_id)
                    authors = _identify_authors_from_zip(project_id) | _extract_common_names_from_filenames(file_contents)
                    all_authors.update(authors)
                except Exception:
                    continue
            
            # Get user's name from detected authors (similar to choose_author_from_zip logic)
            user_name = user_id  # Default fallback
            if all_authors:
                git_username = get_user_git_username()
                if git_username and git_username in all_authors:
                    # Auto-select if git username matches
                    user_name = git_username
                else:
                    # Let user select their name from detected authors
                    authors_list = sorted(list(all_authors))
                    print(f"\n{'='*70}")
                    print("Select Your Name for Resume")
                    print(f"{'='*70}")
                    print("Detected author names from your projects:")
                    for idx, name in enumerate(authors_list, start=1):
                        print(f"  {idx}. {name}")
                    print(f"  {len(authors_list) + 1}. Use my login username: {user_id}")
                    print(f"  {len(authors_list) + 2}. Enter custom name")
                    
                    while True:
                        try:
                            choice = input("\nSelect an option: ").strip()
                            
                            if choice.isdigit():
                                choice_num = int(choice)
                                if 1 <= choice_num <= len(authors_list):
                                    user_name = authors_list[choice_num - 1]
                                    print(f"\nSelected: {user_name}")
                                    break
                                elif choice_num == len(authors_list) + 1:
                                    user_name = user_id
                                    print(f"\nUsing login username: {user_name}")
                                    break
                                elif choice_num == len(authors_list) + 2:
                                    custom_name = input("Enter your name: ").strip()
                                    if custom_name:
                                        user_name = custom_name
                                        print(f"\nUsing custom name: {user_name}")
                                        break
                                    else:
                                        print("Please enter a valid name.")
                                else:
                                    print(f"Please enter a number between 1 and {len(authors_list) + 2}.")
                            else:
                                print("Invalid input. Enter a number.")
                        except (ValueError, KeyboardInterrupt):
                            print("\nUsing default username.")
                            user_name = user_id
                            break
            else:
                # No authors detected, use login username or ask for custom name
                print(f"\nNo author names detected in projects.")
                use_custom = input("Enter your name for the resume (or press Enter to use login username): ").strip()
                if use_custom:
                    user_name = use_custom
                else:
                    user_name = user_id
            
            summarizer = ProjectSummarizer()
            skill_mapper = SkillMapper()
            
            all_skills = set()
            all_languages = set()
            all_frameworks = set()
            project_summaries = []
            
            for project in top_projects:
                try:
                    project_id = project['project_id']
                    
                    # Get stored project summary from database (if available)
                    stored_ranking = get_stored_ranking_by_project_id(project_id)
                    project_summary_text = stored_ranking.get('summary', '') if stored_ranking else ''
                    
                    # If no summary in database, generate one using summarize_project
                    if not project_summary_text:
                        try:
                            # Data Isolation: Pass user_id to verify project ownership
                            project_summary_text = summarize_project(project_id, user_name=user_id)
                        except Exception as e:
                            print(f"[WARNING] Could not generate summary for project {project_id}: {e}")
                            project_summary_text = ''
                    
                    # Get comprehensive summary for additional data
                    # Data Isolation: Pass user_id to verify project ownership
                    summary = summarizer.generate_project_summary(project_id, user_name=user_id)
                    
                    if summary and 'error' not in summary:
                        # Extract languages
                        languages_data = summary.get('languages', {})
                        project_languages = languages_data.get('languages', [])
                        primary_language = languages_data.get('primary_language', 'Unknown')
                        all_languages.update(project_languages)
                        
                        # Get timeline info
                        time_analysis = summary.get('time_analysis', {})
                        duration_days = time_analysis.get('duration_days', 0)
                        intensity = time_analysis.get('intensity', 'Unknown')
                        first_file = time_analysis.get('first_file', '')
                        last_file = time_analysis.get('last_file', '')
                        
                        # Get collaboration info
                        collab_analysis = summary.get('collaboration_analysis', {})
                        collaboration_level = collab_analysis.get('collaboration_level', 'Unknown')
                        
                        # Get file contents for framework detection
                        file_contents = get_file_contents_by_upload_id(project_id)
                        frameworks = ResumeManager._detect_frameworks_from_files(file_contents)
                        all_frameworks.update(frameworks)
                        
                        # Extract skills from deep analysis
                        code_analysis = summary.get('code_analysis', {})
                        deep_analysis_skills = skill_mapper.extract_skills_from_deep_analysis(code_analysis)
                        
                        # Combine all skills for this project
                        project_skills = set(project_languages)
                        project_skills.update(frameworks)
                        project_skills.update(deep_analysis_skills)
                        all_skills.update(project_skills)
                        
                        # Clean project name
                        project_name = project['filename']
                        # Remove common suffixes and extensions
                        clean_name = project_name
                        # Remove file extensions
                        if clean_name.endswith('.zip'):
                            clean_name = clean_name[:-4]
                        # Remove common git suffixes
                        clean_name = clean_name.replace('-master', '').replace('-main', '').replace('-main.zip', '')
                        # Replace underscores and hyphens with spaces
                        clean_name = clean_name.replace('_', ' ').replace('-', ' ')
                        # Title case and clean up multiple spaces
                        clean_name = ' '.join(clean_name.split()).title()
                        # If name is empty or too short, use original
                        if not clean_name or len(clean_name) < 2:
                            clean_name = project_name.replace('.zip', '')
                        
                        # Build enriched project summary for resume
                        project_summaries.append({
                            'project_name': clean_name,
                            'project_id': project_id,
                            'primary_language': primary_language,
                            'languages': project_languages,
                            'frameworks': frameworks,
                            'skills': sorted(list(project_skills))[:15],
                            'duration_days': duration_days,
                            'intensity': intensity,
                            'first_file': first_file,
                            'last_file': last_file,
                            'collaboration_level': collaboration_level,
                            'summary': project_summary_text,  # Use stored summary from database
                            'project_info': summary.get('project_info', {})
                        })
                
                except Exception as e:
                    print(f"[ERROR] Failed to summarize project {project['project_id']}: {e}")
                    continue
            
            # Categorize skills
            categorized_skills = skill_mapper.categorize_skills(all_skills)
            
            # Build comprehensive resume data
            resume_data = {
                'user_name': user_name,
                'user_id': user_id,
                'total_projects_analyzed': len(ranked_projects),
                'top_projects_displayed': len(project_summaries),
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