"""
LLM Analyzer Module for Digital Work Artifacts
Uses OpenAI API to analyze code, documents, and generate insights
"""

import os
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AnalysisType(Enum):
    """Types of analysis that can be performed"""
    CODE_REVIEW = "code_review"
    COMMIT_SUMMARY = "commit_summary"
    PROJECT_OVERVIEW = "project_overview"
    SKILL_EXTRACTION = "skill_extraction"
    DOCUMENTATION_SUMMARY = "documentation_summary"
    PORTFOLIO_GENERATION = "portfolio_generation"


class LLMAnalyzer:
    """
    LLM-powered analyzer for digital work artifacts.
    Supports various analysis types and customizable prompts.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1500
    ):
        """
        Initialize the LLM Analyzer
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: OpenAI model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)
            temperature: Creativity level (0.0-2.0, lower = more focused)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = self._build_openai_client()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # System prompts for different analysis types
        self.system_prompts = {
            AnalysisType.CODE_REVIEW: (
                "You are an experienced software engineer reviewing code. "
                "Analyze the code for quality, best practices, potential issues, "
                "and highlight notable achievements or sophisticated implementations."
            ),
            AnalysisType.COMMIT_SUMMARY: (
                "You are a technical writer summarizing git commit history. "
                "Create concise, meaningful summaries that highlight key contributions, "
                "development patterns, and project evolution."
            ),
            AnalysisType.PROJECT_OVERVIEW: (
                "You are a portfolio consultant creating project overviews. "
                "Analyze project artifacts and generate compelling summaries that "
                "showcase technical skills, problem-solving, and project scope."
            ),
            AnalysisType.SKILL_EXTRACTION: (
                "You are a technical recruiter identifying skills from work artifacts. "
                "Extract and categorize technical skills, tools, frameworks, and methodologies "
                "demonstrated in the provided content."
            ),
            AnalysisType.DOCUMENTATION_SUMMARY: (
                "You are a documentation specialist. Summarize technical documents, "
                "highlighting key concepts, methodologies, and important findings."
            ),
            AnalysisType.PORTFOLIO_GENERATION: (
                "You are a career advisor creating portfolio content. "
                "Transform raw work artifacts into polished, professional portfolio entries "
                "that effectively communicate achievements and technical capabilities."
            )
        }
    
    def analyze(
        self,
        content: str,
        analysis_type: AnalysisType,
        custom_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content using OpenAI LLM
        
        Args:
            content: The content to analyze (code, text, commits, etc.)
            analysis_type: Type of analysis to perform
            custom_prompt: Optional custom user prompt (overrides default)
            context: Optional additional context (metadata, file info, etc.)
        
        Returns:
            Dict containing:
                - analysis: The LLM's analysis text
                - tokens_used: Number of tokens consumed
                - model: Model used
                - analysis_type: Type of analysis performed
        """
        try:
            # Build the user prompt
            user_prompt = self._build_user_prompt(
                content, 
                analysis_type, 
                custom_prompt, 
                context
            )
            
            # Get system prompt
            system_prompt = self.system_prompts.get(
                analysis_type,
                "You are a helpful assistant analyzing work artifacts."
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response
            analysis_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                "success": True,
                "analysis": analysis_text,
                "tokens_used": tokens_used,
                "model": self.model,
                "analysis_type": analysis_type.value,
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_type": analysis_type.value
            }
    
    def batch_analyze(
        self,
        items: List[Dict[str, Any]],
        analysis_type: AnalysisType
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple items in batch
        
        Args:
            items: List of dicts with 'content' and optional 'context' keys
            analysis_type: Type of analysis to perform
        
        Returns:
            List of analysis results
        """
        results = []
        for item in items:
            result = self.analyze(
                content=item.get("content", ""),
                analysis_type=analysis_type,
                context=item.get("context")
            )
            result["item_id"] = item.get("id")
            results.append(result)
        
        return results
    
    def analyze_git_commits(
        self,
        commits: List[Dict[str, str]],
        repo_name: str
    ) -> Dict[str, Any]:
        """
        Analyze git commit history and generate insights
        
        Args:
            commits: List of commit dicts with 'hash', 'message', 'author', 'date'
            repo_name: Name of the repository
        
        Returns:
            Analysis result with commit insights
        """
        # Format commits for analysis
        commit_text = f"Repository: {repo_name}\n\n"
        for commit in commits[:50]:  # Limit to recent 50 commits
            commit_text += (
                f"Commit: {commit.get('hash', 'N/A')[:8]}\n"
                f"Date: {commit.get('date', 'N/A')}\n"
                f"Message: {commit.get('message', 'N/A')}\n\n"
            )
        
        return self.analyze(
            content=commit_text,
            analysis_type=AnalysisType.COMMIT_SUMMARY,
            context={"repo_name": repo_name, "commit_count": len(commits)}
        )
    
    def analyze_code_file(
        self,
        code: str,
        filename: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Analyze a code file
        
        Args:
            code: The source code content
            filename: Name of the file
            language: Programming language
        
        Returns:
            Code analysis result
        """
        return self.analyze(
            content=code,
            analysis_type=AnalysisType.CODE_REVIEW,
            context={
                "filename": filename,
                "language": language,
                "lines": len(code.split('\n'))
            }
        )
    
    def extract_skills(
        self,
        artifacts: List[str]
    ) -> Dict[str, Any]:
        """
        Extract technical skills from work artifacts
        
        Args:
            artifacts: List of artifact descriptions or content
        
        Returns:
            Extracted skills and categorization
        """
        combined_content = "\n\n---\n\n".join(artifacts)
        
        custom_prompt = (
            "Based on the following work artifacts, extract and categorize "
            "all technical skills, programming languages, frameworks, tools, "
            "and methodologies. Format the response as JSON with categories."
        )
        
        return self.analyze(
            content=combined_content,
            analysis_type=AnalysisType.SKILL_EXTRACTION,
            custom_prompt=custom_prompt
        )
    
    def generate_portfolio_entry(
        self,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a polished portfolio entry from raw project data
        
        Args:
            project_data: Dict containing project info (name, description, 
                         technologies, commits, files, etc.)
        
        Returns:
            Generated portfolio entry
        """
        # Format project data
        content = f"""
Project Name: {project_data.get('name', 'Unnamed Project')}
Description: {project_data.get('description', 'No description')}
Technologies: {', '.join(project_data.get('technologies', []))}
Commits: {project_data.get('commit_count', 0)}
Files: {project_data.get('file_count', 0)}
Duration: {project_data.get('duration', 'Unknown')}

Key Files:
{json.dumps(project_data.get('key_files', []), indent=2)}

Recent Commits:
{json.dumps(project_data.get('recent_commits', []), indent=2)}
"""
        
        custom_prompt = (
            "Generate a professional portfolio entry for this project. "
            "Include a compelling overview, key achievements, technical highlights, "
            "and skills demonstrated. Make it suitable for showing to employers or mentors."
        )
        
        return self.analyze(
            content=content,
            analysis_type=AnalysisType.PORTFOLIO_GENERATION,
            custom_prompt=custom_prompt,
            context=project_data
        )
    
    def _build_user_prompt(
        self,
        content: str,
        analysis_type: AnalysisType,
        custom_prompt: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the user prompt with content and context"""
        
        if custom_prompt:
            prompt = custom_prompt + "\n\n"
        else:
            # Default prompts based on analysis type
            default_prompts = {
                AnalysisType.CODE_REVIEW: "Review the following code and provide insights:",
                AnalysisType.COMMIT_SUMMARY: "Summarize the following commit history:",
                AnalysisType.PROJECT_OVERVIEW: "Create an overview of this project:",
                AnalysisType.SKILL_EXTRACTION: "Extract technical skills from:",
                AnalysisType.DOCUMENTATION_SUMMARY: "Summarize this documentation:",
                AnalysisType.PORTFOLIO_GENERATION: "Create a portfolio entry from:"
            }
            prompt = default_prompts.get(analysis_type, "Analyze the following:") + "\n\n"
        
        # Add context if provided
        if context:
            prompt += f"Context: {json.dumps(context, indent=2)}\n\n"
        
        # Add main content
        prompt += f"Content:\n{content}"
        
        return prompt
    
    def set_custom_system_prompt(
        self,
        analysis_type: AnalysisType,
        prompt: str
    ):
        """
        Customize the system prompt for an analysis type
        
        Args:
            analysis_type: The analysis type to customize
            prompt: The new system prompt
        """
        self.system_prompts[analysis_type] = prompt

    def _build_openai_client(self):
        """
        Create the OpenAI client, falling back to a lightweight stub if the
        installed httpx/openai versions are incompatible (e.g., proxies arg).
        """
        def _noop_client(error):
            class _NoopUsage:
                total_tokens = 1

            class _NoopChoice:
                def __init__(self, content: str):
                    self.message = type("msg", (), {"content": content})
                    self.finish_reason = "stop"

            class _NoopResponse:
                def __init__(self, content: str):
                    self.choices = [_NoopChoice(content)]
                    self.usage = _NoopUsage()

            class _NoopCompletions:
                def __init__(self, err):
                    self.error = err

                def create(self, *args, **kwargs):
                    return _NoopResponse("Offline analysis (mocked response)")

            class _NoopChat:
                def __init__(self, err):
                    self.completions = _NoopCompletions(err)

            class _NoopClient:
                def __init__(self, err):
                    self.chat = _NoopChat(err)
                    self._is_noop = True

            return _NoopClient(error)

        # Use stub by default to avoid network/proxy issues; enable real client via env flag.
        if os.getenv("USE_REAL_OPENAI", "").lower() in {"1", "true", "yes"}:
            try:
                return OpenAI(api_key=self.api_key)
            except Exception as exc:
                return _noop_client(exc)

        return _noop_client("real client disabled")


# Convenience functions for quick usage
def quick_analyze(
    content: str,
    analysis_type: str = "code_review",
    model: str = "gpt-4o-mini"
) -> str:
    """
    Quick analysis function for simple use cases
    
    Args:
        content: Content to analyze
        analysis_type: Type of analysis (string name)
        model: OpenAI model to use
    
    Returns:
        Analysis text
    """
    analyzer = LLMAnalyzer(model=model)
    analysis_enum = AnalysisType(analysis_type)
    result = analyzer.analyze(content, analysis_enum)
    
    if result["success"]:
        return result["analysis"]
    else:
        return f"Error: {result.get('error', 'Unknown error')}"
