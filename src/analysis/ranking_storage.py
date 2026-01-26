"""
Ranking Storage Module
Stores and manages project rankings and summaries in the database
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from config.db_config import with_db_cursor, get_connection
from account.user_manager import AuthManager


def init_ranking_storage_table():
    """Create the project_rankings table if it doesn't exist."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_rankings (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
                    rank_position INTEGER NOT NULL,
                    score FLOAT NOT NULL,
                    summary TEXT,
                    ranking_data JSONB,
                    user_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, rank_position, user_name)
                );
            """)
            
            # Add user_name column if it doesn't exist (migration)
            cursor.execute("""
                ALTER TABLE project_rankings
                ADD COLUMN IF NOT EXISTS user_name VARCHAR(255);
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_rankings_project_id 
                ON project_rankings(project_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_rankings_rank_position 
                ON project_rankings(rank_position);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_rankings_user_name 
                ON project_rankings(user_name);
            """)
            
        print("Project rankings table initialized")
    except Exception as e:
        print(f"Error initializing project_rankings table: {e}")
        raise


def save_rankings_to_db(ranked_projects: List[Dict[str, Any]], summaries: Optional[Dict[int, str]] = None) -> bool:
    """
    Save ranked projects and their summaries to the database.
    Preserves existing summaries if new summary is not provided or is empty.
    Only saves rankings for the current logged-in user.
    """
    try:
        init_ranking_storage_table()
        
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            # Get existing summaries before clearing (to preserve them if needed)
            existing_summaries = {}
            cursor.execute(
                "SELECT project_id, summary FROM project_rankings WHERE user_name = %s",
                (user_name,)
            )
            for row in cursor.fetchall():
                if row[1]:  # If summary exists and is not None/empty
                    existing_summaries[row[0]] = row[1]
            
            # Clear existing rankings for current user only
            cursor.execute("DELETE FROM project_rankings WHERE user_name = %s", (user_name,))
            
            # Insert new rankings
            for rank_pos, project in enumerate(ranked_projects, start=1):
                project_id = project.get("project_id")
                score = project.get("score", 0.0)
                
                # Use new summary if provided and not empty, otherwise preserve existing
                if summaries and project_id in summaries and summaries[project_id]:
                    summary = summaries[project_id]
                elif project.get("summary"):
                    summary = project.get("summary")
                elif project_id in existing_summaries:
                    summary = existing_summaries[project_id]
                else:
                    summary = ""
                
                ranking_data = json.dumps({
                    "analysis": project.get("analysis", {}),
                    "filename": project.get("filename", ""),
                    "created_at": project.get("created_at").isoformat() if project.get("created_at") else None
                })
                
                cursor.execute("""
                    INSERT INTO project_rankings (
                        project_id, rank_position, score, summary, ranking_data, user_name, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (project_id, rank_position, user_name) 
                    DO UPDATE SET
                        score = EXCLUDED.score,
                        summary = EXCLUDED.summary,
                        ranking_data = EXCLUDED.ranking_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (project_id, rank_pos, score, summary, ranking_data, user_name))
        
        return True
    except Exception as e:
        print(f"Error saving rankings to database: {e}")
        return False


def get_stored_rankings() -> List[Dict[str, Any]]:
    """
    Retrieve all stored rankings from the database for the current logged-in user.
    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Warning: No user logged in")
            return []
        
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    project_id,
                    rank_position,
                    score,
                    summary,
                    ranking_data,
                    created_at,
                    updated_at
                FROM project_rankings
                WHERE user_name = %s
                ORDER BY rank_position ASC
            """, (user_name,))
            
            results = cursor.fetchall()
        
        rankings = []
        for row in results:
            # JSONB columns are already parsed as dicts by psycopg3
            ranking_data = row[5] if row[5] else {}
            rankings.append({
                "id": row[0],
                "project_id": row[1],
                "rank_position": row[2],
                "score": float(row[3]),
                "summary": row[4],
                "ranking_data": ranking_data,
                "created_at": row[6],
                "updated_at": row[7]
            })
        
        return rankings
    except Exception as e:
        print(f"Error retrieving stored rankings: {e}")
        return []


