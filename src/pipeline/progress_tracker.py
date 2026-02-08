"""
Progress tracking and cancellation support for pipeline operations.

Provides thread-safe progress tracking with callback notifications and
cancellation support for long-running analyses.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
import threading
import time


@dataclass
class ProgressState:
    """Immutable snapshot of analysis progress at a point in time."""
    
    total_files: int
    processed_files: int
    current_file: str
    stage: str  # 'initializing', 'parsing', 'categorizing', 'analyzing', 'complete', 'cancelled'
    should_cancel: bool = False
    current_project: str = ""
    start_time: float = field(default_factory=time.time)
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100.0
    
    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "current_file": self.current_file,
            "stage": self.stage,
            "percentage": self.percentage,
            "should_cancel": self.should_cancel,
            "current_project": self.current_project,
            "elapsed_seconds": self.elapsed_seconds,
        }


class ProgressTracker:
    """
    Thread-safe progress tracking with callback support.
    
    Allows monitoring of long-running pipeline operations and supports
    cancellation requests.
    
    Example:
        tracker = ProgressTracker()
        tracker.register_callback(lambda state: print(f"Progress: {state.percentage:.1f}%"))
        
        tracker.update(total_files=100, stage='analyzing')
        tracker.update(processed_files=50, current_file='example.py')
        
        if tracker.should_cancel():
            print("Cancellation requested!")
    """
    
    def __init__(self):
        """Initialize progress tracker with default state."""
        self._state = ProgressState(
            total_files=0,
            processed_files=0,
            current_file="",
            stage="initializing"
        )
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[ProgressState], None]] = []
    
    def update(self, **kwargs) -> None:
        """
        Update progress state with new values.
        
        Thread-safe update that notifies all registered callbacks.
        
        Args:
            **kwargs: Fields to update (total_files, processed_files, current_file, 
                     stage, current_project, etc.)
        """
        # Create state copy outside the lock
        with self._lock:
            # Create new state with updated values
            state_dict = {
                "total_files": self._state.total_files,
                "processed_files": self._state.processed_files,
                "current_file": self._state.current_file,
                "stage": self._state.stage,
                "should_cancel": self._state.should_cancel,
                "current_project": self._state.current_project,
                "start_time": self._state.start_time,
            }
            
            # Update with new values
            state_dict.update(kwargs)
            
            # Create new immutable state
            self._state = ProgressState(**state_dict)
            
            # Create copy for callbacks while we still have the lock
            state_copy = ProgressState(**state_dict)
            
            # Get callbacks copy
            callbacks_copy = self._callbacks.copy()
        
        # Call callbacks outside of lock to avoid deadlock
        self._notify_callbacks_direct(state_copy, callbacks_copy)
    
    def increment_processed(self, current_file: str = "") -> None:
        """
        Increment processed file count by 1.
        
        Convenience method for the common case of processing one file.
        
        Args:
            current_file: Optional name of the file just processed
        """
        with self._lock:
            new_count = self._state.processed_files + 1
            kwargs = {"processed_files": new_count}
            if current_file:
                kwargs["current_file"] = current_file
        
        self.update(**kwargs)
    
    def register_callback(self, callback: Callable[[ProgressState], None]) -> None:
        """
        Register a callback to be notified on progress updates.
        
        Callbacks are invoked with a ProgressState snapshot on each update.
        Callbacks should be fast and non-blocking.
        
        Args:
            callback: Function that accepts a ProgressState parameter
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ProgressState], None]) -> bool:
        """
        Remove a previously registered callback.
        
        Args:
            callback: The callback function to remove
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False
    
    def request_cancel(self) -> None:
        """
        Request cancellation of the current operation.
        
        Sets the should_cancel flag. The pipeline must check this flag
        and handle cancellation appropriately.
        """
        self.update(should_cancel=True)
    
    def should_cancel(self) -> bool:
        """
        Check if cancellation has been requested.
        
        Returns:
            True if cancellation was requested, False otherwise
        """
        with self._lock:
            return self._state.should_cancel
    
    def get_state(self) -> ProgressState:
        """
        Get an immutable snapshot of the current progress state.
        
        Returns:
            ProgressState: Current state snapshot
        """
        with self._lock:
            # Return a copy of the current state
            return ProgressState(
                total_files=self._state.total_files,
                processed_files=self._state.processed_files,
                current_file=self._state.current_file,
                stage=self._state.stage,
                should_cancel=self._state.should_cancel,
                current_project=self._state.current_project,
                start_time=self._state.start_time,
            )
    
    def reset(self) -> None:
        """
        Reset progress tracker to initial state.
        
        Useful when reusing a tracker for multiple operations.
        Preserves registered callbacks.
        """
        with self._lock:
            self._state = ProgressState(
                total_files=0,
                processed_files=0,
                current_file="",
                stage="initializing"
            )
    
    def _notify_callbacks(self, state: ProgressState) -> None:
        """
        Notify all registered callbacks with current state.
        
        Args:
            state: ProgressState to pass to callbacks
        """
        # Make a copy of callbacks to avoid issues if callbacks modify the list
        with self._lock:
            callbacks_copy = self._callbacks.copy()
        
        self._notify_callbacks_direct(state, callbacks_copy)
    
    def _notify_callbacks_direct(self, state: ProgressState, callbacks: list) -> None:
        """
        Notify callbacks without acquiring lock (lock must already be released).
        
        Args:
            state: ProgressState to pass to callbacks
            callbacks: List of callback functions
        """
        for callback in callbacks:
            try:
                callback(state)
            except Exception:
                # Silently ignore callback errors to prevent one bad callback
                # from breaking the entire tracking system
                pass
