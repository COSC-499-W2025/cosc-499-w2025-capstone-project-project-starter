# src/skills_processor.py (fix imports at the top)
import json
import re
import os
import hashlib
import time
from typing import Dict, Any, List, Set

# Fix imports - try different approaches
try:
    # Try absolute import first
    from skills_config import SKILLS, SKILL_CATEGORIES
except ImportError:
    try:
        # Try relative import
        from .skills_config import SKILLS, SKILL_CATEGORIES
    except ImportError:
        # Fallback - define SKILLS inline (from your ML file)
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
        SKILL_CATEGORIES = {
            "core_engineering": SKILLS[:16],
            "web_backend": SKILLS[16:24],
            "data_storage": SKILLS[24:30],
            "cloud_devops": SKILLS[30:35],
            "systems_lowlevel": SKILLS[35:40],
            "data_ml_ai": SKILLS[40:51],
            "other_domains": SKILLS[51:]
        }

class SkillsProcessor:
    @staticmethod
    def extract_skills_from_llm_response(llm_response: str) -> Dict[str, Any]:
        """
        Extract structured skills from LLM response text using the defined skills list
        
        Args:
            llm_response: Raw text response from LLM
            
        Returns:
            Structured skills data matching the defined SKILLS list
        """
        # Initialize with all skills as False/not detected
        skills_detected = {skill: False for skill in SKILLS}
        skill_evidence = {skill: [] for skill in SKILLS}
        
        # Try to parse as JSON first
        try:
            if llm_response.strip().startswith('{'):
                json_data = json.loads(llm_response)
                return SkillsProcessor._parse_llm_json_response(json_data, skills_detected, skill_evidence)
        except json.JSONDecodeError:
            pass
        
        # Otherwise, use text extraction with the defined skills
        return SkillsProcessor._extract_skills_from_text(llm_response, skills_detected, skill_evidence)
    
    @staticmethod
    def _parse_llm_json_response(json_data: Dict, skills_detected: Dict, skill_evidence: Dict) -> Dict[str, Any]:
        """Parse skills from JSON LLM response"""
        skills_data = {
            "detected_skills": skills_detected.copy(),
            "skill_evidence": skill_evidence.copy(),
            "skill_categories": {},
            "raw_llm_response": json.dumps(json_data)[:5000],
            "parsed_from_json": True
        }
        
        # Look for skills in the JSON response
        response_text = json.dumps(json_data).lower()
        
        for skill in SKILLS:
            skill_lower = skill.lower()
            # Check if skill is mentioned in response
            if skill_lower in response_text or skill.replace("-", " ").lower() in response_text:
                skills_data["detected_skills"][skill] = True
                skills_data["skill_evidence"][skill].append("Mentioned in LLM analysis")
        
        # Categorize detected skills
        skills_data["skill_categories"] = SkillsProcessor._categorize_skills(skills_data["detected_skills"])
        
        return skills_data
    
    @staticmethod
    def _extract_skills_from_text(text: str, skills_detected: Dict, skill_evidence: Dict) -> Dict[str, Any]:
        """Extract skills from text response"""
        text_lower = text.lower()
        
        # Check each skill for mentions in the text
        for skill in SKILLS:
            skill_lower = skill.lower()
            skill_words = skill.replace("-", " ").lower()
            
            # Check for skill mention
            if skill_lower in text_lower or skill_words in text_lower:
                skills_detected[skill] = True
                
                # Find context around the mention
                idx = text_lower.find(skill_lower)
                if idx == -1:
                    idx = text_lower.find(skill_words)
                
                if idx != -1:
                    context_start = max(0, idx - 50)
                    context_end = min(len(text), idx + len(skill) + 50)
                    context = text[context_start:context_end].strip()
                    skill_evidence[skill].append(f"Context: ...{context}...")
        
        # Categorize detected skills
        skill_categories = SkillsProcessor._categorize_skills(skills_detected)
        
        skills_data = {
            "detected_skills": skills_detected,
            "skill_evidence": skill_evidence,
            "skill_categories": skill_categories,
            "raw_llm_response": text[:5000],
            "parsed_from_text": True
        }
        
        return skills_data
    
    @staticmethod
    def _categorize_skills(detected_skills: Dict[str, bool]) -> Dict[str, List[str]]:
        """Categorize detected skills by category"""
        categorized = {category: [] for category in SKILL_CATEGORIES.keys()}
        
        for skill, is_detected in detected_skills.items():
            if is_detected:
                for category, skills in SKILL_CATEGORIES.items():
                    if skill in skills:
                        categorized[category].append(skill)
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
    
    @staticmethod
    def process_ml_summary(ml_summary: Dict) -> Dict[str, Any]:
        """
        Process ML model summary into skills format
        
        Args:
            ml_summary: Summary from ML model (parsed from parse_core)
            
        Returns:
            Structured skills data matching SKILLS format
        """
        # Initialize with all skills as False
        skills_detected = {skill: False for skill in SKILLS}
        skill_evidence = {skill: [] for skill in SKILLS}
        
        if not isinstance(ml_summary, dict):
            return {
                "detected_skills": skills_detected,
                "skill_evidence": skill_evidence,
                "skill_categories": {},
                "source": "ml_model",
                "raw_ml_summary": str(ml_summary)[:2000]
            }
        
        # Extract skills from ML summary based on its structure
        # This depends on how parse_core.summarize_results returns data
        ml_text = json.dumps(ml_summary).lower()
        
        # Check each skill in the ML summary
        for skill in SKILLS:
            skill_lower = skill.lower()
            if skill_lower in ml_text:
                skills_detected[skill] = True
                skill_evidence[skill].append("Detected by ML model")
        
        # Categorize detected skills
        skill_categories = SkillsProcessor._categorize_skills(skills_detected)
        
        return {
            "detected_skills": skills_detected,
            "skill_evidence": skill_evidence,
            "skill_categories": skill_categories,
            "source": "ml_model",
            "raw_ml_summary": json.dumps(ml_summary)[:5000],
            "ml_details": ml_summary
        }
    
    @staticmethod
    def extract_skills_from_code_content(code_content: str, file_path: str = None) -> Dict[str, Any]:
        """
        Extract skills directly from code content using regex patterns (similar to your ML training)
        
        Args:
            code_content: Source code content
            file_path: Path of the file (for additional context)
            
        Returns:
            Structured skills data
        """
        from .code_skills_extractor import CodeSkillsExtractor
        
        extractor = CodeSkillsExtractor()
        return extractor.extract_skills(code_content, file_path)
    
    @staticmethod
    def generate_project_id(zip_path: str) -> str:
        """Generate a unique project ID from zip path"""
        import hashlib
        import os
        import time
        
        file_name = os.path.basename(zip_path)
        timestamp = int(time.time())
        unique_string = f"{file_name}_{timestamp}"
        
        project_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        return f"proj_{project_id}"
    
    @staticmethod
    def get_detected_skills_list(skills_data: Dict[str, Any]) -> List[str]:
        """Extract list of detected skills from skills data"""
        if "detected_skills" in skills_data:
            return [skill for skill, detected in skills_data["detected_skills"].items() if detected]
        return []