"""
Tests for file analysis caching functionality.

This test suite verifies that file analysis results are properly cached
in the database, indexed by SHA256 hash, to avoid redundant analysis of
duplicate files in future pipeline runs.
"""

import tempfile
import pytest
from pathlib import Path

from src.insights.storage import ProjectInsightsStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    store = ProjectInsightsStore(db_path=db_path)
    yield store
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_code_analysis():
    """Sample code analysis result."""
    return {
        "file_path": "/tmp/test.py",
        "language": "Python",
        "lines_of_code": 150,
        "comment_density": 0.15,
        "complexity_score": 8.5,
        "imports": ["os", "sys", "json"],
        "functions": ["main", "process_data", "validate_input"]
    }


@pytest.fixture
def sample_text_analysis():
    """Sample text/documentation analysis result."""
    return {
        "file_path": "/tmp/README.md",
        "word_count": 350,
        "reading_time_minutes": 2.5,
        "sections": ["Introduction", "Installation", "Usage"],
        "has_code_blocks": True
    }


@pytest.fixture
def sample_image_analysis():
    """Sample image analysis result."""
    return {
        "file_path": "/tmp/screenshot.png",
        "width": 1920,
        "height": 1080,
        "format": "PNG",
        "has_transparency": False,
        "dominant_colors": ["#FF0000", "#00FF00", "#0000FF"]
    }


@pytest.fixture
def sample_video_analysis():
    """Sample video analysis result."""
    return {
        "file_path": "/tmp/demo.mp4",
        "duration_seconds": 120,
        "resolution": "1920x1080",
        "fps": 30,
        "codec": "h264"
    }


def test_cache_code_analysis(temp_db, sample_code_analysis):
    """Test caching code analysis results."""
    sha256 = "abc123" * 10 + "abc123"  # 64 chars
    
    # Cache the analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Retrieve the cached analysis
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert cached["language"] == "Python"
    assert cached["lines_of_code"] == 150
    assert cached["functions"] == ["main", "process_data", "validate_input"]


def test_cache_text_analysis(temp_db, sample_text_analysis):
    """Test caching text/documentation analysis results."""
    sha256 = "def456" * 10 + "def456"
    
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='text',
        analysis_result=sample_text_analysis,
        file_ext='.md'
    )
    
    cached = temp_db.get_cached_file_analysis(sha256, 'text')
    
    assert cached is not None
    assert cached["word_count"] == 350
    assert cached["sections"] == ["Introduction", "Installation", "Usage"]


def test_cache_image_analysis(temp_db, sample_image_analysis):
    """Test caching image analysis results."""
    sha256 = "789ghi" * 10 + "789ghi"
    
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='image',
        analysis_result=sample_image_analysis,
        file_ext='.png'
    )
    
    cached = temp_db.get_cached_file_analysis(sha256, 'image')
    
    assert cached is not None
    assert cached["width"] == 1920
    assert cached["height"] == 1080
    assert cached["format"] == "PNG"


def test_cache_video_analysis(temp_db, sample_video_analysis):
    """Test caching video analysis results."""
    sha256 = "jkl012" * 10 + "jkl012"
    
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='video',
        analysis_result=sample_video_analysis,
        file_ext='.mp4'
    )
    
    cached = temp_db.get_cached_file_analysis(sha256, 'video')
    
    assert cached is not None
    assert cached["duration_seconds"] == 120
    assert cached["resolution"] == "1920x1080"


def test_cache_miss(temp_db):
    """Test retrieving non-existent cached analysis returns None."""
    sha256 = "nonexistent" * 5 + "hash"
    
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is None


def test_cache_update(temp_db, sample_code_analysis):
    """Test updating an existing cache entry."""
    sha256 = "update123" * 10 + "upd"
    
    # Cache initial analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Update with new analysis
    updated_analysis = sample_code_analysis.copy()
    updated_analysis["lines_of_code"] = 200
    updated_analysis["complexity_score"] = 12.0
    
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=updated_analysis,
        file_ext='.py'
    )
    
    # Retrieve and verify update
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached["lines_of_code"] == 200
    assert cached["complexity_score"] == 12.0


