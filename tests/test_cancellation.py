"""
Tests for cancellation feature in pipeline and API.
"""
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.insights.api import register_tracker, unregister_tracker, get_tracker, _cleanup_cancelled
from src.pipeline.progress_tracker import ProgressTracker
from src.insights import ProjectInsightsStore


class TestTrackerRegistry:
    """Test the global tracker registry."""
    
    def test_register_and_get_tracker(self):
        """Test registering and retrieving a tracker."""
        tracker = ProgressTracker()
        zip_hash = "test_hash_123"
        
        register_tracker(zip_hash, tracker)
        retrieved = get_tracker(zip_hash)
        
        assert retrieved is tracker
        
        # Cleanup
        unregister_tracker(zip_hash)
    
    def test_get_nonexistent_tracker(self):
        """Test retrieving a tracker that doesn't exist."""
        result = get_tracker("nonexistent_hash")
        assert result is None
    
    def test_unregister_tracker(self):
        """Test unregistering a tracker."""
        tracker = ProgressTracker()
        zip_hash = "test_hash_456"
        
        register_tracker(zip_hash, tracker)
        assert get_tracker(zip_hash) is tracker
        
        unregister_tracker(zip_hash)
        assert get_tracker(zip_hash) is None
    
    def test_thread_safety(self):
        """Test that registry operations are thread-safe."""
        tracker1 = ProgressTracker()
        tracker2 = ProgressTracker()
        errors = []
        
        def register_operation(zip_hash, tracker):
            try:
                register_tracker(zip_hash, tracker)
                time.sleep(0.01)
                unregister_tracker(zip_hash)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=register_operation, args=("hash1", tracker1)),
            threading.Thread(target=register_operation, args=("hash2", tracker2)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestCancellationCleanup:
    """Test cleanup functionality when cancellation occurs."""
    
    def test_cleanup_cancelled_deletes_records(self):
        """Test that cleanup deletes database records."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            store = ProjectInsightsStore(db_path=db_path, encryption_key=b"test_key")
            
            # Create a pipeline result payload
            pipeline_result = {
                "zip_metadata": {
                    "root_name": "test.zip",
                    "file_count": 5,
                    "total_uncompressed_bytes": 1000,
                    "total_compressed_bytes": 500,
                },
                "projects": {
                    "test_project": {
                        "project_name": "test_project",
                        "categorized_contents": {"code": ["test.py"]}
                    }
                }
            }
            
            # Record pipeline run
            stats = store.record_pipeline_run(
                zip_path="/tmp/test.zip",
                pipeline_result=pipeline_result
            )
            assert stats.inserted == 1
            
            # Get the zip hash
            import hashlib
            hasher = hashlib.sha256()
            hasher.update(b"test.zip")
            hasher.update(b"5")
            hasher.update(b"1000")
            hasher.update(b"500")
            zip_hash = hasher.hexdigest()
            
            # Verify data exists
            projects = store.list_projects_for_zip(zip_hash)
            assert len(projects) >= 1
            
            # Run cleanup
            _cleanup_cancelled(zip_hash, store)
            
            # Verify data is deleted
            projects = store.list_projects_for_zip(zip_hash)
            assert len(projects) == 0
            
        finally:
            # Cleanup test database
            Path(db_path).unlink(missing_ok=True)
    
    def test_cleanup_unregisters_tracker(self):
        """Test that cleanup unregisters the tracker."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            store = ProjectInsightsStore(db_path=db_path)
            zip_hash = "test_unregister_hash"
            tracker = ProgressTracker()
            
            # Register tracker
            register_tracker(zip_hash, tracker)
            assert get_tracker(zip_hash) is tracker
            
            # Run cleanup
            _cleanup_cancelled(zip_hash, store)
            
            # Verify tracker is unregistered
            assert get_tracker(zip_hash) is None
            
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestCancellationIntegration:
    """Test cancellation flow through progress tracker."""
    
    def test_tracker_cancellation_flow(self):
        """Test the full cancellation flow with tracker."""
        tracker = ProgressTracker()
        zip_hash = "test_flow_hash"
        
        # Register tracker
        register_tracker(zip_hash, tracker)
        
        # Initially should_cancel is False
        assert tracker.should_cancel() is False
        
        # Request cancellation
        tracker.request_cancel()
        
        # Now should_cancel is True
        assert tracker.should_cancel() is True
        
        # Check state
        state = tracker.get_state()
        assert state.should_cancel is True
        
        # Cleanup
        unregister_tracker(zip_hash)
    
    def test_pipeline_respects_cancellation(self):
        """Test that pipeline checks cancellation flag."""
        tracker = ProgressTracker()
        
        # Simulate pipeline checking for cancellation
        tracker.update(stage='parsing', total_files=100)
        assert tracker.should_cancel() is False
        
        # User requests cancellation
        tracker.request_cancel()
        
        # Pipeline should detect it
        assert tracker.should_cancel() is True
        
        # Update to cancelled stage
        tracker.update(stage='cancelled')
        state = tracker.get_state()
        assert state.stage == 'cancelled'
