"""
Project Summarizer Module

This module provides functionality to generate comprehensive summaries of uploaded projects,
including language detection, project description, collaboration analysis, and time tracking.
"""

from datetime import datetime
from collections import Counter
from config.db_config import with_db_cursor
from project_manager import get_project_by_id
from parsing.file_contents_manager import get_file_contents_by_upload_id, get_file_statistics
from collaborative.identify_projects import _identify_authors_from_zip, _count_git_files, _compute_collab_score, _extract_common_names_from_filenames, _detect_team_structure
from common.constants import LANGUAGE_EXTENSIONS
from typing import Dict, List, Set, Any

def _collab_level_from_score(score: int) -> str:
    """Map score to high-level label."""
    if score >= 100:
        return "Definitely collaborative"
    if score >= 70:
        return "Likely team project"
    if score >= 40:
        return "Possibly collaborative"
    return "Likely individual project"

def _build_analysis_text(level: str, authors: Set[str]) -> str:
    base = f"Based on file names and/or Git presence, this appears to be a {level.lower()}."
    if authors:
        base += " The likely contributors are: " + ", ".join(sorted(authors))
    return base


class ProjectSummarizer:
    """Main class for generating project summaries."""
    
    def __init__(self):
        self.language_extensions = LANGUAGE_EXTENSIONS
    
    def generate_project_summary(self, project_id):
        """
        Generate a comprehensive summary for a project.
        
        Args:
            project_id (int): The ID of the project to summarize
            
        Returns:
            dict: Complete project summary
        """
        # Get project basic info
        project_info = get_project_by_id(project_id)
        if not project_info:
            return {"error": "Project not found"}
        
        # Get file contents and statistics
        file_contents = get_file_contents_by_upload_id(project_id)
        file_stats = get_file_statistics(project_id)
        
        if not file_contents:
            return {"error": "No file contents found for this project"}
        
        summary = {
            "project_info": {
                "id": project_info['id'],
                "filename": project_info['filename'],
                "created_at": project_info['created_at'].strftime("%Y-%m-%d %H:%M:%S") if project_info['created_at'] else "Unknown"
            },
            "languages": self._detect_languages(file_contents),
            "collaboration_analysis": self._analyze_collaboration(project_id),
            "time_analysis": self._analyze_time_patterns(file_contents),
            "file_statistics": file_stats
        }
        try:
            from analysis.local_analyzer import LocalAnalyzer
            local_analyzer = LocalAnalyzer()
            deep_analysis = local_analyzer.analyze_files_from_db(file_contents)
            if deep_analysis:
                summary["code_analysis"] = deep_analysis
        except Exception as e:
            print(f"Warning: Deep analysis failed: {e}")
            summary["code_analysis"] = {}
        return summary
    
    def _detect_languages(self, file_contents):
        language_counts = Counter()
        for file_info in file_contents:
            ext = file_info.get('file_extension', '').lower()
            if ext in self.language_extensions:
                lang = self.language_extensions[ext]
                language_counts[lang] += 1
        sorted_languages = language_counts.most_common()
        return {
            "primary_language": sorted_languages[0][0] if sorted_languages else "Unknown",
            "languages": [lang for lang, _ in sorted_languages[:5]],
            "total_programming_files": sum(language_counts.values())
        }
    
    def _analyze_collaboration(self, project_id: int) -> Dict[str, Any]:
        """
        Analyze if this was worked on by a single user or with others.

        Returns:
            dict: Collaboration analysis
        """
        file_contents = get_file_contents_by_upload_id(project_id)

        indicators = {
            'git_files': _count_git_files(file_contents),
            'multiple_authors': False,   # (kept for compatibility; not directly used below)
            'team_structure': _detect_team_structure(file_contents),
            'has_common_names': False,
            'collaboration_score': 0
        }

        common_names_found = _extract_common_names_from_filenames(file_contents)
        if common_names_found:
            indicators['has_common_names'] = True

        authors = _identify_authors_from_zip(project_id)
        authors.update(common_names_found)

        score = _compute_collab_score(indicators, authors)
        indicators['collaboration_score'] = score

        level = _collab_level_from_score(score)
        analysis = _build_analysis_text(level, authors)

        return {
            "collaboration_level": level,
            "indicators": indicators,
            "analysis": analysis,
        }

    def _analyze_time_patterns(self, file_contents):
        if not file_contents:
            return {}
        creation_times = [f['created_at'] for f in file_contents if f.get('created_at')]
        if not creation_times:
            return {}
        creation_times.sort()
        time_span = creation_times[-1] - creation_times[0]
        if time_span.days == 0:
            intensity = "Single day"
        elif time_span.days <= 7:
            intensity = "Short-term (≤1 week)"
        elif time_span.days <= 30:
            intensity = "Medium-term (≤1 month)"
        else:
            intensity = "Long-term (>1 month)"
        return {
            "duration_days": time_span.days,
            "intensity": intensity,
            "first_file": creation_times[0].strftime("%Y-%m-%d"),
            "last_file": creation_times[-1].strftime("%Y-%m-%d")
        }
    
    def format_summary_for_display(self, summary):
        """
        Format the summary for nice display in the console.
        
        Args:
            summary (dict): The project summary
            
        Returns:
            str: Formatted summary text
        """
        if "error" in summary:
            return f"Error: {summary['error']}"
        
        output = []
        output.append("=" * 80)
        output.append(f"PROJECT SUMMARY: {summary['project_info']['filename']}")
        output.append("=" * 80)
        output.append(f"   Created: {summary['project_info']['created_at']}")
        
        output.append(f"\nOverview:")
        output.append(f"   Primary Language: {summary['languages']['primary_language']}")
        if summary['languages'].get('languages'):
            other_langs = [l for l in summary['languages']['languages'] if l != summary['languages']['primary_language']]
            if other_langs:
                output.append(f"   Other Languages: {', '.join(other_langs[:3])}")
        output.append(f"   Files: {summary['file_statistics']['total_files']} ({summary['file_statistics']['total_size_bytes'] / (1024*1024):.1f} MB)")
        
        if summary.get('time_analysis'):
            ta = summary['time_analysis']
            output.append(f"   Duration: {ta.get('duration_days', 0)} days ({ta.get('intensity', 'Unknown')})")
        
        collab = summary.get('collaboration_analysis', {})
        if collab:
            output.append(f"   Collaboration: {collab.get('collaboration_level', 'Unknown')}")
        
        if 'code_analysis' in summary and summary['code_analysis']:
            output.append(f"\n{'='*80}")
            output.append("CODE ANALYSIS & TECHNICAL INSIGHTS")
            output.append("="*80)
            deep = summary['code_analysis']
            oop = deep.get('oop_principles_summary', {})
            if any(oop.get(k, {}).get('count', 0) > 0 for k in ['abstraction', 'encapsulation', 'polymorphism', 'inheritance']):
                output.append(f"\nObject-Oriented Programming Principles:")
                for principle in ['abstraction', 'encapsulation', 'polymorphism', 'inheritance']:
                    principle_data = oop.get(principle, {})
                    count = principle_data.get('count', 0)
                    if count > 0:
                        output.append(f"   {principle.title()}: {count} instance(s)")
                        examples = principle_data.get('examples', [])[:1]
                        if examples:
                            evidence = examples[0].get('evidence', '')
                            if evidence:
                                output.append(f"      → {evidence}")
            ds = deep.get('data_structure_summary', {})
            if ds:
                output.append(f"\nData Structure Usage & Performance:")
                for struct_name, count in sorted(ds.items(), key=lambda x: -x[1])[:5]:
                    struct_display = struct_name.replace('_', ' ').title()
                    output.append(f"   {struct_display}: {count} usage(s)")
                    perf_notes = {
                        'hash_map': 'O(1) average lookup - efficient for key-value operations',
                        'set': 'O(1) membership test - optimal for unique collections',
                        'list': 'O(n) search, O(1) append - good for sequential access',
                        'tree': 'O(log n) search - balanced for hierarchical data',
                        'array': 'O(1) access, O(n) search - fast random access'
                    }
                    if struct_name in perf_notes:
                        output.append(f"      → {perf_notes[struct_name]}")
            complexity = deep.get('complexity_summary', {})
            if complexity:
                output.append(f"\nAlgorithm Complexity Awareness:")
                nested = complexity.get('nested_loops', 0)
                recursive = complexity.get('recursive_functions', 0)
                awareness = complexity.get('complexity_awareness', False)
                if nested > 0:
                    output.append(f"   Nested Loops: {nested} instance(s) - potential O(n²) or higher")
                if recursive > 0:
                    output.append(f"   Recursive Functions: {recursive} - demonstrates recursive thinking")
                if awareness:
                    output.append(f"   Complexity Annotations: Present - shows awareness of Big-O notation")
            optimizations = deep.get('optimization_summary', [])
            if optimizations:
                output.append(f"\nOptimization Evidence:")
                unique_opt_types = {}
                for opt in optimizations[:5]:
                    opt_type = opt.get('type', 'Unknown')
                    if opt_type not in unique_opt_types:
                        unique_opt_types[opt_type] = opt.get('evidence', '')
                        skill = opt.get('skill_indicator', '')
                        output.append(f"   {opt_type}: {opt.get('evidence', '')}")
                        if skill:
                            output.append(f"      → {skill}")
            quality = deep.get('code_quality_summary', {})
            if quality:
                score = quality.get('average_quality_score', 0)
                strengths = quality.get('strengths', [])
                output.append(f"\nCode Quality Assessment:")
                output.append(f"   Overall Quality Score: {score:.1f}/100")
                if strengths:
                    output.append(f"   Strengths:")
                    for strength in strengths[:5]:
                        output.append(f"      • {strength}")
        
        output.append("=" * 80)
        
        return "\n".join(output)


def summarize_project(project_id):
    """
    Convenience function to generate and display a project summary.
    
    Args:
        project_id (int): The ID of the project to summarize
        
    Returns:
        str: Formatted summary text
    """
    summarizer = ProjectSummarizer()
    summary = summarizer.generate_project_summary(project_id)
    return summarizer.format_summary_for_display(summary)


def get_available_projects():
    """
    Get a list of available projects for summarization.
    
    Returns:
        list: List of project information
    """
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, created_at
                FROM uploaded_files
                ORDER BY filename ASC
            """)
            
            projects = cursor.fetchall()
        return [{"id": row[0], "filename": row[1], "created_at": row[2]} for row in projects]
        
    except ConnectionError:
        print("Could not connect to database.")
        return []
    except Exception as e:
        print(f"Error retrieving projects: {e}")
        return []
