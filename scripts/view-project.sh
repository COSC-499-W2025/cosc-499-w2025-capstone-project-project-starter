#!/bin/bash
# View insights for most recent project

docker compose run --rm -T backend python - <<'PYTHON'
from src.insights.storage import ProjectInsightsStore
import json

store = ProjectInsightsStore(db_path="data/app.db")

# Get most recent run
runs = store.list_recent_zipfiles(limit=1)
if not runs:
    print("❌ No projects found. Run the pipeline first.")
    exit(1)

zip_hash = runs[0]["zip_hash"]
projects = store.list_projects_for_zip(zip_hash)

if not projects:
    print("❌ No projects in this ZIP")
    exit(1)

# Get first non-misc project
project_name = next((p for p in projects if p != "_misc_files"), projects[0])

print(f"\n📁 Project: {project_name}")
print(f"🔑 ZIP Hash: {zip_hash}\n")

# Load insights
payload = store.load_project_insight(zip_hash, project_name)

# Display key information
print("="*70)
print("PROJECT INSIGHTS")
print("="*70 + "\n")

print(f"Project Name: {payload.get('project_name')}")
print(f"Is Git Repo: {payload.get('is_git_repo')}")

git = payload.get('git_analysis', {})
if git and 'error' not in git:
    print(f"\nGit Stats:")
    print(f"  - Commits: {git.get('total_commits', 0)}")
    print(f"  - Contributors: {git.get('total_contributors', 0)}")

portfolio = payload.get('portfolio_item', {})
if portfolio and 'error' not in portfolio:
    print(f"\nPortfolio:")
    print(f"  - Tagline: {portfolio.get('tagline', 'N/A')}")
    print(f"  - Languages: {', '.join(portfolio.get('languages', [])[:5])}")
    print(f"  - Frameworks: {', '.join(portfolio.get('frameworks', [])[:3])}")

resume = payload.get('resume_item', {})
if resume and 'error' not in resume:
    print(f"\nResume Bullets:")
    for i, bullet in enumerate(resume.get('bullets', [])[:3], 1):
        print(f"  {i}. {bullet[:100]}...")

# Check for chronological skills
global_insights = payload.get('global_insights', {})
chron_skills = global_insights.get('chronological_skills', {})
if chron_skills:
    print(f"\nChronological Skills:")
    print(f"  - Total Events: {chron_skills.get('total_events', 0)}")
    print(f"  - Categories: {', '.join(chron_skills.get('categories', []))}")

print("\n" + "="*70)
print("✅ For full details, use: ./scripts/chronological-skills.sh")
print("="*70 + "\n")
PYTHON

