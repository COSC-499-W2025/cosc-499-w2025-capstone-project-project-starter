"""
Project Ranking Module
Ranks projects using database Key Metrics that are pulled rom uploaded files and file contents from other features
"""
from typing import Dict, List, Any, Optional
from config.db_config import get_connection
from analysis.key_metrics import analyze_project_from_db
from project_summarizer import summarize_project
from analysis.ranking_storage import save_rankings_to_db, get_stored_ranking_by_project_id, get_stored_rankings
import os


def calculate_project_score(analysis_data: Dict[str, Any]) -> float:
    """
    this is a function to calculate the score of a project based on the analysis data
    """
    score = 0.0
    
    # Database key_metrics result
    if "by_activity" in analysis_data:
        # Calculate score based on activity types (count and bytes, not pre-calculated score)
        # Weights based on activity type importance (matching activity_classifier weights)
        activity_weights = {"code": 3, "doc": 1.5, "data": 2, "media": 1, "config": 1, "other": 1}
        
        for activity_type, data in analysis_data["by_activity"].items():
            # Use count and bytes instead of pre-calculated score
            file_count = data.get("count", 0)
            total_bytes = data.get("bytes", 0)
            weight = activity_weights.get(activity_type, 1)
            
            # File count contribution
            score += file_count * weight * 10
            
            # Size contribution (normalized, smaller impact than count)
            score += total_bytes / 1000 * weight * 0.1

        # Overall size/complexity signal
        total_lines = analysis_data.get("totals", {}).get("lines", 0)
        score += total_lines * 0.1

        # Language diversity bonus
        by_language = analysis_data.get("by_language", [])
        score += len(by_language) * 10

    # Backward-compatible support if a local analyzer dict is passed
    elif "structure" in analysis_data:
        metrics = analysis_data.get("metrics", {})
        structure = analysis_data.get("structure", {})
        skills = analysis_data.get("skills", [])
        
        # Lines of code bonus
        total_loc = metrics.get("total_lines_of_code", 0)
        score += total_loc * 0.1
        
        # Structure bonuses
        if structure.get("has_tests"):
            score += 50  # Tests are important!
        if structure.get("has_docs"):
            score += 30  # Documentation is valuable
        if structure.get("has_config"):
            score += 20  # Configuration shows maturity
        
        # Skills diversity
        score += len(skills) * 15
        
        # Framework detection bonus
        frameworks = analysis_data.get("frameworks", [])
        score += len(frameworks) * 25
        
        # Code file ratio (more code = better for portfolio)
        code_files = metrics.get("code_files", 0)
        total_files = metrics.get("code_files", 0) + metrics.get("document_files", 0) + \
                      metrics.get("design_files", 0) + metrics.get("other_files", 0)
        if total_files > 0:
            code_ratio = code_files / total_files
            score += code_ratio * 100
    
    return round(score, 2)


