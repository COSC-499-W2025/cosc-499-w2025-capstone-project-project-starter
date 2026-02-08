"""
Tests for Success Metrics Analyzer
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.analyze.success_metrics import SuccessMetricsAnalyzer, SuccessMetrics


@pytest.fixture
def analyzer():
    """Create a success metrics analyzer instance"""
    return SuccessMetricsAnalyzer()


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "project_name": "test_project",
        "is_git_repo": True,
        "git_analysis": {
            "total_commits": 50,
            "total_contributors": 3,
            "duration_days": 30
        },
        "categorized_contents": {
            "code": ["main.py", "utils.py", "test_main.py"],
            "documentation": ["README.md", "DOCS.md"]
        },
        "analysis_results": {
            "code": {
                "metrics": {
                    "total_lines": 1500,
                    "total_files": 3,
                    "languages": ["Python", "JavaScript"],
                    "frameworks": ["Flask", "React"]
                },
                "skill_analysis": {
                    "aggregate": {
                        "advanced_skills": ["async", "decorators", "regex"]
                    }
                }
            },
            "documentation": {
                "totals": {
                    "total_words": 3000,
                    "total_files": 2
                },
                "files": [
                    {
                        "file_name": "README.md",
                        "full_text": "# Test Project\n![build passing](badge.svg)\nThis is an excellent project."
                    }
                ]
            }
        }
    }


def test_analyzer_initialization(analyzer):
    """Test that analyzer initializes correctly"""
    assert analyzer is not None
    assert hasattr(analyzer, 'analyze')


def test_analyze_returns_success_metrics(analyzer, sample_project_data):
    """Test that analyze returns SuccessMetrics object"""
    result = analyzer.analyze(sample_project_data)
    
    assert isinstance(result, SuccessMetrics)
    assert hasattr(result, 'overall_score')
    assert hasattr(result, 'code_quality_score')
    assert hasattr(result, 'to_dict')


def test_overall_score_calculation(analyzer, sample_project_data):
    """Test that overall score is calculated and in valid range"""
    result = analyzer.analyze(sample_project_data)
    
    assert 0 <= result.overall_score <= 100
    assert isinstance(result.overall_score, float)


def test_code_quality_score(analyzer, sample_project_data):
    """Test code quality score calculation"""
    result = analyzer.analyze(sample_project_data)
    
    # Should have a good score due to multiple languages, frameworks, and skills
    assert result.code_quality_score > 50
    assert result.code_quality_score <= 100


def test_test_coverage_estimation(analyzer, sample_project_data):
    """Test test coverage estimation"""
    result = analyzer.analyze(sample_project_data)
    
    # Should detect test file (test_main.py)
    assert result.test_coverage_indicator is not None
    assert result.test_coverage_indicator > 0


def test_documentation_score(analyzer, sample_project_data):
    """Test documentation score calculation"""
    result = analyzer.analyze(sample_project_data)
    
    # Should have good documentation score (README + 3000 words)
    assert result.documentation_score > 40
    assert result.documentation_score <= 100


def test_activity_score(analyzer, sample_project_data):
    """Test activity score based on commits"""
    result = analyzer.analyze(sample_project_data)
    
    # 50 commits should give a decent activity score
    assert result.activity_score > 0
    assert result.activity_score <= 100


def test_collaboration_score(analyzer, sample_project_data):
    """Test collaboration score based on contributors"""
    result = analyzer.analyze(sample_project_data)
    
    # 3 contributors should give a good collaboration score
    assert result.collaboration_score > 50
    assert result.collaboration_score <= 100


def test_badge_extraction(analyzer, sample_project_data):
    """Test that badges are extracted from documentation"""
    result = analyzer.analyze(sample_project_data)
    
    assert len(result.badges) > 0
    assert any(badge['type'] == 'build' for badge in result.badges)


def test_feedback_extraction(analyzer, sample_project_data):
    """Test that positive feedback is extracted"""
    result = analyzer.analyze(sample_project_data)
    
    # Should find "excellent" keyword
    assert len(result.feedback_items) > 0


def test_details_structure(analyzer, sample_project_data):
    """Test that details dictionary has expected structure"""
    result = analyzer.analyze(sample_project_data)
    
    assert 'code_quality' in result.details
    assert 'documentation' in result.details
    assert 'activity' in result.details
    assert 'collaboration' in result.details
    
    # Each detail should have score and description
    assert 'score' in result.details['code_quality']
    assert 'description' in result.details['code_quality']


def test_to_dict_serialization(analyzer, sample_project_data):
    """Test that SuccessMetrics can be serialized to dict"""
    result = analyzer.analyze(sample_project_data)
    result_dict = result.to_dict()
    
    assert isinstance(result_dict, dict)
    assert 'overall_score' in result_dict
    assert 'code_quality_score' in result_dict
    assert 'badges' in result_dict
    assert 'details' in result_dict


def test_handles_missing_git_analysis(analyzer):
    """Test that analyzer handles projects without git analysis"""
    project_data = {
        "project_name": "test",
        "is_git_repo": False,
        "git_analysis": None,
        "categorized_contents": {},
        "analysis_results": {}
    }
    
    result = analyzer.analyze(project_data)
    
    # Should return valid metrics even without git data
    assert isinstance(result, SuccessMetrics)
    assert result.overall_score >= 0


def test_handles_missing_code_analysis(analyzer):
    """Test that analyzer handles projects without code analysis"""
    project_data = {
        "project_name": "test",
        "is_git_repo": False,
        "git_analysis": {},
        "categorized_contents": {},
        "analysis_results": {}
    }
    
    result = analyzer.analyze(project_data)
    
    # Should return valid metrics even without code data
    assert isinstance(result, SuccessMetrics)
    assert result.code_quality_score == 0.0


def test_solo_project_collaboration_score(analyzer):
    """Test collaboration score for solo projects"""
    project_data = {
        "project_name": "test",
        "git_analysis": {
            "total_commits": 10,
            "total_contributors": 1
        },
        "categorized_contents": {},
        "analysis_results": {}
    }
    
    result = analyzer.analyze(project_data)
    
    # Solo project should have lower collaboration score
    assert result.collaboration_score == 30.0


def test_large_codebase_complexity_score(analyzer):
    """Test complexity score for large codebases"""
    project_data = {
        "project_name": "test",
        "git_analysis": {},
        "categorized_contents": {},
        "analysis_results": {
            "code": {
                "metrics": {
                    "total_lines": 15000
                }
            }
        }
    }
    
    result = analyzer.analyze(project_data)
    
    # Large codebase should have high complexity score
    assert result.complexity_score == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
