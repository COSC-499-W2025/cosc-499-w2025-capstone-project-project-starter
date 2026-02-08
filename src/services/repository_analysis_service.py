"""
Repository Analysis Service
Comprehensive service for analyzing Git repositories with AI-powered summarization.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzers.git_analyzer import GitAnalyzer
from analyzers.contributor_analyzer import ContributorAnalyzer
from analyzers.code_quality_analyzer import CodeQualityAnalyzer
from parsers.document_parser import DocumentParser
from llm.openai_client import OpenAIClient
from utils.zip_handler import ZipHandler


class RepositoryAnalysisService:
    """Service for comprehensive repository analysis."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize repository analysis service.
        
        Args:
            api_key: Optional OpenAI API key for AI summarization
        """
        self.openai_client = OpenAIClient(api_key=api_key) if api_key else None
        self.parser = DocumentParser()
        self.zip_handler = ZipHandler()
    
    def analyze_repository(
        self,
        repo_path: str,
        analyze_code_quality: bool = True,
        generate_ai_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Perform comprehensive repository analysis.
        
        Args:
            repo_path: Path to Git repository
            analyze_code_quality: Whether to analyze code quality
            generate_ai_summary: Whether to generate AI-powered summaries
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        print(f"\n{'='*70}")
        print("🔍 Repository Analysis")
        print(f"{'='*70}\n")
        
        repo_path = Path(repo_path)
        
        # Git analysis
        git_analyzer = GitAnalyzer(str(repo_path))
        repo_data = git_analyzer.analyze_repository()
        
        # Enhance with contributor skills
        print("\n🎯 Analyzing contributor skills...")
        for contributor in repo_data['contributors']:
            skills = ContributorAnalyzer.analyze_contributor_skills(
                contributor,
                str(repo_path)
            )
            contributor['skills'] = skills
            
            # Add quality score
            quality_score = ContributorAnalyzer.calculate_contributor_score(contributor)
            contributor['quality_metrics'] = quality_score
        
        # Code quality analysis
        quality_metrics = None
        if analyze_code_quality:
            print("\n📊 Analyzing code quality...")
            quality_metrics = self._analyze_repository_code_quality(repo_path)
        
        # Generate AI summary
        ai_insights = None
        code_summary = None
        if generate_ai_summary and self.openai_client:
            print("\n🤖 Generating AI-powered insights...")
            ai_insights = self._generate_ai_insights(repo_data)
            
            # Generate codebase summary
            print("📝 Analyzing codebase with AI...")
            code_summary = self._analyze_codebase_batch(str(repo_path))
        
        result = {
            "repository_analysis": repo_data,
            "code_quality": quality_metrics,
            "ai_insights": ai_insights,
            "code_summary": code_summary,
            "analysis_complete": True
        }
        
        print("\n✅ Analysis complete!")
        return result
    
    def analyze_zip_file(
        self,
        zip_path: str,
        analyze_code_quality: bool = True,
        generate_ai_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Extract and analyze a zip file (may contain repository or documents).
        
        Args:
            zip_path: Path to zip file
            analyze_code_quality: Whether to analyze code quality
            generate_ai_summary: Whether to generate AI summaries
            
        Returns:
            Dictionary with analysis results
        """
        print(f"\n{'='*70}")
        print("📦 Zip File Analysis")
        print(f"{'='*70}\n")
        
        # Extract zip
        extracted_dir = self.zip_handler.extract_zip(zip_path)
        
        # PRIORITY 1: Check if it contains a Git repository (analyze .git first)
        git_repos = self.zip_handler.find_git_repositories(extracted_dir)
        
        results = {
            "zip_file": str(zip_path),
            "extracted_to": extracted_dir,
            "contains_git_repos": len(git_repos) > 0,
            "git_repositories": [],
            "documents": [],
            "code_summary": None,
            "summary": {}
        }
        
        # Analyze Git repositories FIRST
        if git_repos:
            print(f"\n✅ Found {len(git_repos)} Git repositor{'y' if len(git_repos) == 1 else 'ies'}")
            for repo_path in git_repos:
                print(f"\n📂 Analyzing repository: {Path(repo_path).name}")
                try:
                    repo_analysis = self.analyze_repository(
                        repo_path,
                        analyze_code_quality=analyze_code_quality,
                        generate_ai_summary=generate_ai_summary
                    )
                    results["git_repositories"].append(repo_analysis)
                    
                    # Analyze code files in batch if AI is enabled
                    if generate_ai_summary and self.openai_client:
                        print("\n📝 Analyzing codebase with AI...")
                        code_summary = self._analyze_codebase_batch(repo_path)
                        results["code_summary"] = code_summary
                        
                except Exception as e:
                    print(f"   ⚠️  Error analyzing repository: {e}")
                    results["git_repositories"].append({"error": str(e), "path": repo_path})
        
        # Find and analyze documents (skip hidden files)
        print("\n📄 Searching for documents...")
        supported_extensions = self.parser.get_supported_formats()
        documents = self.zip_handler.find_files_in_extracted(
            extracted_dir,
            extensions=supported_extensions,
            skip_hidden=True  # Skip hidden files like ._files
        )
        
        if documents:
            print(f"   Found {len(documents)} document(s)")
            results["documents"] = self._analyze_documents(
                documents,
                generate_ai_summary=generate_ai_summary
            )
        
        # Generate overall summary
        results["summary"] = self._generate_zip_summary(results)
        
        print("\n✅ Zip analysis complete!")
        return results
    
    def _analyze_repository_code_quality(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze code quality for all code files in repository."""
        # Find code files
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php']
        code_files = []
        
        for ext in code_extensions:
            code_files.extend(repo_path.rglob(f'*{ext}'))
        
        # Exclude common directories
        exclude_patterns = ['node_modules', '__pycache__', 'venv', '.git', 'build', 'dist']
        code_files = [
            f for f in code_files
            if not any(pattern in str(f) for pattern in exclude_patterns)
        ]
        
        print(f"   Analyzing {len(code_files[:20])} code files...")  # Limit to 20 for performance
        
        file_metrics = []
        for file_path in code_files[:20]:  # Analyze first 20 files
            try:
                metrics = CodeQualityAnalyzer.analyze_code_file(str(file_path))
                file_metrics.append(metrics)
            except Exception as e:
                print(f"   ⚠️  Error analyzing {file_path.name}: {e}")
        
        # Aggregate metrics
        aggregated = CodeQualityAnalyzer.aggregate_quality_metrics(file_metrics)
        
        return {
            "files_analyzed": len(file_metrics),
            "total_code_files": len(code_files),
            "file_metrics": file_metrics[:5],  # Include top 5 in detail
            "aggregate_metrics": aggregated
        }
    
    def _analyze_documents(
        self,
        document_paths: List[str],
        generate_ai_summary: bool = False
    ) -> List[Dict[str, Any]]:
        """Analyze a list of documents."""
        results = []
        
        # Limit to first 10 documents for performance
        for doc_path in document_paths[:10]:
            try:
                print(f"   📄 Analyzing: {Path(doc_path).name}")
                parsed = self.parser.parse_file(doc_path)
                
                # Generate AI summary if requested
                if generate_ai_summary and self.openai_client and parsed.get('text'):
                    try:
                        summary = self.openai_client.summarize_text(
                            parsed['text'][:5000],  # Limit text length
                            max_tokens=200
                        )
                        parsed['ai_summary'] = summary
                    except Exception as e:
                        parsed['ai_summary_error'] = str(e)
                
                results.append(parsed)
            except Exception as e:
                results.append({
                    "file": doc_path,
                    "error": str(e)
                })
        
        return results
    
    def _analyze_codebase_batch(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze codebase by batching code files together to reduce API calls.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Dictionary with codebase analysis
        """
        if not self.openai_client:
            return {"error": "OpenAI client not initialized"}
        
        repo_path = Path(repo_path)
        
        # Find all code files
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php']
        code_files_by_type = {}
        
        for ext in code_extensions:
            files = list(repo_path.rglob(f'*{ext}'))
            # Exclude common directories
            exclude_patterns = ['node_modules', '__pycache__', 'venv', '.git', 'build', 'dist', 'test']
            files = [f for f in files if not any(pattern in str(f) for pattern in exclude_patterns)]
            if files:
                code_files_by_type[ext] = files[:10]  # Limit to 10 files per type
        
        if not code_files_by_type:
            return {"error": "No code files found"}
        
        # Batch analyze by file type
        print(f"   Batching {sum(len(files) for files in code_files_by_type.values())} code files...")
        
        try:
            # Collect code samples from different files
            code_samples = []
            for ext, files in code_files_by_type.items():
                for file_path in files[:3]:  # Top 3 files per type
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:2000]  # First 2000 chars
                            code_samples.append(f"File: {file_path.name} ({ext})\n{content}\n")
                    except:
                        continue
            
            # Create batch summary prompt
            batch_text = "\n---\n".join(code_samples[:15])  # Max 15 samples
            prompt = f"""Analyze this codebase and provide:
1. What this program/project does
2. Main technologies and frameworks used
3. Key features or functionality
4. Architecture or structure insights

Code samples:
{batch_text}

Provide a concise summary in 2-3 paragraphs."""
            
            # Get AI summary
            codebase_summary = self.openai_client.summarize_text(prompt, max_tokens=500)
            
            return {
                "codebase_summary": codebase_summary,
                "files_analyzed": sum(len(files) for files in code_files_by_type.values()),
                "languages": list(code_files_by_type.keys())
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_ai_insights(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered insights about the repository."""
        if not self.openai_client:
            return {"error": "OpenAI client not initialized"}
        
        # Prepare summary text
        summary_text = self._prepare_repo_summary_text(repo_data)
        
        try:
            # Generate overall repository summary
            repo_summary = self.openai_client.summarize_text(
                summary_text,
                max_tokens=400
            )
            
            # Generate insights for each contributor
            contributor_insights = []
            for contributor in repo_data['contributors'][:5]:  # Top 5 contributors
                contributor_text = self._prepare_contributor_summary_text(contributor)
                try:
                    insight = self.openai_client.summarize_text(
                        contributor_text,
                        max_tokens=200
                    )
                    contributor_insights.append({
                        "contributor": contributor['name'],
                        "insight": insight
                    })
                except Exception as e:
                    contributor_insights.append({
                        "contributor": contributor['name'],
                        "error": str(e)
                    })
            
            return {
                "repository_summary": repo_summary,
                "contributor_insights": contributor_insights
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _prepare_repo_summary_text(self, repo_data: Dict[str, Any]) -> str:
        """Prepare text summary of repository for AI analysis."""
        text = f"""Repository Analysis Summary:

Total Commits: {repo_data['total_commits']}
Contributors: {repo_data['contributor_count']}
Branches: {repo_data['branch_count']}

Top Contributors:
"""
        for contributor in repo_data['contributors'][:5]:
            text += f"- {contributor['name']}: {contributor['commits']} commits ({contributor['percentage']:.1f}%)\n"
            if 'skills' in contributor:
                langs = contributor['skills'].get('primary_languages', [])
                if langs:
                    text += f"  Languages: {', '.join([l['language'] for l in langs[:3]])}\n"
        
        text += f"\nFile Extensions: {', '.join(list(repo_data.get('file_extensions', {}).keys())[:10])}"
        
        return text
    
    def _prepare_contributor_summary_text(self, contributor: Dict[str, Any]) -> str:
        """Prepare text summary of contributor for AI analysis."""
        text = f"""Contributor Analysis: {contributor['name']}

Commits: {contributor['commits']}
Contribution: {contributor['percentage']:.1f}%
Lines Added: {contributor.get('insertions', 0)}
Lines Deleted: {contributor.get('deletions', 0)}
Files Touched: {contributor.get('unique_files_touched', 0)}

"""
        if 'skills' in contributor:
            skills = contributor['skills']
            text += "Primary Languages:\n"
            for lang in skills.get('primary_languages', [])[:3]:
                text += f"- {lang['language']}: {lang['percentage']:.1f}%\n"
            
            frameworks = skills.get('frameworks_and_tools', [])
            if frameworks:
                text += f"\nFrameworks/Tools: {', '.join([f['framework'] for f in frameworks[:5]])}\n"
        
        if 'quality_metrics' in contributor:
            metrics = contributor['quality_metrics']
            text += f"\nActivity Level: {metrics.get('activity_level', 'Unknown')}\n"
            text += f"Avg Lines per Commit: {metrics.get('avg_lines_per_commit', 0):.1f}\n"
        
        return text
    
    def _generate_zip_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of zip file analysis."""
        summary = {
            "total_git_repos": len(results.get('git_repositories', [])),
            "total_documents": len(results.get('documents', [])),
            "has_code": results.get('contains_git_repos', False)
        }
        
        # Aggregate contributor count
        if results.get('git_repositories'):
            total_contributors = sum(
                repo.get('repository_analysis', {}).get('contributor_count', 0)
                for repo in results['git_repositories']
            )
            summary['total_contributors'] = total_contributors
        
        return summary
    
    def cleanup(self):
        """Clean up temporary files."""
        self.zip_handler.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()



