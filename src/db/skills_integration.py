# src/db/skills_integration.py (CLEAN FIXED VERSION)
import json
import uuid
from datetime import datetime
from .skills_repository import SkillsRepository

def make_metadata_serializable(zip_metadata):
    """
    Convert any metadata object to JSON-serializable format
    """
    if zip_metadata is None:
        return {}
    
    if isinstance(zip_metadata, dict):
        # Already a dict, but need to ensure values are serializable
        result = {}
        for key, value in zip_metadata.items():
            try:
                # Try to serialize each value
                json.dumps({key: value})
                result[key] = value
            except (TypeError, ValueError):
                # Convert to string if not serializable
                result[key] = str(value)
        return result
    
    # Handle ZipInfo object specifically
    if hasattr(zip_metadata, 'filename'):
        return {
            "filename": zip_metadata.filename,
            "file_size": getattr(zip_metadata, 'file_size', None),
            "compress_size": getattr(zip_metadata, 'compress_size', None),
            "type": "zipinfo"
        }
    
    # Try to convert object to dict
    if hasattr(zip_metadata, '__dict__'):
        result = {}
        for key, value in zip_metadata.__dict__.items():
            if not key.startswith('_'):
                try:
                    json.dumps({key: value})
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = str(value)
        return result
    
    # Last resort: convert to string
    return {"metadata": str(zip_metadata)}

def store_ml_results_to_db(project_path, ml_summary, predictions, zip_metadata=None):
    """
    Store ML model results to database
    """
    try:
        # Generate a project ID
        project_id = f"ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Convert metadata to serializable format
        serializable_metadata = make_metadata_serializable(zip_metadata)
        
        # Prepare skills data - ensure everything is JSON serializable
        skills_data = {
            "project_id": project_id,
            "analysis_type": "ml_model",
            "source": "local_ml",
            "ml_summary": str(ml_summary) if not isinstance(ml_summary, (dict, list, str, int, float, bool, type(None))) else ml_summary,
            "predictions": str(predictions) if not isinstance(predictions, (dict, list, str, int, float, bool, type(None))) else predictions,
            "file_path": str(project_path),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="ml_analysis",
            skills_data=skills_data,
            source="ml",
            file_path=str(project_path),
            metadata=serializable_metadata
        )
        
        # Also store the detected skills in detailed_skills table
        detected_skills = []
        if isinstance(ml_summary, dict) and "detected_skills" in ml_summary:
            detected_skills = [skill for skill, detected in ml_summary["detected_skills"].items() if detected]
        elif isinstance(predictions, dict):
            # Try to extract from predictions
            for key, value in predictions.items():
                if isinstance(value, dict) and "skills" in value:
                    detected_skills.extend(value["skills"])
        
        if detected_skills:
            # Remove duplicates
            detected_skills = list(set(detected_skills))
            SkillsRepository.store_detailed_skills(
                project_id=project_id,
                skills_list=detected_skills,
                source="ml",
                confidence=0.9,
                file_path=str(project_path),
                context="ML model analysis"
            )
        
        print(f"✅ ML results stored in database with project ID: {project_id}")
        return project_id
        
    except Exception as e:
        print(f"❌ Failed to store ML results: {e}")
        import traceback
        traceback.print_exc()
        return None

def store_llm_results_to_db(project_path, llm_response, predictions, project_id=None, zip_metadata=None):
    """
    Store LLM analysis results to database
    """
    try:
        if not project_id:
            project_id = f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Convert metadata to serializable format
        serializable_metadata = make_metadata_serializable(zip_metadata)
        
        # Extract skills from LLM response
        llm_skills = extract_skills_from_llm_response(llm_response)
        
        # Prepare LLM data
        llm_data = {
            "project_id": project_id,
            "analysis_type": "llm_analysis",
            "source": "ollama",
            "llm_response": str(llm_response),
            "extracted_skills": llm_skills,
            "predictions": str(predictions) if not isinstance(predictions, (dict, list, str, int, float, bool, type(None))) else predictions,
            "file_path": str(project_path),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="llm_analysis",
            skills_data=llm_data,
            source="ollama",
            file_path=str(project_path),
            metadata=serializable_metadata
        )
        
        # Also store detailed skills if extracted
        if llm_skills:
            SkillsRepository.store_detailed_skills(
                project_id=project_id,
                skills_list=llm_skills,
                source="ollama",
                confidence=0.8,
                file_path=str(project_path),
                context="LLM analysis"
            )
        
        print(f"✅ LLM results stored in database with project ID: {project_id}")
        return project_id
        
    except Exception as e:
        print(f"❌ Failed to store LLM results: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_skills_from_llm_response(llm_response):
    """
    Extract skills from LLM response text
    """
    skills = []
    # Convert to string if needed
    llm_text = str(llm_response).lower()
    
    # Skill keywords from your ML model
    skill_keywords = [
        "testing", "ci", "containerization", "concurrency", "performance", "optimization",
        "security", "cryptography", "logging", "metrics", "monitoring", "tracing",
        "infrastructure", "build", "package", "scripting", "automation", "cli",
        "web", "frontend", "backend", "fullstack", "api", "authentication",
        "authorization", "microservices", "messaging", "queueing", "streaming",
        "sql", "database", "orm", "nosql", "graph", "caching", "cloud",
        "aws", "gcp", "azure", "kubernetes", "bigdata", "systems", "embedded",
        "networking", "parallel", "gpu", "data", "engineering", "visualization",
        "numerics", "ml", "machine learning", "deep learning", "nlp", "vision",
        "recommendation", "mlops", "probabilistic", "game", "functional",
        "serialization", "python", "javascript", "java", "c++", "docker", "postgresql",
        "git"
    ]
    
    for skill in skill_keywords:
        if skill in llm_text:
            # Format skill name nicely
            formatted_skill = skill.title().replace(" ", "-").replace("_", "-")
            skills.append(formatted_skill)
    
    return list(set(skills))  # Remove duplicates

def get_project_summary(project_id):
    """Get summary of stored analysis for a project"""
    try:
        return SkillsRepository.get_project_skills_summary(project_id)
    except Exception as e:
        print(f"Error getting project summary: {e}")
        return None