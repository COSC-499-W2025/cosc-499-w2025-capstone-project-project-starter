from datetime import datetime
from config.db_config import with_db_cursor, get_connection
from analysis.project_ranking import rank_all_projects
from analysis.ranking_storage import get_stored_ranking_by_project_id, get_stored_rankings
from project_summarizer import ProjectSummarizer
from parsing.file_contents_manager import get_file_contents_by_upload_id
from portfolio.skill_mapper import SkillMapper
from database.user_preferences import get_user_git_username
from resume.evidence_extractor import build_evidence
from common.logger import setup_logger
import json
import sys


class ResumeManager:
    """Manages user resume data model and storage operations."""
    logger = setup_logger(__name__)
    
    @staticmethod
    def init_resume_table():
        try:
            with with_db_cursor() as cursor:
                # First, create table if it doesn't exist (with new structure)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS generated_resumes (
                        id SERIAL PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL UNIQUE,
                        resume_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Migration: If old table exists with user_id, migrate to user_name
                # This must happen before creating the index or adding constraints
                cursor.execute("""
                    DO $$
                    BEGIN
                        -- Check if user_id column exists (old schema)
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='generated_resumes' AND column_name='user_id'
                        ) THEN
                            -- Rename user_id to user_name
                            ALTER TABLE generated_resumes RENAME COLUMN user_id TO user_name;
                            
                            -- Drop old index if exists
                            DROP INDEX IF EXISTS idx_generated_resumes_user_id;
                        END IF;
                    END $$;
                """)
                
                # Create index on user_name (works for both new and migrated tables)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_generated_resumes_user_name 
                    ON generated_resumes(user_name);
                """)
                
                # Add foreign key constraint if it doesn't exist
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'fk_user_name' AND table_name = 'generated_resumes'
                        ) THEN
                            ALTER TABLE generated_resumes
                            ADD CONSTRAINT fk_user_name
                            FOREIGN KEY (user_name)
                            REFERENCES user_informations(user_name)
                            ON DELETE CASCADE
                            ON UPDATE CASCADE;
                        END IF;
                    END $$;
                """)
            
            print("[SUCCESS] Resume table initialized successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error initializing resume table: {e}")
            return False
    
    @staticmethod
    def init_portfolio_settings_table():
        """Initialize the portfolio_settings table for storing visibility and component settings."""
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_settings (
                        id SERIAL PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL UNIQUE,
                        is_public BOOLEAN DEFAULT FALSE,
                        show_timeline BOOLEAN DEFAULT TRUE,
                        show_heatmap BOOLEAN DEFAULT TRUE,
                        show_top_projects BOOLEAN DEFAULT TRUE,
                        show_skills BOOLEAN DEFAULT TRUE,
                        show_stats BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_settings_user_name
                    ON portfolio_settings(user_name);
                """)
            print("[SUCCESS] Portfolio settings table initialized successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Error initializing portfolio settings table: {e}")
            return False

    @staticmethod
    def get_portfolio_settings(user_name: str) -> dict:
        """Get portfolio visibility and component settings for a user."""
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT is_public, show_timeline, show_heatmap, show_top_projects,
                           show_skills, show_stats, updated_at
                    FROM portfolio_settings
                    WHERE user_name = %s
                """, (user_name,))
                result = cursor.fetchone()
            if result:
                return {
                    'is_public': result[0],
                    'show_timeline': result[1],
                    'show_heatmap': result[2],
                    'show_top_projects': result[3],
                    'show_skills': result[4],
                    'show_stats': result[5],
                    'updated_at': result[6].isoformat() if result[6] else None
                }
            return {
                'is_public': False,
                'show_timeline': True,
                'show_heatmap': True,
                'show_top_projects': True,
                'show_skills': True,
                'show_stats': True,
                'updated_at': None
            }
        except Exception as e:
            print(f"[ERROR] Failed to get portfolio settings: {e}")
            return {
                'is_public': False, 'show_timeline': True, 'show_heatmap': True,
                'show_top_projects': True, 'show_skills': True, 'show_stats': True,
                'updated_at': None
            }

    @staticmethod
    def save_portfolio_settings(user_name: str, settings: dict) -> bool:
        """Save portfolio visibility and component settings."""
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio_settings
                        (user_name, is_public, show_timeline, show_heatmap,
                         show_top_projects, show_skills, show_stats)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_name)
                    DO UPDATE SET
                        is_public = EXCLUDED.is_public,
                        show_timeline = EXCLUDED.show_timeline,
                        show_heatmap = EXCLUDED.show_heatmap,
                        show_top_projects = EXCLUDED.show_top_projects,
                        show_skills = EXCLUDED.show_skills,
                        show_stats = EXCLUDED.show_stats,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    user_name,
                    settings.get('is_public', False),
                    settings.get('show_timeline', True),
                    settings.get('show_heatmap', True),
                    settings.get('show_top_projects', True),
                    settings.get('show_skills', True),
                    settings.get('show_stats', True)
                ))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save portfolio settings: {e}")
            return False

    @staticmethod
    def init_portfolio_timeline_overrides_table():
        """Initialize the portfolio_timeline_overrides table for per-project skill edits."""
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_timeline_overrides (
                        id SERIAL PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL,
                        project_id INTEGER NOT NULL,
                        hidden_skills JSONB DEFAULT '[]'::jsonb,
                        added_skills JSONB DEFAULT '[]'::jsonb,
                        custom_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_name, project_id)
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_tl_overrides_user
                    ON portfolio_timeline_overrides(user_name);
                """)
            print("[SUCCESS] portfolio_timeline_overrides table initialized")
            return True
        except Exception as e:
            print(f"[ERROR] Error initializing portfolio_timeline_overrides table: {e}")
            return False

    @staticmethod
    def save_timeline_override(user_name: str, project_id: int, override_data: dict) -> bool:
        """Save or update timeline overrides for a specific project."""
        try:
            hidden = json.dumps(override_data.get('hidden_skills', []))
            added = json.dumps(override_data.get('added_skills', []))
            custom_date = override_data.get('custom_date') or None

            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio_timeline_overrides
                        (user_name, project_id, hidden_skills, added_skills, custom_date)
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (user_name, project_id)
                    DO UPDATE SET
                        hidden_skills = EXCLUDED.hidden_skills,
                        added_skills  = EXCLUDED.added_skills,
                        custom_date   = EXCLUDED.custom_date,
                        updated_at    = CURRENT_TIMESTAMP
                """, (user_name, project_id, hidden, added, custom_date))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save timeline override: {e}")
            return False

    @staticmethod
    def get_timeline_overrides(user_name: str) -> dict:
        """Get all timeline overrides for a user, keyed by project_id."""
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT project_id, hidden_skills, added_skills, custom_date
                    FROM portfolio_timeline_overrides
                    WHERE user_name = %s
                """, (user_name,))
                rows = cursor.fetchall()
            result = {}
            for row in rows:
                pid = row[0]
                result[pid] = {
                    'hidden_skills': row[1] if row[1] else [],
                    'added_skills': row[2] if row[2] else [],
                    'custom_date': row[3].isoformat() if row[3] else None
                }
            return result
        except Exception as e:
            print(f"[ERROR] Failed to get timeline overrides: {e}")
            return {}

    @staticmethod
    def init_portfolio_customizations_table():
        try:
            with with_db_cursor() as cursor:
                # Create portfolio_customizations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_customizations (
                        id SERIAL PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL,
                        project_id INTEGER NOT NULL,
                        custom_title TEXT,
                        custom_description TEXT,
                        custom_role TEXT,
                        -- Layout / presentation-only controls. These MUST NOT
                        -- change underlying verified analysis data.
                        display_order INTEGER,
                        highlight BOOLEAN,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_name, project_id)
                    );
                """)
                
                # Create index on user_name for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_customizations_user_name 
                    ON portfolio_customizations(user_name);
                """)
                
                # Create index on project_id for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_customizations_project_id 
                    ON portfolio_customizations(project_id);
                """)

                # Migrations for older schemas: add missing columns if necessary
                cursor.execute("""
                    DO $$
                    BEGIN
                        -- Ensure display_order exists
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'portfolio_customizations'
                              AND column_name = 'display_order'
                        ) THEN
                            ALTER TABLE portfolio_customizations
                            ADD COLUMN display_order INTEGER;
                        END IF;

                        -- Ensure highlight exists
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'portfolio_customizations'
                              AND column_name = 'highlight'
                        ) THEN
                            ALTER TABLE portfolio_customizations
                            ADD COLUMN highlight BOOLEAN;
                        END IF;
                    END $$;
                """)

                # Add foreign key constraint to user_informations
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'fk_portfolio_customizations_user_name' 
                            AND table_name = 'portfolio_customizations'
                        ) THEN
                            ALTER TABLE portfolio_customizations
                            ADD CONSTRAINT fk_portfolio_customizations_user_name
                            FOREIGN KEY (user_name)
                            REFERENCES user_informations(user_name)
                            ON DELETE CASCADE
                            ON UPDATE CASCADE;
                        END IF;
                    END $$;
                """)
            
            print("[SUCCESS] Portfolio customizations table initialized successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error initializing portfolio customizations table: {e}")
            return False
    
    @staticmethod
    def store_user_resume(user_name, resume_data):
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO generated_resumes (user_name, resume_data)
                    VALUES (%s, %s)
                    ON CONFLICT (user_name)
                    DO UPDATE SET 
                        resume_data = EXCLUDED.resume_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_name, json.dumps(resume_data)))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error storing user resume: {e}")
            return False
    
    @staticmethod
    def clear_custom_project_wording(user_id: str, project_id: int) -> bool:
        return ResumeManager.save_custom_project_wording(user_id, project_id, "")


    @staticmethod
    def list_custom_worded_projects(user_id: str) -> list[int]:
        try:
            existing = ResumeManager.get_user_resume(user_id)
            if not existing or "resume_data" not in existing:
                return []

            resume_data = existing.get("resume_data")

            if not isinstance(resume_data, dict):
                return []

            custom_map = resume_data.get("custom_project_wording", {}) or {}
            if not isinstance(custom_map, dict):
                return []

            project_ids: list[int] = []
            for k, v in custom_map.items():
                if isinstance(v, str) and v.strip():
                    try:
                        project_ids.append(int(k))
                    except Exception:
                        # ignore non-int keys
                        continue

            return sorted(project_ids)
        except Exception as e:
            print(f"[ERROR] Failed to list custom worded projects: {e}")
            return []


    @staticmethod
    def save_custom_project_wording(user_id: str, project_id: int, wording: str) -> bool:
        try:
            existing = ResumeManager.get_user_resume(user_id)

            resume_data = existing.get("resume_data") if existing else {}
            if not isinstance(resume_data, dict):
                resume_data = {}

            custom_map = resume_data.get("custom_project_wording", {})

            if not isinstance(custom_map, dict):
                custom_map = {}

            key = str(project_id)
            wording = (wording or "").strip()

            if wording:
                custom_map[key] = wording
            else:
                # empty wording clears customization
                custom_map.pop(key, None)

            resume_data["custom_project_wording"] = custom_map
            return ResumeManager.store_user_resume(user_id, resume_data)

        except Exception as e:
            print(f"[ERROR] Failed to save custom project wording: {e}")
            return False

    @staticmethod
    def save_portfolio_customization(user_name: str, project_id: int, custom_data: dict) -> bool:
        try:
            custom_title = (custom_data.get('custom_title') or "").strip()
            custom_description = (custom_data.get('custom_description') or "").strip()
            custom_role = (custom_data.get('custom_role') or "").strip()
            display_order = custom_data.get('display_order')
            highlight = custom_data.get('highlight')
            
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio_customizations 
                        (user_name, project_id, custom_title, custom_description, custom_role, display_order, highlight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_name, project_id)
                    DO UPDATE SET 
                        custom_title = EXCLUDED.custom_title,
                        custom_description = EXCLUDED.custom_description,
                        custom_role = EXCLUDED.custom_role,
                        display_order = EXCLUDED.display_order,
                        highlight = EXCLUDED.highlight,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    user_name,
                    project_id,
                    custom_title or None,
                    custom_description or None,
                    custom_role or None,
                    display_order,
                    highlight,
                ))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save portfolio customization: {e}")
            return False
    
    @staticmethod
    def get_portfolio_customization(user_name: str, project_id: int) -> dict | None:
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT custom_title,
                           custom_description,
                           custom_role,
                           display_order,
                           highlight,
                           created_at,
                           updated_at
                    FROM portfolio_customizations
                    WHERE user_name = %s AND project_id = %s
                """, (user_name, project_id))
                
                result = cursor.fetchone()
            
            if result:
                return {
                    'project_id': project_id,
                    'custom_title': result[0],
                    'custom_description': result[1],
                    'custom_role': result[2],
                    'display_order': result[3],
                    'highlight': result[4],
                    'created_at': result[5],
                    'updated_at': result[6],
                }
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to get portfolio customization: {e}")
            return None
    
    @staticmethod
    def list_customized_portfolio_projects(user_name: str) -> list[int]:
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT project_id
                    FROM portfolio_customizations
                    WHERE user_name = %s
                    ORDER BY project_id
                """, (user_name,))
                
                results = cursor.fetchall()
            
            return [row[0] for row in results]
            
        except Exception as e:
            print(f"[ERROR] Failed to list customized portfolio projects: {e}")
            return []
    
    @staticmethod
    def clear_portfolio_customization(user_name: str, project_id: int) -> bool:
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM portfolio_customizations
                    WHERE user_name = %s AND project_id = %s
                """, (user_name, project_id))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to clear portfolio customization: {e}")
            return False

    @staticmethod
    def get_user_resume(user_name):
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT resume_data, created_at, updated_at
                    FROM generated_resumes
                    WHERE user_name = %s
                """, (user_name,))
                
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
    def delete_user_resume(user_name):
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM generated_resumes
                    WHERE user_name = %s
                """, (user_name,))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error deleting user resume: {e}")
            return False
    
    @staticmethod
    def resume_exists(user_name):
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM generated_resumes WHERE user_name = %s
                """, (user_name,))
                
                result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            print(f"[ERROR] Error checking resume existence: {e}")
            return False
    
    @staticmethod
    def _detect_frameworks_from_files(file_contents):
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
    def _clean_project_name(filename):
        clean_name = filename
        if clean_name.endswith('.zip'):
            clean_name = clean_name[:-4]
        clean_name = clean_name.replace('-master', '').replace('-main', '').replace('-main.zip', '')
        clean_name = clean_name.replace('_', ' ').replace('-', ' ')
        clean_name = ' '.join(clean_name.split()).title()
        if not clean_name or len(clean_name) < 2:
            clean_name = filename.replace('.zip', '')
        return clean_name

    def generate_user_resume(user_name, top_projects_count=5, selection: dict | None = None):
        try:
            ResumeManager.logger.info(
                "Generate resume start: user=%s top_projects_count=%s selection=%s",
                user_name, top_projects_count, selection
            )

            # --- Phase 1: Get stored rankings (fast DB query, no re-analysis) ---
            stored_rankings = get_stored_rankings(user_name=user_name)
            stored_rankings_map = {r['project_id']: r for r in stored_rankings}

            if stored_rankings:
                ranked_projects = [
                    {
                        "project_id": r["project_id"],
                        "filename": r.get("ranking_data", {}).get("filename", f"Project {r['project_id']}"),
                        "score": r["score"],
                        "created_at": r.get("ranking_data", {}).get("created_at"),
                        "analysis": r.get("ranking_data", {}).get("analysis", {}),
                    }
                    for r in stored_rankings
                ]
            else:
                ranked_projects = rank_all_projects(user_name=user_name)

            if not ranked_projects:
                ResumeManager.logger.warning("No ranked projects found for user=%s", user_name)
                return None

            # --- Phase 2: Apply selection filters ---
            if selection:
                if "top_projects_count" in selection and isinstance(selection["top_projects_count"], int):
                    top_projects_count = selection["top_projects_count"]
                selected_ids = selection.get("selected_project_ids")
                if selected_ids:
                    ranked_projects = [p for p in ranked_projects if p.get("project_id") in selected_ids]

            top_projects = ranked_projects[:top_projects_count]
            ResumeManager.logger.info(
                "Top projects selected: user=%s count=%s total_ranked=%s",
                user_name, len(top_projects), len(ranked_projects)
            )

            # --- Phase 3: Resolve display name (lightweight) ---
            display_name = user_name
            git_username = get_user_git_username(user_name)
            if git_username:
                display_name = git_username

            skill_mapper = SkillMapper()
            custom_wording_map = {}
            try:
                existing_resume = ResumeManager.get_user_resume(user_name)
                if existing_resume and isinstance(existing_resume.get("resume_data"), dict):
                    custom_wording_map = existing_resume["resume_data"].get("custom_project_wording", {}) or {}
                    if not isinstance(custom_wording_map, dict):
                        custom_wording_map = {}
            except Exception:
                custom_wording_map = {}

            all_skills: set = set()
            all_languages: set = set()
            all_frameworks: set = set()
            project_summaries: list = []

            include_skills = True
            skills_mode = "categorized"
            if selection:
                include_skills = selection.get("include_skills", True)
                skills_mode = selection.get("skills_mode", "categorized")

            # --- Phase 4: Process each project (use stored data first, fallback to live analysis) ---
            for project in top_projects:
                try:
                    project_id = project['project_id']
                    stored_ranking = stored_rankings_map.get(project_id)

                    # 4a. Get summary text (custom wording > stored ranking > skip)
                    custom_text = custom_wording_map.get(str(project_id), "")
                    project_summary_text = (custom_text or "").strip()
                    if not project_summary_text and stored_ranking:
                        project_summary_text = stored_ranking.get('summary', '') or ''

                    # 4b. Try to use stored analysis data from ranking_data
                    stored_analysis = project.get('analysis', {})
                    file_contents = get_file_contents_by_upload_id(project_id)

                    if stored_analysis and stored_analysis.get('by_language'):
                        # Build summary dict from stored analysis without re-running heavy computation
                        summarizer = ProjectSummarizer()
                        languages_data = summarizer._detect_languages(file_contents) if file_contents else {}
                        project_languages = languages_data.get('languages', [])
                        primary_language = languages_data.get('primary_language', 'Unknown')

                        timeline = stored_analysis.get('timeline', {})
                        duration_days = timeline.get('duration_days', 0)
                        first_file = timeline.get('start', '')
                        last_file = timeline.get('end', '')
                        active_days = timeline.get('active_days', 0)
                        intensity = 'High' if active_days > 30 else ('Medium' if active_days > 7 else 'Low')

                        collaboration_level = 'Unknown'
                        code_analysis = {}
                        file_stats = stored_analysis.get('totals', {})

                        summary = {
                            'languages': languages_data,
                            'time_analysis': {
                                'duration_days': duration_days,
                                'intensity': intensity,
                                'first_file': first_file,
                                'last_file': last_file,
                            },
                            'collaboration_analysis': {'collaboration_level': collaboration_level},
                            'code_analysis': code_analysis,
                            'project_info': {'id': project_id, 'filename': project.get('filename', '')},
                            'project_structure': {},
                            'file_statistics': file_stats,
                        }
                    else:
                        # No stored analysis — run full summarization (slow path)
                        summarizer = ProjectSummarizer()
                        summary = summarizer.generate_project_summary(project_id, user_name=user_name)
                        if not summary or 'error' in summary:
                            continue

                        languages_data = summary.get('languages', {})
                        project_languages = languages_data.get('languages', [])
                        primary_language = languages_data.get('primary_language', 'Unknown')

                        time_analysis = summary.get('time_analysis', {})
                        duration_days = time_analysis.get('duration_days', 0)
                        intensity = time_analysis.get('intensity', 'Unknown')
                        first_file = time_analysis.get('first_file', '')
                        last_file = time_analysis.get('last_file', '')

                        collaboration_level = summary.get('collaboration_analysis', {}).get('collaboration_level', 'Unknown')
                        code_analysis = summary.get('code_analysis', {})
                        file_stats = summary.get('file_statistics', {})

                    all_languages.update(project_languages)

                    # 4c. Framework detection (fast — just filename matching)
                    frameworks = ResumeManager._detect_frameworks_from_files(file_contents) if file_contents else []
                    all_frameworks.update(frameworks)

                    # 4d. Skills
                    if include_skills:
                        deep_analysis_skills = skill_mapper.extract_skills_from_deep_analysis(code_analysis) if code_analysis else []
                        project_skills = set(project_languages)
                        project_skills.update(frameworks)
                        project_skills.update(deep_analysis_skills)
                        all_skills.update(project_skills)
                    else:
                        project_skills = set()

                    clean_name = ResumeManager._clean_project_name(project.get('filename', f'Project {project_id}'))

                    evidence = build_evidence(
                        {
                            "languages": {"languages": project_languages, "primary_language": primary_language},
                            "frameworks": frameworks,
                            "time_analysis": {
                                "duration_days": duration_days,
                                "intensity": intensity,
                                "first_file": first_file,
                                "last_file": last_file,
                            },
                            "collaboration_analysis": {"collaboration_level": collaboration_level},
                            "code_analysis": code_analysis,
                            "project_info": summary.get("project_info", {}),
                            "project_structure": summary.get("project_structure", {}),
                            "file_statistics": file_stats,
                        }
                    )

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
                        'summary': project_summary_text,
                        'project_info': summary.get('project_info', {}),
                        'evidence': evidence
                    })

                except Exception as e:
                    print(f"[ERROR] Failed to summarize project {project['project_id']}: {e}")
                    continue

            # --- Phase 5: Aggregate skills ---
            if include_skills:
                all_skills_list = sorted(list(all_skills))
                if skills_mode == "categorized":
                    categorized_skills = skill_mapper.categorize_skills(all_skills)
                else:
                    categorized_skills = {}
            else:
                all_skills_list = []
                categorized_skills = {}

            resume_data = {
                'display_name': display_name,
                'user_name': user_name,
                'total_projects_analyzed': len(ranked_projects),
                'top_projects_displayed': len(project_summaries),
                'all_skills': all_skills_list,
                'categorized_skills': categorized_skills,
                'languages': sorted(list(all_languages)),
                'frameworks': sorted(list(all_frameworks)),
                'top_projects': project_summaries,
                'generated_at': datetime.now().isoformat()
            }

            return resume_data

        except Exception as e:
            ResumeManager.logger.exception("Error generating user resume for user=%s: %s", user_name, e)
            print(f"[ERROR] Error generating user resume: {e}")
            return None
