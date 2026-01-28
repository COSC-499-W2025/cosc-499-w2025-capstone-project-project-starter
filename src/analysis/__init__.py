from .analysis_router import AnalysisRouter

__all__ = [
    "AnalysisRouter",
    "analyze_zip_project",
    "analyze_zip_projects_in_dir",
]

# Lazy imports for ranking functionality
def rank_all_projects():
    from . import project_ranking
    return project_ranking.rank_all_projects()

def display_rankings(ranked_projects):
    from . import project_ranking
    return project_ranking.display_rankings(ranked_projects)

def calculate_project_score(analysis_data):
    from . import project_ranking
    return project_ranking.calculate_project_score(analysis_data)

def rank_local_project(project_path):
    from . import project_ranking
    return project_ranking.rank_local_project(project_path)

def analyze_zip_project(zip_path, max_readme_bytes=65536):
    from .zip_project_analyzer import analyze_zip_project
    return analyze_zip_project(zip_path, max_readme_bytes=max_readme_bytes)

def analyze_zip_projects_in_dir(base_dir, max_readme_bytes=65536):
    from .zip_project_analyzer import analyze_zip_projects_in_dir
    return analyze_zip_projects_in_dir(base_dir, max_readme_bytes=max_readme_bytes)
