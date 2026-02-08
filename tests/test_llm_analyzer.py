"""
Unit tests for LLM Analyzer module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from llm_analyzer import LLMAnalyzer, AnalysisType, quick_analyze


class TestLLMAnalyzer:
    """Test suite for LLMAnalyzer class"""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test analysis response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.total_tokens = 150
        return mock_response
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance with mocked API key"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            return LLMAnalyzer(api_key="test-key")
    
    def test_initialization_with_api_key(self):
        """Test analyzer initialization with API key"""
        analyzer = LLMAnalyzer(api_key="test-key-123")
        assert analyzer.api_key == "test-key-123"
        assert analyzer.model == "gpt-4o-mini"
        assert analyzer.temperature == 0.7
    
    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                LLMAnalyzer()
    
    def test_initialization_with_custom_parameters(self):
        """Test initialization with custom parameters"""
        analyzer = LLMAnalyzer(
            api_key="test-key",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2000
        )
        assert analyzer.model == "gpt-4o"
        assert analyzer.temperature == 0.5
        assert analyzer.max_tokens == 2000
    
    def test_system_prompts_exist_for_all_types(self, analyzer):
        """Test that system prompts are defined for all analysis types"""
        for analysis_type in AnalysisType:
            assert analysis_type in analyzer.system_prompts
            assert len(analyzer.system_prompts[analysis_type]) > 0
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_success(self, mock_openai_class, analyzer, mock_openai_response):
        """Test successful analysis"""
        # Setup mock
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        # Run analysis
        result = analyzer.analyze(
            content="Test code",
            analysis_type=AnalysisType.CODE_REVIEW
        )
        
        # Assertions
        assert result["success"] is True
        assert result["analysis"] == "This is a test analysis response"
        assert result["tokens_used"] == 150
        assert result["model"] == "gpt-4o-mini"
        assert result["analysis_type"] == "code_review"
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_with_custom_prompt(self, mock_openai_class, analyzer, mock_openai_response):
        """Test analysis with custom prompt"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        custom_prompt = "Please analyze this carefully"
        result = analyzer.analyze(
            content="Test content",
            analysis_type=AnalysisType.CODE_REVIEW,
            custom_prompt=custom_prompt
        )
        
        assert result["success"] is True
        # Verify the custom prompt was used
        call_args = mock_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert custom_prompt in user_message
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_with_context(self, mock_openai_class, analyzer, mock_openai_response):
        """Test analysis with context"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        context = {"filename": "test.py", "language": "Python"}
        result = analyzer.analyze(
            content="def test(): pass",
            analysis_type=AnalysisType.CODE_REVIEW,
            context=context
        )
        
        assert result["success"] is True
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_api_error(self, mock_openai_class, analyzer):
        """Test handling of API errors"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        analyzer.client = mock_client
        
        result = analyzer.analyze(
            content="Test",
            analysis_type=AnalysisType.CODE_REVIEW
        )
        
        assert result["success"] is False
        assert "API Error" in result["error"]
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_code_file(self, mock_openai_class, analyzer, mock_openai_response):
        """Test code file analysis"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        result = analyzer.analyze_code_file(
            code="def hello(): return 'world'",
            filename="hello.py",
            language="Python"
        )
        
        assert result["success"] is True
        assert result["analysis_type"] == "code_review"
    
    @patch('llm_analyzer.OpenAI')
    def test_analyze_git_commits(self, mock_openai_class, analyzer, mock_openai_response):
        """Test git commit analysis"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        commits = [
            {"hash": "abc123", "message": "Initial commit", "author": "Test", "date": "2024-01-01"},
            {"hash": "def456", "message": "Add feature", "author": "Test", "date": "2024-01-02"}
        ]
        
        result = analyzer.analyze_git_commits(
            commits=commits,
            repo_name="test-repo"
        )
        
        assert result["success"] is True
        assert result["analysis_type"] == "commit_summary"
    
    @patch('llm_analyzer.OpenAI')
    def test_extract_skills(self, mock_openai_class, analyzer, mock_openai_response):
        """Test skill extraction"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        artifacts = [
            "Built with Python and FastAPI",
            "Used React and TypeScript for frontend"
        ]
        
        result = analyzer.extract_skills(artifacts)
        
        assert result["success"] is True
        assert result["analysis_type"] == "skill_extraction"
    
    @patch('llm_analyzer.OpenAI')
    def test_generate_portfolio_entry(self, mock_openai_class, analyzer, mock_openai_response):
        """Test portfolio entry generation"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        project_data = {
            "name": "Test Project",
            "description": "A test project",
            "technologies": ["Python", "FastAPI"],
            "commit_count": 50,
            "file_count": 20
        }
        
        result = analyzer.generate_portfolio_entry(project_data)
        
        assert result["success"] is True
        assert result["analysis_type"] == "portfolio_generation"
    
    @patch('llm_analyzer.OpenAI')
    def test_batch_analyze(self, mock_openai_class, analyzer, mock_openai_response):
        """Test batch analysis"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        analyzer.client = mock_client
        
        items = [
            {"id": "item1", "content": "code 1"},
            {"id": "item2", "content": "code 2"}
        ]
        
        results = analyzer.batch_analyze(items, AnalysisType.CODE_REVIEW)
        
        assert len(results) == 2
        assert results[0]["item_id"] == "item1"
        assert results[1]["item_id"] == "item2"
    
    def test_set_custom_system_prompt(self, analyzer):
        """Test setting custom system prompt"""
        custom_prompt = "You are a specialized code reviewer"
        analyzer.set_custom_system_prompt(AnalysisType.CODE_REVIEW, custom_prompt)
        
        assert analyzer.system_prompts[AnalysisType.CODE_REVIEW] == custom_prompt
    
    def test_build_user_prompt_with_custom_prompt(self, analyzer):
        """Test user prompt building with custom prompt"""
        prompt = analyzer._build_user_prompt(
            content="test content",
            analysis_type=AnalysisType.CODE_REVIEW,
            custom_prompt="Custom instruction",
            context=None
        )
        
        assert "Custom instruction" in prompt
        assert "test content" in prompt
    
    def test_build_user_prompt_with_context(self, analyzer):
        """Test user prompt building with context"""
        context = {"file": "test.py", "lines": 100}
        prompt = analyzer._build_user_prompt(
            content="test content",
            analysis_type=AnalysisType.CODE_REVIEW,
            custom_prompt=None,
            context=context
        )
        
        assert "test.py" in prompt
        assert "test content" in prompt


class TestQuickAnalyze:
    """Test suite for quick_analyze convenience function"""
    
    @patch('llm_analyzer.LLMAnalyzer')
    def test_quick_analyze_success(self, mock_analyzer_class):
        """Test quick analyze function"""
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "success": True,
            "analysis": "Quick analysis result"
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = quick_analyze("test code", "code_review", "gpt-4o-mini")
        
        assert result == "Quick analysis result"
    
    @patch('llm_analyzer.LLMAnalyzer')
    def test_quick_analyze_error(self, mock_analyzer_class):
        """Test quick analyze with error"""
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "success": False,
            "error": "Test error"
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = quick_analyze("test code")
        
        assert "Error" in result
        assert "Test error" in result


class TestAnalysisType:
    """Test AnalysisType enum"""
    
    def test_analysis_types_exist(self):
        """Test that all expected analysis types exist"""
        expected_types = [
            "code_review",
            "commit_summary",
            "project_overview",
            "skill_extraction",
            "documentation_summary",
            "portfolio_generation"
        ]
        
        for expected in expected_types:
            assert any(t.value == expected for t in AnalysisType)
    
    def test_analysis_type_values(self):
        """Test analysis type values are strings"""
        for analysis_type in AnalysisType:
            assert isinstance(analysis_type.value, str)


# Integration tests (require actual API key)
class TestIntegration:
    """Integration tests - only run if API key is available"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY environment variable"
    )
    def test_real_api_call(self):
        """Test actual API call (requires valid API key)"""
        analyzer = LLMAnalyzer(model="gpt-4o-mini", max_tokens=100)
        
        result = analyzer.analyze(
            content="def add(a, b): return a + b",
            analysis_type=AnalysisType.CODE_REVIEW
        )
        
        assert result["success"] is True
        assert len(result["analysis"]) > 0
        assert result["tokens_used"] > 0

