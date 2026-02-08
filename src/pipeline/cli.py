"""Unified CLI for artifact pipeline operations."""

import sys
import os
import json
import getpass
import argparse
from typing import Optional, List, Dict, Any


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.pipeline",
        description="Unified pipeline CLI for analysis, presentation, and display"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run the full artifact pipeline on a ZIP file"
    )
    analyze_parser.add_argument(
        "zip_path",
        help="Path to the ZIP file to analyze"
    )
    analyze_parser.add_argument(
        "--user-id",
        help="User ID for consent storage (default: $PIPELINE_USER_ID or current user)"
    )
    
    present_parser = subparsers.add_parser(
        "present",
        help="Generate portfolio and resume items from stored project insights"
    )
    
    present_mode = present_parser.add_mutually_exclusive_group(required=True)
    present_mode.add_argument(
        "--project-id",
        type=int,
        help="Generate items for a single project by ID"
    )
    present_mode.add_argument(
        "--zip-hash",
        help="Zip hash for selecting projects"
    )
    present_mode.add_argument(
        "--all",
        action="store_true",
        help="Generate items for all projects"
    )
    
    present_parser.add_argument(
        "--project-name",
        help="Project name (required with --zip-hash for single project)"
    )
    present_parser.add_argument(
        "--all-in-zip",
        action="store_true",
        help="Generate items for all projects in the specified zip hash"
    )
    present_parser.add_argument(
        "--db-path",
        help="Path to insights database"
    )
    present_parser.add_argument(
        "--encryption-key-env",
        help="Environment variable name containing encryption key"
    )
    present_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of projects (only for --all)"
    )
    
    portfolio_parser = subparsers.add_parser(
        "show-portfolio",
        help="Display human-friendly portfolio showcase for a project"
    )
    
    portfolio_mode = portfolio_parser.add_mutually_exclusive_group(required=True)
    portfolio_mode.add_argument(
        "--project-id",
        type=int,
        help="Project ID"
    )
    portfolio_mode.add_argument(
        "--zip-hash",
        help="Zip hash (requires --project-name)"
    )
    
    portfolio_parser.add_argument(
        "--project-name",
        help="Project name (required with --zip-hash)"
    )
    portfolio_parser.add_argument(
        "--db-path",
        help="Path to insights database"
    )
    portfolio_parser.add_argument(
        "--encryption-key-env",
        help="Environment variable name containing encryption key"
    )
    
    resume_parser = subparsers.add_parser(
        "show-resume",
        help="Display human-friendly resume item for a project"
    )
    
    resume_mode = resume_parser.add_mutually_exclusive_group(required=True)
    resume_mode.add_argument(
        "--project-id",
        type=int,
        help="Project ID"
    )
    resume_mode.add_argument(
        "--zip-hash",
        help="Zip hash (requires --project-name)"
    )
    
    resume_parser.add_argument(
        "--project-name",
        help="Project name (required with --zip-hash)"
    )
    resume_parser.add_argument(
        "--db-path",
        help="Path to insights database"
    )
    resume_parser.add_argument(
        "--encryption-key-env",
        help="Environment variable name containing encryption key"
    )
    
    list_parser = subparsers.add_parser(
        "list",
        help="List available projects from the insights database"
    )
    list_parser.add_argument(
        "--db-path",
        help="Path to insights database"
    )
    list_parser.add_argument(
        "--encryption-key-env",
        help="Environment variable name containing encryption key"
    )
    list_parser.add_argument(
        "--language",
        action="append",
        help="Filter by programming language (can be specified multiple times)"
    )
    list_parser.add_argument(
        "--framework",
        action="append",
        help="Filter by framework (can be specified multiple times)"
    )
    
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "analyze":
            return handle_analyze(args)
        elif args.command == "present":
            return handle_present(args)
        elif args.command == "show-portfolio":
            return handle_show_portfolio(args)
        elif args.command == "show-resume":
            return handle_show_resume(args)
        elif args.command == "list":
            return handle_list(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_analyze(args) -> int:
    """Handle the 'analyze' subcommand"""
    from src.pipeline.orchestrator import (
        ArtifactPipeline,
        resolve_data_access_consent,
        resolve_llm_consent
    )
    
    user_id = args.user_id or os.getenv("PIPELINE_USER_ID") or getpass.getuser() or "default"
    zip_path = args.zip_path
    data_consent = resolve_data_access_consent(zip_path, user_id)
    if not data_consent:
        print("✗ Data access consent not granted. Exiting.")
        return 0
    
    llm_consent = resolve_llm_consent(zip_path, user_id)
    print(f"\n🚀 Starting artifact pipeline for: {zip_path}")
    print(f"   User: {user_id}")
    print(f"   LLM: {'enabled' if llm_consent else 'disabled'}\n")
    
    pipeline = ArtifactPipeline()
    result = pipeline.start(zip_path, use_llm=llm_consent, data_access_consent=True)
    
    if not result:
        print("\n✓ Pipeline completed (no data to process)")
        return 0
    
    print("\n✅ Pipeline completed successfully!")
    
    return 0


def handle_present(args) -> int:
    """Handle the 'present' subcommand"""
    from src.pipeline.presentation_pipeline import PresentationPipeline
    
    encryption_key = None
    if args.encryption_key_env:
        key_str = os.getenv(args.encryption_key_env)
        if key_str:
            encryption_key = key_str.encode('utf-8')
    
    # Initialize pipeline
    pipeline = PresentationPipeline(
        db_path=args.db_path,
        encryption_key=encryption_key
    )
    
    if args.project_id:
        result = pipeline.generate_by_id(args.project_id, regenerate=True)
        print_single_result(result)
        return 0 if result.success else 1
    
    elif args.zip_hash and args.project_name:
        result = pipeline.generate_by_name(args.zip_hash, args.project_name, regenerate=True)
        print_single_result(result)
        return 0 if result.success else 1
    
    elif args.zip_hash and args.all_in_zip:
        result = pipeline.generate_for_zip(args.zip_hash, regenerate=True)
        print_batch_result(result)
        return 0 if result.failed == 0 else 1
    
    elif args.all:
        result = pipeline.generate_all(regenerate=True, limit=args.limit)
        print_batch_result(result)
        return 0 if result.failed == 0 else 1
    
    else:
        print("Error: Invalid argument combination for 'present'", file=sys.stderr)
        return 1


def handle_show_portfolio(args) -> int:
    """Handle the 'show-portfolio' subcommand"""
    from src.pipeline.presentation_pipeline import PresentationPipeline
    
    if args.zip_hash and not args.project_name:
        print("Error: --zip-hash requires --project-name", file=sys.stderr)
        return 1
    
    # Get encryption key if specified
    encryption_key = None
    if args.encryption_key_env:
        key_str = os.getenv(args.encryption_key_env)
        if key_str:
            encryption_key = key_str.encode('utf-8')
    
    # Initialize pipeline
    pipeline = PresentationPipeline(
        db_path=args.db_path,
        encryption_key=encryption_key
    )
    
    # Generate items
    if args.project_id:
        result = pipeline.generate_by_id(args.project_id, regenerate=True)
    else:
        result = pipeline.generate_by_name(args.zip_hash, args.project_name, regenerate=True)
    
    if not result.success:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1
    
    format_portfolio(result.portfolio_item)
    return 0


def handle_show_resume(args) -> int:
    """Handle the 'show-resume' subcommand"""
    from src.pipeline.presentation_pipeline import PresentationPipeline
    
    if args.zip_hash and not args.project_name:
        print("Error: --zip-hash requires --project-name", file=sys.stderr)
        return 1
    
    # Get encryption key if specified
    encryption_key = None
    if args.encryption_key_env:
        key_str = os.getenv(args.encryption_key_env)
        if key_str:
            encryption_key = key_str.encode('utf-8')
    
    # Initialize pipeline
    pipeline = PresentationPipeline(
        db_path=args.db_path,
        encryption_key=encryption_key
    )
    
    # Generate items
    if args.project_id:
        result = pipeline.generate_by_id(args.project_id, regenerate=True)
    else:
        result = pipeline.generate_by_name(args.zip_hash, args.project_name, regenerate=True)
    
    if not result.success:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1
    
    format_resume(result.resume_item)
    return 0


def handle_list(args) -> int:
    """Handle the 'list' subcommand"""
    from src.pipeline.presentation_pipeline import PresentationPipeline
    
    encryption_key = None
    if args.encryption_key_env:
        key_str = os.getenv(args.encryption_key_env)
        if key_str:
            encryption_key = key_str.encode('utf-8')
    
    pipeline = PresentationPipeline(db_path=args.db_path, encryption_key=encryption_key)
    
    # Apply filters if specified
    filters = {}
    if hasattr(args, 'language') and args.language:
        filters['languages'] = args.language
    if hasattr(args, 'framework') and args.framework:
        filters['frameworks'] = args.framework
    
    projects = pipeline.list_available_projects(filters=filters if filters else None)
    
    if not projects:
        filter_msg = ""
        if filters:
            filter_parts = []
            if 'languages' in filters:
                filter_parts.append(f"languages: {', '.join(filters['languages'])}")
            if 'frameworks' in filters:
                filter_parts.append(f"frameworks: {', '.join(filters['frameworks'])}")
            filter_msg = f" (filtered by {'; '.join(filter_parts)})"
        print(f"\nNo projects found in database{filter_msg}.\n")
        return 0
    
    filter_info = ""
    if filters:
        filter_parts = []
        if 'languages' in filters:
            filter_parts.append(f"Language: {', '.join(filters['languages'])}")
        if 'frameworks' in filters:
            filter_parts.append(f"Framework: {', '.join(filters['frameworks'])}")
        filter_info = f" [Filtered by {' | '.join(filter_parts)}]"
    
    print(f"\n{'='*100}")
    print(f"Available Projects ({len(projects)} total){filter_info}")
    print(f"{'='*100}\n")
    print(f"{'ID':<6} | {'Project Name':<30} | {'Zip Hash':<12} | {'Code':<5} | {'Docs':<5} | {'Git':<4} | {'Updated'}")
    print(f"{'-'*6}-+-{'-'*30}-+-{'-'*12}-+-{'-'*5}-+-{'-'*5}-+-{'-'*4}-+-{'-'*19}")
    
    for proj in projects:
        zip_short = proj['zip_hash'][:12] if proj['zip_hash'] else 'N/A'
        name_short = proj['project_name'][:30] if proj['project_name'] else 'N/A'
        git_status = 'Yes' if proj['is_git_repo'] else 'No'
        updated = proj.get('updated_at', 'N/A')[:19]
        
        print(
            f"{proj['project_id']:<6} | {name_short:<30} | {zip_short:<12} | "
            f"{proj['code_files']:<5} | {proj['doc_files']:<5} | {git_status:<4} | {updated}"
        )
    
    print(f"\n{'='*100}\n")
    return 0


def print_single_result(result) -> None:
    """Print a single PresentationResult as compact JSON"""
    print("\n" + "="*70)
    print("PRESENTATION RESULT")
    print("="*70)
    print(json.dumps(result.to_dict(), indent=2))
    print("="*70 + "\n")


def print_batch_result(result) -> None:
    """Print a BatchPresentationResult with summary"""
    print("\n" + "="*70)
    print("BATCH PRESENTATION RESULTS")
    print("="*70)
    print(f"Total Processed: {result.total_processed}")
    print(f"Successful: {result.successful}")
    print(f"Failed: {result.failed}")
    
    if result.successful > 0:
        print("\nSuccessful Projects:")
        for r in result.results:
            if r.success:
                print(f"  ✓ {r.project_name} (ID: {r.project_id})")
    
    if result.failed > 0:
        print("\nFailed Projects:")
        for r in result.results:
            if not r.success:
                print(f"  ✗ {r.project_name} (ID: {r.project_id}): {r.error}")
    
    print("="*70 + "\n")


def format_portfolio(portfolio_item: Dict[str, Any]) -> None:
    """Format and print a portfolio item in human-friendly format"""
    print("\n" + "="*70)
    print("PORTFOLIO SHOWCASE")
    print("="*70 + "\n")
    
    print(f"Project Name: {portfolio_item.get('project_name', 'N/A')}")
    print(f"Tagline: {portfolio_item.get('tagline', 'N/A')}")
    print(f"\nDescription:")
    print(f"  {portfolio_item.get('description', 'N/A')}")
    
    languages = portfolio_item.get('languages', [])
    if languages:
        print(f"\nLanguages: {', '.join(languages)}")
    
    frameworks = portfolio_item.get('frameworks', [])
    if frameworks:
        print(f"Frameworks: {', '.join(frameworks)}")
    
    skills = portfolio_item.get('skills', [])
    if skills:
        print(f"Skills: {', '.join(skills)}")
    
    key_features = portfolio_item.get('key_features', [])
    if key_features:
        print(f"\nKey Features:")
        for feature in key_features:
            print(f"  • {feature}")
    
    is_collab = portfolio_item.get('is_collaborative', False)
    commits = portfolio_item.get('total_commits', 0)
    loc = portfolio_item.get('total_lines', 0)
    
    print(f"\nMetrics:")
    print(f"  Collaboration: {'Yes' if is_collab else 'No'}")
    if commits > 0:
        print(f"  Commits: {commits}")
    if loc > 0:
        print(f"  Lines of Code: {loc:,}")
    
    print("\n" + "="*70 + "\n")


def format_resume(resume_item: Dict[str, Any]) -> None:
    """Format and print a resume item in human-friendly format"""
    print("\n" + "="*70)
    print("RESUME ITEM")
    print("="*70 + "\n")
    
    print(f"Project Name: {resume_item.get('project_name', 'N/A')}")
    print("\nBullets:")
    
    bullets = resume_item.get('bullets', [])
    for bullet in bullets:
        print(f"  • {bullet}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
