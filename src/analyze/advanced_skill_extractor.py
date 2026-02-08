"""Advanced Skill Extractor - Local AST-based analysis"""

import ast
import json
import re
from pathlib import Path
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


# Skill categorization for better organization
CATEGORY_MAP = {
    'lazy-initialization': 'architecture',
    'memoization': 'architecture',
    'dependency-injection': 'architecture',
    'strategy-pattern': 'architecture',
    'custom-exception-hierarchy': 'architecture',
    'algorithmic-optimization': 'performance',
    'set_deduplication': 'performance',
    'static-type-checking': 'code-quality',
    'modern-python-features': 'code-quality',
    'pythonic-idioms': 'code-quality',
    'graceful-degradation': 'error-handling',
    'exception-handling': 'error-handling',
    'cryptographic-hashing': 'security',
    'resource-management': 'resource-management',
    'java-generics': 'language-feature',
    'java-stream': 'language-feature',
    'java-lambda': 'language-feature',
    'cpp-template': 'language-feature',
    'cpp-smart_ptr': 'language-feature',
    'cpp-move': 'language-feature',
    'javascript-arrow': 'language-feature',
    'javascript-async': 'language-feature',
    'javascript-promise': 'language-feature',
    'typescript-interface': 'language-feature',
    'typescript-generic': 'language-feature',
    'hash-based-structures': 'data-structure',
    'time-complexity-analysis': 'performance',
    'oop-structure': 'architecture',
    'abstraction-principle': 'architecture',
    'encapsulation-principle': 'architecture',
    'polymorphism-principle': 'architecture',
    'inheritance-pattern': 'architecture',
    'function-purity': 'code-quality',
    'side-effects-detected': 'code-quality',
    'algorithm-usage': 'performance',
    'functional-constructs': 'language-feature',
    'memory-management-patterns': 'resource-management',
    'module-architecture': 'architecture',
    'coupling-cohesion': 'architecture'
}



@dataclass
class SkillEvidence:
    skill: str
    evidence_type: str
    location: str
    reasoning: str


