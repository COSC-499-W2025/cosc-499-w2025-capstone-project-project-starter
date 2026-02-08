"""Pipeline for generating portfolio and resume items from stored project insights."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.insights.storage import ProjectInsightsStore
from src.project.presentation import generate_items_from_project_id


@dataclass
class PresentationResult:
    """Result of generating presentation items for a single project"""
    project_id: int
    project_name: str
    zip_hash: str
    portfolio_item: Dict[str, Any]
    resume_item: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "zip_hash": self.zip_hash,
            "portfolio_item": self.portfolio_item,
            "resume_item": self.resume_item,
            "success": self.success,
            "error": self.error
        }


@dataclass
class BatchPresentationResult:
    """Result of batch presentation generation"""
    total_processed: int
    successful: int
    failed: int
    results: List[PresentationResult]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results]
        }


class PresentationPipeline:
    """Pipeline for generating portfolio and resume items from stored project insights."""
    
    def __init__(
        self,
        insights_store: Optional[ProjectInsightsStore] = None,
        db_path: Optional[str] = None,
        encryption_key: Optional[bytes] = None
    ):
        if insights_store is not None:
            self.store = insights_store
        else:
            self.store = ProjectInsightsStore(db_path=db_path, encryption_key=encryption_key)
    
    def generate_by_id(self, project_id: int, regenerate: bool = True) -> PresentationResult:
        """Generate portfolio and resume items for a project by its database ID."""
        try:
            project_metadata = self._get_project_metadata(project_id)
            if project_metadata is None:
                raise ValueError(f"Project with ID {project_id} not found in database")
            
            result = generate_items_from_project_id(
                project_id=project_id,
                store=self.store,
                regenerate=regenerate
            )
            
            return PresentationResult(
                project_id=project_id,
                project_name=project_metadata["project_name"],
                zip_hash=project_metadata["zip_hash"],
                portfolio_item=result["portfolio_item"],
                resume_item=result["resume_item"],
                success=True,
                error=None
            )
        except Exception as e:
            project_name = "Unknown"
            zip_hash = "unknown"
            if project_metadata:
                project_name = project_metadata["project_name"]
                zip_hash = project_metadata["zip_hash"]
            
            return PresentationResult(
                project_id=project_id,
                project_name=project_name,
                zip_hash=zip_hash,
                portfolio_item={},
                resume_item={},
                success=False,
                error=str(e)
            )
    
    def generate_by_name(
        self,
        zip_hash: str,
        project_name: str,
        regenerate: bool = True
    ) -> PresentationResult:
        """Generate portfolio and resume items for a project by zip_hash and project_name."""
        try:
            project_id = self._get_project_id(zip_hash, project_name)
            if project_id is None:
                raise ValueError(f"Project '{project_name}' not found in zip hash '{zip_hash}'")
            return self.generate_by_id(project_id, regenerate=regenerate)
        except Exception as e:
            return PresentationResult(
                project_id=-1,
                project_name=project_name,
                zip_hash=zip_hash,
                portfolio_item={},
                resume_item={},
                success=False,
                error=str(e)
            )
    
    def generate_for_zip(self, zip_hash: str, regenerate: bool = True) -> BatchPresentationResult:
        """Generate portfolio and resume items for all projects in a zip file."""
        project_ids = self._get_projects_for_zip(zip_hash)
        results = []
        successful = 0
        failed = 0
        
        for project_id in project_ids:
            result = self.generate_by_id(project_id, regenerate=regenerate)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        
        return BatchPresentationResult(
            total_processed=len(project_ids),
            successful=successful,
            failed=failed,
            results=results
        )
    
    def generate_all(
        self,
        regenerate: bool = True,
        limit: Optional[int] = None
    ) -> BatchPresentationResult:
        """Generate portfolio and resume items for all projects in the database."""
        project_ids = self._get_all_project_ids(limit=limit)
        results = []
        successful = 0
        failed = 0
        
        for project_id in project_ids:
            result = self.generate_by_id(project_id, regenerate=regenerate)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        
        return BatchPresentationResult(
            total_processed=len(project_ids),
            successful=successful,
            failed=failed,
            results=results
        )
    
    def list_available_projects(self, filters: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
        """
        List all projects available in the database with their metadata.
        
        Args:
            filters: Optional dict with 'languages' and/or 'frameworks' keys containing lists of values to filter by
        
        Returns:
            List of project metadata dictionaries
        """
        import sqlite3
        
        # Build base query
        query = """
            SELECT pi.id, p.project_name, p.slug, i.source_hash, i.source_path,
                   (SELECT COUNT(*) FROM file_info fi WHERE fi.project_info_id = pi.id AND fi.category = 'code') AS code_files,
                   (SELECT COUNT(*) FROM file_info fi WHERE fi.project_info_id = pi.id AND fi.category = 'documentation') AS doc_files,
                   pi.is_git_repo, pi.created_at, pi.updated_at, pi.languages_json, pi.frameworks_json
            FROM project_info pi
            JOIN projects p ON p.id = pi.project_id
            JOIN ingest i ON i.id = pi.ingest_id
            WHERE i.id = (
                SELECT id FROM ingest i2
                WHERE i2.source_hash = i.source_hash
                ORDER BY i2.id DESC
                LIMIT 1
            )
            ORDER BY pi.updated_at DESC;
        """
        
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(query).fetchall()
        
        projects = []
        for row in rows:
            project = {
                "project_id": row[0],
                "project_name": row[1],
                "slug": row[2],
                "zip_hash": row[3],
                "zip_path": row[4],
                "code_files": row[5],
                "doc_files": row[6],
                "is_git_repo": bool(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
                "_languages_json": row[10],
                "_frameworks_json": row[11]
            }
            projects.append(project)
        
        # Apply filters if specified
        if filters:
            filtered_projects = []
            for project in projects:
                include_project = True
                
                # Filter by languages
                if 'languages' in filters and filters['languages']:
                    import json
                    project_languages = []
                    if project['_languages_json']:
                        try:
                            project_languages = json.loads(project['_languages_json'])
                        except:
                            pass
                    # Case-insensitive matching
                    project_langs_lower = [lang.lower() for lang in project_languages]
                    filter_langs_lower = [lang.lower() for lang in filters['languages']]
                    if not any(lang in project_langs_lower for lang in filter_langs_lower):
                        include_project = False
                
                # Filter by frameworks
                if include_project and 'frameworks' in filters and filters['frameworks']:
                    import json
                    project_frameworks = []
                    if project['_frameworks_json']:
                        try:
                            project_frameworks = json.loads(project['_frameworks_json'])
                        except:
                            pass
                    # Case-insensitive matching
                    project_fws_lower = [fw.lower() for fw in project_frameworks]
                    filter_fws_lower = [fw.lower() for fw in filters['frameworks']]
                    if not any(fw in project_fws_lower for fw in filter_fws_lower):
                        include_project = False
                
                if include_project:
                    # Remove internal JSON fields before returning
                    project.pop('_languages_json', None)
                    project.pop('_frameworks_json', None)
                    filtered_projects.append(project)
            
            return filtered_projects
        
        # No filters - remove internal JSON fields and return all
        for project in projects:
            project.pop('_languages_json', None)
            project.pop('_frameworks_json', None)
        return projects
    
    def _get_project_id(self, zip_hash: str, project_name: str) -> Optional[int]:
        import sqlite3
        with sqlite3.connect(self.store.db_path) as conn:
            row = conn.execute(
                """
                SELECT pi.id FROM project_info pi
                JOIN projects p ON p.id = pi.project_id
                JOIN ingest i ON i.id = pi.ingest_id
                WHERE i.source_hash = ? AND p.project_name = ?
                  AND i.id = (
                    SELECT id FROM ingest i2
                    WHERE i2.source_hash = i.source_hash
                    ORDER BY i2.id DESC
                    LIMIT 1
                );
                """,
                (zip_hash, project_name)
            ).fetchone()
        return row[0] if row else None
    
    def _get_project_metadata(self, project_id: int) -> Optional[Dict[str, Any]]:
        import sqlite3
        with sqlite3.connect(self.store.db_path) as conn:
            row = conn.execute(
                """
                SELECT p.project_name, s.source_hash
                FROM project_info pi
                JOIN projects p ON p.id = pi.project_id
                JOIN ingest s ON s.id = pi.ingest_id
                WHERE pi.id = ?;
                """,
                (project_id,)
            ).fetchone()
        return {"project_name": row[0], "zip_hash": row[1]} if row else None
    
    def _get_projects_for_zip(self, zip_hash: str) -> List[int]:
        import sqlite3
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(
                """
                SELECT pi.id FROM project_info pi
                JOIN projects p ON p.id = pi.project_id
                JOIN ingest s ON s.id = pi.ingest_id
                WHERE s.source_hash = ?
                  AND s.id = (
                    SELECT id FROM ingest s2
                    WHERE s2.source_hash = s.source_hash
                    ORDER BY s2.id DESC
                    LIMIT 1
                )
                ORDER BY p.project_name ASC;
                """,
                (zip_hash,)
            ).fetchall()
        return [row[0] for row in rows]
    
    def _get_all_project_ids(self, limit: Optional[int] = None) -> List[int]:
        import sqlite3
        query = """
            SELECT pi.id
            FROM project_info pi
            JOIN ingest s ON s.id = pi.ingest_id
            WHERE s.id = (
                SELECT id FROM ingest s2
                WHERE s2.source_hash = s.source_hash
                ORDER BY s2.id DESC
                LIMIT 1
            )
            ORDER BY pi.updated_at DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        query += ";"
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(query).fetchall()
        return [row[0] for row in rows]