def test_separate_caches_per_analysis_type(temp_db, sample_code_analysis, sample_text_analysis):
    """Test that the same file hash can have different cached analyses per type."""
    sha256 = "multi123" * 10 + "mul"
    
    # Cache code analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Cache text analysis for same hash (different interpretation)
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='text',
        analysis_result=sample_text_analysis,
        file_ext='.md'
    )
    
    # Retrieve both
    code_cached = temp_db.get_cached_file_analysis(sha256, 'code')
    text_cached = temp_db.get_cached_file_analysis(sha256, 'text')
    
    assert code_cached is not None
    assert text_cached is not None
    assert code_cached["language"] == "Python"
    assert text_cached["word_count"] == 350


def test_invalid_analysis_type_cache(temp_db, sample_code_analysis):
    """Test that invalid analysis types raise ValueError."""
    sha256 = "invalid123" * 10 + "inv"
    
    with pytest.raises(ValueError, match="Invalid analysis_type"):
        temp_db.cache_file_analysis(
            sha256=sha256,
            analysis_type='invalid_type',
            analysis_result=sample_code_analysis,
            file_ext='.py'
        )


def test_invalid_analysis_type_retrieve(temp_db):
    """Test that invalid analysis types raise ValueError on retrieval."""
    sha256 = "retrieve123" * 10 + "ret"
    
    with pytest.raises(ValueError, match="Invalid analysis_type"):
        temp_db.get_cached_file_analysis(sha256, 'invalid_type')


def test_access_count_increments(temp_db, sample_code_analysis):
    """Test that access_count increments on each retrieval."""
    sha256 = "access123" * 10 + "acc"
    
    # Cache the analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Retrieve multiple times
    temp_db.get_cached_file_analysis(sha256, 'code')
    temp_db.get_cached_file_analysis(sha256, 'code')
    temp_db.get_cached_file_analysis(sha256, 'code')
    
    # Check database directly
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row = conn.execute(
            f"SELECT access_count FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ? AND analysis_type = ?",
            (sha256, 'code')
        ).fetchone()
        
        assert row is not None
        assert row[0] == 3  # Should have been accessed 3 times


def test_encryption_of_cached_data(temp_db, sample_code_analysis):
    """Test that cached analysis results are encrypted in the database."""
    sha256 = "encrypt123" * 10 + "enc"
    
    # Cache the analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Check that the raw database entry is encrypted (not plain JSON)
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row = conn.execute(
            f"SELECT analysis_result FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ? AND analysis_type = ?",
            (sha256, 'code')
        ).fetchone()
        
        assert row is not None
        encrypted_blob = row[0]
        
        # Verify it's binary data, not plain text
        assert isinstance(encrypted_blob, bytes)
        # Should not contain plain text JSON markers
        assert b'"language"' not in encrypted_blob
        assert b'Python' not in encrypted_blob


def test_cache_without_file_extension(temp_db, sample_code_analysis):
    """Test caching works without providing file extension."""
    sha256 = "noext123" * 10 + "noe"
    
    # Cache without file_ext
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis
    )
    
    # Should still retrieve successfully
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert cached["language"] == "Python"


def test_complex_nested_analysis_result(temp_db):
    """Test caching complex nested analysis results."""
    sha256 = "complex123" * 10 + "com"
    
    complex_analysis = {
        "file_path": "/tmp/complex.py",
        "metadata": {
            "author": "test",
            "version": "1.0",
            "dependencies": ["numpy", "pandas"]
        },
        "analysis": {
            "functions": [
                {"name": "func1", "complexity": 5, "lines": 20},
                {"name": "func2", "complexity": 8, "lines": 35}
            ],
            "classes": [
                {
                    "name": "MyClass",
                    "methods": ["__init__", "process", "validate"]
                }
            ]
        },
        "metrics": {
            "quality_score": 8.5,
            "maintainability": "good",
            "test_coverage": 85.5
        }
    }
    
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=complex_analysis,
        file_ext='.py'
    )
    
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert cached["metadata"]["dependencies"] == ["numpy", "pandas"]
    assert len(cached["analysis"]["functions"]) == 2
    assert cached["analysis"]["classes"][0]["methods"] == ["__init__", "process", "validate"]
    assert cached["metrics"]["test_coverage"] == 85.5


