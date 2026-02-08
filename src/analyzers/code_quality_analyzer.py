"""
Code Quality Analyzer
Analyzes code quality metrics for contributors and repositories.
"""
from pathlib import Path
from typing import Dict, Any, List
import re


class CodeQualityAnalyzer:
    """Analyzer for code quality metrics."""
    
    @staticmethod
    def analyze_code_file(file_path: str, content: str = None) -> Dict[str, Any]:
        """
        Analyze a single code file for quality metrics.
        
        Args:
            file_path: Path to the code file
            content: Optional file content (if already loaded)
            
        Returns:
            Dictionary with quality metrics
        """
        file_path = Path(file_path)
        
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return {"error": str(e)}
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Count different line types
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = CodeQualityAnalyzer._count_comment_lines(lines, file_path.suffix)
        code_lines = total_lines - blank_lines - comment_lines
        
        # Calculate metrics
        comment_ratio = (comment_lines / code_lines * 100) if code_lines > 0 else 0
        blank_ratio = (blank_lines / total_lines * 100) if total_lines > 0 else 0
        
        # Complexity indicators
        complexity_indicators = CodeQualityAnalyzer._analyze_complexity(content, file_path.suffix)
        
        # Code smells
        code_smells = CodeQualityAnalyzer._detect_code_smells(content, file_path.suffix)
        
        # Documentation quality
        doc_quality = CodeQualityAnalyzer._analyze_documentation(content, file_path.suffix)
        
        return {
            "file": file_path.name,
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "comment_ratio": round(comment_ratio, 1),
            "blank_ratio": round(blank_ratio, 1),
            "complexity_indicators": complexity_indicators,
            "code_smells": code_smells,
            "documentation_quality": doc_quality
        }
    
    @staticmethod
    def _count_comment_lines(lines: List[str], extension: str) -> int:
        """Count comment lines based on file type."""
        comment_count = 0
        in_multiline_comment = False
        
        # Comment patterns by extension
        single_line_patterns = {
            '.py': '#',
            '.js': '//',
            '.ts': '//',
            '.java': '//',
            '.cpp': '//',
            '.c': '//',
            '.go': '//',
            '.rs': '//',
            '.rb': '#',
            '.php': '//',
            '.swift': '//',
            '.kt': '//'
        }
        
        multiline_patterns = {
            '.py': ('"""', "'''"),
            '.js': ('/*', '*/'),
            '.ts': ('/*', '*/'),
            '.java': ('/*', '*/'),
            '.cpp': ('/*', '*/'),
            '.c': ('/*', '*/'),
            '.go': ('/*', '*/'),
            '.rs': ('/*', '*/'),
        }
        
        single_comment = single_line_patterns.get(extension.lower(), '#')
        multi_start, multi_end = multiline_patterns.get(extension.lower(), ('/*', '*/'))
        
        for line in lines:
            stripped = line.strip()
            
            # Check multiline comments
            if multi_start in stripped:
                in_multiline_comment = True
            if in_multiline_comment:
                comment_count += 1
            if multi_end in stripped:
                in_multiline_comment = False
                continue
            
            # Check single line comments
            if not in_multiline_comment and stripped.startswith(single_comment):
                comment_count += 1
        
        return comment_count
    
    @staticmethod
    def _analyze_complexity(content: str, extension: str) -> Dict[str, Any]:
        """Analyze code complexity indicators."""
        # Count nested blocks (approximate)
        max_indentation = 0
        avg_indentation = 0
        indented_lines = 0
        
        for line in content.split('\n'):
            if line.strip():
                # Count leading spaces/tabs
                spaces = len(line) - len(line.lstrip())
                if spaces > 0:
                    indented_lines += 1
                    avg_indentation += spaces
                max_indentation = max(max_indentation, spaces)
        
        avg_indentation = avg_indentation / indented_lines if indented_lines > 0 else 0
        
        # Count control structures
        control_keywords = [
            'if', 'else', 'elif', 'for', 'while', 'switch', 'case',
            'try', 'catch', 'except', 'finally'
        ]
        
        control_count = sum(
            len(re.findall(rf'\b{keyword}\b', content))
            for keyword in control_keywords
        )
        
        # Function/method count
        function_patterns = [
            r'\bdef\s+\w+',  # Python
            r'\bfunction\s+\w+',  # JavaScript
            r'\b(public|private|protected)?\s*\w+\s+\w+\s*\(',  # Java/C++
        ]
        
        function_count = sum(
            len(re.findall(pattern, content))
            for pattern in function_patterns
        )
        
        # Long lines
        long_lines = sum(1 for line in content.split('\n') if len(line) > 100)
        
        return {
            "max_indentation_level": max_indentation // 4,  # Approximate nesting
            "control_structures": control_count,
            "functions_methods": function_count,
            "long_lines_over_100_chars": long_lines
        }
    
    @staticmethod
    def _detect_code_smells(content: str, extension: str) -> List[str]:
        """Detect common code smells."""
        smells = []
        
        lines = content.split('\n')
        
        # Very long functions (>50 lines)
        # This is a simplified check
        function_line_counts = []
        current_function_lines = 0
        in_function = False
        
        for line in lines:
            if re.search(r'\b(def|function|public|private|protected)\s+\w+', line):
                if in_function and current_function_lines > 0:
                    function_line_counts.append(current_function_lines)
                in_function = True
                current_function_lines = 0
            elif in_function:
                if line.strip():
                    current_function_lines += 1
        
        if function_line_counts and max(function_line_counts) > 50:
            smells.append("Very long functions detected (>50 lines)")
        
        # Duplicated code patterns (simple check for repeated lines)
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 20:  # Only check meaningful lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        duplicates = sum(1 for count in line_counts.values() if count > 2)
        if duplicates > 5:
            smells.append("Potential code duplication detected")
        
        # Magic numbers
        magic_numbers = re.findall(r'\b\d{2,}\b', content)
        if len(magic_numbers) > 10:
            smells.append("Many magic numbers found (consider using constants)")
        
        # TODO/FIXME comments
        todos = len(re.findall(r'(TODO|FIXME|HACK)', content, re.IGNORECASE))
        if todos > 5:
            smells.append(f"{todos} TODO/FIXME comments found")
        
        # Very long lines
        very_long_lines = sum(1 for line in lines if len(line) > 150)
        if very_long_lines > 3:
            smells.append(f"{very_long_lines} very long lines (>150 chars)")
        
        # Excessive parameters (functions with >5 parameters)
        high_param_functions = re.findall(r'\([^)]{100,}\)', content)
        if len(high_param_functions) > 2:
            smells.append("Functions with many parameters detected")
        
        if not smells:
            smells.append("No obvious code smells detected")
        
        return smells
    
    @staticmethod
    def _analyze_documentation(content: str, extension: str) -> Dict[str, Any]:
        """Analyze documentation quality."""
        # Count docstrings/documentation comments
        docstring_patterns = {
            '.py': r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'',
            '.js': r'/\*\*[\s\S]*?\*/',
            '.ts': r'/\*\*[\s\S]*?\*/',
            '.java': r'/\*\*[\s\S]*?\*/',
        }
        
        pattern = docstring_patterns.get(extension.lower())
        docstring_count = 0
        
        if pattern:
            docstrings = re.findall(pattern, content)
            docstring_count = len(docstrings)
        
        # Count functions
        function_count = len(re.findall(r'\b(def|function|public|private)\s+\w+', content))
        
        # Documentation ratio
        doc_ratio = (docstring_count / function_count * 100) if function_count > 0 else 0
        
        quality_level = "Excellent" if doc_ratio > 80 else \
                       "Good" if doc_ratio > 50 else \
                       "Fair" if doc_ratio > 25 else "Poor"
        
        return {
            "docstring_count": docstring_count,
            "function_count": function_count,
            "documentation_ratio": round(doc_ratio, 1),
            "quality_level": quality_level
        }
    
    @staticmethod
    def aggregate_quality_metrics(file_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate quality metrics across multiple files.
        
        Args:
            file_metrics: List of file quality metrics
            
        Returns:
            Aggregated quality metrics
        """
        if not file_metrics:
            return {}
        
        total_code_lines = sum(m.get('code_lines', 0) for m in file_metrics)
        total_comment_lines = sum(m.get('comment_lines', 0) for m in file_metrics)
        total_files = len(file_metrics)
        
        avg_comment_ratio = sum(m.get('comment_ratio', 0) for m in file_metrics) / total_files
        
        # Collect all code smells
        all_smells = []
        for m in file_metrics:
            all_smells.extend(m.get('code_smells', []))
        
        # Count smell frequency
        smell_frequency = {}
        for smell in all_smells:
            smell_frequency[smell] = smell_frequency.get(smell, 0) + 1
        
        # Overall quality score (0-100)
        quality_score = 100
        
        # Deduct points for issues
        if avg_comment_ratio < 10:
            quality_score -= 20
        elif avg_comment_ratio < 20:
            quality_score -= 10
        
        if smell_frequency:
            quality_score -= min(30, len(smell_frequency) * 5)
        
        quality_score = max(0, quality_score)
        
        quality_rating = "Excellent" if quality_score >= 80 else \
                        "Good" if quality_score >= 60 else \
                        "Fair" if quality_score >= 40 else "Needs Improvement"
        
        return {
            "total_files_analyzed": total_files,
            "total_code_lines": total_code_lines,
            "total_comment_lines": total_comment_lines,
            "average_comment_ratio": round(avg_comment_ratio, 1),
            "code_smells_found": smell_frequency,
            "quality_score": quality_score,
            "quality_rating": quality_rating
        }