def rank_all_projects() -> List[Dict[str, Any]]:
    """
    Rank all uploaded projects in the database by composite score using key_metrics.
    Uses stored scores from database if available, otherwise calculates new scores.
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, filename, created_at FROM uploaded_files")
            projects = cur.fetchall()

        if not projects:
            return []

        # Get all stored rankings to check for existing scores
        stored_rankings = get_stored_rankings()
        stored_scores = {r['project_id']: r['score'] for r in stored_rankings}

        ranked_projects: List[Dict[str, Any]] = []
        for project_id, filename, created_at in projects:
            try:
                # Use stored score if available, otherwise calculate
                if project_id in stored_scores:
                    score = stored_scores[project_id]
                    # Still need analysis data for other purposes, but use stored score
                    analysis = analyze_project_from_db(project_id, silent=True)
                else:
                    analysis = analyze_project_from_db(project_id, silent=True)
                    score = calculate_project_score(analysis)
                
                ranked_projects.append({
                    "project_id": project_id,
                    "filename": filename,
                    "created_at": created_at,
                    "score": score,
                    "analysis": analysis,
                })
            except Exception as e:
                print(f"Error analyzing project {project_id}: {e}")
                continue

        ranked_projects.sort(key=lambda x: x["score"], reverse=True)
        return ranked_projects
    except Exception as e:
        print(f"Error ranking projects: {e}")
        return []

def rank_local_project(project_path: str) -> Dict[str, Any]:
    """Deprecated: local ranking disabled; use database key metrics instead."""
    raise NotImplementedError("Local ranking disabled; use key-metrics-based ranking from DB.")



def display_rankings(ranked_projects: List[Dict[str, Any]]):
    """
    Display ranked projects in a simple format showing only project names and scores.
    
    Args:
        ranked_projects: List of ranked project dictionaries
    """
    if not ranked_projects:
        print("\nNo projects to rank.")
        return
    
    print("\n" + "="*80)
    print("PROJECT RANKINGS")
    print("="*80)
    print(f"{'Rank':<6} {'Score':<10} {'Project Name':<60}")
    print("-"*80)
    
    for i, project in enumerate(ranked_projects, 1):
        filename = project["filename"][:58] + ".." if len(project["filename"]) > 60 else project["filename"]
        print(f"{i:<6} {project['score']:<10} {filename:<60}")
    
    print("="*80)


def rank_and_summarize_top_projects() -> None:
    """
    Rank all projects and summarize the top 3 projects (without displaying rankings).
    """
    print("\nRanking all projects...")
    ranked_projects = rank_all_projects()
    
    if not ranked_projects:
        print("\nNo projects to rank.")
        return
    
    # Summarize top 3 projects
    top_count = min(3, len(ranked_projects))
    if top_count > 0:
        print(f"\n{'='*80}")
        print(f"SUMMARIZING TOP {top_count} PROJECTS")
        print("="*80)
        
        for i in range(top_count):
            project = ranked_projects[i]
            project_id = project['project_id']
            print(f"\n{'='*80}")
            print(f"TOP {i+1} PROJECT: {project['filename']} (Score: {project['score']})")
            print("="*80)
            
            # Check if summary exists in database
            stored_ranking = get_stored_ranking_by_project_id(project_id)
            if stored_ranking and stored_ranking.get('summary'):
                print("\nUsing stored summary from database...")
                print(stored_ranking['summary'])
            else:
                print("\nGenerating summary...")
                try:
                    summary = summarize_project(project_id)
                    print(summary)
                except Exception as e:
                    print(f"Error generating summary for project {project_id}: {e}")
            
            if i < top_count - 1:
                print("\n" + "-"*80)


def save_rankings_with_summaries(ranked_projects: List[Dict[str, Any]], generate_summaries: bool = True) -> bool:
    """
    Save ranked projects and their summaries to the database.
    
    Args:
        ranked_projects: List of ranked project dictionaries
        generate_summaries: If True, generate summaries for all projects. If False, only save rankings.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not ranked_projects:
        print("\nNo projects to save.")
        return False
    
    summaries = {}
    
    if generate_summaries:
        print("\nProcessing summaries for all projects...")
        for i, project in enumerate(ranked_projects, 1):
            project_id = project['project_id']
            filename = project['filename']
            
            # Check if summary exists in database first
            stored_ranking = get_stored_ranking_by_project_id(project_id)
            if stored_ranking and stored_ranking.get('summary'):
                print(f"  [{i}/{len(ranked_projects)}] Using stored summary for: {filename}")
                summaries[project_id] = stored_ranking['summary']
            else:
                print(f"  [{i}/{len(ranked_projects)}] Generating summary for: {filename}")
                try:
                    summary = summarize_project(project_id)
                    summaries[project_id] = summary
                except Exception as e:
                    print(f"    Error generating summary: {e}")
                    summaries[project_id] = f"Error generating summary: {e}"
    
    print("\nSaving rankings and summaries to database...")
    success = save_rankings_to_db(ranked_projects, summaries if summaries else None)
    
    if success:
        print(f"\n✓ Successfully saved {len(ranked_projects)} project rankings to database.")
        if summaries:
            print(f"✓ Successfully saved {len(summaries)} project summaries to database.")
    else:
        print("\n✗ Failed to save rankings to database.")
    
    return success

