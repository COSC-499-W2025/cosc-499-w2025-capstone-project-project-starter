from src.common.constants import COMMON_PROJECT_SUFFIXES

def clean_project_title(filename: str) -> str:
    """Standardizes repository filenames into professional project titles."""
    if not filename:
        return "Unknown Project"
    
    name = filename
    # Remove common extensions and suffixes
    for suffix in COMMON_PROJECT_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            
    # Replace separators with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    
    # Title Case
    return " ".join([w.capitalize() for w in name.split()])