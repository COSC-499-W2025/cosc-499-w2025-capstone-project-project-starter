"""
Test script for document summarization.
This script demonstrates how to use the summarization service.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pytest

# Load environment variables from .env file
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.summarization_service import SummarizationService


@pytest.mark.skip(reason="Integration helper; requires external API and file path")
def test_summarization(file_path: str = ""):
    """
    Test summarization on a document file.
    
    Args:
        file_path: Path to the document to summarize
    """
    print(f"\n{'='*60}")
    print(f"Testing Summarization")
    print(f"{'='*60}\n")
    
    # Check if file exists
    if not Path(file_path).exists():
        print(f"❌ Error: File not found: {file_path}")
        print("\nPlease provide a valid .docx or .pptx file path.")
        return
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        print("\nPlease set up your .env file with your OpenAI API key.")
        print("See README.md for instructions.")
        return
    
    try:
        # Initialize service
        print("🔧 Initializing summarization service...")
        service = SummarizationService()
        
        # Summarize document
        print(f"📄 Processing file: {Path(file_path).name}")
        print("⏳ Parsing document and generating summary...\n")
        
        result = service.summarize_document(file_path)
        
        # Display results
        print(f"{'='*60}")
        print("RESULTS")
        print(f"{'='*60}\n")
        
        print(f"📁 File: {result['file_name']}")
        print(f"📋 Type: {result['file_type'].upper()}")
        print(f"📊 Status: {result['status'].upper()}")
        
        if result['file_type'] == 'docx':
            print(f"📝 Paragraphs: {result['paragraph_count']}")
            print(f"📊 Tables: {result['table_count']}")
        elif result['file_type'] == 'pptx':
            print(f"🎯 Slides: {result['slide_count']}")
        
        print(f"🔤 Word Count: {result['word_count']}")
        
        if result['status'] == 'success':
            print(f"\n{'─'*60}")
            print("📝 SUMMARY:")
            print(f"{'─'*60}")
            print(result['summary'])
            print(f"{'─'*60}\n")
            
            print("✅ Summarization completed successfully!")
            
        elif result['status'] == 'empty':
            print(f"\n⚠️  Warning: {result['summary']}")
            
        elif result['status'] == 'error':
            print(f"\n❌ Error during summarization: {result['error']}")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run the test."""
    print("\n🤖 Document Summarization Test Tool")
    
    # Check if file path is provided
    if len(sys.argv) < 2:
        print("\nUsage: python test_summarization.py <path_to_document>")
        print("Supported formats: .docx, .pptx")
        print("\nExample:")
        print("  python test_summarization.py test_documents/sample.docx")
        return
    
    file_path = sys.argv[1]
    test_summarization(file_path)


if __name__ == "__main__":
    main()
