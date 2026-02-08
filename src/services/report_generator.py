"""
Report Generator
Generates formatted reports from analysis results.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json


class ReportGenerator:
    """Generator for creating formatted analysis reports."""
    
    @staticmethod
    def generate_text_report(analysis_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable text report.
        
        Args:
            analysis_results: Analysis results dictionary
            
        Returns:
            Formatted text report
        """
        report = []
        report.append("=" * 80)
        report.append("REPOSITORY ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Check if this is a zip analysis or direct repo analysis
        if 'zip_file' in analysis_results:
            report.extend(ReportGenerator._format_zip_analysis(analysis_results))
        else:
            report.extend(ReportGenerator._format_repository_analysis(analysis_results))
        
        return "\n".join(report)
    
    @staticmethod
    def _format_repository_analysis(results: Dict[str, Any]) -> list:
        """Format repository analysis results."""
        report = []
        
        repo_data = results.get('repository_analysis', {})
        
        # Repository Overview
        report.append("📊 REPOSITORY OVERVIEW")
        report.append("-" * 80)
        report.append(f"Repository Path: {repo_data.get('repository_path', 'N/A')}")
        report.append(f"Remote URL: {repo_data.get('remote_url', 'N/A')}")
        report.append(f"Total Commits: {repo_data.get('total_commits', 0)}")
        report.append(f"Branches: {repo_data.get('branch_count', 0)}")
        report.append(f"Contributors: {repo_data.get('contributor_count', 0)}")
        report.append("")
        
        # File Extensions
        extensions = repo_data.get('file_extensions', {})
        if extensions:
            report.append("📁 FILE TYPES")
            report.append("-" * 80)
            sorted_exts = sorted(extensions.items(), key=lambda x: x[1], reverse=True)
            for ext, count in sorted_exts[:10]:
                report.append(f"  {ext:20} {count:>5} files")
            report.append("")
        
        # Contributors
        contributors = repo_data.get('contributors', [])
        if contributors:
            report.append("👥 CONTRIBUTORS")
            report.append("=" * 80)
            
            for i, contributor in enumerate(contributors, 1):
                report.append(f"\n{i}. {contributor['name']} <{contributor['email']}>")
                report.append("-" * 80)
                report.append(f"   Commits: {contributor['commits']} ({contributor['percentage']:.1f}%)")
                report.append(f"   Lines Added: +{contributor.get('insertions', 0)}")
                report.append(f"   Lines Deleted: -{contributor.get('deletions', 0)}")
                report.append(f"   Files Touched: {contributor.get('unique_files_touched', 0)}")
                
                # Activity period
                if contributor.get('first_commit'):
                    report.append(f"   First Commit: {contributor['first_commit']}")
                    report.append(f"   Last Commit: {contributor['last_commit']}")
                
                # Skills
                if 'skills' in contributor:
                    skills = contributor['skills']
                    
                    report.append("\n   💡 PRIMARY SKILLS:")
                    langs = skills.get('primary_languages', [])
                    for lang in langs[:5]:
                        report.append(f"      • {lang['language']:20} {lang['percentage']:>5.1f}% ({lang['files']} files)")
                    
                    frameworks = skills.get('frameworks_and_tools', [])
                    if frameworks:
                        report.append("\n   🛠️  FRAMEWORKS & TOOLS:")
                        for fw in frameworks[:8]:
                            report.append(f"      • {fw['framework']:25} ({fw['mentions']} mentions)")
                    
                    work_areas = skills.get('work_areas', {})
                    if work_areas:
                        report.append("\n   📋 WORK AREAS:")
                        for area, count in sorted(work_areas.items(), key=lambda x: x[1], reverse=True):
                            report.append(f"      • {area:25} {count:>3} files")
                
                # Quality Metrics
                if 'quality_metrics' in contributor:
                    metrics = contributor['quality_metrics']
                    report.append("\n   📊 QUALITY METRICS:")
                    report.append(f"      Activity Level: {metrics.get('activity_level', 'N/A')}")
                    report.append(f"      Avg Lines/Commit: {metrics.get('avg_lines_per_commit', 0):.1f}")
                    report.append(f"      Files/Commit: {metrics.get('files_per_commit', 0):.1f}")
                    report.append(f"      Code Churn: {metrics.get('code_churn_percentage', 0):.1f}%")
                    
                    indicators = metrics.get('quality_indicators', [])
                    if indicators:
                        report.append("\n   ✨ QUALITY INDICATORS:")
                        for indicator in indicators:
                            report.append(f"      • {indicator}")
            
            report.append("")
        
        # Code Quality
        if 'code_quality' in results and results['code_quality']:
            quality = results['code_quality']
            report.append("📈 CODE QUALITY ANALYSIS")
            report.append("=" * 80)
            
            if 'aggregate_metrics' in quality:
                agg = quality['aggregate_metrics']
                report.append(f"Files Analyzed: {quality.get('files_analyzed', 0)} of {quality.get('total_code_files', 0)}")
                report.append(f"Total Code Lines: {agg.get('total_code_lines', 0):,}")
                report.append(f"Total Comment Lines: {agg.get('total_comment_lines', 0):,}")
                report.append(f"Average Comment Ratio: {agg.get('average_comment_ratio', 0):.1f}%")
                report.append(f"\nQuality Score: {agg.get('quality_score', 0)}/100")
                report.append(f"Quality Rating: {agg.get('quality_rating', 'N/A')}")
                
                smells = agg.get('code_smells_found', {})
                if smells:
                    report.append("\n⚠️  Code Issues Found:")
                    for smell, count in sorted(smells.items(), key=lambda x: x[1], reverse=True):
                        report.append(f"   • {smell} ({count} occurrences)")
            
            report.append("")
        
        # Codebase Summary
        code_summary = results.get('code_summary')
        if code_summary and not code_summary.get('error'):
            report.append("=" * 80)
            report.append("📝 CODEBASE ANALYSIS")
            report.append("=" * 80)
            report.append(f"Files Analyzed: {code_summary.get('files_analyzed', 0)}")
            report.append(f"Languages Detected: {', '.join(code_summary.get('languages', []))}")
            report.append("")
            
            if 'codebase_summary' in code_summary:
                report.append("🤖 WHAT THIS PROJECT DOES:")
                report.append("-" * 80)
                report.append(code_summary['codebase_summary'])
                report.append("")
        
        # AI Insights
        if 'ai_insights' in results and results['ai_insights']:
            insights = results['ai_insights']
            
            if 'repository_summary' in insights:
                report.append("🤖 AI-POWERED REPOSITORY INSIGHTS")
                report.append("=" * 80)
                report.append(insights['repository_summary'])
                report.append("")
            
            if 'contributor_insights' in insights:
                report.append("👥 CONTRIBUTOR INSIGHTS")
                report.append("-" * 80)
                for insight in insights['contributor_insights']:
                    if 'insight' in insight:
                        report.append(f"\n{insight['contributor']}:")
                        report.append(insight['insight'])
                        report.append("")
        
        return report
    
    @staticmethod
    def _format_zip_analysis(results: Dict[str, Any]) -> list:
        """Format zip file analysis results."""
        report = []
        
        report.append("📦 ZIP FILE ANALYSIS")
        report.append("-" * 80)
        report.append(f"Zip File: {results.get('zip_file', 'N/A')}")
        report.append(f"Extracted To: {results.get('extracted_to', 'N/A')}")
        report.append("")
        
        summary = results.get('summary', {})
        report.append("📊 SUMMARY")
        report.append("-" * 80)
        report.append(f"Git Repositories: {summary.get('total_git_repos', 0)}")
        report.append(f"Documents: {summary.get('total_documents', 0)}")
        if 'total_contributors' in summary:
            report.append(f"Total Contributors: {summary.get('total_contributors', 0)}")
        report.append("")
        
        # Codebase Summary (AI-powered)
        code_summary = results.get('code_summary')
        if code_summary and not code_summary.get('error'):
            report.append("=" * 80)
            report.append("📝 CODEBASE ANALYSIS")
            report.append("=" * 80)
            report.append(f"Files Analyzed: {code_summary.get('files_analyzed', 0)}")
            report.append(f"Languages Detected: {', '.join(code_summary.get('languages', []))}")
            report.append("")
            
            if 'codebase_summary' in code_summary:
                report.append("🤖 AI-POWERED CODEBASE SUMMARY:")
                report.append("-" * 80)
                report.append(code_summary['codebase_summary'])
                report.append("")
        
        # Repository analyses
        git_repos = results.get('git_repositories', [])
        if git_repos:
            report.append("=" * 80)
            report.append("GIT REPOSITORIES")
            report.append("=" * 80)
            
            for i, repo_analysis in enumerate(git_repos, 1):
                if 'error' in repo_analysis:
                    report.append(f"\n{i}. Error: {repo_analysis['error']}")
                else:
                    report.append(f"\n{'='*80}")
                    report.append(f"REPOSITORY {i}")
                    report.append(f"{'='*80}")
                    report.extend(ReportGenerator._format_repository_analysis(repo_analysis))
        
        # Document analyses
        documents = results.get('documents', [])
        if documents:
            report.append("\n" + "=" * 80)
            report.append("DOCUMENTS FOUND")
            report.append("=" * 80)
            
            for i, doc in enumerate(documents, 1):
                report.append(f"\n{i}. {doc.get('file_name', 'Unknown')}")
                report.append(f"   Type: {doc.get('file_type', 'Unknown')}")
                report.append(f"   Word Count: {doc.get('word_count', 0)}")
                
                if 'ai_summary' in doc:
                    report.append(f"\n   Summary:")
                    report.append(f"   {doc['ai_summary']}")
        
        return report
    
    @staticmethod
    def generate_json_report(analysis_results: Dict[str, Any]) -> str:
        """
        Generate a JSON report.
        
        Args:
            analysis_results: Analysis results dictionary
            
        Returns:
            JSON formatted report
        """
        return json.dumps(analysis_results, indent=2, default=str)
    
    @staticmethod
    def save_report(
        report_content: str,
        output_path: str,
        format: str = 'txt'
    ) -> str:
        """
        Save report to file.
        
        Args:
            report_content: Report content string
            output_path: Path to save the report
            format: Report format ('txt' or 'json')
            
        Returns:
            Path to saved report
        """
        from pathlib import Path
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(output_path)



