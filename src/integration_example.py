"""
Integration Example: How to use LLM Analyzer with the artifact mining system

This demonstrates how the LLM analyzer integrates with the overall
digital work artifact mining architecture.
"""

import os
from typing import List, Dict, Any
from llm_analyzer import LLMAnalyzer, AnalysisType


class ArtifactAnalysisPipeline:
    """
    Example pipeline showing how LLM analysis integrates with artifact mining.
    
    This would work with:
    - R2: Type Detection (Misha)
    - R3: Git Adapter (Abijeet)
    - R4: Office/PDF Adapter (Abhinav)
    - R6: Storage Layer (Abdur)
    - R7: Analytics (Tahsin)
    """
    
    def __init__(self):
        self.llm_analyzer = LLMAnalyzer(model="gpt-4o-mini")
        self.analysis_cache = {}  # Simple cache to avoid re-analyzing
    
    def process_git_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Example: Process a Git repository
        Integrates with R3 (Git Adapter) + LLM Analysis
        """
        print(f"\n📁 Processing repository: {repo_path}")
        
        # Step 1: Git Adapter extracts data (R3 - Abijeet's work)
        # This is mock data - real implementation would use GitPython
        repo_data = {
            "name": os.path.basename(repo_path),
            "commits": [
                {
                    "hash": "abc123def",
                    "message": "Implement LLM integration for artifact analysis",
                    "author": "Team 14",
                    "date": "2024-10-20",
                    "files_changed": 3,
                    "insertions": 150,
                    "deletions": 20
                },
                {
                    "hash": "def456ghi",
                    "message": "Add privacy redaction policies",
                    "author": "Team 14",
                    "date": "2024-10-19",
                    "files_changed": 2,
                    "insertions": 80,
                    "deletions": 5
                }
            ],
            "languages": ["Python", "TypeScript"],
            "total_commits": 127,
            "contributors": 6
        }
        
        # Step 2: LLM Analysis
        print("🤖 Analyzing commit history with LLM...")
        commit_analysis = self.llm_analyzer.analyze_git_commits(
            commits=repo_data["commits"],
            repo_name=repo_data["name"]
        )
        
        # Step 3: Combine data
        result = {
            "repo_name": repo_data["name"],
            "basic_stats": {
                "total_commits": repo_data["total_commits"],
                "contributors": repo_data["contributors"],
                "languages": repo_data["languages"]
            },
            "llm_insights": commit_analysis["analysis"] if commit_analysis["success"] else None,
            "tokens_used": commit_analysis.get("tokens_used", 0)
        }
        
        print(f"✅ Analysis complete! Tokens used: {result['tokens_used']}")
        return result
    
    def process_code_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Example: Process a code file
        Integrates with R2 (Type Detection) + LLM Analysis
        """
        print(f"\n📄 Processing code file: {file_path}")
        
        # Step 1: Type detection (R2 - Misha's work)
        # Real implementation would use magic numbers, etc.
        language = self._detect_language(file_path)
        
        # Step 2: Check cache to avoid re-analysis
        content_hash = hash(content)
        cache_key = f"{file_path}:{content_hash}"
        
        if cache_key in self.analysis_cache:
            print("📦 Retrieved from cache")
            return self.analysis_cache[cache_key]
        
        # Step 3: LLM Analysis
        print(f"🤖 Analyzing {language} code with LLM...")
        code_analysis = self.llm_analyzer.analyze_code_file(
            code=content,
            filename=os.path.basename(file_path),
            language=language
        )
        
        # Step 4: Build result
        result = {
            "file_path": file_path,
            "language": language,
            "lines": len(content.split('\n')),
            "llm_review": code_analysis["analysis"] if code_analysis["success"] else None,
            "tokens_used": code_analysis.get("tokens_used", 0)
        }
        
        # Step 5: Cache result
        self.analysis_cache[cache_key] = result
        
        print(f"✅ Analysis complete! Tokens used: {result['tokens_used']}")
        return result
    
    def generate_project_portfolio(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Example: Generate portfolio summary from all artifacts
        Integrates with R7 (Analytics) + R10 (Export)
        """
        print("\n📊 Generating portfolio summary...")
        
        # Step 1: Aggregate artifact data (R7 - Tahsin's work)
        project_summary = {
            "name": "Digital Work Artifact Miner",
            "description": "Privacy-first portfolio generation tool",
            "technologies": self._extract_technologies(artifacts),
            "commit_count": sum(a.get("commits", 0) for a in artifacts),
            "file_count": len(artifacts),
            "duration": "3 months",
            "key_files": [a.get("name") for a in artifacts[:5]],
            "recent_commits": [
                a.get("recent_activity", "N/A") 
                for a in artifacts[:3]
            ]
        }
        
        # Step 2: LLM Portfolio Generation
        print("🤖 Generating professional portfolio entry...")
        portfolio_result = self.llm_analyzer.generate_portfolio_entry(project_summary)
        
        # Step 3: Build final portfolio
        result = {
            "project_data": project_summary,
            "portfolio_entry": portfolio_result["analysis"] if portfolio_result["success"] else None,
            "tokens_used": portfolio_result.get("tokens_used", 0),
            "ready_for_export": True  # Can now be exported (R10)
        }
        
        print(f"✅ Portfolio generated! Tokens used: {result['tokens_used']}")
        return result
    
    def extract_skills_from_artifacts(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Example: Extract technical skills from artifacts
        Useful for R10 (Export) - resume building
        """
        print("\n🎯 Extracting skills from artifacts...")
        
        # Step 1: Prepare artifact descriptions
        descriptions = []
        for artifact in artifacts:
            desc = f"{artifact.get('type', 'unknown')}: {artifact.get('description', 'N/A')}"
            descriptions.append(desc)
        
        # Step 2: LLM Skill Extraction
        print("🤖 Using LLM to identify skills...")
        skill_result = self.llm_analyzer.extract_skills(descriptions)
        
        result = {
            "skills": skill_result["analysis"] if skill_result["success"] else None,
            "artifact_count": len(artifacts),
            "tokens_used": skill_result.get("tokens_used", 0)
        }
        
        print(f"✅ Skills extracted! Tokens used: {result['tokens_used']}")
        return result
    
    def _detect_language(self, file_path: str) -> str:
        """Simple language detection by extension"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.go': 'Go',
            '.rs': 'Rust'
        }
        ext = os.path.splitext(file_path)[1]
        return ext_map.get(ext, 'Unknown')
    
    def _extract_technologies(self, artifacts: List[Dict[str, Any]]) -> List[str]:
        """Extract unique technologies from artifacts"""
        techs = set()
        for artifact in artifacts:
            if 'technologies' in artifact:
                techs.update(artifact['technologies'])
            if 'language' in artifact:
                techs.add(artifact['language'])
        return sorted(list(techs))


def demo_full_pipeline():
    """
    Demonstrate the complete integration workflow
    """
    print("=" * 70)
    print("🚀 ARTIFACT ANALYSIS PIPELINE DEMO")
    print("=" * 70)
    
    pipeline = ArtifactAnalysisPipeline()
    
    # Example 1: Process Git Repository
    repo_result = pipeline.process_git_repository(
        "/path/to/capstone-project-team-14"
    )
    print("\n📋 Repository Insights:")
    print(f"  - Total Commits: {repo_result['basic_stats']['total_commits']}")
    print(f"  - Contributors: {repo_result['basic_stats']['contributors']}")
    print(f"  - Languages: {', '.join(repo_result['basic_stats']['languages'])}")
    print(f"\n💡 LLM Insights:\n{repo_result['llm_insights'][:200]}...")
    
    # Example 2: Process Code File
    sample_code = """
class ArtifactScanner:
    def __init__(self, config):
        self.config = config
        self.artifacts = []
    
    def scan_directory(self, path):
        '''Scan directory for artifacts'''
        for root, dirs, files in os.walk(path):
            for file in files:
                artifact = self.process_file(os.path.join(root, file))
                if artifact:
                    self.artifacts.append(artifact)
        return self.artifacts
"""
    
    code_result = pipeline.process_code_file(
        "src/scanner.py",
        sample_code
    )
    print(f"\n📋 Code Analysis:")
    print(f"  - Language: {code_result['language']}")
    print(f"  - Lines: {code_result['lines']}")
    print(f"\n💡 LLM Review:\n{code_result['llm_review'][:200]}...")
    
    # Example 3: Generate Portfolio
    mock_artifacts = [
        {
            "name": "llm_analyzer.py",
            "type": "code",
            "technologies": ["Python", "OpenAI API"],
            "description": "LLM integration module",
            "commits": 15
        },
        {
            "name": "git_adapter.py",
            "type": "code",
            "technologies": ["Python", "GitPython"],
            "description": "Git repository analysis",
            "commits": 20
        },
        {
            "name": "api/endpoints.py",
            "type": "code",
            "technologies": ["Python", "FastAPI"],
            "description": "REST API endpoints",
            "commits": 25
        }
    ]
    
    portfolio_result = pipeline.generate_project_portfolio(mock_artifacts)
    print(f"\n📋 Portfolio Entry:")
    print(f"{portfolio_result['portfolio_entry'][:300]}...")
    
    # Example 4: Extract Skills
    skills_result = pipeline.extract_skills_from_artifacts(mock_artifacts)
    print(f"\n📋 Extracted Skills:")
    print(f"{skills_result['skills'][:200]}...")
    
    # Summary
    total_tokens = (
        repo_result['tokens_used'] +
        code_result['tokens_used'] +
        portfolio_result['tokens_used'] +
        skills_result['tokens_used']
    )
    
    print("\n" + "=" * 70)
    print("📊 PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Total tokens used: {total_tokens}")
    print(f"Estimated cost: ${total_tokens * 0.0000015:.4f} (gpt-4o-mini)")
    print(f"Artifacts processed: {len(mock_artifacts) + 1}")  # +1 for repo
    print("=" * 70)


def demo_batch_processing():
    """
    Demonstrate batch processing of multiple files
    """
    print("\n" + "=" * 70)
    print("🔄 BATCH PROCESSING DEMO")
    print("=" * 70)
    
    analyzer = LLMAnalyzer(model="gpt-4o-mini")
    
    # Simulate multiple code files
    code_files = [
        {
            "id": "utils.py",
            "content": "def parse_date(s): return datetime.strptime(s, '%Y-%m-%d')",
            "context": {"filename": "utils.py", "language": "Python"}
        },
        {
            "id": "models.py",
            "content": "class Artifact:\n    def __init__(self, path):\n        self.path = path",
            "context": {"filename": "models.py", "language": "Python"}
        },
        {
            "id": "config.py",
            "content": "CONFIG = {'db': 'sqlite:///app.db', 'debug': True}",
            "context": {"filename": "config.py", "language": "Python"}
        }
    ]
    
    print(f"\n🔄 Analyzing {len(code_files)} files in batch...")
    results = analyzer.batch_analyze(code_files, AnalysisType.CODE_REVIEW)
    
    for result in results:
        print(f"\n📄 {result['item_id']}:")
        if result['success']:
            print(f"  ✅ {result['analysis'][:100]}...")
            print(f"  📊 Tokens: {result['tokens_used']}")
        else:
            print(f"  ❌ Error: {result['error']}")
    
    total_tokens = sum(r.get('tokens_used', 0) for r in results if r['success'])
    print(f"\n📊 Batch Summary:")
    print(f"  - Files processed: {len(results)}")
    print(f"  - Total tokens: {total_tokens}")
    print(f"  - Avg tokens/file: {total_tokens // len(results)}")
    print(f"  - Cost: ${total_tokens * 0.0000015:.4f}")


if __name__ == "__main__":
    try:
        # Run full pipeline demo
        demo_full_pipeline()
        
        # Run batch processing demo
        demo_batch_processing()
        
        print("\n✨ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("  1. Set OPENAI_API_KEY in .env file")
        print("  2. Installed dependencies: pip install -r requirements.txt")
        print("  3. Activated your virtual environment")

