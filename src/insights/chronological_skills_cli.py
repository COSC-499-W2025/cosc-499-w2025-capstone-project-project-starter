#!/usr/bin/env python3
"""
CLI tool to retrieve and display chronological skills timeline.

Usage:
    python -m src.insights.chronological_skills_cli
    python -m src.insights.chronological_skills_cli --format json
    python -m src.insights.chronological_skills_cli --format csv
    python -m src.insights.chronological_skills_cli --output skills.json
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Optional

from src.insights.storage import ProjectInsightsStore


def display_timeline_text(chron_skills: dict) -> None:
    """Display chronological skills timeline in text format."""
    timeline = chron_skills.get("timeline", [])
    
    print("\n" + "="*70)
    print("📅 CHRONOLOGICAL LIST OF SKILLS EXERCISED")
    print("="*70)
    print(f"\nTotal Skill Events: {chron_skills.get('total_events', 0)}")
    print(f"Categories: {', '.join(chron_skills.get('categories', []))}")
    
    if timeline:
        first_date = timeline[0]['timestamp'].split('T')[0]
        last_date = timeline[-1]['timestamp'].split('T')[0]
        print(f"Date Range: {first_date} to {last_date}")
    
    print("\n" + "="*70 + "\n")
    
    # Print full chronological list
    for i, event in enumerate(timeline, 1):
        timestamp = event['timestamp'].split('T')[0]  # Get date only
        time = event['timestamp'].split('T')[1].split('.')[0] if 'T' in event['timestamp'] else ''
        category = event['category'].upper()
        file_path = event['file']
        file_name = file_path.split('/')[-1]
        skills = event['skills']
        
        print(f"{i}. 📅 {timestamp} {time}")
        print(f"   📁 File: {file_name}")
        print(f"   🏷️  Category: {category}")
        print(f"   🎯 Skills: {', '.join(skills) if skills else 'No skills detected'}")
        print()
    
    print("="*70)
    print(f"✅ Chronological skills list complete ({len(timeline)} events)")
    print("="*70)


def export_json(chron_skills: dict, output_path: Optional[str] = None) -> None:
    """Export chronological skills to JSON file."""
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(chron_skills, f, indent=2)
        print(f"✅ Chronological skills saved to: {output_path}")
    else:
        print(json.dumps(chron_skills, indent=2))


def export_csv(chron_skills: dict, output_path: Optional[str] = None) -> None:
    """Export chronological skills to CSV file."""
    import io
    
    output = io.StringIO() if not output_path else open(output_path, 'w', newline='')
    
    try:
        writer = csv.writer(output)
        writer.writerow(['Date', 'Time', 'File', 'Category', 'Skills'])
        
        for event in chron_skills.get('timeline', []):
            timestamp_parts = event['timestamp'].split('T')
            date = timestamp_parts[0]
            time = timestamp_parts[1].split('.')[0] if len(timestamp_parts) > 1 else ''
            file_name = event['file'].split('/')[-1]
            category = event['category']
            skills = '; '.join(event['skills'])
            
            writer.writerow([date, time, file_name, category, skills])
        
        if output_path:
            print(f"✅ Chronological skills CSV saved to: {output_path}")
        else:
            print(output.getvalue())
    finally:
        if output_path:
            output.close()


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve and display chronological skills timeline"
    )
    parser.add_argument(
        '--db-path',
        default='data/app.db',
        help='Path to database (default: data/app.db)'
    )
    parser.add_argument(
        '--zip-hash',
        help='Specific ZIP hash to query (default: most recent)'
    )
    parser.add_argument(
        '--project',
        help='Specific project name (default: first project)'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--output',
        help='Output file path (if not specified, prints to stdout)'
    )
    
    args = parser.parse_args()
    
    # Initialize store
    try:
        store = ProjectInsightsStore(db_path=args.db_path)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}", file=sys.stderr)
        return 1
    
    # Get ZIP hash
    if args.zip_hash:
        zip_hash = args.zip_hash
    else:
        runs = store.list_recent_zipfiles(limit=1)
        if not runs:
            print("❌ No pipeline runs found. Run the pipeline first:", file=sys.stderr)
            print("   docker compose run --rm backend python -m src.pipeline.orchestrator tests/categorize/demo_projects.zip", file=sys.stderr)
            return 1
        zip_hash = runs[0]["zip_hash"]
    
    # Get project name
    projects = store.list_projects_for_zip(zip_hash)
    if not projects:
        print(f"❌ No projects found for ZIP hash: {zip_hash}", file=sys.stderr)
        return 1
    
    if args.project:
        project_name = args.project
    else:
        # Get first non-misc project
        project_name = next((p for p in projects if p != "_misc_files"), projects[0])
    
    # Load chronological skills
    try:
        payload = store.load_project_insight(zip_hash, project_name)
        global_insights = payload.get("global_insights", {})
        chron_skills = global_insights.get("chronological_skills", {})
    except Exception as e:
        print(f"❌ Error loading project insights: {e}", file=sys.stderr)
        return 1
    
    if not chron_skills or not chron_skills.get("timeline"):
        print(f"❌ No chronological skills found for project: {project_name}", file=sys.stderr)
        print(f"Available global insights keys: {list(global_insights.keys())}", file=sys.stderr)
        return 1
    
    # Output in requested format
    if args.format == 'json':
        export_json(chron_skills, args.output)
    elif args.format == 'csv':
        export_csv(chron_skills, args.output)
    else:
        display_timeline_text(chron_skills)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

