"""
INPUTS:
- File paths (str or Path): Individual files or directories to analyze
- Project root (optional Path): Root directory for project-level framework detection
- File content (str): Automatically read from file paths

OUTPUTS:
- AnalysisResult: Dataclass containing:
    * file_path (str): Path to analyzed file
    * language (str): Detected programming language
    * frameworks (List[str]): Detected frameworks
    * skills (List[str]): Extracted technical skills
    * lines_of_code (int): Non-comment, non-blank lines
    * file_type (str): 'code', 'test', or 'documentation'

- ContributionMetrics: Aggregated metrics containing:
    * total_files (int): Number of files analyzed
    * total_lines (int): Total lines of code
    * languages (List[str]): All detected languages
    * frameworks (List[str]): All detected frameworks
    * skills (List[str]): All extracted skills
    * code_files (int): Count of code files
    * test_files (int): Count of test files

USAGE:
    from pathlib import Path
    from code_analyzer import CodeAnalyzer
    
    # Initialize analyzer (optional: provide project root for manifest parsing)
    analyzer = CodeAnalyzer(project_root=Path('/path/to/project'))
    
    # Analyze a single file
    result = analyzer.analyze_file('src/main.py')
    print(f"Language: {result.language}")
    print(f"Frameworks: {result.frameworks}")
    print(f"Skills: {result.skills}")
    
    # Analyze entire directory
    results = analyzer.analyze_directory('/path/to/project')
    
    # Calculate aggregated metrics
    metrics = analyzer.calculate_contribution_metrics(results)
    print(f"Total files: {metrics.total_files}")
    print(f"Languages used: {metrics.languages}")
    print(f"Frameworks: {metrics.frameworks}")
    
    # Convert to dictionary for JSON serialization
    metrics_dict = metrics.to_dict()
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

from .lang_frameworks import (
    detect_language_by_ext_and_shebang,
    detect_frameworks_from_source,
    detect_frameworks_from_manifests,
    merge_file_and_project_frameworks
)


@dataclass
class AnalysisResult:
    file_path: str
    language: str
    frameworks: List[str]
    skills: List[str]
    lines_of_code: int
    file_type: str
    
    def to_dict(self) -> Dict:
        return {
            'file_path': self.file_path,
            'language': self.language,
            'frameworks': self.frameworks,
            'skills': self.skills,
            'lines_of_code': self.lines_of_code,
            'file_type': self.file_type
        }


@dataclass
class ContributionMetrics:
    total_files: int
    total_lines: int
    languages: List[str]
    frameworks: List[str]
    skills: List[str]
    code_files: int
    test_files: int
    
    def to_dict(self) -> Dict:
        return {
            'total_files': self.total_files,
            'total_lines': self.total_lines,
            'languages': self.languages,
            'frameworks': self.frameworks,
            'skills': self.skills,
            'code_files': self.code_files,
            'test_files': self.test_files
        }


class CodeAnalyzer:
    
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """
        Initialize the CodeAnalyzer.
        
        Args:
            project_root: Optional path to project root for manifest-based framework detection.
                         If None, only source-based detection will be used.
        """
        self.project_root = Path(project_root) if project_root else None
        self._project_frameworks = None  # Cached project frameworks
        
        # Legacy framework patterns - kept for backward compatibility
        self.frameworks = {
            'python': ['fastapi', 'django', 'flask', 'sqlalchemy', 'pytest', 'pandas', 'numpy'],
            'javascript': ['react', 'vue', 'angular', 'express', 'jest', 'node'],
            'java': ['spring', 'hibernate', 'junit', 'maven'],
            'cpp': ['boost', 'qt', 'opencv']
        }
    
    def _get_project_frameworks(self) -> set:
        """Get project-level frameworks, cached after first call."""
        if self._project_frameworks is None:
            if self.project_root:
                self._project_frameworks = detect_frameworks_from_manifests(self.project_root)
            else:
                self._project_frameworks = set()
        return self._project_frameworks
    
    def detect_language(self, content: str, filename: str) -> str:
        """Detect programming language - delegates to lang_frameworks module."""
        language = detect_language_by_ext_and_shebang(filename, content)
        
        # Map newer language names to legacy names for backward compatibility
        if language == 'typescript':
            return 'javascript'  # Treat TypeScript as JavaScript for compatibility
        
        return language
    
    def detect_frameworks(self, content: str, language: str) -> List[str]:
        """Detect frameworks - delegates to lang_frameworks module and merges with project frameworks."""
        # Get frameworks from source code
        file_frameworks = detect_frameworks_from_source(language, content)
        
        # Get project-level frameworks
        project_frameworks = self._get_project_frameworks()
        
        # Merge both sources
        return merge_file_and_project_frameworks(file_frameworks, project_frameworks)
    
    def extract_skills(self, content: str, language: str) -> List[str]:
        skills = [language] if language != 'unknown' else []
        
        frameworks = self.detect_frameworks(content, language)
        skills.extend(frameworks)
        
        content_lower = content.lower()
        if language == 'python':
            if 'class ' in content:
                skills.append('object-oriented-programming')
            if 'async def' in content:
                skills.append('asynchronous-programming')
        elif language == 'javascript':
            if '=>' in content:
                skills.append('arrow-functions')
            if 'useState' in content or 'useEffect' in content:
                skills.append('react-hooks')
        
        return list(set(skills))  
    
    def detect_file_type(self, content: str, filename: str) -> str:
        filename_lower = filename.lower()
        
        if (filename_lower.startswith('test_') or 
            filename_lower.endswith('_test.py') or
            'test' in filename_lower and 'def test_' in content.lower()):
            return 'test'
        
        if (filename_lower.endswith('.md') or 
            filename_lower.endswith('.txt') or
            filename_lower in ['readme', 'changelog']):
            return 'documentation'
        
        return 'code'
    
    def analyze_file(self, file_path: Union[str, Path]) -> AnalysisResult:
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')
        
        language = self.detect_language(content, file_path.name)
        frameworks = self.detect_frameworks(content, language)
        skills = self.extract_skills(content, language)
        file_type = self.detect_file_type(content, file_path.name)
        
        lines = [line for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')]
        lines_of_code = len(lines)
        
        return AnalysisResult(
            file_path=str(file_path),
            language=language,
            frameworks=frameworks,
            skills=skills,
            lines_of_code=lines_of_code,
            file_type=file_type
        )
    
    def analyze_directory(self, directory_path: Union[str, Path]) -> List[AnalysisResult]:
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")
        
        results = []
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.cc', '.c', '.h'}
        
        for file_path in directory_path.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in code_extensions and
                not self._should_skip_file(file_path)):
                
                try:
                    result = self.analyze_file(file_path)
                    results.append(result)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
                    continue
        
        return results
    
    def _should_skip_file(self, file_path: Path) -> bool:
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'build', 'dist'}
        return any(part in skip_dirs for part in file_path.parts)
    
    def calculate_contribution_metrics(self, results: List[AnalysisResult]) -> ContributionMetrics:
        if not results:
            return ContributionMetrics(0, 0, [], [], [], 0, 0)
        
        total_files = len(results)
        total_lines = sum(r.lines_of_code for r in results)
        
        languages = list(set(r.language for r in results if r.language != 'unknown'))
        frameworks = list(set(fw for r in results for fw in r.frameworks))
        skills = list(set(skill for r in results for skill in r.skills))
        
        code_files = sum(1 for r in results if r.file_type == 'code')
        test_files = sum(1 for r in results if r.file_type == 'test')
        
        return ContributionMetrics(
            total_files=total_files,
            total_lines=total_lines,
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            skills=sorted(skills),
            code_files=code_files,
            test_files=test_files
        )