"""
Integration tests for orchestrator with presentation features (portfolio and resume items)

This test module verifies that the presentation generation integrates correctly
with the project analysis pipeline without requiring the full orchestrator stack.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.project.presentation import generate_portfolio_item, generate_resume_item


class TestPresentationIntegration:
    """
    Integration tests for presentation generation with project analysis data
    
    These tests verify that portfolio and resume items can be correctly generated
    from project analysis dictionaries that match the structure returned by
    ArtifactPipeline._process_project()
    """
    
    def test_presentation_with_full_project_dict(self):
        """Test presentation generation with complete project data"""
        # Simulate a complete project dict from _process_project
        project_dict = {
            "project_name": "E-Commerce API",
            "project_path": "/fake/path/ecommerce",
            "is_git_repo": True,
            "git_analysis": {
                "total_commits": 250,
                "total_contributors": 4,
                "contributors": []
            },
            "categorized_contents": {
                "code": ["api.py", "models.py", "tests.py"],
                "documentation": ["README.md"],
                "images": [],
                "other": []
            },
            "analysis_results": {
                "code": {
                    "metrics": {
                        "languages": ["Python", "JavaScript"],
                        "frameworks": ["Django", "React", "PostgreSQL"],
                        "skills": ["REST API", "Authentication", "Database Design"],
                        "total_files": 45,
                        "total_lines": 6000
                    }
                }
            }
        }
        
        # Generate presentation items
        portfolio = generate_portfolio_item(project_dict)
        resume = generate_resume_item(project_dict)
        
        # Verify portfolio structure and content
        assert isinstance(portfolio, dict)
        assert portfolio["project_name"] == "E-Commerce API"
        # Tagline may use "Collaborative", "Team-based", or "Multi-contributor"
        assert any(word in portfolio["tagline"] for word in ["Collaborative", "Team-based", "Multi-contributor"])
        assert "Python" in portfolio["tagline"] or "multi-language" in portfolio["tagline"]
        assert portfolio["is_collaborative"] is True
        assert portfolio["total_commits"] == 250
        assert portfolio["total_lines"] == 6000
        assert portfolio["languages"] == ["Python", "JavaScript"]
        assert "Django" in portfolio["frameworks"]
        
        # Verify resume structure and content
        assert isinstance(resume, dict)
        assert resume["project_name"] == "E-Commerce API"
        assert len(resume["bullets"]) >= 2
        assert len(resume["bullets"]) <= 3
        
        bullets_text = " ".join(resume["bullets"])
        assert "Python" in bullets_text or "JavaScript" in bullets_text
        # May say "250+ commits" or "250 commits", "4 contributors" or "4 team members"
        assert "250" in bullets_text or "4" in bullets_text
        assert any(skill in bullets_text for skill in ["REST API", "Authentication", "Database Design"])
    
    def test_presentation_with_minimal_project_dict(self):
        """Test presentation generation with minimal project data"""
        # Minimal project dict (no Git, no analysis)
        project_dict = {
            "project_name": "Simple Script",
            "project_path": "/fake/path/script",
            "is_git_repo": False,
            "git_analysis": None,
            "categorized_contents": {},
            "analysis_results": {}
        }
        
        # Generate presentation items
        portfolio = generate_portfolio_item(project_dict)
        resume = generate_resume_item(project_dict)
        
        # Should still produce valid output
        assert isinstance(portfolio, dict)
        assert portfolio["project_name"] == "Simple Script"
        assert len(portfolio["tagline"]) > 0
        assert len(portfolio["description"]) > 0
        assert portfolio["is_collaborative"] is False
        assert portfolio["total_commits"] == 0
        
        assert isinstance(resume, dict)
        assert resume["project_name"] == "Simple Script"
        assert len(resume["bullets"]) >= 1
    
    def test_presentation_with_individual_git_project(self):
        """Test presentation generation for individual project with Git"""
        project_dict = {
            "project_name": "Personal Blog",
            "project_path": "/fake/path/blog",
            "is_git_repo": True,
            "git_analysis": {
                "total_commits": 75,
                "total_contributors": 1
            },
            "categorized_contents": {},
            "analysis_results": {
                "code": {
                    "metrics": {
                        "languages": ["Python"],
                        "frameworks": ["Flask", "SQLite"],
                        "skills": ["Web Development", "Templating"],
                        "total_files": 20,
                        "total_lines": 1800
                    }
                }
            }
        }
        
        portfolio = generate_portfolio_item(project_dict)
        resume = generate_resume_item(project_dict)
        
        # Should identify as individual project
        assert portfolio["is_collaborative"] is False
        assert "Individual" in portfolio["tagline"]
        assert portfolio["total_commits"] == 75
        
        bullets_text = " ".join(resume["bullets"])
        assert "Developed" in bullets_text
        assert "75" in bullets_text or "disciplined" in bullets_text.lower()
    
    def test_presentation_handles_analysis_errors(self):
        """Test that presentation handles analysis errors gracefully"""
        project_dict = {
            "project_name": "Error Project",
            "project_path": "/fake/path",
            "is_git_repo": False,
            "git_analysis": {"error": "Git failed"},
            "categorized_contents": {},
            "analysis_results": {
                "code": {"error": "Analysis failed"}
            }
        }
        
        # Should not crash
        portfolio = generate_portfolio_item(project_dict)
        resume = generate_resume_item(project_dict)
        
        assert isinstance(portfolio, dict)
        assert isinstance(resume, dict)
        assert portfolio["project_name"] == "Error Project"
        assert resume["project_name"] == "Error Project"
    
    def test_presentation_reflects_metrics(self):
        """Test that generated items accurately reflect input metrics"""
        project_dict = {
            "project_name": "Mobile App",
            "project_path": "/fake/path/mobile",
            "is_git_repo": True,
            "git_analysis": {
                "total_commits": 150,
                "total_contributors": 3
            },
            "categorized_contents": {},
            "analysis_results": {
                "code": {
                    "metrics": {
                        "languages": ["Swift", "Kotlin"],
                        "frameworks": ["UIKit", "Jetpack Compose"],
                        "skills": ["Mobile UI", "RESTful API", "Local Storage"],
                        "total_files": 60,
                        "total_lines": 5500
                    }
                }
            }
        }
        
        portfolio = generate_portfolio_item(project_dict)
        resume = generate_resume_item(project_dict)
        
        # Portfolio should match metrics exactly
        assert portfolio["languages"] == ["Swift", "Kotlin"]
        assert portfolio["frameworks"] == ["UIKit", "Jetpack Compose"]
        assert portfolio["skills"] == ["Mobile UI", "RESTful API", "Local Storage"]
        assert portfolio["total_lines"] == 5500
        assert portfolio["total_commits"] == 150
        assert portfolio["is_collaborative"] is True
        
        # Resume should mention key metrics
        bullets_text = " ".join(resume["bullets"])
        assert "Swift" in bullets_text or "Kotlin" in bullets_text
        # May say "150+ commits" or "150 commits", "3 contributors" or "3 team members"
        assert "150" in bullets_text or "3" in bullets_text
        assert any(skill in bullets_text for skill in portfolio["skills"][:3])

