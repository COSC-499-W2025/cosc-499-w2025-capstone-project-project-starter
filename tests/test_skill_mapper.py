# tests/test_skill_mapper.py
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.skill_mapper import SkillMapper


class TestSkillMapper:
    """Test suite for SkillMapper functionality"""
    
    def test_map_technical_skill_known(self):
        """Test mapping known technical skills"""
        assert SkillMapper.map_technical_skill('Python') == 'Python Programming'
        assert SkillMapper.map_technical_skill('abstraction') == 'Object-Oriented Design'
        assert SkillMapper.map_technical_skill('hash_map') == 'Hash Tables & Key-Value Data Structures'
    
    def test_map_technical_skill_unknown(self):
        """Test mapping unknown technical skills"""
        result = SkillMapper.map_technical_skill('custom_skill')
        assert result == 'Custom Skill'
    
    
    def test_extract_skills_from_deep_analysis(self):
        """Test extracting skills from deep analysis"""
        deep_analysis = {
            'oop_principles_summary': {
                'abstraction': {'count': 5},
                'encapsulation': {'count': 3}
            },
            'data_structure_summary': {'hash_map': 10, 'list': 5},
            'complexity_summary': {'nested_loops': 3, 'recursive_functions': 2},
            'code_quality_summary': {'error_handling': 5, 'documentation': 3}
        }
        skills = SkillMapper.extract_skills_from_deep_analysis(deep_analysis)
        assert len(skills) > 0
        assert 'Object-Oriented Design' in skills
        assert 'Hash Tables & Key-Value Data Structures' in skills
    
    def test_extract_skills_from_deep_analysis_empty(self):
        """Test extracting skills from empty analysis"""
        skills = SkillMapper.extract_skills_from_deep_analysis({})
        assert len(skills) == 0
    
    def test_extract_skills_from_project_summary(self):
        """Test extracting skills from project summary"""
        project_summary = {
            'languages': {'languages': ['Python', 'JavaScript']},
            'frameworks': ['Flask', 'React']
        }
        skills = SkillMapper.extract_skills_from_project_summary(project_summary)
        assert 'Python Programming' in skills
        assert 'JavaScript Programming' in skills
        assert 'Flask Web Framework' in skills or 'Flask' in str(skills)
    
    def test_categorize_skills(self):
        """Test skill categorization"""
        skills = {'Python', 'Flask', 'abstraction', 'hash_map'}
        categorized = SkillMapper.categorize_skills(skills)
        assert len(categorized) > 0
        assert 'Programming Languages' in categorized or 'Web Frameworks' in categorized
    
    def test_categorize_skills_empty(self):
        """Test categorizing empty skill set"""
        categorized = SkillMapper.categorize_skills(set())
        assert len(categorized) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

