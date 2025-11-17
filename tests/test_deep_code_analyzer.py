import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from analysis.deep_code_analyzer import DeepCodeAnalyzer


class TestDeepCodeAnalyzer:
    """Test cases for DeepCodeAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return DeepCodeAnalyzer()
    

    def test_detect_data_structures_python(self, analyzer):
        """Test data structure detection in Python."""
        python_code = """
my_dict = {}
my_list = []
my_set = set()
result = my_dict.get('key')
my_list.append(1)
my_set.add(2)
"""
        result = analyzer._detect_data_structures(python_code, 'Python')
        
        assert 'structures_detected' in result
        assert 'hash_map' in result['structures_detected'] or result['total_structures'] > 0
    
    def test_analyze_complexity_patterns(self, analyzer):
        """Test complexity pattern detection."""
        code = """
for i in range(n):
    for j in range(m):
        result[i][j] = i * j
"""
        result = analyzer._analyze_complexity_patterns(code)
        
        assert 'nested_loops' in result
        assert len(result['nested_loops']) > 0
    
    def test_detect_optimizations(self, analyzer):
        """Test optimization detection."""
        code = """
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        result = analyzer._detect_optimizations(code)
        
        assert len(result) > 0
        assert any(opt['type'] == 'Caching/Memoization' for opt in result)
    
    def test_assess_code_quality(self, analyzer):
        """Test code quality assessment."""
        code = """
def example():
    try:
        result = process_data()
        return result
    except Exception as e:
        raise
"""
        result = analyzer._assess_code_quality(code, 'Python')
        
        assert 'error_handling' in result
        assert 'overall_score' in result
        assert result['error_handling'] > 0
    
    def test_aggregate_analysis(self, analyzer):
        """Test aggregation of multiple file analyses."""
        file_analyses = [
            {
                'oop_principles': {
                    'abstraction': [{'class': 'Base', 'evidence': 'test'}],
                    'encapsulation': []
                },
                'data_structures': {
                    'structures_detected': {'hash_map': {'count': 5}}
                },
                'complexity_analysis': {
                    'nested_loops': [{'line': 10}],
                    'complexity_indicators': []
                },
                'optimization_evidence': [],
                'code_quality': {'overall_score': 50}
            }
        ]
        
        result = analyzer.aggregate_analysis(file_analyses)
        
        assert 'oop_principles_summary' in result
        assert result['oop_principles_summary']['abstraction']['count'] == 1
        assert 'data_structure_summary' in result
        assert result['code_quality_summary']['average_quality_score'] == 50
    
    def test_analyze_code_file_empty(self, analyzer):
        """Test analysis of empty file."""
        result = analyzer.analyze_code_file("test.py", "", "Python")
        assert result == {}
    
    def test_analyze_code_file_python(self, analyzer):
        """Test complete file analysis for Python."""
        code = """
class Test:
    def __init__(self):
        self._private = 1
"""
        result = analyzer.analyze_code_file("test.py", code, "Python")
        
        assert 'file_path' in result
        assert 'language' in result
        assert 'oop_principles' in result
        assert 'data_structures' in result
        assert 'complexity_analysis' in result
        assert 'optimization_evidence' in result
        assert 'code_quality' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

