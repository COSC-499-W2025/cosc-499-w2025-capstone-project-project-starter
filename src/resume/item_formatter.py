from typing import Dict, Any, List
from datetime import datetime
from src.common.schemas import ResumeItemResponse

class ItemFormatter:
    """
    Dedicated formatter for transforming a SINGLE project's data 
    into a structured API response (Milestone 2).
    
    Differing from ResumeFormatter (which handles full document generation),
    this class focuses on granular, object-level data transformation.
    """

    @staticmethod
    def format_resume_item(project_data: Dict[str, Any]) -> ResumeItemResponse:
        """
        Transforms raw project summary data into a ResumeItemResponse.
        
        Args:
            project_data (dict): Raw dictionary from ProjectSummarizer.
            
        Returns:
            ResumeItemResponse: Validated Pydantic model.
        """
        # 1. Safe Data Extraction
        info = project_data.get('project_info', {})
        # Fallback to filename if name isn't present
        raw_name = info.get('filename', 'Untitled Project')
        
        # 2. Name Cleaning Logic (Replicated from ResumeManager to avoid dependency)
        clean_title = ItemFormatter._clean_project_title(raw_name)
        
        # 3. Dates
        created_at = info.get('created_at')
        date_str = ItemFormatter._format_date(created_at)

        # 4. Tech Stack Aggregation
        # Combine languages, frameworks, and deep-analysis skills
        langs = project_data.get('languages', {}).get('detected_languages', [])
        frameworks = project_data.get('frameworks', [])
        
        # Handle cases where frameworks might be a dict or list
        if isinstance(frameworks, dict):
            frameworks = list(frameworks.keys())
            
        # Deduplicate and sort
        tech_stack = sorted(list(set(langs + frameworks)))

        # 5. Smart Bullet Point Generation
        bullets = ItemFormatter._generate_smart_bullets(project_data, clean_title, tech_stack)

        return ResumeItemResponse(
            project_title=clean_title,
            role="Software Developer", # Default, can be updated via user preferences later
            start_date=date_str,
            end_date="Present",
            description_bullets=bullets,
            technologies=tech_stack[:10] # Cap at 10 for resume brevity
        )

    @staticmethod
    def _clean_project_title(filename: str) -> str:
        """Cleans filenames into professional project titles."""
        if not filename:
            return "Unknown Project"
        
        name = filename
        # Remove common extensions and suffixes
        for suffix in ['.zip', '-main', '-master', '_main', '_master']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                
        # Replace separators with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Title Case
        return " ".join([w.capitalize() for w in name.split()])

    @staticmethod
    def _format_date(date_val: Any) -> str:
        """Formats date to 'Month YYYY'."""
        if not date_val:
            return "N/A"
        try:
            # Handle both string ISO format and datetime objects
            if isinstance(date_val, str):
                dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
            else:
                dt = date_val
            return dt.strftime("%b %Y")
        except Exception:
            return str(date_val)[:10]

    @staticmethod
    def _generate_smart_bullets(data: Dict[str, Any], title: str, tech: List[str]) -> List[str]:
        """Generates dynamic, metrics-driven bullet points."""
        bullets = []
        stats = data.get('file_statistics', {})
        loc = stats.get('total_lines_of_code', 0)
        file_count = stats.get('total_files', 0)
        tech_str = f" using {', '.join(tech[:3])}" if tech else ""
        bullets.append(f"Engineered '{title}'{tech_str}, managing {file_count} source files.")
        if loc > 500:
            bullets.append(f"Maintained a codebase of {loc}+ lines, ensuring modularity and readability.")
        
        # Bullet 3: Features (Tests/Docs)
        structure = data.get('project_structure', {})
        if structure.get('has_tests'):
             bullets.append("Implemented comprehensive unit tests to ensure system reliability.")
        elif structure.get('has_docs'):
             bullets.append("Created detailed technical documentation to facilitate code maintenance.")
             
        # Fallback if no specific features found
        if len(bullets) < 2:
            bullets.append("Optimized application logic for performance and scalability.")
            
        return bullets