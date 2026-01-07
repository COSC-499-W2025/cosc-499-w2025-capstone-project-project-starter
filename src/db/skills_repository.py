# src/db/skills_repository.py (COMPLETE FIXED VERSION)
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from .connect import get_db_connection

# Try to import SKILLS, but provide fallback
try:
    from skills_config import SKILLS, SKILL_CATEGORIES
except ImportError:
    try:
        from ..skills_config import SKILLS, SKILL_CATEGORIES
    except ImportError:
        # Fallback skills list (from ML training file)
        SKILLS = [
            "Testing", "CI", "Containerization", "Concurrency", "Performance-Optimization",
            "Security-Cryptography", "Security-Application", "Security-Network", "Logging",
            "Metrics-Monitoring", "Tracing", "Infrastructure-as-Code", "Build-Systems",
            "Package-Management", "Scripting-Automation", "CLI-Tooling",
            "Web-Frontend", "Web-Backend", "Web-Fullstack", "Web-API",
            "Authentication-Authorization", "Microservices", "Messaging-Queueing",
            "Streaming-Processing", "SQL-DML", "SQL-DDL", "Database-ORM", "Database-NoSQL",
            "Database-Graph", "Caching", "Cloud-AWS", "Cloud-GCP", "Cloud-Azure",
            "Orchestration-Kubernetes", "BigData", "Systems-Programming", "Embedded",
            "Networking-LowLevel", "Parallel-Computing", "GPU-Computing", "Data-Wrangling",
            "Data-Engineering", "Data-Visualization", "Numerics", "ML-Classic",
            "ML-DeepLearning", "ML-NLP", "ML-Vision", "ML-Recommendation", "MLOps",
            "Probabilistic-Programming", "Game-Development", "Functional-Programming",
            "Serialization"
        ]
        SKILL_CATEGORIES = {}

class SkillsRepository:
    @staticmethod
    def store_skills_analysis(project_id: str, analysis_type: str, 
                             skills_data: Dict[str, Any], source: str = "llm",
                             file_path: str = None, metadata: Dict = None):
        """
        Store skills analysis in the database
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Ensure skills table exists
            SkillsRepository._ensure_skills_table(cursor)
            
            # Prepare data for storage
            skills_json = json.dumps(skills_data)
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            # Store the analysis
            cursor.execute("""
                INSERT INTO skills_analysis 
                (project_id, analysis_type, source, skills_data, file_path, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (project_id, analysis_type, source, skills_json, file_path, json.dumps(metadata)))
            
            conn.commit()
            print(f"[SkillsRepository] Stored {source} analysis for project {project_id}")
            
        except Exception as e:
            print(f"[SkillsRepository] Error storing skills analysis: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def store_detailed_skills(project_id: str, skills_list: List[str], 
                             source: str, confidence: float = 1.0,
                             file_path: str = None, context: str = None):
        """
        Store individual skills with details
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Ensure detailed skills table exists
            SkillsRepository._ensure_detailed_skills_table(cursor)
            
            for skill in skills_list:
                if skill in SKILLS:
                    cursor.execute("""
                        INSERT INTO detailed_skills 
                        (project_id, skill_name, source, confidence, file_path, context, detected_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (project_id, skill, source, confidence, file_path, context))
            
            conn.commit()
            print(f"[SkillsRepository] Stored {len(skills_list)} skills for project {project_id}")
            
        except Exception as e:
            print(f"[SkillsRepository] Error storing detailed skills: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    @staticmethod
    def _ensure_skills_table(cursor):
        """Ensure skills_analysis table exists"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_analysis (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(255) NOT NULL,
                analysis_type VARCHAR(100) NOT NULL,
                source VARCHAR(50) NOT NULL,
                skills_data JSONB NOT NULL,
                file_path TEXT,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes if they don't exist
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_analysis_project 
            ON skills_analysis(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_analysis_source 
            ON skills_analysis(source)
        """)
    
    @staticmethod
    def _ensure_detailed_skills_table(cursor):
        """Ensure detailed_skills table exists"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detailed_skills (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(255) NOT NULL,
                skill_name VARCHAR(100) NOT NULL,
                source VARCHAR(50) NOT NULL,
                confidence FLOAT DEFAULT 1.0,
                file_path TEXT,
                context TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes if they don't exist
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detailed_skills_project 
            ON detailed_skills(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detailed_skills_name 
            ON detailed_skills(skill_name)
        """)
    
    @staticmethod
    def get_project_skills_summary(project_id: str) -> Dict[str, Any]:
        """Get summary of all skills detected for a project"""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all skills analyses
            cursor.execute("""
                SELECT source, skills_data 
                FROM skills_analysis 
                WHERE project_id = %s
                ORDER BY created_at DESC
            """, (project_id,))
            
            analyses = cursor.fetchall()
            
            # Aggregate skills from all sources
            all_skills = set()
            skill_sources = {}
            
            for source, skills_json in analyses:
                try:
                    skills_data = json.loads(skills_json)
                    if "detected_skills" in skills_data:
                        detected = [s for s, d in skills_data["detected_skills"].items() if d]
                        all_skills.update(detected)
                        skill_sources[source] = detected
                except:
                    continue
            
            # Get detailed skills count
            cursor.execute("""
                SELECT skill_name, COUNT(*) as count, 
                       STRING_AGG(DISTINCT source, ', ') as sources
                FROM detailed_skills 
                WHERE project_id = %s
                GROUP BY skill_name
                ORDER BY count DESC
            """, (project_id,))
            
            detailed_stats = cursor.fetchall()
            
            return {
                "project_id": project_id,
                "all_detected_skills": sorted(list(all_skills)),
                "skills_by_source": skill_sources,
                "detailed_stats": [
                    {"skill": row[0], "count": row[1], "sources": row[2]} 
                    for row in detailed_stats
                ],
                "total_analyses": len(analyses)
            }
            
        except Exception as e:
            print(f"[SkillsRepository] Error getting project summary: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()