def main():  # pragma: no cover
    """CLI entry point for the presentation pipeline"""
    import sys
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Generate portfolio and resume items from stored project insights."
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--project-id", type=int, help="Generate items for a single project by ID")
    mode_group.add_argument("--project-name", type=str, help="Generate items for a project by name (requires --zip-hash)")
    mode_group.add_argument("--zip-hash", type=str, help="Generate items for all projects in a zip file")
    mode_group.add_argument("--all", action="store_true", help="Generate items for all projects in database")
    mode_group.add_argument("--list", action="store_true", help="List all available projects")
    
    parser.add_argument("--db-path", help="Path to insights database (default: from DATABASE_URL env var)")
    parser.add_argument("--no-regenerate", action="store_true", help="Skip regeneration if items exist")
    parser.add_argument("--limit", type=int, help="Limit number of projects to process (only for --all)")
    parser.add_argument("--output", type=str, help="Output file path for JSON results")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    
    args = parser.parse_args()
    
    if args.project_name and not args.zip_hash:
        parser.error("--project-name requires --zip-hash")
    
    try:
        pipeline = PresentationPipeline(db_path=args.db_path)
        
        if args.list:
            projects = pipeline.list_available_projects()
            print(f"\nFound {len(projects)} project(s) in database:\n")
            for proj in projects:
                print(f"  ID: {proj['project_id']:<5} | Name: {proj['project_name']:<30} | Zip: {proj['zip_hash'][:12]}...")
                print(f"             | Code: {proj['code_files']:<5} | Docs: {proj['doc_files']:<5} | Git: {'Yes' if proj['is_git_repo'] else 'No'}")
                print(f"             | Updated: {proj['updated_at']}\n")
            return
        
        regenerate = not args.no_regenerate
        result = None
        
        if args.project_id:
            print(f"Generating items for project ID {args.project_id}...")
            result = pipeline.generate_by_id(args.project_id, regenerate=regenerate)
            result_dict = result.to_dict()
        elif args.project_name:
            print(f"Generating items for project '{args.project_name}'...")
            result = pipeline.generate_by_name(args.zip_hash, args.project_name, regenerate=regenerate)
            result_dict = result.to_dict()
        elif args.zip_hash:
            print(f"Generating items for all projects in zip...")
            result = pipeline.generate_for_zip(args.zip_hash, regenerate=regenerate)
            result_dict = result.to_dict()
        elif args.all:
            print(f"Generating items for all projects...")
            if args.limit:
                print(f"   (Limited to {args.limit} projects)")
            result = pipeline.generate_all(regenerate=regenerate, limit=args.limit)
            result_dict = result.to_dict()
        
        json_indent = 2 if args.pretty else None
        json_output = json.dumps(result_dict, indent=json_indent)
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_output)
            print(f"Results written to: {args.output}")
        else:
            print("\n" + "="*70)
            print("RESULTS")
            print("="*70)
            print(json_output)
        
        if isinstance(result, BatchPresentationResult):
            print(f"\nProcessed {result.total_processed} project(s)")
            print(f"  Successful: {result.successful}, Failed: {result.failed}")
        elif isinstance(result, PresentationResult):
            if result.success:
                print(f"\nSuccessfully generated items for '{result.project_name}'")
            else:
                print(f"\nFailed to generate items: {result.error}")
                sys.exit(1)
    
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
