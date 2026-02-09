import pytest
from unittest.mock import MagicMock
from datetime import datetime

@pytest.fixture
def mock_db_session():
    """Shared mock for database sessions."""
    return MagicMock()

@pytest.fixture
def mock_project_data():
    """
    A comprehensive mock project dictionary that satisfies the needs of:
    - ItemFormatter (Resume)
    - PortfolioFormatter (Portfolio)
    - ProjectAnalyzer (Analysis output verification)
    """
    return {
        'project_info': {
            'id': 101,
            'filename': 'stock_trader_v2.zip',
            'created_at': '2025-01-20T10:00:00',
            'user_name': 'test_user'
        },
        'file_statistics': {
            'total_lines_of_code': 1200,
            'total_files': 15,
            'languages': {'Python': 800, 'JavaScript': 400},
            'total_size_mb': 4.0
        },
        'languages': {
            'detected_languages': ['Python', 'JavaScript']
        },
        'frameworks': ['React', 'FastAPI'],
        'project_structure': {
            'has_tests': True,
            'has_docs': True,
            'tree': ['src/main.py', 'src/api.py', 'tests/test_main.py']
        },
        'collaboration_analysis': {
            'contributors': ['Kevin', 'Sami']
        },
        # Legacy fields for backward compatibility
        'lines_of_code': 1200,
        'file_count': 15,
        'code_quality_score': 85,
        'files': ['src/main.py', 'src/api.py', 'tests/test_main.py']
    }