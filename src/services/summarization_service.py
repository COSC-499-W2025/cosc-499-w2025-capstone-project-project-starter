"""
Summarization Service
Combines document parsing with OpenAI summarization.
"""
from typing import Dict, Any
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from llm.openai_client import OpenAIClient
from parsers.document_parser import DocumentParser

# Load environment variables (e.g., OPENAI_API_KEY from .env)
load_dotenv()


class SummarizationService:
    """Service for summarizing documents using OpenAI."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the summarization service.
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        self.openai_client = OpenAIClient(api_key=api_key)
        self.parser = DocumentParser()
    
    def summarize_document(
        self, 
        file_path: str, 
        max_summary_tokens: int = 500,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Parse and summarize a document.
        
        Args:
            file_path: Path to the document file (.docx or .pptx)
            max_summary_tokens: Maximum tokens for the summary
            model: OpenAI model to use
            
        Returns:
            Dictionary containing the original metadata, extracted text, and summary
        """
        # Parse the document
        parsed_data = self.parser.parse_file(file_path)
        
        # Check if there's text to summarize
        if not parsed_data["text"] or not parsed_data["text"].strip():
            return {
                **parsed_data,
                "summary": "No content to summarize.",
                "status": "empty"
            }
        
        # Summarize the text
        try:
            summary = self.openai_client.summarize_text(
                text=parsed_data["text"],
                max_tokens=max_summary_tokens,
                model=model
            )
            
            return {
                **parsed_data,
                "summary": summary,
                "status": "success"
            }
            
        except Exception as e:
            return {
                **parsed_data,
                "summary": None,
                "status": "error",
                "error": str(e)
            }
