"""
Example usage of the LLM Analyzer module
Demonstrates various analysis capabilities
"""

from llm_analyzer import LLMAnalyzer, AnalysisType, quick_analyze


def example_code_review():
    """Example: Analyze a code snippet"""
    print("\n=== Example 1: Code Review ===\n")
    
    code_sample = """
def calculate_portfolio_metrics(artifacts):
    '''Calculate comprehensive portfolio metrics'''
    total_commits = sum(a.get('commits', 0) for a in artifacts)
    languages = set()
    
    for artifact in artifacts:
        if 'language' in artifact:
            languages.add(artifact['language'])
    
    return {
        'total_commits': total_commits,
        'languages': list(languages),
        'project_count': len(artifacts)
    }
"""
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    result = analyzer.analyze_code_file(
        code=code_sample,
        filename="metrics.py",
        language="Python"
    )
    
    if result["success"]:
        print(f"Analysis:\n{result['analysis']}")
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")


def example_commit_analysis():
    """Example: Analyze git commit history"""
    print("\n=== Example 2: Commit History Analysis ===\n")
    
    commits = [
        {
            "hash": "abc123def456",
            "message": "Implement file type detection with magic numbers",
            "author": "Misha Gavura",
            "date": "2024-10-15"
        },
        {
            "hash": "def456ghi789",
            "message": "Add Git adapter for repository analysis",
            "author": "Abijeet Dhillon",
            "date": "2024-10-16"
        },
        {
            "hash": "ghi789jkl012",
            "message": "Create REST API endpoints for artifacts",
            "author": "Abhinav Malik",
            "date": "2024-10-17"
        },
        {
            "hash": "jkl012mno345",
            "message": "Implement privacy redaction policies",
            "author": "Abdur Rehman",
            "date": "2024-10-18"
        }
    ]
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini", temperature=0.5)
    result = analyzer.analyze_git_commits(
        commits=commits,
        repo_name="capstone-project-team-14"
    )
    
    if result["success"]:
        print(f"Commit Analysis:\n{result['analysis']}")
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")


def example_skill_extraction():
    """Example: Extract skills from project artifacts"""
    print("\n=== Example 3: Skill Extraction ===\n")
    
    artifacts = [
        "Built a FastAPI REST service with async endpoints and dependency injection",
        "Implemented Git repository analysis using GitPython and pydriller libraries",
        "Created database schema with SQLAlchemy ORM and Alembic migrations",
        "Developed React frontend with TypeScript and Material-UI components",
        "Set up CI/CD pipeline with GitHub Actions and Docker containers"
    ]
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    result = analyzer.extract_skills(artifacts)
    
    if result["success"]:
        print(f"Extracted Skills:\n{result['analysis']}")
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")


def example_portfolio_generation():
    """Example: Generate portfolio entry from project data"""
    print("\n=== Example 4: Portfolio Entry Generation ===\n")
    
    project_data = {
        "name": "Digital Work Artifact Miner",
        "description": "Privacy-first application for analyzing and showcasing digital work",
        "technologies": ["Python", "FastAPI", "SQLAlchemy", "GitPython", "React", "TypeScript"],
        "commit_count": 127,
        "file_count": 45,
        "duration": "3 months",
        "key_files": [
            "src/llm_analyzer.py - LLM integration for artifact analysis",
            "src/git_adapter.py - Git repository parsing and metrics",
            "src/api/endpoints.py - REST API implementation"
        ],
        "recent_commits": [
            "Implemented OpenAI integration for intelligent analysis",
            "Added privacy-first scanning with PII redaction",
            "Created comprehensive test suite with 90% coverage"
        ]
    }
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini", temperature=0.7)
    result = analyzer.generate_portfolio_entry(project_data)
    
    if result["success"]:
        print(f"Portfolio Entry:\n{result['analysis']}")
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")


def example_custom_analysis():
    """Example: Custom analysis with custom prompt"""
    print("\n=== Example 5: Custom Analysis ===\n")
    
    content = """
    This project demonstrates full-stack development with:
    - Backend API design and implementation
    - Database schema design and ORM usage
    - Git repository analysis algorithms
    - LLM integration for intelligent insights
    - Privacy-first architecture
    """
    
    custom_prompt = """
    Analyze this project description and:
    1. Identify the technical complexity level
    2. Suggest what role this would be good for (e.g., backend, full-stack)
    3. Rate the innovation level (1-10)
    4. Provide 3 talking points for an interview
    """
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    result = analyzer.analyze(
        content=content,
        analysis_type=AnalysisType.PROJECT_OVERVIEW,
        custom_prompt=custom_prompt
    )
    
    if result["success"]:
        print(f"Custom Analysis:\n{result['analysis']}")
        print(f"\nTokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")


def example_quick_analyze():
    """Example: Quick analysis using convenience function"""
    print("\n=== Example 6: Quick Analysis ===\n")
    
    code = """
def process_artifacts(artifacts, filters):
    filtered = [a for a in artifacts if matches_filters(a, filters)]
    return sorted(filtered, key=lambda x: x['date'], reverse=True)
"""
    
    analysis = quick_analyze(code, analysis_type="code_review")
    print(f"Quick Analysis:\n{analysis}")


def example_batch_analysis():
    """Example: Batch analysis of multiple items"""
    print("\n=== Example 7: Batch Analysis ===\n")
    
    items = [
        {
            "id": "file1",
            "content": "def add(a, b): return a + b",
            "context": {"filename": "math_utils.py"}
        },
        {
            "id": "file2",
            "content": "class User:\n    def __init__(self, name):\n        self.name = name",
            "context": {"filename": "models.py"}
        }
    ]
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    results = analyzer.batch_analyze(items, AnalysisType.CODE_REVIEW)
    
    for result in results:
        print(f"\nFile: {result.get('item_id')}")
        if result["success"]:
            print(f"Analysis: {result['analysis'][:200]}...")
        else:
            print(f"Error: {result['error']}")


def example_custom_system_prompt():
    """Example: Customizing system prompts"""
    print("\n=== Example 8: Custom System Prompt ===\n")
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    
    # Customize the system prompt for code review
    analyzer.set_custom_system_prompt(
        AnalysisType.CODE_REVIEW,
        "You are a senior software architect specializing in Python. "
        "Focus on architectural patterns, scalability, and maintainability. "
        "Be encouraging but thorough in your feedback."
    )
    
    code = """
class ArtifactRepository:
    def __init__(self, db_session):
        self.db = db_session
    
    def get_by_id(self, artifact_id):
        return self.db.query(Artifact).filter_by(id=artifact_id).first()
"""
    
    result = analyzer.analyze_code_file(code, "repository.py", "Python")
    
    if result["success"]:
        print(f"Analysis with Custom Prompt:\n{result['analysis']}")


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Analyzer - Example Usage")
    print("=" * 60)
    
    try:
        # Run all examples
        example_code_review()
        example_commit_analysis()
        example_skill_extraction()
        example_portfolio_generation()
        example_custom_analysis()
        example_quick_analyze()
        example_batch_analysis()
        example_custom_system_prompt()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("\nMake sure you have:")
        print("1. Set OPENAI_API_KEY in your .env file")
        print("2. Installed dependencies: pip install -r requirements.txt")

