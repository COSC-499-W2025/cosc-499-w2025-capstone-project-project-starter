# src/db/skills_integration.py (COMPLETE FIXED VERSION)
import json
import uuid
import re
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

def extract_skills_from_ml_data(ml_summary, predictions):
    """
    Extract skill names from ML analysis results
    """
    skills = []
    
    # Convert everything to strings for pattern matching
    ml_text = str(ml_summary)
    pred_text = str(predictions)
    combined_text = ml_text + "\n" + pred_text
    
    print(f"DEBUG extract_skills_from_ml_data - Combined text preview: {combined_text[:500]}...")
    
    # Pattern 1: Look for "Skill-Name: files=X" pattern (from console output)
    pattern1 = r'([A-Z][a-zA-Z\-]+): files=\d+'
    matches = re.findall(pattern1, combined_text)
    skills.extend(matches)
    
    # Pattern 2: Look for indented skills in project summary
    pattern2 = r'^\s+([A-Z][a-zA-Z\-]+): files=\d+'
    matches = re.findall(pattern2, combined_text, re.MULTILINE)
    skills.extend(matches)
    
    # Pattern 3: Look for skills in dictionary format
    if isinstance(ml_summary, list):
        for item in ml_summary:
            if isinstance(item, dict):
                # Check for skill-related keys
                for key, value in item.items():
                    key_lower = str(key).lower()
                    if any(skill_word in key_lower for skill_word in ['skill', 'type', 'category', 'name']):
                        if value and isinstance(value, str) and len(value) > 2:
                            skills.append(value)
    
    # Pattern 4: Look in predictions
    if isinstance(predictions, list):
        for item in predictions:
            if isinstance(item, dict):
                # Look for 'skill' key
                if 'skill' in item and item['skill']:
                    skills.append(str(item['skill']))
                # Look for keys containing 'skill'
                for key, value in item.items():
                    if 'skill' in str(key).lower() and value and isinstance(value, str) and len(value) > 2:
                        skills.append(value)
    
    # Pattern 5: Look for common skill keywords
    skill_keywords = [
        "Testing", "CI", "Containerization", "Concurrency", "Performance", "Optimization",
        "Security", "Cryptography", "Logging", "Metrics", "Monitoring", "Tracing",
        "Infrastructure", "Build", "Package", "Scripting", "Automation", "CLI",
        "Web", "Frontend", "Backend", "Fullstack", "API", "Authentication",
        "Authorization", "Microservices", "Messaging", "Queueing", "Streaming",
        "SQL", "Database", "ORM", "NoSQL", "Graph", "Caching", "Cloud",
        "AWS", "GCP", "Azure", "Kubernetes", "BigData", "Systems", "Embedded",
        "Networking", "Parallel", "GPU", "Data", "Engineering", "Visualization",
        "Numerics", "ML", "Machine-Learning", "Deep-Learning", "NLP", "Vision",
        "Recommendation", "MLOps", "Probabilistic", "Game", "Functional",
        "Serialization", "Python", "JavaScript", "Java", "C++", "Docker", "PostgreSQL",
        "Git", "Functional-Programming"
    ]
    
    for skill in skill_keywords:
        if skill in combined_text:
            skills.append(skill)
    
    # Clean up: remove duplicates, empty strings, and very short strings
    skills = [s.strip() for s in skills if s and len(str(s).strip()) > 2]
    
    # Remove common false positives
    false_positives = ["Project", "File", "Path", "Summary", "Binary", "Non", "All"]
    skills = [s for s in skills if s not in false_positives]
    
    skills = list(set(skills))
    
    print(f"DEBUG extract_skills_from_ml_data - Extracted skills: {skills}")
    return skills

def store_ml_results_to_db(project_path, ml_summary, predictions, zip_metadata=None):
    """
    Store ML model results to database
    """
    try:
        # Generate a project ID
        project_id = f"ml_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Convert metadata to serializable format
        serializable_metadata = make_metadata_serializable(zip_metadata)
        
        # Extract skills BEFORE creating skills_data
        detected_skills = extract_skills_from_ml_data(ml_summary, predictions)
        
        # Prepare skills data - ensure everything is JSON serializable
        skills_data = {
            "project_id": project_id,
            "analysis_type": "ml_model",
            "source": "local_ml",
            "ml_summary": ml_summary if isinstance(ml_summary, (dict, list, str, int, float, bool, type(None))) else str(ml_summary),
            "predictions": predictions if isinstance(predictions, (dict, list, str, int, float, bool, type(None))) else str(predictions),
            "file_path": str(project_path),
            "detected_skills": detected_skills,  # Add detected skills to the data
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
        if detected_skills:
            SkillsRepository.store_detailed_skills(
                project_id=project_id,
                skills_list=detected_skills,
                source="ml",
                confidence=0.9,
                file_path=str(project_path),
                context="ML model analysis"
            )
            print(f"DEBUG: Stored {len(detected_skills)} skills to detailed_skills table")
        else:
            print("DEBUG: No skills to store in detailed_skills table")
        
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
            "predictions": predictions if isinstance(predictions, (dict, list, str, int, float, bool, type(None))) else str(predictions),
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