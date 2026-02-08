"""
Success Metrics Analyzer
Generates evidence of success metrics for a given project based on various indicators
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
import re


@dataclass
class SuccessMetrics:
    """Container for success evidence metrics"""
    
    # Overall score (0-100)
    overall_score: float
    
    # Code quality metrics
    code_quality_score: float
    test_coverage_indicator: Optional[float]
    documentation_score: float
    
    # Activity metrics
    activity_score: float
    commit_frequency_score: float
    collaboration_score: float
    
    # Impact metrics
    complexity_score: float
    scale_score: float
    
    # Extracted evidence
    badges: List[Dict[str, str]]
    feedback_items: List[str]
    evaluation_notes: List[str]
    
    # Detailed breakdown
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class SuccessMetricsAnalyzer:
    """Analyzes project data to generate success evidence metrics"""
    
    # Badge patterns to look for in README files
    BADGE_PATTERNS = {
        'build': r'!\[.*build.*\]\(.*\)',
        'coverage': r'!\[.*coverage.*\]\(.*\)',
        'license': r'!\[.*license.*\]\(.*\)',
        'version': r'!\[.*version.*\]\(.*\)',
        'stars': r'!\[.*stars.*\]\(.*\)',
        'downloads': r'!\[.*downloads.*\]\(.*\)',
    }
    
    # Keywords indicating positive feedback
    POSITIVE_FEEDBACK_KEYWORDS = [
        'excellent', 'great', 'outstanding', 'impressive', 'well-done',
        'award', 'winner', 'recognition', 'success', 'achievement',
        'grade: a', 'score: 9', 'score: 10', '100%', 'perfect'
    ]
    
    def analyze(self, project_data: Dict[str, Any]) -> SuccessMetrics:
        """
        Analyze project data and generate success metrics
        
        Args:
            project_data: Complete project analysis data from orchestrator
            
        Returns:
            SuccessMetrics object with computed scores and evidence
        """
        # Extract components
        git_analysis = project_data.get('git_analysis', {})
        code_analysis = project_data.get('analysis_results', {}).get('code', {})
        doc_analysis = project_data.get('analysis_results', {}).get('documentation', {})
        categorized = project_data.get('categorized_contents', {})
        
        # Calculate individual metric scores
        code_quality = self._calculate_code_quality_score(code_analysis)
        test_coverage = self._estimate_test_coverage(categorized, code_analysis)
        documentation = self._calculate_documentation_score(doc_analysis, categorized)
        
        activity = self._calculate_activity_score(git_analysis)
        commit_freq = self._calculate_commit_frequency_score(git_analysis)
        collaboration = self._calculate_collaboration_score(git_analysis)
        
        complexity = self._calculate_complexity_score(code_analysis)
        scale = self._calculate_scale_score(code_analysis, git_analysis)
        
        # Extract evidence
        badges = self._extract_badges(doc_analysis)
        feedback = self._extract_feedback(doc_analysis)
        evaluation = self._extract_evaluation_notes(doc_analysis)
        
        # Calculate overall score (weighted average)
        overall = self._calculate_overall_score(
            code_quality, test_coverage or 0, documentation,
            activity, commit_freq, collaboration,
            complexity, scale
        )
        
        # Build detailed breakdown
        details = {
            'code_quality': {
                'score': code_quality,
                'description': self._get_score_description(code_quality)
            },
            'test_coverage': {
                'estimated': test_coverage,
                'description': 'Estimated based on test file presence' if test_coverage else 'No test files detected'
            },
            'documentation': {
                'score': documentation,
                'description': self._get_score_description(documentation)
            },
            'activity': {
                'score': activity,
                'description': self._get_score_description(activity)
            },
            'collaboration': {
                'score': collaboration,
                'description': self._get_collaboration_description(git_analysis)
            },
            'complexity': {
                'score': complexity,
                'description': self._get_complexity_description(code_analysis)
            },
            'scale': {
                'score': scale,
                'description': self._get_scale_description(code_analysis, git_analysis)
            }
        }
        
        return SuccessMetrics(
            overall_score=overall,
            code_quality_score=code_quality,
            test_coverage_indicator=test_coverage,
            documentation_score=documentation,
            activity_score=activity,
            commit_frequency_score=commit_freq,
            collaboration_score=collaboration,
            complexity_score=complexity,
            scale_score=scale,
            badges=badges,
            feedback_items=feedback,
            evaluation_notes=evaluation,
            details=details
        )
    
    def _calculate_code_quality_score(self, code_analysis: Dict[str, Any]) -> float:
        """Calculate code quality score based on code metrics"""
        if not code_analysis or 'error' in code_analysis:
            return 0.0
        
        metrics = code_analysis.get('metrics', {})
        score = 50.0  # Base score
        
        # Bonus for multiple languages (shows versatility)
        languages = metrics.get('languages', [])
        if len(languages) > 1:
            score += min(len(languages) * 5, 20)
        
        # Bonus for framework usage (shows modern practices)
        frameworks = metrics.get('frameworks', [])
        if frameworks:
            score += min(len(frameworks) * 5, 15)
        
        # Bonus for advanced skills
        skill_data = code_analysis.get('skill_analysis', {})
        if skill_data:
            advanced_skills = skill_data.get('aggregate', {}).get('advanced_skills', [])
            score += min(len(advanced_skills) * 2, 15)
        
        return min(score, 100.0)
    
    def _estimate_test_coverage(self, categorized: Dict[str, Any], code_analysis: Dict[str, Any]) -> Optional[float]:
        """Estimate test coverage based on test file presence"""
        if not categorized or 'error' in categorized:
            return None
        
        code_files = categorized.get('code', [])
        if not code_files:
            return None
        
        # Count test files
        test_files = [f for f in code_files if self._is_test_file(f)]
        
        if not test_files:
            return 0.0
        
        # Estimate coverage: ratio of test files to total code files (capped at 100%)
        ratio = len(test_files) / len(code_files)
        estimated_coverage = min(ratio * 100, 100.0)
        
        return round(estimated_coverage, 2)
    
    def _is_test_file(self, filepath: str) -> bool:
        """Check if a file is a test file"""
        filename = Path(filepath).name.lower()
        return any([
            filename.startswith('test_'),
            filename.endswith('_test.py'),
            filename.endswith('.test.js'),
            filename.endswith('.spec.js'),
            filename.endswith('.test.ts'),
            filename.endswith('.spec.ts'),
            'test' in filename and 'tests' in filepath.lower()
        ])
    
    def _calculate_documentation_score(self, doc_analysis: Dict[str, Any], categorized: Dict[str, Any]) -> float:
        """Calculate documentation quality score"""
        if not doc_analysis or 'error' in doc_analysis:
            return 0.0
        
        score = 0.0
        
        # Check for README
        doc_files = categorized.get('documentation', []) if categorized else []
        has_readme = any('readme' in Path(f).name.lower() for f in doc_files)
        if has_readme:
            score += 30.0
        
        # Score based on documentation quantity
        totals = doc_analysis.get('totals', {})
        total_words = totals.get('total_words', 0)
        
        if total_words > 5000:
            score += 40.0
        elif total_words > 2000:
            score += 30.0
        elif total_words > 500:
            score += 20.0
        elif total_words > 100:
            score += 10.0
        
        # Bonus for multiple documentation files
        total_files = totals.get('total_files', 0)
        if total_files > 3:
            score += 20.0
        elif total_files > 1:
            score += 10.0
        
        return min(score, 100.0)
    
    def _calculate_activity_score(self, git_analysis: Dict[str, Any]) -> float:
        """Calculate activity/engagement score based on git history"""
        if not git_analysis or 'error' in git_analysis:
            return 0.0
        
        total_commits = git_analysis.get('total_commits', 0)
        
        if total_commits == 0:
            return 0.0
        
        # Score based on commit count
        if total_commits > 100:
            return 100.0
        elif total_commits > 50:
            return 85.0
        elif total_commits > 20:
            return 70.0
        elif total_commits > 10:
            return 55.0
        elif total_commits > 5:
            return 40.0
        else:
            return 25.0
    
    def _calculate_commit_frequency_score(self, git_analysis: Dict[str, Any]) -> float:
        """Calculate commit frequency score"""
        if not git_analysis or 'error' in git_analysis:
            return 0.0
        
        # Check for duration information
        duration_days = git_analysis.get('duration_days', 0)
        total_commits = git_analysis.get('total_commits', 0)
        
        if duration_days == 0 or total_commits == 0:
            return 0.0
        
        # Calculate commits per week
        commits_per_week = (total_commits / duration_days) * 7
        
        if commits_per_week > 10:
            return 100.0
        elif commits_per_week > 5:
            return 85.0
        elif commits_per_week > 2:
            return 70.0
        elif commits_per_week > 1:
            return 55.0
        else:
            return 40.0
    
    def _calculate_collaboration_score(self, git_analysis: Dict[str, Any]) -> float:
        """Calculate collaboration score based on contributors"""
        if not git_analysis or 'error' in git_analysis:
            return 0.0
        
        total_contributors = git_analysis.get('total_contributors', 0)
        
        if total_contributors == 0:
            return 0.0
        elif total_contributors == 1:
            return 30.0  # Solo project
        elif total_contributors == 2:
            return 60.0
        elif total_contributors <= 4:
            return 80.0
        else:
            return 100.0  # Large team
    
    def _calculate_complexity_score(self, code_analysis: Dict[str, Any]) -> float:
        """Calculate complexity score based on code metrics"""
        if not code_analysis or 'error' in code_analysis:
            return 0.0
        
        metrics = code_analysis.get('metrics', {})
        total_lines = metrics.get('total_lines', 0)
        
        if total_lines == 0:
            return 0.0
        
        # Score based on lines of code (indicator of complexity)
        if total_lines > 10000:
            return 100.0
        elif total_lines > 5000:
            return 85.0
        elif total_lines > 2000:
            return 70.0
        elif total_lines > 1000:
            return 55.0
        elif total_lines > 500:
            return 40.0
        else:
            return 25.0
    
    def _calculate_scale_score(self, code_analysis: Dict[str, Any], git_analysis: Dict[str, Any]) -> float:
        """Calculate project scale score"""
        score = 0.0
        
        # Code metrics contribution
        if code_analysis and 'error' not in code_analysis:
            metrics = code_analysis.get('metrics', {})
            total_files = metrics.get('total_files', 0)
            
            if total_files > 50:
                score += 50.0
            elif total_files > 20:
                score += 40.0
            elif total_files > 10:
                score += 30.0
            else:
                score += 20.0
        
        # Git metrics contribution
        if git_analysis and 'error' not in git_analysis:
            total_commits = git_analysis.get('total_commits', 0)
            
            if total_commits > 100:
                score += 50.0
            elif total_commits > 50:
                score += 40.0
            elif total_commits > 20:
                score += 30.0
            else:
                score += 20.0
        
        return min(score, 100.0)
    
    def _extract_badges(self, doc_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract badges from documentation"""
        badges = []
        
        if not doc_analysis or 'error' in doc_analysis:
            return badges
        
        # Look through documentation files for badge patterns
        files = doc_analysis.get('files', [])
        for file_data in files:
            content = file_data.get('full_text', '')
            if not content:
                continue
            
            for badge_type, pattern in self.BADGE_PATTERNS.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    badges.append({
                        'type': badge_type,
                        'markdown': match,
                        'source_file': file_data.get('file_name', 'unknown')
                    })
        
        return badges
    
    def _extract_feedback(self, doc_analysis: Dict[str, Any]) -> List[str]:
        """Extract feedback indicators from documentation"""
        feedback_items = []
        
        if not doc_analysis or 'error' in doc_analysis:
            return feedback_items
        
        files = doc_analysis.get('files', [])
        for file_data in files:
            content = file_data.get('full_text', '').lower()
            if not content:
                continue
            
            # Look for positive feedback keywords
            for keyword in self.POSITIVE_FEEDBACK_KEYWORDS:
                if keyword in content:
                    # Extract the sentence containing the keyword
                    sentences = content.split('.')
                    for sentence in sentences:
                        if keyword in sentence:
                            feedback_items.append(sentence.strip())
                            break
        
        return feedback_items[:10]  # Limit to 10 items
    
    def _extract_evaluation_notes(self, doc_analysis: Dict[str, Any]) -> List[str]:
        """Extract evaluation/assessment notes from documentation"""
        evaluation_notes = []
        
        if not doc_analysis or 'error' in doc_analysis:
            return evaluation_notes
        
        files = doc_analysis.get('files', [])
        for file_data in files:
            filename = file_data.get('file_name', '').lower()
            
            # Look for files that might contain evaluations
            if any(keyword in filename for keyword in ['feedback', 'review', 'evaluation', 'grade', 'assessment']):
                content = file_data.get('full_text', '')
                if content:
                    # Add a note about this file
                    evaluation_notes.append(f"Found evaluation document: {file_data.get('file_name', 'unknown')}")
                    
                    # Extract first few lines as sample
                    lines = content.split('\n')[:5]
                    sample = '\n'.join(lines).strip()
                    if sample:
                        evaluation_notes.append(f"Sample: {sample[:200]}...")
        
        return evaluation_notes[:5]  # Limit to 5 notes
    
    def _calculate_overall_score(self, code_quality: float, test_coverage: float,
                                  documentation: float, activity: float, commit_freq: float,
                                  collaboration: float, complexity: float, scale: float) -> float:
        """Calculate weighted overall success score"""
        # Weighted components
        weights = {
            'code_quality': 0.20,
            'test_coverage': 0.10,
            'documentation': 0.15,
            'activity': 0.15,
            'commit_freq': 0.10,
            'collaboration': 0.10,
            'complexity': 0.10,
            'scale': 0.10
        }
        
        overall = (
            code_quality * weights['code_quality'] +
            test_coverage * weights['test_coverage'] +
            documentation * weights['documentation'] +
            activity * weights['activity'] +
            commit_freq * weights['commit_freq'] +
            collaboration * weights['collaboration'] +
            complexity * weights['complexity'] +
            scale * weights['scale']
        )
        
        return round(overall, 2)
    
    def _get_score_description(self, score: float) -> str:
        """Get textual description of a score"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Very Good"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def _get_collaboration_description(self, git_analysis: Dict[str, Any]) -> str:
        """Get collaboration description"""
        if not git_analysis or 'error' in git_analysis:
            return "No Git history available"
        
        contributors = git_analysis.get('total_contributors', 0)
        if contributors == 0:
            return "No contributors found"
        elif contributors == 1:
            return "Solo project"
        else:
            return f"Collaborative project with {contributors} contributors"
    
    def _get_complexity_description(self, code_analysis: Dict[str, Any]) -> str:
        """Get complexity description"""
        if not code_analysis or 'error' in code_analysis:
            return "No code analysis available"
        
        metrics = code_analysis.get('metrics', {})
        total_lines = metrics.get('total_lines', 0)
        
        if total_lines > 10000:
            return f"Large codebase ({total_lines:,} lines)"
        elif total_lines > 2000:
            return f"Medium-sized codebase ({total_lines:,} lines)"
        else:
            return f"Small codebase ({total_lines:,} lines)"
    
    def _get_scale_description(self, code_analysis: Dict[str, Any], git_analysis: Dict[str, Any]) -> str:
        """Get scale description"""
        parts = []
        
        if code_analysis and 'error' not in code_analysis:
            metrics = code_analysis.get('metrics', {})
            total_files = metrics.get('total_files', 0)
            parts.append(f"{total_files} files")
        
        if git_analysis and 'error' not in git_analysis:
            total_commits = git_analysis.get('total_commits', 0)
            parts.append(f"{total_commits} commits")
        
        if parts:
            return ", ".join(parts)
        else:
            return "Scale information unavailable"
