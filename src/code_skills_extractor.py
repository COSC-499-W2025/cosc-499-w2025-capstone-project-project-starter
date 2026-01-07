# src/code_skills_extractor.py
import re
from typing import Dict, Any, List, Set
from .skills_config import SKILLS

class CodeSkillsExtractor:
    def __init__(self):
        # Define regex patterns for each skill (simplified from your training file)
        self.skill_patterns = self._compile_skill_patterns()
        
    def _compile_skill_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for each skill"""
        patterns = {}
        
        # Simplified patterns based on your training file
        patterns["Testing"] = re.compile(r"\bpytest\b|\bjunit\b|\bunittest\b|\bRSpec\b|\bMocha\b|\bJest\b")
        patterns["CI"] = re.compile(r"\.github\/workflows|Jenkinsfile|\.gitlab-ci\.yml")
        patterns["Containerization"] = re.compile(r"^\s*FROM\s+", re.I | re.M)
        patterns["Python"] = re.compile(r"\bimport\s+\w+|\bdef\s+\w+\s*\(|\bclass\s+\w+")
        patterns["JavaScript"] = re.compile(r"\bfunction\s+\w+|\bconst\s+\w+|\blet\s+\w+|\b=>\s*{")
        patterns["SQL-DML"] = re.compile(r"\bSELECT\b.*\bFROM\b|\bINSERT\s+INTO\b|\bUPDATE\b|\bDELETE\b", re.I)
        patterns["SQL-DDL"] = re.compile(r"\bCREATE\s+TABLE\b|\bALTER\s+TABLE\b|\bDROP\s+TABLE\b", re.I)
        patterns["Web-Backend"] = re.compile(r"\bExpress\(\)|\bFlask\(\)|\bDjango\b|\bFastAPI\(\)", re.I)
        patterns["Web-Frontend"] = re.compile(r"\bReact\b|\bVue\b|\bAngular\b|\buseState\b|\buseEffect\b", re.I)
        patterns["Database-ORM"] = re.compile(r"\bSQLAlchemy\b|\bsequelize\b|\bmongoose\b|\bHibernate\b", re.I)
        patterns["Database-NoSQL"] = re.compile(r"\bMongoDB\b|\bCassandra\b|\bRedis\b|\bFirebase\b", re.I)
        patterns["Docker"] = re.compile(r"\bdocker\b|\bDockerfile\b|\bdocker-compose\b", re.I)
        patterns["Kubernetes"] = re.compile(r"\bkubectl\b|\bDeployment\b|\bPod\b|\bService\b", re.I)
        patterns["AWS"] = re.compile(r"\bboto3\b|\bS3\b|\bLambda\b|\bEC2\b", re.I)
        patterns["Machine Learning"] = re.compile(r"\btensorflow\b|\bkeras\b|\bpytorch\b|\bsklearn\b", re.I)
        
        # Add more patterns as needed from your training file
        return patterns
    
    def extract_skills(self, code_content: str, file_path: str = None) -> Dict[str, Any]:
        """
        Extract skills from code content using regex patterns
        
        Args:
            code_content: Source code content
            file_path: Path of the file
            
        Returns:
            Structured skills data
        """
        skills_detected = {skill: False for skill in SKILLS}
        skill_evidence = {skill: [] for skill in SKILLS}
        
        # Check file path for hints
        if file_path:
            file_path_lower = file_path.lower()
            if "test" in file_path_lower or "__test__" in file_path_lower:
                skills_detected["Testing"] = True
                skill_evidence["Testing"].append(f"Test file: {file_path}")
            
            if "docker" in file_path_lower or "Dockerfile" in file_path:
                skills_detected["Containerization"] = True
                skill_evidence["Containerization"].append(f"Docker file: {file_path}")
            
            if "migration" in file_path_lower or ".sql" in file_path:
                skills_detected["SQL-DDL"] = True
                skill_evidence["SQL-DDL"].append(f"SQL file: {file_path}")
        
        # Check code content with patterns
        for skill, pattern in self.skill_patterns.items():
            if skill in SKILLS and pattern.search(code_content):
                skills_detected[skill] = True
                # Extract example matches
                matches = pattern.findall(code_content[:1000])
                if matches:
                    unique_matches = list(set(matches[:3]))  # Show first 3 unique matches
                    skill_evidence[skill].append(f"Code patterns: {', '.join(unique_matches)}")
        
        # Categorize skills
        from .skills_processor import SkillsProcessor
        skill_categories = SkillsProcessor._categorize_skills(skills_detected)
        
        return {
            "detected_skills": skills_detected,
            "skill_evidence": skill_evidence,
            "skill_categories": skill_categories,
            "source": "code_analysis",
            "file_path": file_path,
            "content_preview": code_content[:1000]
        }