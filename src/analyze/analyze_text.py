#!/usr/bin/env python3
"""
Text Analyzer - Main Script
Usage:
  - python src/analyze/analyze_text.py <file1> <file2> ...
  - python -m src.analyze.analyze_text <file1> <file2> ...
"""

import sys
import json
from pathlib import Path

# Robust import whether run as a module or as a script
try:
    from src.analyze.text_analyzer import TextAnalyzer
except ModuleNotFoundError:
    # Add project root (two levels up: src/analyze/ -> src/ -> project_root/)
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.analyze.text_analyzer import TextAnalyzer


def main():
    """Main entry point for text analysis"""
    
    # Check if files were provided
    if len(sys.argv) < 2:
        print("Usage: python analyze_text.py <file1> <file2> ...")
        print("Example: python analyze_text.py document.pdf report.docx notes.txt")
        sys.exit(1)
    
    # Get file paths from command line arguments
    file_paths = sys.argv[1:]
    
    # Validate files exist
    for file_path in file_paths:
        if not Path(file_path).exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
    
    # Create analyzer
    analyzer = TextAnalyzer()
    
    # Analyze files
    if len(file_paths) == 1:
        # Single file analysis
        metrics = analyzer.analyze_file(file_paths[0])
        result = metrics.to_dict()
        print(json.dumps(result, indent=2))
    else:
        # Batch analysis
        results = analyzer.analyze_batch(file_paths)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
