#!/bin/bash
# List all projects in the database

docker compose run --rm -T backend python - <<'PYTHON'
from src.insights.storage import ProjectInsightsStore

store = ProjectInsightsStore(db_path="data/app.db")
runs = store.list_recent_zipfiles(limit=20)

print("\n" + "="*70)
print("📦 ALL PROJECTS IN DATABASE")
print("="*70 + "\n")

if not runs:
    print("❌ No projects found. Run the pipeline first:")
    print("   ./scripts/run-pipeline.sh tests/categorize/demo_projects.zip\n")
    exit()

for i, run in enumerate(runs, 1):
    print(f"{i}. ZIP: {run['zip_path']}")
    print(f"   Hash: {run['zip_hash']}")
    print(f"   Projects: {run['total_projects']}")
    print(f"   Created: {run['created_at']}")
    
    # List individual projects
    projects = store.list_projects_for_zip(run['zip_hash'])
    for proj in projects:
        if proj != "_misc_files":
            print(f"   - {proj}")
    print()

print("="*70)
print(f"✅ Total ZIP files: {len(runs)}")
print("="*70 + "\n")
PYTHON

