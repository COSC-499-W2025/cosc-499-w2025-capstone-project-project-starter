from __future__ import annotations
import argparse
from typing import Tuple
from pathlib import Path
import sys

# allowed "python -m src.tools.cleanup_insights"
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.db_config import get_connection  # noqa: E402

# Handle optional import for different psycopg versions
try:
    from psycopg import errors as pg_errors  # psycopg v3
except Exception:  # pragma: no cover
    pg_errors = None

# Check if a table exists in the database
def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    return cur.fetchone() is not None

# Delete insights and the uploaded file record for a specific project
def delete_insights(project_id: int, user_name: str = None) -> Tuple[int, int, int]:
    """
    Delete previously generated insights and the uploaded file itself for a project.
    
    Requirement: Delete previously generated insights and ensure files that are 
    shared across multiple reports do not get affected.
    
    This function safely deletes project-specific data with user isolation:
    - Verifies the project belongs to the specified user before deletion
    - file_contents are tied to uploaded_file_id (project_id), so deleting by 
      project_id only affects files from that specific project
    - Files from other projects remain untouched, ensuring shared files across 
      multiple reports are not affected
    
    Args:
        project_id: The ID of the project to delete
        user_name: Username to verify project ownership. If None, skips verification (not recommended)
        
    Returns: 
        Tuple of (deleted_metrics, deleted_files, deleted_projects)
          - deleted_metrics: Number of project_metrics records deleted
          - deleted_files: Number of file_contents records deleted  
          - deleted_projects: Number of uploaded_files records deleted (should be 1)
    
    Raises:
        PermissionError: If project doesn't belong to the specified user
        ValueError: If project_id is invalid
    """
    deleted_metrics = 0
    deleted_files = 0
    deleted_projects = 0

    with get_connection() as conn, conn.cursor() as cur:
        # Data Isolation: Verify project ownership if user_name is provided
        if user_name is not None:
            cur.execute(
                "SELECT id FROM uploaded_files WHERE id = %s AND user_name = %s;",
                (project_id, user_name)
            )
            if cur.fetchone() is None:
                raise PermissionError(
                    f"Project {project_id} not found or does not belong to user '{user_name}'"
                )
        # Clean up project_metrics if the table exists
        try:
            if _table_exists(cur, "project_metrics"):
                cur.execute("DELETE FROM project_metrics WHERE project_id = %s;", (project_id,))
                deleted_metrics = cur.rowcount or 0
        except Exception as e:
            # Some setups may not have project_metrics table
            # If the error indicates undefined table, we ignore it
            if pg_errors and isinstance(e, getattr(pg_errors, "UndefinedTable", tuple())):
                deleted_metrics = 0
            else:
                # Re-raise unexpected exceptions
                raise

        # Clean up file_contents
        cur.execute("DELETE FROM file_contents WHERE uploaded_file_id = %s;", (project_id,))
        deleted_files = cur.rowcount or 0

        # Finally remove the uploaded_files record itself
        cur.execute("DELETE FROM uploaded_files WHERE id = %s;", (project_id,))
        deleted_projects = cur.rowcount or 0

        conn.commit()

    return deleted_metrics, deleted_files, deleted_projects


# Entry point for command-line execution
def main():
    ap = argparse.ArgumentParser(description="Delete previously generated insights and the uploaded file for a project.")
    ap.add_argument("--project-id", "-p", type=int, required=True, help="uploaded_files.id / project_id to clean")
    ap.add_argument("--user-name", "-u", type=str, help="Username to verify project ownership (optional, but recommended for security)")
    ap.add_argument("--force", "-f", action="store_true", help="Skip ownership verification (dangerous, use with caution)")
    args = ap.parse_args()

    # Determine user_name: use provided value, or None if --force is specified
    user_name = None if args.force else args.user_name
    
    if not args.force and not args.user_name:
        print("[WARNING] No --user-name specified and --force not used.")
        print("[WARNING] For security, please specify --user-name to verify ownership.")
        print("[WARNING] Use --force to skip verification (not recommended).")
        confirm = input("Continue without verification? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("[CANCELLED] Operation cancelled.")
            return
    
    try:
        m, f, p = delete_insights(args.project_id, user_name=user_name)
        print(
            f"[CLEANUP] project_id={args.project_id} | "
            f"project_metrics deleted={m}, file_contents deleted={f}, uploaded_files deleted={p}"
        )
    except PermissionError as e:
        print(f"[ERROR] Permission denied: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to delete project: {e}")


if __name__ == "__main__":
    main()
