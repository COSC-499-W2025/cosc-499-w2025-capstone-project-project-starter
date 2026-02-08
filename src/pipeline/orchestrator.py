"""
Pipeline Orchestrator
Connects ZIP parser, file categorizer, and local analyzer components
"""

import json
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import getpass
from datetime import datetime

from src.ingest.zip_parser import parse_zip
from src.categorize.file_categorizer import categorize_folder_structure
from src.analyze.text_analyzer import TextAnalyzer, TextMetrics
from src.analyze.code_analyzer import CodeAnalyzer
from src.analyze.video_analyzer import VideoAnalyzer
from src.analyze.advanced_skill_extractor import AdvancedSkillExtractor
from src.analyze.success_metrics import SuccessMetricsAnalyzer
from src.image_processor import ImageProcessor
from src.git.individual_contrib_analyzer import summarize_author_contrib
from src.insights import ProjectInsightsStore
from src.pipeline.progress_tracker import ProgressTracker
from src.project.presentation import (
    extract_project_metrics,
    generate_portfolio_item,
    generate_resume_item,
)
from src.config.config_manager import UserConfigManager


class ArtifactPipeline:
    """
    Orchestrator that connects the ZIP parser, file categorizer, and local analyzers.
    
    Usage:
        pipeline = ArtifactPipeline()
        result = pipeline.start('/path/to/project.zip')
        print(result['analysis_results'])
    """
    
    # Video file extensions to detect in "other" category
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
    
    def __init__(
        self,
        insights_store: Optional[ProjectInsightsStore] = None,
        enable_insights: bool = True,
    ):
        """
        Initialize the pipeline orchestrator and all analyzers.

        Args:
            insights_store: Optional ProjectInsightsStore used to persist pipeline output.
            enable_insights: When True, automatically initialize the default store if one
                isn't provided (requires INSIGHTS_ENCRYPTION_KEY).
        """
        self.text_analyzer = TextAnalyzer()
        self.code_analyzer = CodeAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.image_processor = ImageProcessor()
        self.skill_extractor = AdvancedSkillExtractor()
        self.success_metrics_analyzer = SuccessMetricsAnalyzer()
        self.temp_dir = None
        self.insights_store = insights_store
        self.sha256_lookup = {}  # Maps abs_path -> sha256 hash for caching
        self.progress_tracker = ProgressTracker()

        if self.insights_store is None and enable_insights:
            try:
                self.insights_store = ProjectInsightsStore()
            except Exception as exc:  # pragma: no cover - warning path
                print(f"⚠️  Insights storage disabled: {exc}")
                self.insights_store = None
    
    def start(
        self,
        zip_path: str,
        use_llm: bool = False,
        data_access_consent: bool = True,
        prompt_project_names: bool = False,
    ) -> Dict[str, Any]:
        """
        Main entry point - parse ZIP, identify projects, analyze each project
        
        Args:
            zip_path: Path to the ZIP file to analyze
            use_llm: When True, also run the optional LLM summarization step
            data_access_consent: When False, exits immediately without processing
            prompt_project_names: When True, prompt for custom project names after analysis
            
        Returns:
            Dictionary containing:
                - zip_metadata: Info about the ZIP file
                - projects: Dictionary where each key is a project name (top-level directory)
                    Each project contains:
                        - is_git_repo: bool
                        - git_analysis: {...} (if Git repo)
                        - categorized_contents: file categorization
                        - analysis_results: results from analyzers by file type
        """
        # Validate input
        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        if not zip_path.suffix.lower() == '.zip':
            raise ValueError(f"File must be a ZIP archive, got: {zip_path.suffix}")
        
        if not data_access_consent:
            print("\n✗ Data access consent not granted. Exiting without processing.\n")
            return {}
        
        print(f"\n{'='*70}", flush=True)
        print(f"🚀 Starting Artifact Pipeline", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"📦 ZIP File: {zip_path.name}", flush=True)
        print(f"", flush=True)  # Empty line for spacing
        
        # Calculate zip hash for tracking
        zip_hash = self._get_zip_hash(zip_path)
        
        # Register tracker for cancellation support
        from src.insights.api import register_tracker, unregister_tracker
        register_tracker(zip_hash, self.progress_tracker)
        
        # Initialize progress tracking
        self.progress_tracker.reset()
        self.progress_tracker.update(stage='parsing', total_files=0, processed_files=0)
        
        try:
            # Step 1: Parse ZIP metadata
            print(f"\n[1/9] Parsing ZIP file metadata...", flush=True)
            zip_index = parse_zip(str(zip_path))
            print(f"✓ Parsed {zip_index.file_count} files", flush=True)
            
            # Check for cancellation
            if self.progress_tracker.should_cancel():
                print("\n⚠️  Analysis cancelled by user")
                self._cleanup_on_cancel(zip_hash)
                return {"status": "cancelled", "message": "Analysis cancelled by user"}
            
            self.progress_tracker.update(total_files=zip_index.file_count, stage='extracting')
            
            # Step 2: Extract to temporary directory
            print(f"\n[2/9] Extracting ZIP contents...", flush=True)
            self.temp_dir = Path(tempfile.mkdtemp(prefix="unzipped_"))
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Extract with path normalization to handle Windows-style backslashes
                for member in zf.infolist():
                    # Normalize path separators (handle Windows ZIP files on Linux)
                    member_path = member.filename.replace('\\', '/')
                    
                    # Skip macOS metadata files
                    if '__MACOSX' in member_path or member_path.startswith('.'):
                        continue
                    
                    # Skip directory entries (they'll be created automatically)
                    # Directory entries end with / or are explicitly marked as directories
                    if member.is_dir() or member_path.endswith('/'):
                        continue
                    
                    # Create the target path
                    target_path = self.temp_dir / member_path
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract the file
                    with zf.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
            print(f"✓ Extracted to: {self.temp_dir}", flush=True)

            # Check for cancellation
            if self.progress_tracker.should_cancel():
                print("\n⚠️  Analysis cancelled by user")
                self._cleanup_on_cancel(zip_hash)
                return {"status": "cancelled", "message": "Analysis cancelled by user"}

            # Capture file-level metadata for the entire archive
            print(f"     Building file metadata...", flush=True)
            file_info = self._build_file_info(zip_index)
            self.sha256_lookup = self._build_sha256_lookup(file_info)
            print(f"     ✓ Built metadata for {len(file_info)} files", flush=True)
            
            self.progress_tracker.update(stage='categorizing')
            print(f"     Categorizing files...", flush=True)
            
            try:
                categorized_contents_full = categorize_folder_structure(str(self.temp_dir))
                print(f"     ✓ Categorization complete", flush=True)
            except Exception as exc:
                categorized_contents_full = {"error": str(exc)}
                print(f"     ⚠️  Categorization error: {exc}", flush=True)
            
            # Step 3: Identify top-level projects and loose files
            print(f"\n[3/9] Identifying projects (top-level directories)...", flush=True)
            projects, loose_files = self._identify_projects()
            print(f"✓ Found {len(projects)} project(s): {', '.join(projects.keys())}", flush=True)
            if loose_files:
                print(f"✓ Found {len(loose_files)} loose file(s) not in any project", flush=True)
            
            self.progress_tracker.update(stage='analyzing', processed_files=0)
            
            # Step 4: Process each project
            print(f"\n[4/9] Processing each project...", flush=True)
            project_results = {}
            
            for project_name, project_path in projects.items():
                # Check for cancellation before processing each project
                if self.progress_tracker.should_cancel():
                    print("\n⚠️  Analysis cancelled by user", flush=True)
                    self._cleanup_on_cancel(zip_hash)
                    return {"status": "cancelled", "message": "Analysis cancelled by user"}
                
                print(f"\n  📁 Processing project: {project_name}", flush=True)
                self.progress_tracker.update(current_project=project_name)
                project_results[project_name] = self._process_project(project_name, project_path)
            
            # Step 4b: Process loose files if any exist
            if loose_files:
                print(f"\n  📂 Processing miscellaneous files...")
                misc_result = self._process_loose_files(loose_files)
                project_results['_misc_files'] = misc_result
            
            # Step 5: Build final result
            print(f"\n[5/9] Compiling results...")
            self.progress_tracker.update(stage='compiling')
            result = {
                "zip_metadata": {
                    "root_name": zip_index.root_name,
                    "file_count": zip_index.file_count,
                    "total_uncompressed_bytes": zip_index.total_uncompressed_bytes,
                    "total_compressed_bytes": zip_index.total_compressed_bytes,
                },
                "file_info": file_info,
                "categorized_contents": categorized_contents_full,
                "projects": project_results
            }
            
            # Step 6: Print summary
            print(f"\n[6/9] Generating summary...")
            self._print_summary(result)

            # Optional LLM summarization (gated by user consent)
            if use_llm:
                print(f"\n🤖 LLM summarization enabled by user consent. Running summarization service...")
                llm_output = self._run_llm_summarization(project_results)
                result["llm_summaries"] = llm_output
            
            # Step 7: Rank projects and generate summaries
            print(f"\n[7/9] Ranking projects and generating summaries...")
            ranking_results = self._rank_and_summarize_projects(project_results)
            result["project_ranking"] = ranking_results
            
            if ranking_results.get("ranked_projects"):
                top_count = len(ranking_results["ranked_projects"])
                print(f"     ✓ Ranked {ranking_results['total_projects_ranked']} projects (top {top_count} selected)")
            else:
                print(f"     ℹ️  {ranking_results.get('message', 'No projects to rank')}")
            
            # Step 8: Build chronological skills timeline
            print(f"\n[8/9] Building chronological skills timeline...")
            skills_timeline = self._build_chronological_skills()
            result["chronological_skills"] = skills_timeline
            
            if skills_timeline.get("timeline"):
                event_count = skills_timeline.get("total_events", 0)
                categories = skills_timeline.get("categories", [])
                print(f"     ✓ Generated timeline with {event_count} skill events across {len(categories)} categories")
            else:
                print(f"     ℹ️  {skills_timeline.get('message', 'No skill timeline generated')}")
            
            if prompt_project_names:
                self._prompt_for_project_names(project_results)

            # Step 9: Persist to database (after all analysis including ranking and skills)
            if self.insights_store:
                print(f"\n[9/9] Persisting insights to database...")
                # Ensure all data is JSON serializable before persisting
                serializable_result = self._make_json_serializable(result)
                self._persist_insights(zip_path, serializable_result)
                print(f"     ✓ All results including ranking and skills saved to database")
            else:
                print(f"\n[9/9] Compilation complete (database persistence disabled)")
            
            # Save JSON report to reports/ directory
            print(f"\n📄 Saving JSON report...")
            report_path = self._save_json_report(zip_path, result)
            print(f"     ✓ Report saved to: {report_path}")
            
            # Mark progress as complete
            self.progress_tracker.update(stage='complete', processed_files=zip_index.file_count)
            
            return result
            
        finally:
            # Unregister tracker
            unregister_tracker(zip_hash)
            
            # Always clean up temp directory
            if self.temp_dir and self.temp_dir.exists():
                print(f"\n🧹 Cleaning up temporary directory...")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _get_zip_hash(self, zip_path: Path) -> str:
        """Calculate SHA256 hash of zip file for tracking."""
        import hashlib
        hasher = hashlib.sha256()
        with open(zip_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _cleanup_on_cancel(self, zip_hash: str) -> None:
        """Clean up database records when cancelled."""
        if self.insights_store:
            try:
                counts = self.insights_store.delete_zip(zip_hash)
                print(f"     ✓ Deleted {counts.get('deleted_projects', 0)} partial records")
            except Exception as e:
                print(f"     ⚠️  Cleanup error: {e}")
    
    def _identify_projects(self) -> tuple[Dict[str, Path], List[Path]]:
        """
        Identify top-level directories as individual projects and collect loose files
        
        Handles common ZIP structures where extraction creates a wrapper folder.
        For example, if demo_projects.zip extracts to:
          temp_dir/demo_projects/project-mobile/
          temp_dir/demo_projects/project-webapp/
          temp_dir/demo_projects/notes.txt
        
        We want to identify project-mobile and project-webapp as projects,
        and notes.txt as a loose file.
        
        Returns:
            Tuple of (projects dict, loose files list)
            - projects: Dictionary mapping project name to project path
            - loose_files: List of file paths that aren't in any project
        """
        projects = {}
        loose_files = []
        
        if not self.temp_dir or not self.temp_dir.exists():
            return projects, loose_files
        
        # Get all top-level items in the extracted directory
        top_level_dirs = []
        top_level_files = []
        
        for item in self.temp_dir.iterdir():
            # Skip hidden files and macOS metadata
            if item.name.startswith('.') or item.name.startswith('__MACOSX'):
                continue
            if item.is_dir():
                top_level_dirs.append(item)
            elif item.is_file():
                top_level_files.append(item)
        
        # Case 1: No directories found - treat temp_dir as single project
        if not top_level_dirs:
            projects['root'] = self.temp_dir
            return projects, []
        
        # Case 2: Exactly one top-level directory (likely a wrapper folder from ZIP)
        # Check if it contains subdirectories that should be treated as projects
        if len(top_level_dirs) == 1:
            wrapper_dir = top_level_dirs[0]
            subdirs = []
            wrapper_files = []
            
            # Look for subdirectories and files inside the wrapper
            for item in wrapper_dir.iterdir():
                if item.name.startswith('.') or item.name.startswith('__MACOSX'):
                    continue
                if item.is_dir():
                    subdirs.append(item)
                elif item.is_file():
                    wrapper_files.append(item)
            
            # If we found subdirectories, use those as projects
            if subdirs:
                for subdir in subdirs:
                    projects[subdir.name] = subdir
                # Files in wrapper become loose files
                loose_files = wrapper_files
            else:
                # No subdirectories, so the wrapper itself is the project
                projects[wrapper_dir.name] = wrapper_dir
                # No loose files in this case
        
        # Case 3: Multiple top-level directories - each is a project
        else:
            for item in top_level_dirs:
                projects[item.name] = item
            # Top-level files become loose files
            loose_files = top_level_files
        
        return projects, loose_files

    def _build_file_info(self, zip_index) -> List[Dict[str, Any]]:
        """
        Build a list of file metadata entries for the extracted ZIP contents.
        Mirrors categorize_parse_zip() output structure so tests can assert on it.
        """
        file_info = []
        if not self.temp_dir:
            return file_info

        for entry in getattr(zip_index, "files", []):
            # Skip macOS metadata
            if "__MACOSX" in entry.rel_path or Path(entry.rel_path).name.startswith("._"):
                continue

            extracted_path = self.temp_dir / entry.rel_path
            if not extracted_path.exists():
                continue

            file_info.append({
                "abs_path": str(extracted_path.resolve()),
                "rel_path": entry.rel_path,
                "size": entry.size,
                "compressed_size": entry.compressed_size,
                "is_compressed": entry.is_compressed,
                "sha256": entry.sha256,
                "depth": entry.depth,
                "ext": entry.ext,
                "is_text_guess": entry.is_text_guess,
            })

        return file_info
    
    def _build_sha256_lookup(self, file_info: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Build a mapping from absolute file paths to SHA256 hashes.
        
        Args:
            file_info: List of file metadata dictionaries
            
        Returns:
            Dictionary mapping abs_path to sha256 hash
        """
        lookup = {}
        for info in file_info:
            lookup[info["abs_path"]] = info["sha256"]
        return lookup
    
    def _get_cached_analysis(self, file_path: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Check if a file's analysis is cached and return it.
        
        Args:
            file_path: Absolute path to the file
            analysis_type: Type of analysis ('code', 'text', 'image', 'video')
            
        Returns:
            Cached analysis result or None if not found
        """
        if not self.insights_store:
            return None
        
        # Get SHA256 hash for this file
        file_hash = self.sha256_lookup.get(file_path)
        if not file_hash:
            return None
        
        # Query cache
        try:
            cached = self.insights_store.get_cached_file_analysis(
                sha256=file_hash,
                analysis_type=analysis_type
            )
            return cached
        except Exception:
            return None
    
    def _cache_analysis(self, file_path: str, analysis_type: str, result: Dict[str, Any]) -> None:
        """
        Cache a file's analysis result.
        
        Args:
            file_path: Absolute path to the file
            analysis_type: Type of analysis ('code', 'text', 'image', 'video')
            result: Analysis result dictionary to cache
        """
        if not self.insights_store:
            return
        
        # Get SHA256 hash and file extension
        file_hash = self.sha256_lookup.get(file_path)
        if not file_hash:
            return
        
        file_ext = Path(file_path).suffix
        
        # Store in cache
        try:
            self.insights_store.cache_file_analysis(
                sha256=file_hash,
                analysis_type=analysis_type,
                analysis_result=result,
                file_ext=file_ext
            )
        except Exception:
            pass
    
    def _process_loose_files(self, loose_files: List[Path]) -> Dict[str, Any]:
        """
        Process loose files that aren't part of any project
        
        Args:
            loose_files: List of file paths
            
        Returns:
            Dictionary with analysis results for loose files
        """
        result = {
            "project_name": "Miscellaneous Files",
            "is_git_repo": False,
            "git_analysis": None,
            "categorized_contents": {},
            "analysis_results": {}
        }
        
        print(f"     ℹ️  Processing {len(loose_files)} loose files")
        
        # Manually categorize loose files by examining each one
        categorized = {
            "code": [],
            "code_by_language": {},
            "documentation": [],
            "images": [],
            "sketches": [],
            "other": []
        }
        
        from src.categorize.file_categorizer import categorize_file, _get_language
        
        for file_path in loose_files:
            file_str = str(file_path)
            category = categorize_file(file_path.name)
            
            if category == "code":
                lang = _get_language(file_path.name) or "unknown"
                categorized["code"].append(file_str)
                categorized["code_by_language"].setdefault(lang, []).append(file_str)
            else:
                categorized[category].append(file_str)
        
        result["categorized_contents"] = categorized
        
        # Count files by type
        code_count = len(categorized.get('code', []))
        doc_count = len(categorized.get('documentation', []))
        img_count = len(categorized.get('images', []))
        print(f"     ✓ Categorized: {code_count} code, {doc_count} docs, {img_count} images")
        
        # Analyze files with appropriate analyzers
        print(f"     🔬 Running file analyzers...")
        try:
            analysis_results = self._analyze_categorized_files(categorized)
            result["analysis_results"] = analysis_results
            print(f"     ✓ Analysis complete")
        except Exception as e:
            print(f"     ✗ Error during analysis: {e}")
            result["analysis_results"] = {"error": str(e)}
        
        return result
    
    def _process_project(self, project_name: str, project_path: Path) -> Dict[str, Any]:
        """
        Process a single project: check Git status, categorize, and analyze
        
        Args:
            project_name: Name of the project
            project_path: Path to the project directory
            
        Returns:
            Dictionary with project analysis results
        """
        result = {
            "project_name": project_name,
            "project_path": str(project_path),
            "is_git_repo": False,
            "git_analysis": None,
            "categorized_contents": {},
            "analysis_results": {}
        }
        
        # Check if this is a Git repository
        git_dir = project_path / ".git"
        is_git = git_dir.exists() and git_dir.is_dir()
        result["is_git_repo"] = is_git
        
        if is_git:
            print(f"     🔍 Git repository detected", flush=True)
            print(f"     📊 Running Git analysis...", flush=True)
            try:
                # Run git analysis - we'll analyze all contributors
                git_analysis = self._analyze_git_project(project_path)
                result["git_analysis"] = git_analysis
                
                # Print appropriate message based on results
                if git_analysis.get('total_commits', 0) > 0:
                    contributors = git_analysis.get('total_contributors', 0)
                    print(f"     ✓ Git analysis complete ({git_analysis['total_commits']} commits, {contributors} contributors)", flush=True)
                else:
                    message = git_analysis.get('message', 'No commits found')
                    print(f"     ℹ️  {message}", flush=True)
            except Exception as e:
                print(f"     ⚠️  Warning: Git analysis failed: {e}", flush=True)
                result["git_analysis"] = {"error": str(e)}
        else:
            print(f"     ℹ️  Not a Git repository", flush=True)
        
        # Categorize files in this project
        print(f"     📁 Categorizing files...", flush=True)
        try:
            categorized_contents = categorize_folder_structure(str(project_path))
            result["categorized_contents"] = categorized_contents
            
            # Count files by type
            code_count = len(categorized_contents.get('code', []))
            doc_count = len(categorized_contents.get('documentation', []))
            img_count = len(categorized_contents.get('images', []))
            print(f"     ✓ Categorized: {code_count} code, {doc_count} docs, {img_count} images", flush=True)
        except Exception as e:
            print(f"     ✗ Error categorizing files: {e}", flush=True)
            result["categorized_contents"] = {"error": str(e)}
            return result
        
        # Analyze files with appropriate analyzers
        print(f"     🔬 Running file analyzers...", flush=True)
        try:
            analysis_results = self._analyze_categorized_files(categorized_contents)
            result["analysis_results"] = analysis_results
            print(f"     ✓ Analysis complete", flush=True)
        except Exception as e:
            print(f"     ✗ Error during analysis: {e}", flush=True)
            result["analysis_results"] = {"error": str(e)}
        
        # Generate portfolio and resume items
        print(f"     📝 Generating presentation items...", flush=True)
        try:
            metrics = extract_project_metrics(result)
            result["project_metrics"] = metrics.to_dict()
            portfolio_item = generate_portfolio_item(result, metrics=metrics)
            resume_item = generate_resume_item(result, metrics=metrics)
            result["portfolio_item"] = portfolio_item
            result["resume_item"] = resume_item
            print(f"     ✓ Presentation items generated", flush=True)
        except Exception as e:
            print(f"     ⚠️  Warning: Failed to generate presentation items: {e}", flush=True)
            result["portfolio_item"] = {"error": str(e)}
            result["resume_item"] = {"error": str(e)}
        
        # Generate success metrics
        print(f"     🎯 Generating success metrics...", flush=True)
        try:
            success_metrics = self.success_metrics_analyzer.analyze(result)
            result["success_metrics"] = success_metrics.to_dict()
            print(f"     ✓ Success metrics generated (Overall: {success_metrics.overall_score:.1f}/100)", flush=True)
        except Exception as e:
            print(f"     ⚠️  Warning: Failed to generate success metrics: {e}", flush=True)
            result["success_metrics"] = {"error": str(e)}
        
        return result
    
    def _analyze_git_project(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze Git repository to extract contribution metrics
        
        Args:
            project_path: Path to the Git repository
            
        Returns:
            Dictionary with Git analysis results
        """
        from src.git._git_utils import iter_commits
        
        # Get all commits to identify contributors
        try:
            all_commits = list(iter_commits(project_path))
        except Exception as e:
            return {
                "total_commits": 0,
                "contributors": [],
                "message": f"Unable to read Git history: {str(e)}"
            }
        
        if not all_commits:
            return {
                "total_commits": 0,
                "contributors": [],
                "message": "Git repository is empty (no commits yet)"
            }
        
        # Identify unique contributors
        contributors_set = set()
        for commit in all_commits:
            contributors_set.add((commit["author_name"], commit["author_email"]))
        
        # Analyze each contributor
        contributor_analyses = []
        for name, email in contributors_set:
            try:
                # Use email as identifier (preferred)
                contrib_summary = summarize_author_contrib(
                    project_path,
                    email,
                    prefer_email=True,
                    fuzzy=False
                )
                contributor_analyses.append(contrib_summary)
            except Exception as e:
                print(f"        ⚠️  Could not analyze contributor {name}: {e}")
                continue
        
        # Sort contributors by commit count
        contributor_analyses.sort(key=lambda x: x["commits"], reverse=True)
        
        return {
            "total_commits": len(all_commits),
            "total_contributors": len(contributor_analyses),
            "contributors": contributor_analyses
        }
    
    def _analyze_categorized_files(self, categorized_contents: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze files by category using appropriate analyzers
        
        Args:
            categorized_contents: Dictionary from file categorizer
            
        Returns:
            Dictionary with analysis results for each category
        """
        results = {}
        
        # Analyze documentation files (PDF, DOCX, TXT, MD)
        doc_files = categorized_contents.get('documentation', [])
        if doc_files:
            print(f"  📄 Analyzing {len(doc_files)} documentation file(s)...", flush=True)
            try:
                doc_results = []
                cache_hits = 0
                
                for doc_file in doc_files:
                    # Check for cancellation
                    if self.progress_tracker.should_cancel():
                        break
                    
                    # Check cache first
                    cached_result = self._get_cached_analysis(doc_file, 'text')
                    
                    if cached_result:
                        doc_results.append(cached_result)
                        cache_hits += 1
                    else:
                        # Not in cache - analyze it
                        try:
                            metrics = self.text_analyzer.analyze_file(doc_file)
                            result_dict = metrics.to_dict()
                            doc_results.append(result_dict)
                            # Cache for future use
                            self._cache_analysis(doc_file, 'text', result_dict)
                        except Exception as e:
                            print(f"     ⚠️  Warning: Could not analyze {Path(doc_file).name}: {e}")
                            continue
                    
                    # Update progress after each file
                    self.progress_tracker.increment_processed(current_file=Path(doc_file).name)
                
                # Calculate totals
                totals = self.text_analyzer._calculate_totals(
                    [TextMetrics(**r) for r in doc_results]
                )
                
                results['documentation'] = {
                    'files': doc_results,
                    'totals': totals
                }
                
                if cache_hits > 0:
                    cache_rate = (cache_hits / len(doc_files)) * 100
                    print(f"     ♻️  Cache hits: {cache_hits}/{len(doc_files)} ({cache_rate:.1f}%)", flush=True)
                print(f"     ✓ Documentation analysis complete", flush=True)
            except Exception as e:
                print(f"     ✗ Error analyzing documentation: {e}", flush=True)
                results['documentation'] = {"error": str(e)}
        else:
            print(f"  📄 No documentation files to analyze", flush=True)
            results['documentation'] = None
        
        # Analyze image files (PNG, JPG, JPEG, etc.)
        image_files = categorized_contents.get('images', [])
        if image_files:
            print(f"  🖼️  Analyzing {len(image_files)} image file(s)...", flush=True)
            try:
                image_results = []
                cache_hits = 0
                
                for image_file in image_files:
                    # Check for cancellation
                    if self.progress_tracker.should_cancel():
                        break
                    
                    # Check cache first
                    cached_result = self._get_cached_analysis(image_file, 'image')
                    
                    if cached_result:
                        image_results.append(cached_result)
                        cache_hits += 1
                    else:
                        # Not in cache - analyze it
                        try:
                            result = self.image_processor.analyze_image(image_file)
                            image_results.append(result)
                            # Cache for future use
                            self._cache_analysis(image_file, 'image', result)
                        except Exception as e:
                            print(f"     ⚠️  Warning: Could not analyze {Path(image_file).name}: {e}")
                            image_results.append({
                                "file_path": image_file,
                                "error": str(e)
                            })
                            continue
                    
                    # Update progress after each file
                    self.progress_tracker.increment_processed(current_file=Path(image_file).name)
                
                results['images'] = image_results
                
                if cache_hits > 0:
                    cache_rate = (cache_hits / len(image_files)) * 100
                    print(f"     ♻️  Cache hits: {cache_hits}/{len(image_files)} ({cache_rate:.1f}%)", flush=True)
                print(f"     ✓ Image analysis complete", flush=True)
            except Exception as e:
                print(f"     ✗ Error analyzing images: {e}", flush=True)
                results['images'] = {"error": str(e)}
        else:
            print(f"  🖼️  No image files to analyze", flush=True)
            results['images'] = None
        
        # Analyze code files
        code_files = categorized_contents.get('code', [])
        if code_files:
            print(f"  💻 Analyzing {len(code_files)} code file(s)...", flush=True)
            try:
                # CodeAnalyzer needs to be called per file
                code_results = []
                skill_analyses = []
                cache_hits = 0
                
                for code_file in code_files:
                    try:
                        # Check cache first
                        cached_result = self._get_cached_analysis(code_file, 'code')
                        
                        if cached_result:
                            # Use cached result
                            code_results.append(cached_result)
                            cache_hits += 1
                            # Still run skill extraction (not cached separately yet)
                            try:
                                skill_analysis = self.skill_extractor.analyze_file(Path(code_file))
                                skill_analyses.append(skill_analysis)
                            except Exception:
                                pass
                        else:
                            # Not in cache - analyze it
                            analysis = self.code_analyzer.analyze_file(code_file)
                            result_dict = analysis.to_dict()
                            code_results.append(result_dict)
                            
                            # Cache for future use
                            self._cache_analysis(code_file, 'code', result_dict)
                            
                            # Run advanced skill extraction
                            skill_analysis = self.skill_extractor.analyze_file(Path(code_file))
                            skill_analyses.append(skill_analysis)
                    except Exception as e:
                        print(f"     ⚠️  Warning: Could not analyze {Path(code_file).name}: {e}")
                        continue
                
                # Calculate aggregate metrics
                from src.analyze.code_analyzer import AnalysisResult
                analysis_objs = []
                for r in code_results:
                    analysis_objs.append(AnalysisResult(**r))
                
                metrics = self.code_analyzer.calculate_contribution_metrics(analysis_objs)
                
                # Aggregate skill extraction results
                skill_aggregate = self.skill_extractor.aggregate_skills({
                    sa.file_path: sa for sa in skill_analyses
                })
                
                results['code'] = {
                    'files': code_results,
                    'metrics': metrics.to_dict(),
                    'skill_analysis': {
                        'per_file': [sa.to_dict() for sa in skill_analyses],
                        'aggregate': skill_aggregate
                    }
                }
                if cache_hits > 0:
                    cache_rate = (cache_hits / len(code_files)) * 100
                    print(f"     ♻️  Cache hits: {cache_hits}/{len(code_files)} ({cache_rate:.1f}%)", flush=True)
                print(f"     ✓ Code analysis complete ({len(code_results)} files)", flush=True)
                print(f"     ✓ Skill extraction complete ({skill_aggregate['total_files_analyzed']} files, {len(skill_aggregate['advanced_skills'])} advanced skills)", flush=True)
            except Exception as e:
                print(f"     ✗ Error analyzing code: {e}", flush=True)
                results['code'] = {"error": str(e)}
        else:
            print(f"  💻 No code files to analyze", flush=True)
            results['code'] = None
        
        # Analyze video files (check "other" category for video extensions)
        other_files = categorized_contents.get('other', [])
        video_files = [f for f in other_files if Path(f).suffix.lower() in self.VIDEO_EXTENSIONS]
        
        if video_files:
            print(f"  🎥 Analyzing {len(video_files)} video file(s)...", flush=True)
            try:
                # VideoAnalyzer needs to be called per file
                video_results = []
                cache_hits = 0
                
                for video_file in video_files:
                    try:
                        # Check cache first
                        cached_result = self._get_cached_analysis(video_file, 'video')
                        
                        if cached_result:
                            video_results.append(cached_result)
                            cache_hits += 1
                        else:
                            # Not in cache - analyze it
                            analysis = self.video_analyzer.analyze_file(video_file, transcribe=False)
                            if analysis:
                                result_dict = analysis.to_dict()
                                video_results.append(result_dict)
                                # Cache for future use
                                self._cache_analysis(video_file, 'video', result_dict)
                    except Exception as e:
                        print(f"     ⚠️  Warning: Could not analyze {Path(video_file).name}: {e}")
                        continue
                
                # Calculate collection metrics
                from src.analyze.video_analyzer import VideoAnalysisResult
                video_objs = []
                for r in video_results:
                    video_objs.append(VideoAnalysisResult(**r))
                
                metrics = self.video_analyzer.calculate_collection_metrics(video_objs)
                
                results['videos'] = {
                    'files': video_results,
                    'metrics': metrics.to_dict()
                }
                if cache_hits > 0:
                    cache_rate = (cache_hits / len(video_files)) * 100
                    print(f"     ♻️  Cache hits: {cache_hits}/{len(video_files)} ({cache_rate:.1f}%)", flush=True)
                print(f"     ✓ Video analysis complete ({len(video_results)} files)", flush=True)
            except Exception as e:
                print(f"     ✗ Error analyzing videos: {e}", flush=True)
                results['videos'] = {"error": str(e)}
        else:
            print(f"  🎥 No video files to analyze", flush=True)
            results['videos'] = None
        
        return results

    def _run_llm_summarization(self, projects: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the optional LLM summarization service against documentation files.

        Args:
            projects: The project results dictionary produced by the pipeline.

        Returns:
            Dictionary keyed by project name containing LLM summaries or errors.
        """
        try:
            from src.services.summarization_service import SummarizationService
        except Exception as exc:
            print(f"     ⚠️  LLM summarization unavailable: {exc}")
            return {"error": f"LLM summarization unavailable: {exc}"}

        try:
            summarizer = SummarizationService()
        except Exception as exc:
            print(f"     ⚠️  LLM summarization unavailable: {exc}")
            return {"error": f"LLM summarization unavailable: {exc}"}
        summaries: Dict[str, Any] = {}

        for project_name, project_data in projects.items():
            docs = project_data.get("categorized_contents", {}).get("documentation", [])
            if not docs:
                continue

            project_summaries = []
            for doc_path in docs:
                try:
                    summary = summarizer.summarize_document(doc_path)
                    summary.setdefault("file_path", doc_path)
                    project_summaries.append(summary)
                except Exception as exc:
                    project_summaries.append({
                        "file_path": doc_path,
                        "status": "error",
                        "error": str(exc)
                    })

            if project_summaries:
                summaries[project_name] = project_summaries

        if summaries:
            print(f"     ✓ LLM summarization complete for {len(summaries)} project(s)")
        else:
            print("     ℹ️  No documentation found for LLM summarization")

        return summaries

    def _persist_insights(self, zip_path: Path, payload: Dict[str, Any]) -> None:
        """Persist pipeline output to the configured insights store."""
        if not self.insights_store:
            return
        try:
            stats = self.insights_store.record_pipeline_run(
                str(zip_path),
                payload,
                pipeline_version="artifact-pipeline/v1",
            )
            print(
                f"     ✓ Stored insights ({stats.project_count} projects, "
                f"{stats.inserted} inserted / {stats.updated} updated / {stats.deleted} deleted)"
            )
        except Exception as exc:
            print(f"     ⚠️  Warning: Unable to persist insights: {exc}")
    
    def _save_json_report(self, zip_path: Path, result: Dict[str, Any]) -> Path:
        """Save analysis results to a JSON file in the reports/ directory.
        
        Args:
            zip_path: Path to the original ZIP file being analyzed
            result: The complete analysis result dictionary
            
        Returns:
            Path to the saved JSON report file
        """
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate report filename with timestamp only
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"report_{timestamp}.json"
        report_path = reports_dir / report_filename
        
        # Ensure result is JSON serializable
        serializable_result = self._make_json_serializable(result)
        
        # Write JSON report with nice formatting
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def _print_summary(self, result: Dict[str, Any]) -> None:
        """Print a summary of the analysis results"""
        print(f"\n{'='*70}")
        print(f"✅ Pipeline Complete!")
        print(f"{'='*70}")
        
        # ZIP metadata summary
        zip_meta = result.get('zip_metadata', {})
        print(f"\n📊 ZIP Summary:")
        print(f"   • Total files: {zip_meta.get('file_count', 0)}")
        print(f"   • Uncompressed size: {self._format_bytes(zip_meta.get('total_uncompressed_bytes', 0))}")
        print(f"   • Compressed size: {self._format_bytes(zip_meta.get('total_compressed_bytes', 0))}")
        
        # Projects summary
        projects = result.get('projects', {})
        regular_projects = {k: v for k, v in projects.items() if k != '_misc_files'}
        misc_files = projects.get('_misc_files')
        
        print(f"\n📦 Projects Found: {len(regular_projects)}")
        if misc_files:
            print(f"📂 Miscellaneous Files: Yes ({len(misc_files.get('categorized_contents', {}).get('code', []) + misc_files.get('categorized_contents', {}).get('documentation', []) + misc_files.get('categorized_contents', {}).get('images', []))} loose files)")
        
        for project_name, project_data in regular_projects.items():
            print(f"\n{'─'*70}")
            print(f"📁 Project: {project_name}")
            print(f"{'─'*70}")
            
            # Git status
            is_git = project_data.get('is_git_repo', False)
            if is_git:
                print(f"   🔍 Git Repository: YES")
                git_analysis = project_data.get('git_analysis', {})
                if git_analysis and 'error' not in git_analysis:
                    print(f"      • Total commits: {git_analysis.get('total_commits', 0)}")
                    print(f"      • Contributors: {git_analysis.get('total_contributors', 0)}")
                    
                    # Show top 3 contributors
                    contributors = git_analysis.get('contributors', [])
                    if contributors:
                        print(f"      • Top contributors:")
                        for i, contrib in enumerate(contributors[:3], 1):
                            author = contrib.get('author', {})
                            commits = contrib.get('commits', 0)
                            print(f"         {i}. {author.get('name', 'Unknown')} ({commits} commits)")
            else:
                print(f"   🔍 Git Repository: NO")
            
            # Categorization summary
            categorized = project_data.get('categorized_contents', {})
            if categorized and 'error' not in categorized:
                print(f"\n   📁 File Categorization:")
                print(f"      • Code files: {len(categorized.get('code', []))}")
                
                # Show languages breakdown
                code_by_lang = categorized.get('code_by_language', {})
                if code_by_lang:
                    print(f"        Languages detected:")
                    for lang, files in sorted(code_by_lang.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                        print(f"          - {lang}: {len(files)} files")
                
                print(f"      • Documentation files: {len(categorized.get('documentation', []))}")
                print(f"      • Image files: {len(categorized.get('images', []))}")
                print(f"      • Video files: {len([f for f in categorized.get('other', []) if Path(f).suffix.lower() in self.VIDEO_EXTENSIONS])}")
            
            # Analysis summary
            analysis = project_data.get('analysis_results', {})
            if analysis and 'error' not in analysis:
                print(f"\n   🔬 Analysis Results:")
                
                # Documentation analysis
                doc_analysis = analysis.get('documentation')
                if doc_analysis and doc_analysis is not None and 'error' not in doc_analysis:
                    totals = doc_analysis.get('totals', {})
                    print(f"      • Documentation: {totals.get('total_files', 0)} files, {totals.get('total_words', 0):,} words")
                
                # Image analysis
                img_analysis = analysis.get('images')
                if img_analysis and img_analysis is not None and 'error' not in img_analysis:
                    total_size = sum(img.get('file_stats', {}).get('size_mb', 0) for img in img_analysis)
                    print(f"      • Images: {len(img_analysis)} files, {total_size:.2f} MB")
                
                # Code analysis
                code_analysis = analysis.get('code')
                if code_analysis and code_analysis is not None and 'error' not in code_analysis:
                    metrics = code_analysis.get('metrics', {})
                    print(f"      • Code: {metrics.get('total_files', 0)} files, {metrics.get('total_lines', 0):,} lines")
                    langs = metrics.get('languages', [])
                    if langs:
                        print(f"        Languages: {', '.join(langs)}")
                    
                    # Display skill analysis insights
                    skill_data = code_analysis.get('skill_analysis', {})
                    if skill_data:
                        aggregate = skill_data.get('aggregate', {})
                        advanced_skills = aggregate.get('advanced_skills', [])
                        design_patterns = aggregate.get('design_patterns', [])
                        if advanced_skills:
                            print(f"        Advanced Skills: {', '.join(advanced_skills[:5])}")
                            if len(advanced_skills) > 5:
                                print(f"          ... and {len(advanced_skills) - 5} more")
                        if design_patterns:
                            print(f"        Design Patterns: {', '.join(design_patterns[:3])}")
                            if len(design_patterns) > 3:
                                print(f"          ... and {len(design_patterns) - 3} more")
                
                # Video analysis
                video_analysis = analysis.get('videos')
                if video_analysis and video_analysis is not None and 'error' not in video_analysis:
                    metrics = video_analysis.get('metrics', {})
                    duration = metrics.get('total_duration', 0)
                    print(f"      • Videos: {metrics.get('total_videos', 0)} files, {duration:.1f}s duration")
            
            # Portfolio and Resume items
            portfolio_item = project_data.get('portfolio_item')
            resume_item = project_data.get('resume_item')
            
            if portfolio_item and 'error' not in portfolio_item:
                print(f"\n   📝 Portfolio Item:")
                print(f"      • Tagline: {portfolio_item.get('tagline', 'N/A')}")
                print(f"      • Collaborative: {portfolio_item.get('is_collaborative', False)}")
                if portfolio_item.get('languages'):
                    print(f"      • Languages: {', '.join(portfolio_item.get('languages', [])[:5])}")
                if portfolio_item.get('frameworks'):
                    print(f"      • Frameworks: {', '.join(portfolio_item.get('frameworks', [])[:3])}")
            
            if resume_item and 'error' not in resume_item:
                print(f"\n   📄 Resume Bullets:")
                for i, bullet in enumerate(resume_item.get('bullets', []), 1):
                    # Truncate long bullets for display
                    display_bullet = bullet[:120] + '...' if len(bullet) > 120 else bullet
                    print(f"      {i}. {display_bullet}")
            
            # Success Metrics
            success_metrics = project_data.get('success_metrics')
            if success_metrics and 'error' not in success_metrics:
                print(f"\n   🎯 Evidence of Success:")
                print(f"      • Overall Score: {success_metrics.get('overall_score', 0):.1f}/100")
                print(f"      • Code Quality: {success_metrics.get('code_quality_score', 0):.1f}/100")
                print(f"      • Documentation: {success_metrics.get('documentation_score', 0):.1f}/100")
                print(f"      • Activity: {success_metrics.get('activity_score', 0):.1f}/100")
                print(f"      • Collaboration: {success_metrics.get('collaboration_score', 0):.1f}/100")
                
                # Show test coverage if available
                test_cov = success_metrics.get('test_coverage_indicator')
                if test_cov is not None:
                    print(f"      • Estimated Test Coverage: {test_cov:.1f}%")
                
                # Show badges if found
                badges = success_metrics.get('badges', [])
                if badges:
                    print(f"      • Badges Found: {len(badges)} ({', '.join(set(b['type'] for b in badges))})")
                
                # Show feedback items if found
                feedback = success_metrics.get('feedback_items', [])
                if feedback:
                    print(f"      • Positive Feedback Indicators: {len(feedback)} found")
        
        # Miscellaneous files summary
        if misc_files:
            print(f"\n{'─'*70}")
            print(f"📂 Miscellaneous Files (not in any project)")
            print(f"{'─'*70}")
            
            # Categorization summary
            categorized = misc_files.get('categorized_contents', {})
            if categorized:
                print(f"\n   📁 File Categorization:")
                print(f"      • Code files: {len(categorized.get('code', []))}")
                
                code_by_lang = categorized.get('code_by_language', {})
                if code_by_lang:
                    print(f"        Languages detected:")
                    for lang, files in sorted(code_by_lang.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                        print(f"          - {lang}: {len(files)} files")
                
                print(f"      • Documentation files: {len(categorized.get('documentation', []))}")
                print(f"      • Image files: {len(categorized.get('images', []))}")
                print(f"      • Video files: {len([f for f in categorized.get('other', []) if Path(f).suffix.lower() in self.VIDEO_EXTENSIONS])}")
            
            # Analysis summary
            analysis = misc_files.get('analysis_results', {})
            if analysis:
                print(f"\n   🔬 Analysis Results:")
                
                doc_analysis = analysis.get('documentation')
                if doc_analysis and 'error' not in doc_analysis:
                    totals = doc_analysis.get('totals', {})
                    print(f"      • Documentation: {totals.get('total_files', 0)} files, {totals.get('total_words', 0):,} words")
                
                img_analysis = analysis.get('images')
                if img_analysis and 'error' not in img_analysis:
                    total_size = sum(img.get('file_stats', {}).get('size_mb', 0) for img in img_analysis)
                    print(f"      • Images: {len(img_analysis)} files, {total_size:.2f} MB")
                
                code_analysis = analysis.get('code')
                if code_analysis and 'error' not in code_analysis:
                    metrics = code_analysis.get('metrics', {})
                    print(f"      • Code: {metrics.get('total_files', 0)} files, {metrics.get('total_lines', 0):,} lines")
                    
                    # Display skill analysis insights
                    skill_data = code_analysis.get('skill_analysis', {})
                    if skill_data:
                        aggregate = skill_data.get('aggregate', {})
                        advanced_skills = aggregate.get('advanced_skills', [])
                        design_patterns = aggregate.get('design_patterns', [])
                        if advanced_skills:
                            print(f"        Advanced Skills: {', '.join(advanced_skills[:5])}")
                        if design_patterns:
                            print(f"        Design Patterns: {', '.join(design_patterns[:3])}")
                
                video_analysis = analysis.get('videos')
                if video_analysis and 'error' not in video_analysis:
                    metrics = video_analysis.get('metrics', {})
                    print(f"      • Videos: {metrics.get('total_videos', 0)} files, {metrics.get('total_duration', 0):.1f}s duration")
        
        # Project ranking summary
        ranking = result.get('project_ranking', {})
        if ranking and ranking.get('ranked_projects'):
            print(f"\n{'─'*70}")
            print(f"🏆 Top Ranked Projects")
            print(f"{'─'*70}")
            
            for proj in ranking.get('ranked_projects', [])[:5]:
                rank = proj.get('rank', 0)
                name = proj.get('name', 'Unknown')
                score = proj.get('score', 0.0)
                collab = "Collaborative" if proj.get('is_collaborative') else "Individual"
                commits = proj.get('commits', 0)
                loc = proj.get('lines_of_code', 0)
                
                print(f"\n   #{rank}. {name} (Score: {score:.2f})")
                print(f"      • Type: {collab}")
                if commits > 0:
                    print(f"      • Commits: {commits}")
                if loc > 0:
                    print(f"      • Lines of Code: {loc:,}")
                
                languages = proj.get('languages', [])
                if languages:
                    print(f"      • Languages: {', '.join(languages[:3])}")
            
            # Show summaries if available
            summaries = ranking.get('top_summaries', [])
            if summaries:
                print(f"\n   📝 Project Summaries:")
                for summary in summaries[:3]:
                    print(f"\n      #{summary.get('rank')}: {summary.get('summary', '')}")
        
        # Chronological skills summary
        chron_skills = result.get('chronological_skills', {})
        if chron_skills and chron_skills.get('timeline'):
            print(f"\n{'─'*70}")
            print(f"📅 Chronological Skills Timeline")
            print(f"{'─'*70}")
            
            total_events = chron_skills.get('total_events', 0)
            categories = chron_skills.get('categories', [])
            
            print(f"\n   • Total skill events: {total_events}")
            print(f"   • Categories: {', '.join(categories)}")
            
            # Show first 5 and last 5 events
            timeline = chron_skills.get('timeline', [])
            if timeline:
                print(f"\n   📊 First 5 Events:")
                for event in timeline[:5]:
                    timestamp = event.get('timestamp', '')
                    if 'T' in timestamp:
                        timestamp = timestamp.split('T')[0]
                    category = event.get('category', 'unknown')
                    skills = event.get('skills', [])
                    file_path = event.get('file', '')
                    file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                    
                    print(f"      • [{timestamp}] {category.upper()}: {file_name}")
                    if skills:
                        print(f"        Skills: {', '.join(skills[:3])}")
                
                if len(timeline) > 5:
                    print(f"\n   📊 Most Recent 5 Events:")
                    for event in timeline[-5:]:
                        timestamp = event.get('timestamp', '')
                        if 'T' in timestamp:
                            timestamp = timestamp.split('T')[0]
                        category = event.get('category', 'unknown')
                        skills = event.get('skills', [])
                        file_path = event.get('file', '')
                        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                        
                        print(f"      • [{timestamp}] {category.upper()}: {file_name}")
                        if skills:
                            print(f"        Skills: {', '.join(skills[:3])}")
        
        print(f"\n{'='*70}\n")
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes into human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert NumPy types, PIL types, and other non-serializable objects to JSON-serializable types.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable version of the object
        """
        import numpy as np
        from datetime import datetime, date
        
        # Handle None, strings, numbers first (most common cases)
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Handle collections recursively
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        
        # Handle NumPy types
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        
        # Handle datetime types
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # Handle bytes
        elif isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                return obj.hex()
        
        # Handle PIL/Pillow types (IFDRational, etc.)
        elif hasattr(obj, '__class__') and 'PIL' in obj.__class__.__module__:
            # Try to convert to basic types
            if hasattr(obj, 'numerator') and hasattr(obj, 'denominator'):
                # IFDRational or Fraction-like object
                try:
                    return float(obj)
                except:
                    return f"{obj.numerator}/{obj.denominator}"
            else:
                return str(obj)
        
        # Handle numpy scalar types with .item() method
        elif hasattr(obj, 'item'):
            try:
                return obj.item()
            except:
                return str(obj)
        
        # Handle objects with __dict__ (custom classes)
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        
        # Fallback: convert to string
        else:
            try:
                # Check if it's already JSON serializable
                import json
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def _convert_to_project_info(self, project_name: str, project_data: Dict[str, Any]):
        """
        Convert orchestrator project result to ProjectInfo object for ranking.
        
        Args:
            project_name: Name of the project
            project_data: Project data from orchestrator results
            
        Returns:
            ProjectInfo object or None if conversion fails
        """
        from src.project.aggregator import ProjectInfo, compute_rank_inputs, compute_preliminary_score
        
        try:
            git_analysis = project_data.get("git_analysis", {})
            code_analysis = project_data.get("analysis_results", {}).get("code", {})
            
            # Extract duration info from git analysis
            duration_info = {"start": None, "end": None, "days": 0}
            if isinstance(git_analysis, dict) and ("error" not in git_analysis):
                if "first_commit_at" in git_analysis:
                    duration_info = {
                        "start": git_analysis.get("first_commit_at"),
                        "end": git_analysis.get("last_commit_at"),
                        "days": git_analysis.get("duration_days", 0)
                    }
            
            # Determine if collaborative
            is_collaborative = False
            if project_data.get("is_git_repo") and git_analysis:
                is_collaborative = git_analysis.get("total_contributors", 0) > 1
            
            # Extract contributors
            authors = []
            if git_analysis and "contributors" in git_analysis:
                for contrib in git_analysis.get("contributors", []):
                    author_info = contrib.get("author", {})
                    authors.append({
                        "name": author_info.get("name", "Unknown"),
                        "email": author_info.get("email", ""),
                        "commits": contrib.get("commits", 0)
                    })
            
            # Extract languages and frameworks
            languages = []
            frameworks = []
            if code_analysis and "error" not in code_analysis:
                metrics = code_analysis.get("metrics", {})
                languages = metrics.get("languages", [])
                frameworks = metrics.get("frameworks", [])
            
            # Extract skills
            skills = []
            if code_analysis and "error" not in code_analysis:
                skill_data = code_analysis.get("skill_analysis", {})
                if skill_data:
                    aggregate = skill_data.get("aggregate", {})
                    skills = aggregate.get("advanced_skills", [])
            
            # Extract activity mix
            activity_mix = {}
            if git_analysis and "error" not in git_analysis:
                activity_mix = git_analysis.get("activity_mix", {})
            
            # Extract totals
            total_commits = 0
            total_files = 0
            total_loc = 0
            
            if git_analysis and "error" not in git_analysis:
                total_commits = git_analysis.get("total_commits", 0)
            
            if code_analysis and "error" not in code_analysis:
                metrics = code_analysis.get("metrics", {})
                total_files = metrics.get("total_files", 0)
                total_loc = metrics.get("total_lines", 0)
            
            # Create ProjectInfo
            project_info = ProjectInfo(
                id=project_name,
                name=project_name,
                source="merged",
                duration=duration_info,
                is_collaborative=is_collaborative,
                authors=authors,
                languages=languages,
                frameworks=frameworks,
                skills=skills,
                activity_mix=activity_mix,
                lines_of_code=total_loc,
                totals={"files": total_files, "commits": total_commits},
                notes=[],
                rank_inputs={},
                preliminary_score=0.0
            )
            
            # Compute ranking metrics
            project_info.rank_inputs = compute_rank_inputs(project_info)
            project_info.preliminary_score = compute_preliminary_score(project_info.rank_inputs)
            
            return project_info
            
        except Exception as e:
            print(f"     ⚠️  Could not convert project {project_name} to ProjectInfo: {e}")
            return None
    
    def _rank_and_summarize_projects(self, project_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rank projects and generate summaries for top N projects.
        
        Args:
            project_results: Dictionary of project results from orchestrator
            
        Returns:
            Dictionary containing ranked_projects and top_summaries
        """
        from src.project.top_summary import rank_projects, generate_summaries
        
        try:
            # Convert to ProjectInfo objects (skip _misc_files)
            project_infos = []
            for proj_name, proj_data in project_results.items():
                if proj_name == '_misc_files':
                    continue
                
                project_info = self._convert_to_project_info(proj_name, proj_data)
                if project_info:
                    project_infos.append(project_info)
            
            if not project_infos:
                return {
                    "ranked_projects": [],
                    "top_summaries": [],
                    "message": "No projects available for ranking"
                }
            
            # Rank projects
            top_projects = rank_projects(project_infos, n=5, criteria="score")
            
            # Generate summaries
            summaries = generate_summaries(project_infos, n=5, criteria="score")
            
            return {
                "ranked_projects": [
                    {
                        "rank": idx + 1,
                        "name": p.name,
                        "score": p.preliminary_score,
                        "is_collaborative": p.is_collaborative,
                        "languages": p.languages,
                        "frameworks": p.frameworks,
                        "commits": p.totals.get("commits", 0),
                        "lines_of_code": p.lines_of_code,
                        "duration_days": p.duration.get("days", 0),
                    }
                    for idx, p in enumerate(top_projects)
                ],
                "top_summaries": summaries,
                "total_projects_ranked": len(project_infos)
            }
            
        except Exception as e:
            print(f"     ⚠️  Project ranking failed: {e}")
            return {
                "ranked_projects": [],
                "top_summaries": [],
                "error": str(e)
            }
    
    def _build_chronological_skills(self) -> Dict[str, Any]:
        """
        Build chronological timeline of skills across all analyzed files.
        
        Returns:
            Dictionary containing chronological skill timeline
        """
        from src.analyze.chronological_skills import ChronologicalSkillList
        
        try:
            if not self.temp_dir or not self.temp_dir.exists():
                return {
                    "timeline": [],
                    "message": "No temporary directory available for skill timeline"
                }
            
            skill_tracker = ChronologicalSkillList()
            timeline = skill_tracker.build_skill_timeline(str(self.temp_dir))
            
            # Convert timeline to serializable format
            serializable_timeline = []
            for event in timeline:
                event_data = {
                    "file": event["file"],
                    "timestamp": event["timestamp"].isoformat() if hasattr(event["timestamp"], "isoformat") else str(event["timestamp"]),
                    "category": event["category"],
                    "skills": event["skills"],
                    "metadata": self._make_json_serializable(event.get("metadata", {}))
                }
                serializable_timeline.append(event_data)
            
            return {
                "timeline": serializable_timeline,
                "total_events": len(serializable_timeline),
                "categories": list(set(e["category"] for e in serializable_timeline))
            }
            
        except Exception as e:
            print(f"     ⚠️  Chronological skills timeline failed: {e}")
            return {
                "timeline": [],
                "error": str(e)
            }

    def _prompt_for_project_names(self, project_results: Dict[str, Any]) -> None:
        if not project_results:
            return
        print("\nOptional: customize project names for presentation outputs.")
        for project_name, project_data in project_results.items():
            if project_name == "_misc_files":
                continue
            if not _prompt_yes_no(
                f"\nAdd a custom project name for '{project_name}'?",
                default=False,
            ):
                continue
            custom_name = input("  Enter project name (leave blank to keep default): ").strip()
            if custom_name:
                project_data["project_name"] = custom_name


def _prompt_for_llm_consent() -> bool:
    """
    Prompt the user for LLM consent with a short privacy explanation.
    """
    print(
        "\n  IMPORTANT: This pipeline can call an LLM summarization service to generate an AI-written analysis."
        "\n  If you choose 'n', only the local analyzers will run and your data stays on this machine."
        "\n  Privacy notice: enabling the external LLM service will send derived summaries "
        "\n  to a hosted API. No raw files leave the machine, but continue only if you are comfortable "
        "\n  with that data flow. Local-only analysis is available if you opt out."
    )

    while True:
        response = input("\n  Enable LLM summarization? (y/n): ").strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")


def resolve_llm_consent(zip_path: str, user_id: str) -> bool:
    """
    Load stored consent from the user configuration; prompt and persist if missing.
    """
    manager = UserConfigManager()
    zip_str = str(Path(zip_path))

    existing = manager.load_config(user_id, silent=True)
    if existing:
        if existing.zip_file != zip_str:
            manager.update_config(user_id, zip_file=zip_str)
            existing.zip_file = zip_str
        if existing.llm_consent_asked:
            status = "enabled" if existing.llm_consent else "disabled"
            print(f"\n🔐 Using stored LLM consent for user '{user_id}': {status}")
            return existing.llm_consent
        # Consent not asked yet; prompt now
        consent = _prompt_for_llm_consent()
        manager.update_config(
            user_id,
            zip_file=existing.zip_file,
            llm_consent=consent,
            llm_consent_asked=True,
        )
        return consent

    consent = _prompt_for_llm_consent()
    stored = manager.update_config(
        user_id,
        zip_file=zip_str,
        llm_consent=consent,
        llm_consent_asked=True,
    ) if existing else manager.create_config(
        user_id,
        zip_str,
        consent,
        llm_consent_asked=True,
        data_access_consent=False,
    )
    if not stored:
        print("⚠️  Unable to persist consent choice; proceeding with this selection for the current run.")
    else:
        print(f"✅ Saved consent choice for user '{user_id}' to local configuration.")
    return consent


def _prompt_for_data_access_consent() -> bool:
    """
    Prompt the user for data-access consent with an official notice (stored once).
    """
    print(
        "\n  IMPORTANT: This pipeline will read and analyze the files in your ZIP archive on this machine."
        "\n  No data leaves your machine unless you explicitly enable LLM summarization later."
        "\n  Proceed only if you consent to local processing of your files."
    )

    while True:
        response = input("\n  Allow local analysis of your data? (y/n): ").strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")


def resolve_data_access_consent(zip_path: str, user_id: str) -> bool:
    """
    Load stored data-access consent; prompt and persist if missing.
    """
    manager = UserConfigManager()
    zip_str = str(Path(zip_path))

    existing = manager.load_config(user_id, silent=True)
    if existing:
        if existing.zip_file != zip_str:
            manager.update_config(user_id, zip_file=zip_str)
            existing.zip_file = zip_str
        if existing.data_access_consent:
            print(f"\n🔐 Using stored data access consent for user '{user_id}': granted")
            return True
        print(f"\n🔐 Data access consent for user '{user_id}' was not previously provided.")
        consent = _prompt_for_data_access_consent()
        stored = manager.update_config(
            user_id,
            zip_file=existing.zip_file,
            data_access_consent=consent,
        )
        if not stored:
            print("⚠️  Unable to persist consent choice; proceeding with this selection for the current run.")
        else:
            print(f"✅ Saved data access consent for user '{user_id}' to local configuration.")
        return consent

    consent = _prompt_for_data_access_consent()
    stored = manager.create_config(
        user_id,
        zip_str,
        llm_consent=False,
        llm_consent_asked=False,
        data_access_consent=consent,
    )
    if not stored:
        print("⚠️  Unable to persist consent choice; proceeding with this selection for the current run.")
    else:
        print(f"✅ Saved data access consent for user '{user_id}' to local configuration.")
    return consent


def _prompt_yes_no(message: str, default: bool = False) -> bool:
    """
    Simple yes/no prompt with default handling.
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        resp = input(f"{message} ({default_str}): ").strip().lower()
        if not resp:
            return default
        if resp in {"y", "yes"}:
            return True
        if resp in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")


def _prompt_for_data_access_consent() -> bool:
    """
    Prompt the user for data-access consent with an official notice.

    - Always prompts; consent is NOT persisted. You will be asked each run.
    - If declined, pipeline exits immediately without processing.
    """
    print(
        "\n🔐 Data Access Consent Required\n\n"
        "This pipeline will read and analyze the files contained in your ZIP archive on this machine.\n"
        "No data leaves your machine unless you explicitly enable LLM summarization later in this run.\n"
        "If you do not consent to local analysis of your files, the pipeline will terminate now."
    )
    return _prompt_yes_no("\nDo you consent to local analysis of your data?", default=False)


def main():  # pragma: no cover - CLI entry point
    """
    Example usage / CLI entry point
    """
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run the artifact pipeline against a ZIP file."
    )
    parser.add_argument("zip_path", help="Path to the ZIP file to analyze")
    parser.add_argument(
        "--user-id",
        help="Identifier for storing consent in the local configuration (default: $PIPELINE_USER_ID or current user)",
    )

    args = parser.parse_args()

    user_id = args.user_id or os.getenv("PIPELINE_USER_ID") or getpass.getuser() or "default"
    data_access_consent = resolve_data_access_consent(args.zip_path, user_id)
    if not data_access_consent:
        print("\n✗ Data access consent not granted. Exiting without processing.\n")
        return

    llm_consent = resolve_llm_consent(args.zip_path, user_id)
    
    try:
        # Create pipeline and run
        pipeline = ArtifactPipeline()
        result = pipeline.start(
            args.zip_path,
            use_llm=llm_consent,
            data_access_consent=data_access_consent,
            prompt_project_names=True,
        )

        # If user declined data access or nothing to report, exit quietly
        if not result:
            return
        
        # Print detailed analysis results by project
        print("\n" + "="*70)
        print("📋 DETAILED ANALYSIS RESULTS BY PROJECT")
        print("="*70)
        
        projects = result.get('projects', {})
        
        # Separate regular projects from misc files
        regular_projects = {k: v for k, v in projects.items() if k != '_misc_files'}
        misc_files = projects.get('_misc_files')
        
        # Process regular projects first
        for project_name, project_data in regular_projects.items():
            print("\n" + "="*70)
            print(f"PROJECT: {project_name}")
            print("="*70)
            
            # Git Analysis
            if project_data.get('is_git_repo'):
                git_analysis = project_data.get('git_analysis', {})
                print("\n" + "-"*70)
                print("🔍 GIT ANALYSIS")
                print("-"*70)
                if git_analysis:
                    if 'error' in git_analysis:
                        print(f"Error: {git_analysis['error']}")
                    else:
                        print(json.dumps(git_analysis, indent=2))
                else:
                    print("No Git analysis data available")

            # File Analysis Results
            analysis = project_data.get('analysis_results', {})
            
            print("\n" + "-"*70)
            print("📄 DOCUMENTATION ANALYSIS")
            print("-"*70)
            doc_data = analysis.get('documentation')
            if doc_data is None:
                print("No documentation files to analyze")
            elif isinstance(doc_data, dict) and 'error' in doc_data:
                print(f"Error: {doc_data['error']}")
            else:
                print(json.dumps(doc_data, indent=2))
            
            print("\n" + "-"*70)
            print("🖼️  IMAGE ANALYSIS")
            print("-"*70)
            img_data = analysis.get('images')
            if img_data is None:
                print("No image files to analyze")
            elif isinstance(img_data, dict) and 'error' in img_data:
                print(f"Error: {img_data['error']}")
            elif img_data:
                # Print summary for each image (full output can be very large)
                for i, img in enumerate(img_data, 1):
                    print(f"\n[Image {i}] {img.get('file_name', 'unknown')}")
                    print(f"  Resolution: {img.get('resolution', {}).get('width', 0)}x{img.get('resolution', {}).get('height', 0)}")
                    print(f"  Size: {img.get('file_stats', {}).get('size_mb', 0):.2f} MB")
                    print(f"  Format: {img.get('format', {}).get('format', 'unknown')}")
                    content = img.get('content_classification', {})
                    print(f"  Type: {content.get('primary_type', 'unknown')}")
            else:
                print("No image files found")
            
            print("\n" + "-"*70)
            print("💻 CODE ANALYSIS")
            print("-"*70)
            code_data = analysis.get('code')
            if code_data is None:
                print("No code files to analyze")
            elif isinstance(code_data, dict) and 'error' in code_data:
                print(f"Error: {code_data['error']}")
            elif code_data:
                # Print individual file analyses
                files = code_data.get('files', [])
                if files:
                    print(f"Individual File Analysis ({len(files)} files):")
                    print(json.dumps(files, indent=2))
                
                # Print aggregate metrics summary
                metrics = code_data.get('metrics', {})
                print(f"\n{'─'*70}")
                print("Aggregate Metrics Summary:")
                print(json.dumps(metrics, indent=2))
                
                # Print advanced skill analysis
                skill_analysis = code_data.get('skill_analysis', {})
                if skill_analysis:
                    print(f"\n{'─'*70}")
                    print("Advanced Skill Analysis:")
                    print(json.dumps(skill_analysis, indent=2))
            else:
                print("No code files found")
            
            print("\n" + "-"*70)
            print("🎥 VIDEO ANALYSIS")
            print("-"*70)
            video_data = analysis.get('videos')
            if video_data is None:
                print("No video files to analyze")
            elif isinstance(video_data, dict) and 'error' in video_data:
                print(f"Error: {video_data['error']}")
            elif video_data:
                print(json.dumps(video_data, indent=2))
            else:
                print("No video files found")
            
            # Success Metrics
            print("\n" + "-"*70)
            print("🎯 SUCCESS METRICS")
            print("-"*70)
            success_data = project_data.get('success_metrics')
            if success_data and 'error' not in success_data:
                print(json.dumps(success_data, indent=2))
            else:
                print("Success metrics not available")
        
        # Process miscellaneous files section if it exists
        if misc_files:
            print("\n" + "="*70)
            print(f"MISCELLANEOUS FILES (not in any project)")
            print("="*70)
            
            # File Analysis Results (no Git analysis for loose files)
            analysis = misc_files.get('analysis_results', {})
            
            print("\n" + "-"*70)
            print("📄 DOCUMENTATION ANALYSIS")
            print("-"*70)
            doc_data = analysis.get('documentation')
            if doc_data is None:
                print("No documentation files")
            elif isinstance(doc_data, dict) and 'error' in doc_data:
                print(f"Error: {doc_data['error']}")
            else:
                print(json.dumps(doc_data, indent=2))
            
            print("\n" + "-"*70)
            print("🖼️  IMAGE ANALYSIS")
            print("-"*70)
            img_data = analysis.get('images')
            if img_data is None:
                print("No image files")
            elif isinstance(img_data, dict) and 'error' in img_data:
                print(f"Error: {img_data['error']}")
            elif img_data:
                for i, img in enumerate(img_data, 1):
                    print(f"\n[Image {i}] {img.get('file_name', 'unknown')}")
                    print(f"  Resolution: {img.get('resolution', {}).get('width', 0)}x{img.get('resolution', {}).get('height', 0)}")
                    print(f"  Size: {img.get('file_stats', {}).get('size_mb', 0):.2f} MB")
                    print(f"  Format: {img.get('format', {}).get('format', 'unknown')}")
                    content = img.get('content_classification', {})
                    print(f"  Type: {content.get('primary_type', 'unknown')}")
            else:
                print("No image files")
            
            print("\n" + "-"*70)
            print("💻 CODE ANALYSIS")
            print("-"*70)
            code_data = analysis.get('code')
            if code_data is None:
                print("No code files")
            elif isinstance(code_data, dict) and 'error' in code_data:
                print(f"Error: {code_data['error']}")
            elif code_data:
                files = code_data.get('files', [])
                if files:
                    print(f"Individual File Analysis ({len(files)} files):")
                    print(json.dumps(files, indent=2))
                
                metrics = code_data.get('metrics', {})
                print(f"\n{'─'*70}")
                print("Aggregate Metrics Summary:")
                print(json.dumps(metrics, indent=2))
                
                # Print advanced skill analysis
                skill_analysis = code_data.get('skill_analysis', {})
                if skill_analysis:
                    print(f"\n{'─'*70}")
                    print("Advanced Skill Analysis:")
                    print(json.dumps(skill_analysis, indent=2))
            else:
                print("No code files")
            
            print("\n" + "-"*70)
            print("🎥 VIDEO ANALYSIS")
            print("-"*70)
            video_data = analysis.get('videos')
            if video_data is None:
                print("No video files")
            elif isinstance(video_data, dict) and 'error' in video_data:
                print(f"Error: {video_data['error']}")
            elif video_data:
                print(json.dumps(video_data, indent=2))
            else:
                print("No video files")
            
            # Success Metrics
            print("\n" + "-"*70)
            print("🎯 SUCCESS METRICS")
            print("-"*70)
            success_data = misc_files.get('success_metrics')
            if success_data and 'error' not in success_data:
                print(json.dumps(success_data, indent=2))
            else:
                print("Success metrics not available for miscellaneous files")
        
        if llm_consent:
            llm_output = result.get("llm_summaries")
            print("\n" + "="*70)
            print("🤖 LLM SUMMARIZATION OUTPUT")
            print("="*70)
            if llm_output:
                print(json.dumps(llm_output, indent=2))
            else:
                print("No LLM summaries were generated for this run.")
        
        # Print project ranking results
        ranking_data = result.get("project_ranking")
        print("\n" + "="*70)
        print("🏆 PROJECT RANKING & SUMMARIES")
        print("="*70)
        if ranking_data:
            if 'error' in ranking_data:
                print(f"Error: {ranking_data['error']}")
            else:
                print(json.dumps(ranking_data, indent=2))
        else:
            print("No project ranking data available")
        
        # Print chronological skills timeline
        skills_data = result.get("chronological_skills")
        print("\n" + "="*70)
        print("📅 CHRONOLOGICAL SKILLS TIMELINE")
        print("="*70)
        if skills_data:
            if 'error' in skills_data:
                print(f"Error: {skills_data['error']}")
            else:
                # Print summary stats
                print(f"\nTotal Events: {skills_data.get('total_events', 0)}")
                print(f"Categories: {', '.join(skills_data.get('categories', []))}")
                
                # Print full timeline in JSON (should already be serializable from _build_chronological_skills)
                print("\nFull Timeline:")
                try:
                    print(json.dumps(skills_data.get('timeline', []), indent=2))
                except (TypeError, ValueError) as e:
                    print(f"Warning: Could not serialize timeline to JSON: {e}")
                    print("Timeline data contains non-serializable types. Showing basic info only.")
        else:
            print("No chronological skills data available")
        
        print("\n" + "="*70)
        print("✅ Analysis Complete - All results printed above")
        print("="*70 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