def get_stored_ranking_by_project_id(project_id: int) -> Optional[Dict[str, Any]]:
    """
    Get stored ranking for a specific project for the current logged-in user.

    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Warning: No user logged in")
            return None
        
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    project_id,
                    rank_position,
                    score,
                    summary,
                    ranking_data,
                    created_at,
                    updated_at
                FROM project_rankings
                WHERE project_id = %s AND user_name = %s
            """, (project_id, user_name))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # JSONB columns are already parsed as dicts by psycopg3
            ranking_data = row[5] if row[5] else {}
            return {
                "id": row[0],
                "project_id": row[1],
                "rank_position": row[2],
                "score": float(row[3]),
                "summary": row[4],
                "ranking_data": ranking_data,
                "created_at": row[6],
                "updated_at": row[7]
            }
    except Exception as e:
        print(f"Error retrieving ranking for project {project_id}: {e}")
        return None


def update_ranking_score(project_id: int, new_score: float) -> bool:
    """
    Update the score for a stored ranking for the current logged-in user.

    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            cursor.execute("""
                UPDATE project_rankings
                SET score = %s, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = %s AND user_name = %s
            """, (new_score, project_id, user_name))
            
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating ranking score: {e}")
        return False


def update_ranking_summary(project_id: int, new_summary: str) -> bool:
    """
    Update the summary for a stored ranking for the current logged-in user.
    
    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            cursor.execute("""
                UPDATE project_rankings
                SET summary = %s, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = %s AND user_name = %s
            """, (new_summary, project_id, user_name))
            
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating ranking summary: {e}")
        return False


def update_ranking_position(project_id: int, new_position: int) -> bool:
    """
    Update the rank position for a stored ranking for the current logged-in user.

    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            # Check if the new position is already taken by current user's ranking
            cursor.execute("""
                SELECT project_id FROM project_rankings
                WHERE rank_position = %s AND project_id != %s AND user_name = %s
            """, (new_position, project_id, user_name))
            
            existing_project = cursor.fetchone()
            if existing_project:
                # Swap positions if needed
                existing_id = existing_project[0]
                # Get current position
                cursor.execute("""
                    SELECT rank_position FROM project_rankings
                    WHERE project_id = %s AND user_name = %s
                """, (project_id, user_name))
                current_pos_result = cursor.fetchone()
                if current_pos_result:
                    current_pos = current_pos_result[0]
                    # Swap
                    cursor.execute("""
                        UPDATE project_rankings
                        SET rank_position = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE project_id = %s AND user_name = %s
                    """, (current_pos, existing_id, user_name))
            
            cursor.execute("""
                UPDATE project_rankings
                SET rank_position = %s, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = %s AND user_name = %s
            """, (new_position, project_id, user_name))
            
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating ranking position: {e}")
        return False


def delete_stored_rankings() -> bool:
    """
    Delete all stored rankings from the database for the current logged-in user.

    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            cursor.execute("DELETE FROM project_rankings WHERE user_name = %s", (user_name,))
            return True
    except Exception as e:
        print(f"Error deleting stored rankings: {e}")
        return False


def clean_error_summaries() -> bool:
    """
    Remove error messages from stored summaries in the database for the current logged-in user.
    This clears out invalid summaries that start with 'Error:'.
    
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    try:
        # Get current user for data isolation
        user_name = AuthManager.get_current_username()
        if not user_name:
            print("Error: No user logged in")
            return False
        
        with with_db_cursor() as cursor:
            # Update summaries that are error messages to NULL for current user only
            cursor.execute("""
                UPDATE project_rankings
                SET summary = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE summary LIKE 'Error:%' AND user_name = %s
            """, (user_name,))
            
            affected_rows = cursor.rowcount
            if affected_rows > 0:
                print(f"Cleaned {affected_rows} error summaries from database")
            else:
                print("No error summaries found in database")
            
            return True
    except Exception as e:
        print(f"Error cleaning error summaries: {e}")
        return False

