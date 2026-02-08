"""
OpenAI Client Module
Provides a clean interface for interacting with OpenAI's API for summarization tasks.
"""
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
import httpx


class OpenAIClient:
    """Client for OpenAI API interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, will read from OPENAI_API_KEY environment variable.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Either pass it to the constructor "
                "or set the OPENAI_API_KEY environment variable."
            )

        self.client = self._build_client()

    def _build_client(self):
        """
        Build the OpenAI client, handling environments where httpx proxies arg
        isn't supported by falling back to a custom http_client.
        """
        try:
            return OpenAI(api_key=self.api_key)
        except TypeError as exc:
            # Handle httpx versions that don't accept the proxies kwarg
            try:
                custom_http = httpx.Client()
                return OpenAI(api_key=self.api_key, http_client=custom_http)
            except Exception:
                raise exc
        except Exception as exc:
            # Bubble other errors so callers can see the cause
            raise exc
    
    def summarize_text(
        self, 
        text: str, 
        max_tokens: int = 500,
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Summarize the given text using OpenAI's API.
        
        Args:
            text: The text to summarize
            max_tokens: Maximum tokens in the summary
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        
        Returns:
            The summarized text
        """
        if not text or not text.strip():
            raise ValueError("Text to summarize cannot be empty")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, accurate summaries of documents. "
                                   "Focus on key points, main ideas, and important details."
                    },
                    {
                        "role": "user",
                        "content": f"Please provide a concise summary of the following text:\n\n{text}"
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content
            return summary.strip()
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate summary: {str(e)}")
