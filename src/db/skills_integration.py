# Update the store_ml_results_to_db function in src/db/skills_integration.py
import json
import uuid
from datetime import datetime
from .skills_repository import SkillsRepository

def store_ml_results_to_db(project_path, ml_summary, predictions, zip_metadata=None):
    """
    Store ML model results to database
    """
    try:
        # Generate a project ID
        project_id = f"ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Convert zip_metadata to JSON-serializable format if it exists
        serializable_metadata = {}
        if zip_metadata:
            if isinstance(zip_metadata, dict):
                # If it's already a dict, use it
                serializable_metadata = zip_metadata
            elif hasattr(zip_metadata, '__dict__'):
                # If it's an object with __dict__, convert it
                serializable_metadata = {k: v for k, v in zip_metadata.__dict__.items() 
                                       if not k.startswith('_')}
            else:
                # Try to convert to string representation
                serializable_metadata = {"metadata": str(zip_metadata)}
        
        # Prepare skills data
        skills_data = {
            "project_id": project_id,
            "analysis_type": "ml_model",
            "source": "local_ml",
            "ml_summary": ml_summary,
            "predictions": predictions,
            "file_path": project_path,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="ml_analysis",
            skills_data=skills_data,
            source="ml",
            file_path=project_path,
            metadata=serializable_metadata
        )
        
        print(f"✅ ML results stored in database with project ID: {project_id}")
        return project_id
        
    except Exception as e:
        print(f"❌ Failed to store ML results: {e}")
        import traceback
        traceback.print_exc()  # Add this for debugging
        return None

# Also update the store_llm_results_to_db function similarly:
def store_llm_results_to_db(project_path, llm_response, predictions, project_id=None, zip_metadata=None):
    """
    Store LLM analysis results to database
    """
    try:
        if not project_id:
            project_id = f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Convert zip_metadata to JSON-serializable format
        serializable_metadata = {}
        if zip_metadata:
            if isinstance(zip_metadata, dict):
                serializable_metadata = zip_metadata
            elif hasattr(zip_metadata, '__dict__'):
                serializable_metadata = {k: v for k, v in zip_metadata.__dict__.items() 
                                       if not k.startswith('_')}
            else:
                serializable_metadata = {"metadata": str(zip_metadata)}
        
        # Extract skills from LLM response
        llm_skills = extract_skills_from_llm_response(llm_response)
        
        # Prepare LLM data
        llm_data = {
            "project_id": project_id,
            "analysis_type": "llm_analysis",
            "source": "ollama",
            "llm_response": llm_response,
            "extracted_skills": llm_skills,
            "predictions": predictions,
            "file_path": project_path,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="llm_analysis",
            skills_data=llm_data,
            source="ollama",
            file_path=project_path,
            metadata=serializable_metadata
        )
        
        # Also store detailed skills if extracted
        if llm_skills:
            SkillsRepository.store_detailed_skills(
                project_id=project_id,
                skills_list=llm_skills,
                source="ollama",
                confidence=0.8,
                file_path=project_path,
                context="LLM analysis"
            )
        
        print(f"✅ LLM results stored in database with project ID: {project_id}")
        return project_id
        
    except Exception as e:
        print(f"❌ Failed to store LLM results: {e}")
        import traceback
        traceback.print_exc()  # Add this for debugging
        return None

# Keep the rest of the file the same...
def store_llm_results_to_db(project_path, llm_response, predictions, project_id=None, zip_metadata=None):
    """
    Store LLM analysis results to database
    """
    try:
        if not project_id:
            project_id = f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Extract skills from LLM response (you might need to parse this)
        llm_skills = extract_skills_from_llm_response(llm_response)
        
        # Prepare LLM data
        llm_data = {
            "project_id": project_id,
            "analysis_type": "llm_analysis",
            "source": "ollama",
            "llm_response": llm_response,
            "extracted_skills": llm_skills,
            "predictions": predictions,
            "file_path": project_path,
            "metadata": zip_metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="llm_analysis",
            skills_data=llm_data,
            source="ollama",
            file_path=project_path,
            metadata=zip_metadata
        )
        
        # Also store detailed skills if extracted
        if llm_skills:
            SkillsRepository.store_detailed_skills(
                project_id=project_id,
                skills_list=llm_skills,
                source="ollama",
                confidence=0.8,
                file_path=project_path,
                context="LLM analysis"
            )
        
        print(f"✅ LLM results stored in database with project ID: {project_id}")
        return project_id
        
    except Exception as e:
        print(f"❌ Failed to store LLM results: {e}")
        return None

def extract_skills_from_llm_response(llm_response):
    """
    Extract skills from LLM response text
    This is a simple implementation - you might need to enhance it
    """
    skills = []
    # Simple keyword matching - enhance based on your needs
    skill_keywords = [
        "python", "javascript", "java", "c++", "docker", "postgresql",
        "machine learning", "deep learning", "web development", "api",
        "frontend", "backend", "database", "git", "testing", "ci/cd"
    ]
    
    response_lower = llm_response.lower()
    for skill in skill_keywords:
        if skill in response_lower:
            skills.append(skill.title())
    
    return list(set(skills))  # Remove duplicates

def get_project_summary(project_id):
    """Get summary of stored analysis for a project"""
    try:
        return SkillsRepository.get_project_skills_summary(project_id)
    except Exception as e:
        print(f"Error getting project summary: {e}")
        return None