def test_cache_reuse_workflow(temp_db, sample_code_analysis):
    """Test complete workflow: cache, retrieve multiple times, verify access tracking."""
    sha256 = "workflow123" * 10 + "wor"
    
    # Step 1: Cache the analysis
    temp_db.cache_file_analysis(
        sha256=sha256,
        analysis_type='code',
        analysis_result=sample_code_analysis,
        file_ext='.py'
    )
    
    # Step 2: Retrieve multiple times (simulating duplicate file detection)
    for i in range(5):
        cached = temp_db.get_cached_file_analysis(sha256, 'code')
        assert cached is not None
        assert cached["language"] == "Python"
    
    # Step 3: Verify access count
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row = conn.execute(
            f"SELECT access_count FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256,)
        ).fetchone()
        assert row[0] == 5


def test_duplicate_file_detection_simulation(temp_db, sample_code_analysis):
    """Simulate duplicate file detection across multiple pipeline runs."""
    sha256_file1 = "file1hash" * 10 + "file"
    sha256_file2 = "file2hash" * 10 + "file"
    sha256_duplicate = "file1hash" * 10 + "file"  # Same as file1
    
    # First run: Analyze file1 and file2
    temp_db.cache_file_analysis(sha256_file1, 'code', sample_code_analysis, '.py')
    temp_db.cache_file_analysis(sha256_file2, 'code', sample_code_analysis, '.py')
    
    # Second run: Encounter duplicate of file1
    cached = temp_db.get_cached_file_analysis(sha256_duplicate, 'code')
    assert cached is not None
    assert cached["language"] == "Python"
    
    # Verify file2 wasn't accessed
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row1 = conn.execute(
            f"SELECT access_count FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256_file1,)
        ).fetchone()
        row2 = conn.execute(
            f"SELECT access_count FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256_file2,)
        ).fetchone()
        
        assert row1[0] == 1  # file1 was accessed (cache hit)
        assert row2[0] == 0  # file2 was not accessed


def test_cache_performance_benefit(temp_db, sample_code_analysis):
    """Test that cache provides performance benefit by avoiding re-analysis."""
    sha256 = "perf123" * 10 + "per"
    
    # Simulate expensive analysis (first time)
    temp_db.cache_file_analysis(sha256, 'code', sample_code_analysis, '.py')
    
    # Simulate cache hit (second time) - should be instant
    import time
    start = time.time()
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    duration = time.time() - start
    
    assert cached is not None
    assert duration < 0.1  # Should be very fast (< 100ms)


def test_multiple_analysis_types_same_file(temp_db, sample_code_analysis, sample_text_analysis):
    """Test caching different analysis types for the same file hash."""
    sha256 = "polyglot123" * 10 + "pol"
    
    # Cache both code and text analysis for same hash
    # (e.g., a .py file that could be analyzed as code or text)
    temp_db.cache_file_analysis(sha256, 'code', sample_code_analysis, '.py')
    temp_db.cache_file_analysis(sha256, 'text', sample_text_analysis, '.py')
    
    # Retrieve both
    code_cached = temp_db.get_cached_file_analysis(sha256, 'code')
    text_cached = temp_db.get_cached_file_analysis(sha256, 'text')
    
    assert code_cached["language"] == "Python"
    assert text_cached["word_count"] == 350


def test_cache_with_empty_result(temp_db):
    """Test caching empty or minimal analysis results."""
    sha256 = "empty123" * 10 + "emp"
    
    empty_analysis = {
        "file_path": "/tmp/empty.py",
        "lines_of_code": 0,
        "error": "File is empty"
    }
    
    temp_db.cache_file_analysis(sha256, 'code', empty_analysis, '.py')
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert cached["lines_of_code"] == 0
    assert cached["error"] == "File is empty"


def test_last_accessed_timestamp_updates(temp_db, sample_code_analysis):
    """Test that last_accessed timestamp updates on each retrieval."""
    sha256 = "timestamp123" * 10 + "tim"
    
    # Cache analysis
    temp_db.cache_file_analysis(sha256, 'code', sample_code_analysis, '.py')
    
    # Get initial timestamp
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row1 = conn.execute(
            f"SELECT last_accessed FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256,)
        ).fetchone()
        first_access = row1[0]
    
    # Wait a moment and retrieve again
    import time
    time.sleep(0.1)
    temp_db.get_cached_file_analysis(sha256, 'code')
    
    # Check timestamp was updated
    with temp_db._connect() as conn:
        row2 = conn.execute(
            f"SELECT last_accessed FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256,)
        ).fetchone()
        second_access = row2[0]
    
    assert second_access > first_access


