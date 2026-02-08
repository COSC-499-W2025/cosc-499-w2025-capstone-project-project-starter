"""
Demonstration test showing presentation generation in action

This test demonstrates the portfolio and resume generation feature
integrated into the artifact pipeline.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.project.presentation import generate_portfolio_item, generate_resume_item


def test_demonstration_portfolio_and_resume_generation():
    """
    Demonstration: Generate portfolio and resume items from project analysis
    
    This test simulates what happens inside ArtifactPipeline._process_project()
    after analysis completes. The presentation generators create structured
    summaries suitable for portfolio sites and résumés.
    """
    
    # Sample project dict as returned by _process_project
    collaborative_project = {
        "project_name": "Mobile Food Delivery App",
        "project_path": "/projects/food-delivery",
        "is_git_repo": True,
        "git_analysis": {
            "total_commits": 342,
            "total_contributors": 5,
            "contributors": []
        },
        "categorized_contents": {
            "code": ["app.py", "models.py", "api.py"],
            "documentation": ["README.md", "API_DOCS.md"]
        },
        "analysis_results": {
            "code": {
                "metrics": {
                    "languages": ["Python", "JavaScript", "Swift", "Kotlin"],
                    "frameworks": ["Django", "React Native", "PostgreSQL", "Redis"],
                    "skills": [
                        "RESTful API Design",
                        "Real-time Updates",
                        "Mobile Development",
                        "Database Optimization",
                        "Authentication & Authorization"
                    ],
                    "total_files": 127,
                    "total_lines": 15420
                }
            }
        }
    }
    
    # Generate presentation items (as done in orchestrator)
    portfolio = generate_portfolio_item(collaborative_project)
    resume = generate_resume_item(collaborative_project)
    
    # Verify portfolio structure
    print("\n" + "="*70)
    print("PORTFOLIO ITEM")
    print("="*70)
    print(f"Project: {portfolio['project_name']}")
    print(f"Tagline: {portfolio['tagline']}")
    print(f"Description: {portfolio['description']}")
    print(f"Languages: {', '.join(portfolio['languages'])}")
    print(f"Frameworks: {', '.join(portfolio['frameworks'][:5])}")
    print(f"Skills: {', '.join(portfolio['skills'][:5])}")
    print(f"Collaborative: {portfolio['is_collaborative']}")
    print(f"Commits: {portfolio['total_commits']}")
    print(f"Lines of Code: {portfolio['total_lines']:,}")
    
    # Verify resume structure
    print("\n" + "="*70)
    print("RESUME ITEM")
    print("="*70)
    print(f"Project: {resume['project_name']}")
    print("\nBullet Points:")
    for i, bullet in enumerate(resume['bullets'], 1):
        print(f"{i}. {bullet}")
    
    print("\n" + "="*70)
    
    # Assertions
    assert portfolio['project_name'] == "Mobile Food Delivery App"
    # Tagline may use "Collaborative", "Team-based", or "Multi-contributor"
    assert any(word in portfolio['tagline'] for word in ['Collaborative', 'Team-based', 'Multi-contributor'])
    assert portfolio['is_collaborative'] is True
    assert portfolio['total_commits'] == 342
    assert portfolio['total_lines'] == 15420
    
    assert resume['project_name'] == "Mobile Food Delivery App"
    assert len(resume['bullets']) >= 2  # May have 2-3 bullets
    # May mention languages explicitly or say "multi-language"
    assert any('Python' in bullet or 'JavaScript' in bullet or 'multi-language' in bullet for bullet in resume['bullets'])
    # May say "342+ commits" or "342 commits", "5 contributors" or "5 team members"
    assert any('342' in bullet or '5' in bullet for bullet in resume['bullets'])
    
    print("\n[PASS] Demonstration test passed!\n")


if __name__ == "__main__":
    test_demonstration_portfolio_and_resume_generation()

