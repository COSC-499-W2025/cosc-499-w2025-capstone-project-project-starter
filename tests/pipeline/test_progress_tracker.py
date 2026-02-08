"""
Comprehensive tests for progress tracking and cancellation functionality.
"""

import pytest
import threading
import time
from pathlib import Path

from src.pipeline.progress_tracker import ProgressState, ProgressTracker


class TestProgressState:
    """Test the ProgressState dataclass."""
    
    def test_percentage_calculation_empty(self):
        """Test percentage when no files."""
        state = ProgressState(
            total_files=0,
            processed_files=0,
            current_file="",
            stage="initializing"
        )
        assert state.percentage == 0.0
    
    def test_percentage_calculation_partial(self):
        """Test percentage calculation with partial progress."""
        state = ProgressState(
            total_files=100,
            processed_files=50,
            current_file="test.py",
            stage="analyzing"
        )
        assert state.percentage == 50.0
    
    def test_percentage_calculation_complete(self):
        """Test percentage when all files processed."""
        state = ProgressState(
            total_files=100,
            processed_files=100,
            current_file="last.py",
            stage="complete"
        )
        assert state.percentage == 100.0
    
    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        start_time = time.time() - 5.0  # 5 seconds ago
        state = ProgressState(
            total_files=10,
            processed_files=5,
            current_file="test.py",
            stage="analyzing",
            start_time=start_time
        )
        # Should be approximately 5 seconds (allow small margin)
        assert 4.9 < state.elapsed_seconds < 5.5
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = ProgressState(
            total_files=100,
            processed_files=25,
            current_file="example.py",
            stage="analyzing",
            should_cancel=False,
            current_project="test-project"
        )
        
        result = state.to_dict()
        
        assert result["total_files"] == 100
        assert result["processed_files"] == 25
        assert result["current_file"] == "example.py"
        assert result["stage"] == "analyzing"
        assert result["percentage"] == 25.0
        assert result["should_cancel"] is False
        assert result["current_project"] == "test-project"
        assert "elapsed_seconds" in result