def test_cache_statistics_query(temp_db, sample_code_analysis, sample_text_analysis, sample_image_analysis):
    """Test querying cache statistics."""
    # Cache multiple files
    for i in range(10):
        sha = f"code{i}" + "x" * (64 - len(f"code{i}"))
        temp_db.cache_file_analysis(sha, 'code', sample_code_analysis, '.py')
    
    for i in range(5):
        sha = f"text{i}" + "x" * (64 - len(f"text{i}"))
        temp_db.cache_file_analysis(sha, 'text', sample_text_analysis, '.md')
    
    for i in range(3):
        sha = f"img{i}" + "x" * (64 - len(f"img{i}"))
        temp_db.cache_file_analysis(sha, 'image', sample_image_analysis, '.png')
    
    # Query statistics
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        
        # Total cached files
        total = conn.execute(f"SELECT COUNT(*) FROM {FILE_ANALYSIS_CACHE_TABLE}").fetchone()[0]
        assert total == 18
        
        # Count by type
        stats = conn.execute(
            f"SELECT analysis_type, COUNT(*) FROM {FILE_ANALYSIS_CACHE_TABLE} GROUP BY analysis_type"
        ).fetchall()
        
        stats_dict = {row[0]: row[1] for row in stats}
        assert stats_dict['code'] == 10
        assert stats_dict['text'] == 5
        assert stats_dict['image'] == 3


def test_cache_survives_restart(temp_db, sample_code_analysis):
    """Test that cached data persists after closing and reopening database."""
    sha256 = "persist123" * 10 + "per"
    db_path = temp_db.db_path
    
    # Cache data
    temp_db.cache_file_analysis(sha256, 'code', sample_code_analysis, '.py')
    
    # Close database (simulate restart)
    del temp_db
    
    # Reopen database
    from src.insights.storage import ProjectInsightsStore
    new_store = ProjectInsightsStore(db_path=db_path)
    
    # Retrieve cached data
    cached = new_store.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert cached["language"] == "Python"
    assert cached["lines_of_code"] == 150


def test_large_analysis_result_caching(temp_db):
    """Test caching very large analysis results."""
    sha256 = "large123" * 10 + "lar"
    
    # Create large analysis result
    large_analysis = {
        "file_path": "/tmp/large.py",
        "functions": [
            {"name": f"func_{i}", "complexity": i % 20, "lines": i * 10}
            for i in range(1000)
        ],
        "imports": [f"module_{i}" for i in range(500)],
        "classes": [
            {"name": f"Class_{i}", "methods": [f"method_{j}" for j in range(50)]}
            for i in range(100)
        ]
    }
    
    # Cache and retrieve
    temp_db.cache_file_analysis(sha256, 'code', large_analysis, '.py')
    cached = temp_db.get_cached_file_analysis(sha256, 'code')
    
    assert cached is not None
    assert len(cached["functions"]) == 1000
    assert len(cached["imports"]) == 500
    assert len(cached["classes"]) == 100


def test_concurrent_cache_access(temp_db, sample_code_analysis):
    """Test thread-safety of cache operations."""
    import threading
    
    sha256 = "thread123" * 10 + "thr"
    errors = []
    
    def cache_operation():
        try:
            temp_db.cache_file_analysis(sha256, 'code', sample_code_analysis, '.py')
            cached = temp_db.get_cached_file_analysis(sha256, 'code')
            assert cached is not None
        except Exception as e:
            errors.append(e)
    
    # Run multiple threads concurrently
    threads = [threading.Thread(target=cache_operation) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should have no errors due to locking
    assert len(errors) == 0
    
    # Verify final access count
    with temp_db._connect() as conn:
        from src.insights.storage import FILE_ANALYSIS_CACHE_TABLE
        row = conn.execute(
            f"SELECT access_count FROM {FILE_ANALYSIS_CACHE_TABLE} WHERE sha256 = ?",
            (sha256,)
        ).fetchone()
        # Access count should be >= 10 (one per thread retrieval)
        assert row[0] >= 10
