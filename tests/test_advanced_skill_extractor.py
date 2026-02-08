"""Tests for Advanced Skill Extractor"""

import pytest
from pathlib import Path
from src.analyze.advanced_skill_extractor import (
    AdvancedSkillExtractor,
    DeepSkillAnalysis,
    SkillEvidence
)


@pytest.fixture
def extractor():
    return AdvancedSkillExtractor()


@pytest.fixture
def sample_code_with_caching():
    return '''
def get_data(self):
    if self._cache is None:
        self._cache = expensive_operation()
    return self._cache
'''


@pytest.fixture
def sample_code_with_set_optimization():
    return '''
def remove_duplicates(items):
    return list(set(items))
'''


@pytest.fixture
def sample_code_with_type_hints():
    return '''
def process(data: List[str], count: int) -> Dict[str, int]:
    return {"result": count}

def analyze(items: Optional[List[str]]) -> bool:
    return True
'''


@pytest.fixture
def sample_code_with_exception():
    return '''
class CustomError(Exception):
    pass

class ValidationError(Exception):
    pass
'''


def test_extractor_initialization(extractor):
    assert extractor is not None
    assert extractor.skill_patterns is not None


def test_detect_lazy_initialization(extractor, sample_code_with_caching, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text(sample_code_with_caching)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'lazy-initialization' in analysis.advanced_skills
    assert any(e.skill == 'lazy-initialization' for e in analysis.evidence)


def test_detect_set_optimization(extractor, sample_code_with_set_optimization, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text(sample_code_with_set_optimization)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'algorithmic-optimization' in analysis.advanced_skills
    assert analysis.complexity_insights.get('set_deduplication', 0) > 0


def test_detect_type_hints(extractor, sample_code_with_type_hints, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text(sample_code_with_type_hints)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'static-type-checking' in analysis.advanced_skills


def test_detect_custom_exceptions(extractor, sample_code_with_exception, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text(sample_code_with_exception)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'custom-exception-hierarchy' in analysis.design_patterns


def test_syntax_error_handling(extractor, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def broken(:\n    pass")
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'syntax-error-detected' in analysis.basic_skills


def test_analyze_directory(extractor, tmp_path):
    (tmp_path / "file1.py").write_text("def test(): pass")
    (tmp_path / "file2.py").write_text("x = list(set([1,2,3]))")
    
    results = extractor.analyze_directory(tmp_path)
    
    assert len(results) == 2


def test_aggregate_skills(extractor, tmp_path):
    (tmp_path / "file1.py").write_text("x = list(set([1,2,3]))")
    (tmp_path / "file2.py").write_text("x = list(set([4,5,6]))")
    
    results = extractor.analyze_directory(tmp_path)
    aggregated = extractor.aggregate_skills(results)
    
    assert 'algorithmic-optimization' in aggregated['advanced_skills']
    assert aggregated['total_files_analyzed'] == 2


def test_evidence_structure(extractor, sample_code_with_caching, tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text(sample_code_with_caching)
    
    analysis = extractor.analyze_file(test_file)
    
    if analysis.evidence:
        evidence = analysis.evidence[0]
        assert hasattr(evidence, 'skill')
        assert hasattr(evidence, 'evidence_type')
        assert hasattr(evidence, 'location')
        assert hasattr(evidence, 'reasoning')


def test_dataclass_detection(extractor, tmp_path):
    code = '''
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
'''
    test_file = tmp_path / "test.py"
    test_file.write_text(code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'modern-python-features' in analysis.advanced_skills


def test_context_manager_detection(extractor, tmp_path):
    code = '''
with open('file.txt') as f:
    data = f.read()

with connection() as conn:
    conn.execute()
'''
    test_file = tmp_path / "test.py"
    test_file.write_text(code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'resource-management' in analysis.advanced_skills


def test_comprehension_detection(extractor, tmp_path):
    code = '''
squares = [x**2 for x in range(10)]
evens = [x for x in range(10) if x % 2 == 0]
names = {p.name for p in people}
mapping = {k: v for k, v in items}
'''
    test_file = tmp_path / "test.py"
    test_file.write_text(code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'pythonic-idioms' in analysis.advanced_skills


def test_graceful_degradation_detection(extractor, tmp_path):
    code = '''
try:
    result = risky_operation()
except Exception:
    result = fallback_value()
'''
    test_file = tmp_path / "test.py"
    test_file.write_text(code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'graceful-degradation' in analysis.advanced_skills


def test_cryptographic_hashing_detection(extractor, tmp_path):
    code = '''
import hashlib

def hash_file(content):
    return hashlib.sha256(content).hexdigest()
'''
    test_file = tmp_path / "test.py"
    test_file.write_text(code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'cryptographic-hashing' in analysis.advanced_skills


def test_java_language_detection(extractor, tmp_path):
    java_code = '''
public class Example {
    private List<String> items;
    
    public void process() {
        items.stream()
            .filter(x -> x.length() > 5)
            .collect(Collectors.toList());
    }
}
'''
    test_file = tmp_path / "Example.java"
    test_file.write_text(java_code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'java' in analysis.basic_skills
    assert any('java-' in skill for skill in analysis.advanced_skills)


def test_cpp_language_detection(extractor, tmp_path):
    cpp_code = '''
#include <memory>
#include <vector>

template<typename T>
class Container {
    std::unique_ptr<T> data;
    
    void move_data() {
        auto moved = std::move(data);
    }
};
'''
    test_file = tmp_path / "container.cpp"
    test_file.write_text(cpp_code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'cpp' in analysis.basic_skills
    assert any('cpp-' in skill for skill in analysis.advanced_skills)


def test_javascript_language_detection(extractor, tmp_path):
    js_code = '''
const processData = async (items) => {
    const {name, age} = person;
    const result = await Promise.all(items);
    return [...result, ...newItems];
};
'''
    test_file = tmp_path / "script.js"
    test_file.write_text(js_code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'javascript' in analysis.basic_skills
    assert any('javascript-' in skill for skill in analysis.advanced_skills)


def test_c_language_detection(extractor, tmp_path):
    c_code = '''
#include <stdlib.h>

typedef struct Node {
    int data;
    struct Node* next;
} Node;

Node* create_node(int value) {
    Node* node = (Node*)malloc(sizeof(Node));
    node->data = value;
    return node;
}
'''
    test_file = tmp_path / "linked_list.c"
    test_file.write_text(c_code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'c' in analysis.basic_skills


def test_hash_based_structures_detection(extractor, tmp_path):
    java_code = '''
import java.util.HashMap;

public class Cache {
    private HashMap<String, Object> cache = new HashMap<>();
}
'''
    test_file = tmp_path / "Cache.java"
    test_file.write_text(java_code)
    
    analysis = extractor.analyze_file(test_file)
    
    assert 'hash-based-structures' in analysis.advanced_skills


def test_multi_language_directory(extractor, tmp_path):
    (tmp_path / "script.py").write_text("def test(): pass")
    (tmp_path / "Main.java").write_text("public class Main {}")
    (tmp_path / "app.js").write_text("const x = 5;")
    
    results = extractor.analyze_directory(tmp_path)
    
    assert len(results) == 3
    languages = set()
    for analysis in results.values():
        languages.update(analysis.basic_skills)
    
    assert 'python' in languages
    assert 'java' in languages
    assert 'javascript' in languages


def test_category_map_exists():
    """Verify CATEGORY_MAP is defined and comprehensive"""
    from src.analyze.advanced_skill_extractor import CATEGORY_MAP
    
    assert len(CATEGORY_MAP) > 15
    assert 'lazy-initialization' in CATEGORY_MAP
    assert CATEGORY_MAP['lazy-initialization'] == 'architecture'


def test_skill_categorization(extractor, tmp_path):
    """Verify skills are correctly categorized"""
    code = """
from dataclasses import dataclass

@dataclass
class User:
    name: str

def optimize(items):
    return list(set(items))
"""
    file = tmp_path / "test.py"
    file.write_text(code)
    
    analysis = extractor.analyze_file(file)
    analysis.categorize_skills()
    
    # Check categories exist
    assert 'code-quality' in analysis.skill_categories
    assert 'performance' in analysis.skill_categories
    
    # Check skills are in correct categories
    assert 'modern-python-features' in analysis.skill_categories['code-quality']
    assert 'algorithmic-optimization' in analysis.skill_categories['performance']


def test_code_snippet_extraction(extractor):
    """Test the _extract_code_snippet method directly"""
    code = """line 1
line 2
line 3 TARGET
line 4
line 5"""
    
    snippet = extractor._extract_code_snippet(code, line_number=3, context_lines=1)
    
    # Should contain target line with marker
    assert "→   3 | line 3 TARGET" in snippet
    
    # Should contain context lines
    assert "2 | line 2" in snippet
    assert "4 | line 4" in snippet
    
    # Should NOT contain line 1 or 5 (outside context)
    assert "line 1" not in snippet
    assert "line 5" not in snippet


def test_evidence_has_code_snippets(extractor, tmp_path):
    """Verify evidence now contains actual code snippets (not just descriptions)"""
    code = """
def get_data(self):
    if self._cache is None:
        self._cache = load_data()
    return self._cache
"""
    file = tmp_path / "test.py"
    file.write_text(code)
    
    analysis = extractor.analyze_file(file)
    
    # Find lazy-initialization evidence
    lazy_evidence = [e for e in analysis.evidence if 'lazy' in e.skill]
    assert len(lazy_evidence) > 0
    
    # Check that location contains actual code with line numbers
    location = lazy_evidence[0].location
    assert "if self._cache is None" in location
    assert "|" in location  # Line number separator
    assert "→" in location  # Target line marker


def test_categorize_skills_method(extractor, tmp_path):
    """Test that categorize_skills() method works"""
    code = """
@dataclass
class User:
    name: str

def process():
    return list(set([1, 2, 3]))

try:
    risky_operation()
except Exception:
    fallback()
"""
    file = tmp_path / "test.py"
    file.write_text(code)
    
    analysis = extractor.analyze_file(file)
    
    # Categories should be available after analysis (ordering step)
    assert len(analysis.skill_categories) > 0
    
    # Check expected categories
    assert 'code-quality' in analysis.skill_categories
    assert 'performance' in analysis.skill_categories
    assert 'error-handling' in analysis.skill_categories