class TestProgressTracker:
    """Test the ProgressTracker class."""
    
    def test_initialization(self):
        """Test tracker initializes with default state."""
        tracker = ProgressTracker()
        state = tracker.get_state()
        
        assert state.total_files == 0
        assert state.processed_files == 0
        assert state.current_file == ""
        assert state.stage == "initializing"
        assert state.should_cancel is False
    
    def test_update_single_field(self):
        """Test updating a single field."""
        tracker = ProgressTracker()
        tracker.update(total_files=100)
        
        state = tracker.get_state()
        assert state.total_files == 100
        assert state.processed_files == 0  # Other fields unchanged
    
    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        tracker = ProgressTracker()
        tracker.update(
            total_files=50,
            processed_files=10,
            current_file="test.py",
            stage="analyzing"
        )
        
        state = tracker.get_state()
        assert state.total_files == 50
        assert state.processed_files == 10
        assert state.current_file == "test.py"
        assert state.stage == "analyzing"
    
    def test_increment_processed(self):
        """Test convenience method for incrementing processed count."""
        tracker = ProgressTracker()
        tracker.update(total_files=10, processed_files=0)
        
        tracker.increment_processed("file1.py")
        state = tracker.get_state()
        assert state.processed_files == 1
        assert state.current_file == "file1.py"
        
        tracker.increment_processed("file2.py")
        state = tracker.get_state()
        assert state.processed_files == 2
        assert state.current_file == "file2.py"
    
    def test_increment_processed_without_filename(self):
        """Test incrementing without specifying current file."""
        tracker = ProgressTracker()
        tracker.update(total_files=5, processed_files=0, current_file="old.py")
        
        tracker.increment_processed()
        state = tracker.get_state()
        assert state.processed_files == 1
        assert state.current_file == "old.py"  # Unchanged
    
    def test_cancellation_request(self):
        """Test requesting cancellation."""
        tracker = ProgressTracker()
        
        assert not tracker.should_cancel()
        
        tracker.request_cancel()
        
        assert tracker.should_cancel()
        state = tracker.get_state()
        assert state.should_cancel is True
    
    def test_reset(self):
        """Test resetting tracker to initial state."""
        tracker = ProgressTracker()
        
        # Set some state
        tracker.update(
            total_files=100,
            processed_files=50,
            current_file="test.py",
            stage="analyzing"
        )
        tracker.request_cancel()
        
        # Reset
        tracker.reset()
        
        # Should be back to initial state
        state = tracker.get_state()
        assert state.total_files == 0
        assert state.processed_files == 0
        assert state.current_file == ""
        assert state.stage == "initializing"
        assert state.should_cancel is False
    
    def test_callback_registration(self):
        """Test registering and receiving callbacks."""
        tracker = ProgressTracker()
        received_states = []
        
        def callback(state: ProgressState):
            received_states.append(state)
        
        tracker.register_callback(callback)
        
        # Trigger updates
        tracker.update(total_files=10)
        tracker.update(processed_files=5)
        
        # Should have received 2 callbacks
        assert len(received_states) == 2
        assert received_states[0].total_files == 10
        assert received_states[1].processed_files == 5
    
    def test_multiple_callbacks(self):
        """Test multiple callbacks receive updates."""
        tracker = ProgressTracker()
        callback1_calls = []
        callback2_calls = []
        
        tracker.register_callback(lambda s: callback1_calls.append(s.processed_files))
        tracker.register_callback(lambda s: callback2_calls.append(s.processed_files))
        
        tracker.update(processed_files=10)
        tracker.update(processed_files=20)
        
        assert callback1_calls == [10, 20]
        assert callback2_calls == [10, 20]
    
    def test_callback_unregistration(self):
        """Test unregistering callbacks."""
        tracker = ProgressTracker()
        calls = []
        
        def callback(state: ProgressState):
            calls.append(state.processed_files)
        
        tracker.register_callback(callback)
        tracker.update(processed_files=1)
        
        # Unregister
        success = tracker.unregister_callback(callback)
        assert success is True
        
        tracker.update(processed_files=2)
        
        # Should only have received first callback
        assert calls == [1]
    
    def test_unregister_nonexistent_callback(self):
        """Test unregistering a callback that was never registered."""
        tracker = ProgressTracker()
        
        def callback(state: ProgressState):
            pass
        
        success = tracker.unregister_callback(callback)
        assert success is False
    
    def test_callback_exception_handling(self):
        """Test that callback exceptions don't break tracking."""
        tracker = ProgressTracker()
        good_calls = []
        
        def bad_callback(state: ProgressState):
            raise ValueError("Intentional error")
        
        def good_callback(state: ProgressState):
            good_calls.append(state.processed_files)
        
        tracker.register_callback(bad_callback)
        tracker.register_callback(good_callback)
        
        # This should not raise an exception despite bad_callback failing
        tracker.update(processed_files=5)
        
        # Good callback should still have been called
        assert good_calls == [5]
    
    def test_thread_safety_concurrent_updates(self):
        """Test thread safety with concurrent updates."""
        tracker = ProgressTracker()
        tracker.update(total_files=1000, processed_files=0)
        
        def worker():
            for _ in range(100):
                tracker.increment_processed()
        
        # Start 10 threads, each incrementing 100 times
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have processed 1000 files total
        state = tracker.get_state()
        assert state.processed_files == 1000
    
    def test_thread_safety_concurrent_reads(self):
        """Test thread safety with concurrent reads and writes."""
        tracker = ProgressTracker()
        tracker.update(total_files=100)
        errors = []
        
        def reader():
            try:
                for _ in range(50):
                    state = tracker.get_state()
                    # State should always be consistent
                    assert 0 <= state.processed_files <= state.total_files
                    time.sleep(0.001)  # Small delay
            except AssertionError as e:
                errors.append(e)
        
        def writer():
            for i in range(50):
                tracker.update(processed_files=i)
                time.sleep(0.001)
        
        # Run concurrent readers and writer
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]
        writer_thread = threading.Thread(target=writer)
        
        for t in reader_threads:
            t.start()
        writer_thread.start()
        
        for t in reader_threads:
            t.join()
        writer_thread.join()
        
        # No errors should have occurred
        assert len(errors) == 0
    
    def test_callback_thread_safety(self):
        """Test that callbacks are thread-safe."""
        tracker = ProgressTracker()
        callback_calls = []
        lock = threading.Lock()
        
        def callback(state: ProgressState):
            with lock:
                callback_calls.append(state.processed_files)
        
        tracker.register_callback(callback)
        
        def updater(value):
            tracker.update(processed_files=value)
        
        # Update from multiple threads
        threads = [threading.Thread(target=updater, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have received all callbacks
        assert len(callback_calls) == 10
        assert set(callback_calls) == set(range(10))


class TestProgressTrackerIntegration:
    """Integration tests with the pipeline."""
    
    def test_progress_tracking_stages(self):
        """Test that progress moves through expected stages."""
        tracker = ProgressTracker()
        stages = []
        
        def stage_tracker(state: ProgressState):
            stages.append(state.stage)
        
        tracker.register_callback(stage_tracker)
        
        # Simulate pipeline stages
        tracker.update(stage='parsing')
        tracker.update(stage='extracting')
        tracker.update(stage='categorizing')
        tracker.update(stage='analyzing')
        tracker.update(stage='compiling')
        tracker.update(stage='complete')
        
        assert stages == ['parsing', 'extracting', 'categorizing', 
                         'analyzing', 'compiling', 'complete']
    
    def test_cancellation_workflow(self):
        """Test typical cancellation workflow."""
        tracker = ProgressTracker()
        tracker.update(total_files=100, stage='analyzing')
        
        # Simulate processing files
        for i in range(10):
            if tracker.should_cancel():
                break
            tracker.increment_processed(f"file{i}.py")
        
        # Request cancellation
        tracker.request_cancel()
        
        # Continue processing (should stop due to cancellation check)
        for i in range(10, 20):
            if tracker.should_cancel():
                tracker.update(stage='cancelled')
                break
            tracker.increment_processed(f"file{i}.py")
        
        state = tracker.get_state()
        assert state.should_cancel is True
        assert state.stage == 'cancelled'
        assert state.processed_files == 10  # Only processed first 10
    
    def test_progress_percentage_calculation(self):
        """Test realistic progress percentage tracking."""
        tracker = ProgressTracker()
        percentages = []
        
        def track_percentage(state: ProgressState):
            percentages.append(state.percentage)
        
        tracker.register_callback(track_percentage)
        tracker.update(total_files=20)
        
        # Process 20 files
        for i in range(20):
            tracker.increment_processed()
        
        # Should have 20 percentage values (one per file)
        assert len(percentages) == 20
        # Last percentage should be 100%
        assert percentages[-1] == 100.0
        # Percentages should be increasing
        assert percentages == sorted(percentages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