@dataclass
class DeepSkillAnalysis:
    file_path: str
    language: str
    basic_skills: List[str] = field(default_factory=list)
    advanced_skills: List[str] = field(default_factory=list)
    design_patterns: List[str] = field(default_factory=list)
    complexity_insights: Dict[str, Any] = field(default_factory=dict)
    evidence: List[SkillEvidence] = field(default_factory=list)
    skill_categories: Dict[str, List[str]] = field(default_factory=dict)
    
    def categorize_skills(self):
        self.skill_categories = {}
        all_skills = self.advanced_skills + self.design_patterns
        for skill in all_skills:
            category = CATEGORY_MAP.get(skill, 'other')
            self.skill_categories.setdefault(category, []).append(skill)
        for cat in self.skill_categories:
            self.skill_categories[cat].sort()
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary representation for serialization/databases."""
        if not self.skill_categories:
            self.categorize_skills()
        return {
            "file_path": self.file_path,
            "language": self.language,
            "basic_skills": self.basic_skills,
            "advanced_skills": self.advanced_skills,
            "design_patterns": self.design_patterns,
            "skill_categories": self.skill_categories,
            "complexity_insights": self.complexity_insights,
            "evidence": [
                {
                    "skill": e.skill,
                    "type": e.evidence_type,
                    "reasoning": e.reasoning,
                    "location": e.location,
                }
                for e in self.evidence
            ],
        }



class AdvancedSkillExtractor:
    
    def __init__(self):
        self.skill_patterns = self._initialize_patterns()
        self.language_extensions = {
            '.py': 'python',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }
    
    def _detect_language(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        return self.language_extensions.get(ext, 'unknown')
    
    def _initialize_patterns(self) -> Dict[str, Any]:
        return {
            'caching': {
                'keywords': ['cache', 'memoize', 'cached', '_cached'],
                'patterns': [r'if.*is None:', r'@lru_cache', r'@cache']
            },
            'lazy_evaluation': {
                'keywords': ['lazy', '_lazy', 'deferred'],
                'patterns': [r'if.*is None:.*=', r'property.*return']
            },
            'set_optimization': {
                'keywords': ['set(', 'frozenset('],
                'patterns': [r'list\(set\(', r'set\([^\)]+\)']
            },
            'dependency_injection': {
                'keywords': ['inject', 'Optional[', 'Union['],
                'patterns': [r'def __init__\(self.*:.*\)']
            },
            'type_hints': {
                'keywords': ['List[', 'Dict[', 'Optional[', 'Union[', 'Set['],
                'patterns': [r'def.*\(.*:.*\)\s*->', r':\s*List\[', r':\s*Dict\[']
            },
            'context_managers': {
                'keywords': ['with ', '__enter__', '__exit__'],
                'patterns': [r'with\s+\w+.*as\s+\w+:']
            },
            'custom_exceptions': {
                'keywords': ['Exception)', 'Error)'],
                'patterns': [r'class\s+\w+Error\(', r'class\s+\w+Exception\(']
            },
            'dataclasses': {
                'keywords': ['@dataclass', 'from dataclasses'],
                'patterns': [r'@dataclass']
            },
            'async_programming': {
                'keywords': ['async def', 'await ', 'asyncio'],
                'patterns': [r'async\s+def\s+', r'await\s+']
            },
            'comprehensions': {
                'keywords': ['for ', ' in '],
                'patterns': [r'\[.+for\s+\w+\s+in\s+', r'\{.+for\s+\w+\s+in\s+']
            }
        }
    
    def _append_unique(self, items: List[str], value: str) -> None:
        if value not in items:
            items.append(value)

    def _add_evidence(
        self,
        analysis: DeepSkillAnalysis,
        skill: str,
        evidence_type: str,
        reasoning: str,
        location: str = "File-level",
        bucket: str = "advanced",
    ) -> None:
        for ev in analysis.evidence:
            if ev.skill == skill and (ev.location == location or ev.reasoning == reasoning or ev.evidence_type == evidence_type):
                return
        target = analysis.advanced_skills if bucket == "advanced" else analysis.design_patterns
        self._append_unique(target, skill)
        analysis.evidence.append(
            SkillEvidence(
                skill=skill,
                evidence_type=evidence_type,
                location=location,
                reasoning=reasoning,
            )
        )
    
    def analyze_file(self, file_path: Path) -> DeepSkillAnalysis:
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')
        
        language = self._detect_language(file_path)
        analysis = DeepSkillAnalysis(file_path=str(file_path), language=language)
        analysis.basic_skills.append(language)
        
        if language == 'python':
            try:
                tree = ast.parse(content)
                self._detect_caching_patterns(tree, content, analysis)
                self._detect_design_patterns(tree, content, analysis)
                self._detect_complexity_awareness(tree, content, analysis)
                self._detect_error_handling(tree, content, analysis)
                self._detect_type_safety(tree, content, analysis)
                self._detect_data_structures(tree, content, analysis)
                self._detect_python_cs_concepts(tree, content, analysis)
                self._detect_time_complexity(tree, content, analysis)
            except SyntaxError:
                analysis.basic_skills.append('syntax-error-detected')
        else:
            self._analyze_generic(content, language, analysis)
            self._detect_time_complexity(None, content, analysis)

        self._order_skills(analysis)
        return analysis
    
    def _detect_caching_patterns(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.If):
                        test_str = ast.unparse(stmt.test) if hasattr(ast, 'unparse') else ''
                        if 'is None' in test_str or '== None' in test_str:
                            snippet = self._extract_code_snippet(content, stmt.lineno, context_lines=2)
                            self._add_evidence(
                                analysis,
                                skill='lazy-initialization',
                                evidence_type='pattern',
                                reasoning='Detected lazy initialization pattern with None check',
                                location=snippet
                            )
                            break
        
        if '@lru_cache' in content or '@cache' in content:
            self._add_evidence(
                analysis,
                skill='memoization',
                evidence_type='decorator',
                reasoning='Uses functools caching decorators for performance',
            )
    def _detect_design_patterns(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        has_enum = 'Enum' in content or 'from enum import' in content
        has_dict_dispatch = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                if len(node.value.keys) > 2:
                    has_dict_dispatch = True
        
        if has_enum and has_dict_dispatch:
            self._add_evidence(
                analysis,
                skill='strategy-pattern',
                evidence_type='pattern',
                reasoning='Enum + dictionary dispatch indicates Strategy pattern',
                location='Class-level',
                bucket='design'
            )
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                for arg in node.args.args[1:]:
                    if arg.annotation:
                        annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else ''
                        if 'Optional' in annotation_str or 'Union' in annotation_str:
                            self._add_evidence(
                                analysis,
                                skill='dependency-injection',
                                evidence_type='pattern',
                                reasoning='Optional dependencies injected via constructor',
                                location='__init__ method',
                                bucket='design'
                            )
                            break
        custom_exceptions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ast.unparse(base) if hasattr(ast, 'unparse') else ''
                    if 'Exception' in base_name or 'Error' in base_name:
                        custom_exceptions.append(node.name)
        
        if custom_exceptions:
            self._add_evidence(
                analysis,
                skill='custom-exception-hierarchy',
                evidence_type='pattern',
                reasoning='Defines domain-specific exceptions for fine-grained error handling',
                location=f'Classes: {", ".join(custom_exceptions)}',
                bucket='design'
            )

    def _detect_complexity_awareness(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        set_usage_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ''
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name == 'list' and len(node.args) > 0:
                    if isinstance(node.args[0], ast.Call) and isinstance(node.args[0].func, ast.Name):
                        if node.args[0].func.id == 'set':
                            set_usage_count += 1
        
        if set_usage_count > 0:
            analysis.complexity_insights['set_deduplication'] = set_usage_count
            self._add_evidence(
                analysis,
                skill='algorithmic-optimization',
                evidence_type='data-structure',
                reasoning='Uses set conversion to deduplicate data in O(n)',
                location=f'{set_usage_count} set() conversions'
            )
        
        if any(token in content for token in ['hashlib', 'sha256', 'md5']):
            self._add_evidence(
                analysis,
                skill='cryptographic-hashing',
                evidence_type='library',
                reasoning='Uses cryptographic hashing for data integrity or IDs',
                location='hashlib/md5 usage'
            )

    def _detect_error_handling(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        try_except_count = 0
        graceful_degradation = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                try_except_count += 1
                if node.handlers:
                    for handler in node.handlers:
                        if len(handler.body) > 1 or (len(handler.body) == 1 and not isinstance(handler.body[0], (ast.Pass, ast.Raise))):
                            graceful_degradation = True
        
        if try_except_count > 0:
            self._append_unique(analysis.basic_skills, 'exception-handling')
        
        if graceful_degradation:
            self._add_evidence(
                analysis,
                skill='graceful-degradation',
                evidence_type='pattern',
                reasoning='Implements fallback logic inside exception handlers',
                location=f'{try_except_count} try-except blocks'
            )

    def _detect_type_safety(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        type_hint_count = 0
        return_type_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if arg.annotation:
                        type_hint_count += 1
                if node.returns:
                    return_type_count += 1
        
        total_annotations = type_hint_count + return_type_count
        if total_annotations >= 5:
            self._add_evidence(
                analysis,
                skill='static-type-checking',
                evidence_type='annotation',
                reasoning='Comprehensive type hints enable static analysis and IDE support',
                location=f'{type_hint_count} parameters, {return_type_count} returns'
            )
        if '@dataclass' in content:
            self._add_evidence(
                analysis,
                skill='modern-python-features',
                evidence_type='decorator',
                reasoning='Uses dataclasses for structured data with automatic methods',
                location='Class definitions'
            )

    def _detect_data_structures(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        comprehension_count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                comprehension_count += 1
        
        if comprehension_count > 3:
            self._add_evidence(
                analysis,
                skill='pythonic-idioms',
                evidence_type='syntax',
                reasoning='Uses comprehensions for concise, efficient iteration',
                location=f'{comprehension_count} comprehensions'
            )
        with_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                with_count += 1
        if with_count > 0:
            self._add_evidence(
                analysis,
                skill='resource-management',
                evidence_type='pattern',
                reasoning='Uses context managers for automatic resource cleanup',
                location=f'{with_count} with statements'
            )

    def _analyze_generic(self, content: str, language: str, analysis: DeepSkillAnalysis):
        pattern_library = {
            'java': [
                {
                    'skill': 'java-generics',
                    'pattern': r'<[A-Z][a-zA-Z0-9,\s<>]*>',
                    'type': 'syntax',
                    'reasoning': 'Uses parameterized Java generics for type safety'
                },
                {
                    'skill': 'java-stream',
                    'pattern': r'\.stream\(\)',
                    'type': 'pattern',
                    'reasoning': 'Uses Java Stream API for functional pipelines'
                },
                {
                    'skill': 'java-lambda',
                    'pattern': r'->',
                    'type': 'syntax',
                    'reasoning': 'Lambda expressions indicate functional style'
                },
                {
                    'skill': 'exception-handling',
                    'pattern': r'class\s+\w+Exception\s+extends',
                    'type': 'pattern',
                    'reasoning': 'Defines custom exception classes for error handling'
                }
            ],
            'cpp': [
                {
                    'skill': 'cpp-template',
                    'pattern': r'template\s*<',
                    'type': 'syntax',
                    'reasoning': 'Template definitions indicate generic programming'
                },
                {
                    'skill': 'cpp-smart_ptr',
                    'pattern': r'(unique_ptr|shared_ptr|weak_ptr)',
                    'type': 'pattern',
                    'reasoning': 'Modern smart pointers improve memory safety'
                },
                {
                    'skill': 'cpp-move',
                    'pattern': r'std::move',
                    'type': 'syntax',
                    'reasoning': 'Move semantics highlight performance awareness'
                }
            ],
            'javascript': [
                {
                    'skill': 'javascript-arrow',
                    'pattern': r'=>',
                    'type': 'syntax',
                    'reasoning': 'Arrow functions indicate modern JavaScript usage'
                },
                {
                    'skill': 'javascript-async',
                    'pattern': r'async\s+function',
                    'type': 'pattern',
                    'reasoning': 'Async functions for concurrent workflows'
                },
                {
                    'skill': 'javascript-promise',
                    'pattern': r'new\s+Promise|Promise\.',
                    'type': 'pattern',
                    'reasoning': 'Promise usage for async control flow'
                }
            ],
            'typescript': [
                {
                    'skill': 'typescript-interface',
                    'pattern': r'interface\s+\w+',
                    'type': 'syntax',
                    'reasoning': 'Interfaces define TypeScript contracts'
                },
                {
                    'skill': 'typescript-generic',
                    'pattern': r'<[A-Z][a-zA-Z0-9,\s]*>',
                    'type': 'syntax',
                    'reasoning': 'Generic declarations highlight reusable components'
                }
            ],
            'c': [
                {
                    'skill': 'resource-management',
                    'pattern': r'(malloc|calloc|realloc|free)',
                    'type': 'pattern',
                    'reasoning': 'Manual memory management primitives detected'
                }
            ]
        }
        
        for entry in pattern_library.get(language, []):
            match = re.search(entry['pattern'], content)
            if not match:
                continue
            snippet = self._snippet_from_match(content, match.start())
            self._add_evidence(
                analysis,
                skill=entry['skill'],
                evidence_type=entry['type'],
                reasoning=entry['reasoning'],
                location=snippet
            )
        
        hash_match = re.search(r'(HashMap|HashSet|unordered_map|unordered_set|dict|Map|Set)', content)
        if hash_match:
            snippet = self._snippet_from_match(content, hash_match.start())
            self._add_evidence(
                analysis,
                skill='hash-based-structures',
                evidence_type='data-structure',
                reasoning='Uses hash-based collections for O(1) lookups',
                location=snippet
            )
        
        if re.search(r'(try|catch|except|throw|throws)', content, re.IGNORECASE):
            self._append_unique(analysis.basic_skills, 'exception-handling')

        self._detect_generic_cs_concepts(language, content, analysis)

    def _detect_python_cs_concepts(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        self._detect_oop_structure(tree, content, analysis)
        self._detect_abstraction(tree, content, analysis)
        self._detect_encapsulation(tree, content, analysis)
        self._detect_polymorphism(tree, content, analysis)
        self._detect_inheritance(tree, content, analysis)
        self._detect_function_purity(tree, content, analysis)
        self._detect_side_effects(tree, content, analysis)
        self._detect_algorithm_usage(content, analysis)
        self._detect_functional_constructs(tree, content, analysis)
        self._detect_memory_management_patterns(tree, content, analysis)
        self._detect_module_architecture(content, analysis)
        self._detect_coupling_and_cohesion(content, analysis)

    def _detect_oop_structure(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if methods:
                    self._add_evidence(
                        analysis,
                        skill='oop-structure',
                        evidence_type='pattern',
                        reasoning='Class with methods detected indicating object-oriented structure',
                        location=f'class {node.name}',
                        bucket='design'
                    )
                    break

    def _detect_abstraction(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = getattr(base, 'id', getattr(base, 'attr', ''))
                    if base_name in {'ABC', 'ABCMeta'}:
                        self._add_evidence(
                            analysis,
                            skill='abstraction-principle',
                            evidence_type='pattern',
                            reasoning='Class inherits from abstract base',
                            location=f'class {node.name}',
                            bucket='design'
                        )
                        return
        if 'NotImplementedError' in content:
            self._add_evidence(
                analysis,
                skill='abstraction-principle',
                evidence_type='pattern',
                reasoning='Methods raise NotImplementedError to enforce abstraction',
                location='NotImplementedError usage',
                bucket='design'
            )

    def _detect_encapsulation(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.attr.startswith('_'):
                self._add_evidence(
                    analysis,
                    skill='encapsulation-principle',
                    evidence_type='pattern',
                    reasoning='Prefixed attributes indicate encapsulation practices',
                    location=f'attribute {node.attr}',
                    bucket='design'
                )
                return

    def _detect_polymorphism(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if any(isinstance(dec, ast.Name) and dec.id in {'singledispatch', 'abstractmethod'} for dec in node.decorator_list):
                    self._add_evidence(
                        analysis,
                        skill='polymorphism-principle',
                        evidence_type='pattern',
                        reasoning='Function decorated for dispatch or abstract behavior',
                        location=f'function {node.name}',
                        bucket='design'
                    )
                    return
        if 'isinstance' in content:
            self._add_evidence(
                analysis,
                skill='polymorphism-principle',
                evidence_type='pattern',
                reasoning='Type checks suggest polymorphic handling',
                location='isinstance usage',
                bucket='design'
            )

    def _detect_inheritance(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.bases:
                self._add_evidence(
                    analysis,
                    skill='inheritance-pattern',
                    evidence_type='pattern',
                    reasoning='Class inherits from another base class',
                    location=f'class {node.name}',
                    bucket='design'
                )
                return

    def _detect_function_purity(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_side_effect = any(isinstance(n, (ast.Assign, ast.AugAssign, ast.Raise)) for n in ast.walk(node))
                calls = {getattr(n.func, 'id', getattr(n.func, 'attr', '')) for n in ast.walk(node) if isinstance(n, ast.Call)}
                impure_calls = {'print', 'open', 'requests', 'logging', 'write'}
                if not has_side_effect and calls.isdisjoint(impure_calls):
                    self._add_evidence(
                        analysis,
                        skill='function-purity',
                        evidence_type='pattern',
                        reasoning='Function appears pure with return-only behavior',
                        location=f'function {node.name}'
                    )
                    return

    def _detect_side_effects(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = getattr(node.func, 'id', getattr(node.func, 'attr', ''))
                if func_name in {'print', 'open', 'write', 'logging', 'requests'}:
                    self._add_evidence(
                        analysis,
                        skill='side-effects-detected',
                        evidence_type='pattern',
                        reasoning='Function call indicates observable side effects',
                        location=f'call {func_name}'
                    )
                    return

    def _detect_algorithm_usage(self, content: str, analysis: DeepSkillAnalysis):
        clean = self._strip_comments_strings(content)
        patterns = {
            'heapq': r'\bheapq\b',
            'bisect': r'\bbisect\b',
            'deque': r'\bdeque\b',
            'sorted': r'\bsorted\s*\(',
            'bfs': r'\bbfs\b',
            'dfs': r'\bdfs\b'
        }
        for label, pat in patterns.items():
            if re.search(pat, clean):
                self._add_evidence(
                    analysis,
                    skill='algorithm-usage',
                    evidence_type='pattern',
                    reasoning=f'Algorithmic keyword detected: {label}',
                    location=f'keyword {label}'
                )
                return

    def _detect_functional_constructs(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.Lambda)):
                self._add_evidence(
                    analysis,
                    skill='functional-constructs',
                    evidence_type='pattern',
                    reasoning='Functional construct (comprehension or lambda) detected',
                    location='functional construct usage'
                )
                return
        if re.search(r'\b(map|filter|reduce)\(', content):
            self._add_evidence(
                analysis,
                skill='functional-constructs',
                evidence_type='pattern',
                reasoning='Functional helper (map/filter/reduce) detected',
                location='functional helper usage'
            )

    def _detect_memory_management_patterns(self, tree: ast.AST, content: str, analysis: DeepSkillAnalysis):
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                self._add_evidence(
                    analysis,
                    skill='memory-management-patterns',
                    evidence_type='pattern',
                    reasoning='Context manager manages resources safely',
                    location='with-statement'
                )
                return
        if 'gc.' in content:
            self._add_evidence(
                analysis,
                skill='memory-management-patterns',
                evidence_type='pattern',
                reasoning='Garbage-collection utilities referenced',
                location='gc usage'
            )

    def _detect_module_architecture(self, content: str, analysis: DeepSkillAnalysis):
        if '__all__' in content or 'if __name__' in content:
            self._add_evidence(
                analysis,
                skill='module-architecture',
                evidence_type='pattern',
                reasoning='Module exports or entry points defined',
                location='module structure declaration',
                bucket='design'
            )

    def _detect_coupling_and_cohesion(self, content: str, analysis: DeepSkillAnalysis):
        import_count = len(re.findall(r'^\s*(import|from)\s+', content, re.MULTILINE))
        if import_count >= 5:
            self._add_evidence(
                analysis,
                skill='coupling-cohesion',
                evidence_type='pattern',
                reasoning='High number of imports suggests coupling considerations',
                location='import section',
                bucket='design'
            )

    # Time Complexity Detection
    def _detect_time_complexity(self, tree: Optional[ast.AST], content: str, analysis: DeepSkillAnalysis):
        if analysis.language == 'python':
            self._detect_time_complexity_python(tree, content, analysis)
        else:
            self._detect_time_complexity_generic(content, analysis)

    def _detect_time_complexity_python(self, tree: Optional[ast.AST], content: str, analysis: DeepSkillAnalysis):
        max_depth = 0
        recursion_found = False
        algo_hits: List[str] = []

        def loop_depth(node, depth=0):
            nonlocal max_depth
            if isinstance(node, (ast.For, ast.While)):
                depth += 1
                max_depth = max(max_depth, depth)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {'sorted', 'heapq', 'bisect', 'deque'}:
                    algo_hits.append(node.func.id)
            for child in ast.iter_child_nodes(node):
                loop_depth(child, depth)

        if tree:
            loop_depth(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    fname = node.name
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == fname:
                            recursion_found = True
                if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    max_depth = max(max_depth, 2)

        clean = self._strip_comments_strings(content)
        patterns = [r'\bbfs\b', r'\bdfs\b', r'\bheapq\b', r'\bbisect\b', r'\bdeque\b', r'\bsorted\s*\(', r'\bsort\s*\(']
        algo_hits.extend([pat for pat in patterns if re.search(pat, clean)])

        label = 'low'
        if max_depth >= 3:
            label = 'high'
        elif recursion_found or algo_hits:
            label = 'moderate'

        analysis.complexity_insights['max_loop_nesting'] = max_depth
        if recursion_found:
            analysis.complexity_insights['recursion'] = True
        if algo_hits:
            analysis.complexity_insights['algorithms'] = list(set(algo_hits))
        analysis.complexity_insights['overall_complexity'] = label

        self._add_evidence(
            analysis,
            skill='time-complexity-analysis',
            evidence_type='pattern',
            reasoning=f'Detected nested loops up to depth {max_depth}; recursion={recursion_found}; algorithms={bool(algo_hits)}',
            location='complexity scan'
        )

    def _detect_time_complexity_generic(self, content: str, analysis: DeepSkillAnalysis):
        loop_hits = len(re.findall(r'for\s*\(.*?\)', content))
        max_depth = 1 if loop_hits else 0
        if loop_hits >= 3:
            max_depth = 3
        elif loop_hits == 2:
            max_depth = 2

        recursion_found = False
        func_defs = re.findall(r'\b(\w+)\s*\(', content)
        for name in set(func_defs):
            pattern = rf'{name}\s*\(.*{name}\s*\('
            if re.search(pattern, content, re.DOTALL):
                recursion_found = True
                break

        algo_keywords = ['sort', 'binarySearch', 'Collections.sort', 'std::sort', 'Arrays.sort', 'BFS', 'DFS']
        algo_hits = [kw for kw in algo_keywords if re.search(kw, content)]

        label = 'low'
        if max_depth >= 3:
            label = 'high'
        elif recursion_found or algo_hits:
            label = 'moderate'

        analysis.complexity_insights['max_loop_nesting'] = max_depth
        if recursion_found:
            analysis.complexity_insights['recursion'] = True
        if algo_hits:
            analysis.complexity_insights['algorithms'] = list(set(algo_hits))
        analysis.complexity_insights['overall_complexity'] = label

        self._add_evidence(
            analysis,
            skill='time-complexity-analysis',
            evidence_type='pattern',
            reasoning=f'Detected nested loops up to depth {max_depth}; recursion={recursion_found}; algorithms={bool(algo_hits)}',
            location='complexity scan'
        )

    def _strip_comments_strings(self, content: str) -> str:
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'#.*', '', content)
        content = re.sub(r'\".*?\"', '', content, flags=re.DOTALL)
        content = re.sub(r"\'.*?\'", '', content, flags=re.DOTALL)
        return content

    def _detect_generic_cs_concepts(self, language: str, content: str, analysis: DeepSkillAnalysis):
        clean = self._strip_comments_strings(content)
        def add(skill, reasoning, location='file-level', bucket='advanced'):
            self._add_evidence(
                analysis,
                skill=skill,
                evidence_type='pattern',
                reasoning=reasoning,
                location=location,
                bucket=bucket
            )

        if re.search(r'\bclass\s+\w+\s*[{:]', clean):
            add('oop-structure', 'Class definitions imply OOP structure', 'class declaration', bucket='design')
        if re.search(r'\b(abstract|interface)\b', clean):
            add('abstraction-principle', 'Abstract class or interface detected', 'abstract/interface declaration', bucket='design')
        if re.search(r'\bprivate\s+\w+', clean):
            add('encapsulation-principle', 'Private fields indicate encapsulation', 'private field', bucket='design')
        if re.search(r'\b(override|virtual|implements)\b', clean):
            add('polymorphism-principle', 'Override/virtual keywords suggest polymorphism', 'method override', bucket='design')
        if re.search(r'\b(extends|:)\s*\w+', clean) and language in {'java', 'cpp', 'typescript', 'csharp'}:
            add('inheritance-pattern', 'Inheritance hierarchy detected', 'inheritance clause', bucket='design')
        if re.search(r'\b(lambda|=>)\b', clean) and language in {'javascript', 'typescript', 'cpp', 'csharp', 'go', 'rust'}:
            add('functional-constructs', 'Lambda expression detected', 'lambda usage')
        if re.search(r'\b(map|filter|reduce|stream\.|collect)\b', clean):
            add('functional-constructs', 'Functional helper detected', 'functional helper usage')
        if re.search(r'\b(console\.log|System\.out|fmt\.Print|printf)\b', clean):
            add('side-effects-detected', 'Output/logging indicates side effects', 'logging statement')
        if re.search(r'\b(sort|search|DFS|BFS|heap|priority\s+queue)\b', clean):
            add('algorithm-usage', 'Algorithmic keyword detected', 'algorithm keyword')
        if re.search(r'\b(new\s+\w+|delete|malloc|free)\b', clean):
            add('memory-management-patterns', 'Manual memory management detected', 'memory management section')
        if re.search(r'\b(namespace|module|package)\b', clean):
            add('module-architecture', 'Namespace or module declaration found', 'module declaration', bucket='design')
        import_count = len(re.findall(r'^\s*(import|using|require)\s+', clean, re.MULTILINE))
        if import_count >= 5:
            add('coupling-cohesion', 'Multiple imports suggest coupling considerations', 'import block', bucket='design')

    def _detect_time_complexity(self, tree: Optional[ast.AST], content: str, analysis: DeepSkillAnalysis):
        if analysis.language == 'python':
            self._detect_time_complexity_python(tree, content, analysis)
        else:
            self._detect_time_complexity_generic(content, analysis)

    def _detect_time_complexity_python(self, tree: Optional[ast.AST], content: str, analysis: DeepSkillAnalysis):
        max_depth = 0
        recursion_found = False
        algo_hits: List[str] = []
        branch_count = 0
        return_count = 0
        class_method_counts: List[int] = []

        def loop_depth(node, depth=0):
            nonlocal max_depth, branch_count, return_count
            if isinstance(node, (ast.For, ast.While)):
                depth += 1
                max_depth = max(max_depth, depth)
            if isinstance(node, (ast.If, ast.Try, ast.BoolOp)):
                branch_count += 1
            if isinstance(node, ast.Return):
                return_count += 1
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {'sorted', 'heapq', 'bisect', 'deque'}:
                    algo_hits.append(node.func.id)
            for child in ast.iter_child_nodes(node):
                loop_depth(child, depth)

        if tree:
            loop_depth(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    method_total = sum(1 for n in node.body if isinstance(n, ast.FunctionDef))
                    if method_total:
                        class_method_counts.append(method_total)
                if isinstance(node, ast.FunctionDef):
                    fname = node.name
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == fname:
                            recursion_found = True
                if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    max_depth = max(max_depth, 2)

        clean = self._strip_comments_strings(content)
        algo_patterns = {
            'bfs': r'\bbfs\b',
            'dfs': r'\bdfs\b',
            'heapq': r'\bheapq\b',
            'bisect': r'\bbisect\b',
            'deque': r'\bdeque\b',
            'sorted': r'\bsorted\s*\(',
            'sort': r'\bsort\s*\('
        }
        for label_key, pat in algo_patterns.items():
            if re.search(pat, clean):
                algo_hits.append(label_key)

        label = 'low'
        if max_depth >= 3:
            label = 'high'
        elif recursion_found or algo_hits:
            label = 'moderate'

        analysis.complexity_insights['max_loop_nesting'] = max_depth
        if recursion_found:
            analysis.complexity_insights['recursion'] = True
        if algo_hits:
            analysis.complexity_insights['algorithms'] = list(set(algo_hits))
        if branch_count:
            analysis.complexity_insights['cyclomatic_estimate'] = branch_count + 1
        if return_count:
            analysis.complexity_insights['return_count'] = return_count
        if class_method_counts:
            analysis.complexity_insights['methods_per_class_mean'] = sum(class_method_counts) / len(class_method_counts)
            analysis.complexity_insights['largest_class_methods'] = max(class_method_counts)
        analysis.complexity_insights['overall_complexity'] = label

        self._add_evidence(
            analysis,
            skill='time-complexity-analysis',
            evidence_type='pattern',
            reasoning=f'Detected nested loops up to depth {max_depth}; recursion={recursion_found}; algorithms={bool(algo_hits)}',
            location='complexity scan'
        )

    def _detect_time_complexity_generic(self, content: str, analysis: DeepSkillAnalysis):
        clean = self._strip_comments_strings(content)
        loop_hits = len(re.findall(r'\b(for|while|foreach|forEach)\s*\(.*?\)', clean))
        max_depth = 1 if loop_hits else 0
        if loop_hits >= 3:
            max_depth = 3
        elif loop_hits == 2:
            max_depth = 2

        recursion_found = False
        def_locs = []
        for m in re.finditer(r'\b(?:function\s+|def\s+|[A-Za-z_<>\[\]]+\s+)?([A-Za-z_]\w*)\s*\([^;{]*\)\s*{', clean):
            def_locs.append((m.group(1), m.end()))
        for name, end in def_locs:
            call_pat = rf'\b{name}\s*\('
            if re.search(call_pat, clean[end:]):
                recursion_found = True
                break

        algo_patterns = [
            ('sort', r'\bsort\s*\('),
            ('binarySearch', r'\bbinarySearch\b'),
            ('Collections.sort', r'\bCollections\.sort\b'),
            ('std::sort', r'\bstd::sort\b'),
            ('Arrays.sort', r'\bArrays\.sort\b'),
            ('BFS', r'\bBFS\b'),
            ('DFS', r'\bDFS\b')
        ]
        algo_hits = [label for label, pat in algo_patterns if re.search(pat, clean)]

        branch_count = len(re.findall(r'\b(if|else if|switch|case)\b', clean))
        return_count = len(re.findall(r'\breturn\b', clean))
        class_blocks = list(re.finditer(r'\bclass\s+\w+\s*{([^}]*)}', clean, re.DOTALL))
        class_method_counts: List[int] = []
        for m in class_blocks:
            body = m.group(1)
            methods = re.findall(r'\b(?:public|private|protected)?\s*(?:static\s+)?[A-Za-z_][\w<>\[\]]*\s+([A-Za-z_]\w*)\s*\([^;{]*\)\s*{', body)
            class_method_counts.append(len(methods))

        label = 'low'
        if max_depth >= 3:
            label = 'high'
        elif recursion_found or algo_hits:
            label = 'moderate'

        analysis.complexity_insights['max_loop_nesting'] = max_depth
        if recursion_found:
            analysis.complexity_insights['recursion'] = True
        if algo_hits:
            analysis.complexity_insights['algorithms'] = [re.sub(r'\\b', '', a) for a in algo_hits]
        if branch_count:
            analysis.complexity_insights['cyclomatic_estimate'] = branch_count + 1
        if return_count:
            analysis.complexity_insights['return_count'] = return_count
        if class_method_counts:
            analysis.complexity_insights['methods_per_class_mean'] = sum(class_method_counts) / len(class_method_counts)
            analysis.complexity_insights['largest_class_methods'] = max(class_method_counts)
        analysis.complexity_insights['overall_complexity'] = label

        self._add_evidence(
            analysis,
            skill='time-complexity-analysis',
            evidence_type='pattern',
            reasoning=f'Detected nested loops up to depth {max_depth}; recursion={recursion_found}; algorithms={bool(algo_hits)}',
            location='complexity scan'
        )

    def _order_skills(self, analysis: DeepSkillAnalysis):
        priority = {
            'architecture': 0,
            'performance': 1,
            'code-quality': 2,
            'language-feature': 3,
            'security': 4,
            'error-handling': 5,
            'resource-management': 6,
            'data-structure': 7,
        }
        def sort_skills(skills: List[str]) -> List[str]:
            return sorted(skills, key=lambda s: priority.get(CATEGORY_MAP.get(s, ''), 99))
        analysis.advanced_skills = sort_skills(analysis.advanced_skills)
        analysis.design_patterns = sort_skills(analysis.design_patterns)
        analysis.categorize_skills()

    def analyze_directory(self, directory: Path) -> Dict[str, DeepSkillAnalysis]:
        results = {}
        extensions = tuple(self.language_extensions.keys())
        
        for code_file in directory.rglob('*'):
            if code_file.suffix.lower() not in self.language_extensions:
                continue
            if any(part.lower() in {'vendor', 'dist', 'build'} for part in code_file.parts):
                continue
            if code_file.name.endswith(('.min.js', '.bundle.js')):
                continue
            try:
                if code_file.stat().st_size > 10000:
                    continue
            except OSError:
                continue
            if any(skip in code_file.parts for skip in ['__pycache__', '.venv', 'venv', 'node_modules', 'build', 'dist']):
                continue
            
            try:
                analysis = self.analyze_file(code_file)
                results[str(code_file)] = analysis
            except Exception as e:
                print(f"Error analyzing {code_file}: {e}")
        output_path = Path(directory) / "skill_analysis_results.json"
        serializable = {file_path: analysis.to_dict() for file_path, analysis in results.items()}
        output_path.write_text(json.dumps(serializable, indent=2))
        print(f"Saved analysis to {output_path}")            
        return results
    
    def aggregate_skills(self, analyses: Dict[str, DeepSkillAnalysis]) -> Dict[str, Any]:
        all_basic = set()
        all_advanced = set()
        all_patterns = set()
        evidence_by_skill = defaultdict(list)
        
        for analysis in analyses.values():
            all_basic.update(analysis.basic_skills)
            all_advanced.update(analysis.advanced_skills)
            all_patterns.update(analysis.design_patterns)
            
            for evidence in analysis.evidence:
                evidence_by_skill[evidence.skill].append({
                    "type": evidence.evidence_type,
                    "reasoning": evidence.reasoning,
                    "location": evidence.location,
                })
        
        return {
            'basic_skills': sorted(list(all_basic)),
            'advanced_skills': sorted(list(all_advanced)),
            'design_patterns': sorted(list(all_patterns)),
            'evidence_count': sum(len(v) for v in evidence_by_skill.values()),
            'evidence_by_skill': dict(evidence_by_skill),
            'total_files_analyzed': len(analyses)
        }


    def _extract_code_snippet(self, content, line_number, context_lines=2):
        lines = content.split('\n')
        line_idx = line_number - 1
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        snippet = []
        for i in range(start, end):
            marker = "→" if i == line_idx else " "
            snippet.append(f"{marker} {i+1:3d} | {lines[i]}")
        return '\n'.join(snippet)

    def _snippet_from_match(self, content: str, start_idx: int) -> str:
        """Create a snippet for a regex match index."""
        line_number = content[:start_idx].count('\n') + 1
        return self._extract_code_snippet(content, line_number)


def analyze_single_file(file_path):
    """Run analysis on one file and export JSON next to it."""
    from pathlib import Path
    import json

    file_path = Path(file_path)
    extractor = AdvancedSkillExtractor()
    analysis = extractor.analyze_file(file_path)

    # Prepare output data
    data = {
        "file_path": analysis.file_path,
        "basic_skills": analysis.basic_skills,
        "advanced_skills": analysis.advanced_skills,
        "design_patterns": analysis.design_patterns,
        "skill_categories": analysis.skill_categories,
        "complexity_insights": analysis.complexity_insights,
        "evidence": [
            {
                "skill": e.skill,
                "type": e.evidence_type,
                "reasoning": e.reasoning,
                "location": e.location,
            }
            for e in analysis.evidence
        ],
    }

    output_path = file_path.with_suffix(".skill_analysis.json")
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Saved single-file analysis to {output_path}")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python -m src.analyze.advanced_skill_extractor <path_to_file_or_dir>")
        sys.exit(1)

    target = Path(sys.argv[1])
    extractor = AdvancedSkillExtractor()

    if target.is_file():
        analyze_single_file(target)
    elif target.is_dir():
        extractor.analyze_directory(target)
    else:
        print(f"Invalid path: {target}")
