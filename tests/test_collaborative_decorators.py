"""
Pytest tests for collaborative.decorators.requires_collaborative.

Covers:
- When collaborative permission is granted: wrapped function is executed
- When prefs is None: wrapper prints message and does NOT call function
- When collaborative flag is False: same行为 as no prefs
"""

import os
import sys
import pytest

# Add src directory to Python path (same pattern as other tests)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from collaborative.decorators import requires_collaborative


# Helpers
def make_callable_tracker():
    """
    Returns (tracker_dict, wrapped_func) where:
    - tracker_dict["called"] is set to True when func is executed
    - wrapped_func() returns a known value for assertions
    """
    tracker = {"called": False}

    @requires_collaborative
    def sample_func(x, y=0):
        tracker["called"] = True
        return x + y

    return tracker, sample_func

def test_requires_collaborative_allows_when_flag_true(monkeypatch, capfd):
    """
    If CollaborativeStorage.get_preferences() returns a truthy prefs
    with prefs[1] == True, the wrapped function should be executed.
    """

    def fake_get_prefs():
        return (True, True, None)

    monkeypatch.setattr(
        "collaborative.decorators.CollaborativeStorage.get_preferences",
        staticmethod(lambda: fake_get_prefs())
    )

    tracker, wrapped = make_callable_tracker()

    result = wrapped(2, y=3)  # 2 + 3 = 5

    out, _ = capfd.readouterr()
    assert "Collaborative permission required" not in out
    assert tracker["called"] is True
    assert result == 5


def test_requires_collaborative_blocks_when_prefs_none(monkeypatch, capfd):
    """
    If get_preferences() returns None, collaborative defaults to False,
    and the wrapped function should NOT be executed.
    """

    monkeypatch.setattr(
        "collaborative.decorators.CollaborativeStorage.get_preferences",
        staticmethod(lambda: None)
    )

    tracker, wrapped = make_callable_tracker()

    result = wrapped(1, y=2)

    out, _ = capfd.readouterr()
    assert "Collaborative permission required" in out
    assert tracker["called"] is False
    assert result is None  # wrapper returns None when blocked


def test_requires_collaborative_blocks_when_flag_false(monkeypatch, capfd):
    """
    If get_preferences() returns a prefs tuple with collaborative=False,
    the wrapped function should NOT be executed.
    """

    def fake_get_prefs():
        return (True, False, None)

    monkeypatch.setattr(
        "collaborative.decorators.CollaborativeStorage.get_preferences",
        staticmethod(lambda: fake_get_prefs())
    )

    tracker, wrapped = make_callable_tracker()

    result = wrapped(10, y=20)

    out, _ = capfd.readouterr()
    assert "Collaborative permission required" in out
    assert tracker["called"] is False
    assert result is None
