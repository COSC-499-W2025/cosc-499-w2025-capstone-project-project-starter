import tempfile
from pathlib import Path
from code_analyzer import CodeAnalyzer


def example_basic_usage():
    """Basic usage example"""
    print("=== Local Code Analyzer Example ===\n")
    
    # Create sample code
    sample_code = '''
import fastapi
from sqlalchemy import Column, Integer, String

app = fastapi.FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_path = f.name
    
    try:
        analyzer = CodeAnalyzer()
        
        result = analyzer.analyze_file(temp_path)
        
        print(f"File: {Path(result.file_path).name}")
        print(f"Language: {result.language}")
        print(f"Frameworks: {result.frameworks}")
        print(f"Skills: {result.skills}")
        print(f"Lines of Code: {result.lines_of_code}")
        print(f"File Type: {result.file_type}")
        
    finally:
        Path(temp_path).unlink()


def example_directory_analysis():
    print("\n=== Directory Analysis ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        app_file = Path(temp_dir) / "app.py"
        test_file = Path(temp_dir) / "test_app.py"
        
        app_file.write_text('''
import fastapi
app = fastapi.FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
''')
        
        test_file.write_text('''
import pytest
from app import app

def test_read_root():
    response = app.get("/")
    assert response.status_code == 200
''')
        
        analyzer = CodeAnalyzer()
        results = analyzer.analyze_directory(temp_dir)
        
        print(f"Found {len(results)} files:")
        for result in results:
            print(f"\n  {Path(result.file_path).name}:")
            print(f"    Language: {result.language}")
            print(f"    Frameworks: {result.frameworks}")
            print(f"    Skills: {result.skills}")
            print(f"    Lines: {result.lines_of_code}")
            print(f"    Type: {result.file_type}")
        
        metrics = analyzer.calculate_contribution_metrics(results)
        
        print(f"\n=== Project Metrics ===")
        print(f"Total Files: {metrics.total_files}")
        print(f"Total Lines: {metrics.total_lines}")
        print(f"Languages: {metrics.languages}")
        print(f"Frameworks: {metrics.frameworks}")
        print(f"Skills: {metrics.skills}")
        print(f"Code Files: {metrics.code_files}")
        print(f"Test Files: {metrics.test_files}")


if __name__ == "__main__":
    try:
        example_basic_usage()
        example_directory_analysis()
        print("\n[SUCCESS] All examples completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Make sure you have the required dependencies installed.")