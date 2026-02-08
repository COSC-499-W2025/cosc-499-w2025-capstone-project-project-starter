"""
Contributor Analyzer
Analyzes contributor skills, expertise, and code patterns from their contributions.
"""
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import defaultdict
import re


class ContributorAnalyzer:
    """Analyzer for detecting contributor skills and expertise."""
    
    # Language and skill mappings
    LANGUAGE_MAP = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React/JSX',
        '.tsx': 'React/TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Headers',
        '.hpp': 'C++ Headers',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.m': 'Objective-C',
        '.r': 'R',
        '.sql': 'SQL',
        '.sh': 'Shell/Bash',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.less': 'LESS',
        '.xml': 'XML',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.md': 'Markdown/Documentation',
        '.rst': 'reStructuredText',
        '.tex': 'LaTeX',
        '.dockerfile': 'Docker',
        '.proto': 'Protocol Buffers',
        '.graphql': 'GraphQL'
    }
    
    # Framework/technology patterns (in file paths or names)
    FRAMEWORK_PATTERNS = {
        'React': ['react', 'jsx', 'tsx', 'components'],
        'Angular': ['angular', '@angular', 'ng-'],
        'Vue': ['vue', '.vue'],
        'Django': ['django', 'models.py', 'views.py', 'urls.py'],
        'Flask': ['flask', 'app.py', 'blueprints'],
        'FastAPI': ['fastapi', 'routers', 'schemas'],
        'Spring': ['spring', 'springframework'],
        'Node.js': ['node_modules', 'package.json', 'express'],
        'Docker': ['Dockerfile', 'docker-compose'],
        'Kubernetes': ['k8s', 'kubernetes', '.yaml'],
        'TensorFlow': ['tensorflow', 'tf.'],
        'PyTorch': ['pytorch', 'torch'],
        'SQL': ['.sql', 'database', 'migrations'],
        'MongoDB': ['mongodb', 'mongoose'],
        'Redis': ['redis'],
        'GraphQL': ['.graphql', 'apollo', 'resolvers'],
        'REST API': ['api', 'endpoints', 'routes'],
        'Testing': ['test_', '_test', 'spec.', 'tests/'],
        'CI/CD': ['.github/workflows', '.gitlab-ci', 'jenkins'],
        'AWS': ['aws', 's3', 'lambda', 'ec2'],
        'Azure': ['azure'],
        'GCP': ['gcp', 'google-cloud']
    }
    
    @staticmethod
    def analyze_contributor_skills(
        contributor_data: Dict[str, Any],
        repo_path: str = None
    ) -> Dict[str, Any]:
        """
        Analyze a contributor's skills based on their file contributions.
        
        Args:
            contributor_data: Dictionary with contributor stats (must have 'files_touched')
            repo_path: Optional path to repository for additional analysis
            
        Returns:
            Dictionary with skill analysis
        """
        files_touched = contributor_data.get('files_touched', [])
        
        # Detect languages
        language_count = defaultdict(int)
        for file in files_touched:
            ext = Path(file).suffix.lower()
            if ext in ContributorAnalyzer.LANGUAGE_MAP:
                language = ContributorAnalyzer.LANGUAGE_MAP[ext]
                language_count[language] += 1
        
        # Detect frameworks and technologies
        framework_count = defaultdict(int)
        for file in files_touched:
            file_lower = file.lower()
            for framework, patterns in ContributorAnalyzer.FRAMEWORK_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in file_lower:
                        framework_count[framework] += 1
                        break
        
        # Categorize work areas
        work_areas = ContributorAnalyzer._categorize_work_areas(files_touched)
        
        # Calculate primary skills (top languages)
        total_files = len(files_touched)
        primary_languages = []
        if language_count:
            sorted_langs = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
            for lang, count in sorted_langs[:5]:  # Top 5
                percentage = (count / total_files * 100) if total_files > 0 else 0
                primary_languages.append({
                    "language": lang,
                    "files": count,
                    "percentage": round(percentage, 1)
                })
        
        # Calculate framework expertise
        frameworks = []
        if framework_count:
            sorted_frameworks = sorted(framework_count.items(), key=lambda x: x[1], reverse=True)
            for framework, count in sorted_frameworks[:10]:  # Top 10
                frameworks.append({
                    "framework": framework,
                    "mentions": count
                })
        
        return {
            "primary_languages": primary_languages,
            "frameworks_and_tools": frameworks,
            "work_areas": work_areas,
            "total_files_touched": total_files,
            "language_diversity": len(language_count),
            "framework_diversity": len(framework_count)
        }
    
    @staticmethod
    def _categorize_work_areas(files: List[str]) -> Dict[str, int]:
        """Categorize files into work areas."""
        areas = defaultdict(int)
        
        for file in files:
            file_lower = file.lower()
            
            # Backend
            if any(x in file_lower for x in ['api', 'backend', 'server', 'models', 'database', 'controllers']):
                areas['Backend'] += 1
            
            # Frontend
            if any(x in file_lower for x in ['frontend', 'ui', 'components', 'views', 'pages', 'styles']):
                areas['Frontend'] += 1
            
            # Testing
            if any(x in file_lower for x in ['test', 'spec', '__tests__']):
                areas['Testing'] += 1
            
            # Documentation
            if any(x in file_lower for x in ['.md', '.rst', 'docs/', 'readme', 'documentation']):
                areas['Documentation'] += 1
            
            # DevOps/Infrastructure
            if any(x in file_lower for x in ['docker', 'ci', 'cd', 'deploy', 'infra', 'k8s', 'terraform']):
                areas['DevOps/Infrastructure'] += 1
            
            # Database
            if any(x in file_lower for x in ['.sql', 'migration', 'schema', 'database']):
                areas['Database'] += 1
            
            # Configuration
            if any(x in file_lower for x in ['config', '.json', '.yaml', '.yml', '.toml', '.ini']):
                areas['Configuration'] += 1
        
        return dict(areas)
    
    @staticmethod
    def calculate_contributor_score(contributor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate an overall contribution score and quality metrics.
        
        Args:
            contributor_data: Dictionary with contributor stats
            
        Returns:
            Dictionary with scoring metrics
        """
        commits = contributor_data.get('commits', 0)
        insertions = contributor_data.get('insertions', 0)
        deletions = contributor_data.get('deletions', 0)
        unique_files = contributor_data.get('unique_files_touched', 0)
        
        # Calculate metrics
        net_additions = insertions - deletions
        avg_lines_per_commit = (insertions + deletions) / commits if commits > 0 else 0
        files_per_commit = unique_files / commits if commits > 0 else 0
        
        # Code churn (deletions / insertions ratio)
        code_churn = (deletions / insertions * 100) if insertions > 0 else 0
        
        # Quality indicators
        quality_indicators = []
        
        if avg_lines_per_commit < 200:
            quality_indicators.append("Small, focused commits")
        elif avg_lines_per_commit > 500:
            quality_indicators.append("Large commits (consider breaking down)")
        
        if code_churn < 30:
            quality_indicators.append("Low code churn (stable code)")
        elif code_churn > 70:
            quality_indicators.append("High code churn (frequent rewrites)")
        
        if files_per_commit < 3:
            quality_indicators.append("Focused changes")
        elif files_per_commit > 10:
            quality_indicators.append("Wide-ranging changes")
        
        # Activity level
        if commits < 10:
            activity_level = "Low"
        elif commits < 50:
            activity_level = "Medium"
        elif commits < 200:
            activity_level = "High"
        else:
            activity_level = "Very High"
        
        return {
            "activity_level": activity_level,
            "total_commits": commits,
            "net_additions": net_additions,
            "avg_lines_per_commit": round(avg_lines_per_commit, 1),
            "files_per_commit": round(files_per_commit, 1),
            "code_churn_percentage": round(code_churn, 1),
            "quality_indicators": quality_indicators
        }



