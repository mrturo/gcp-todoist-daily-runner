"""
Test for is_task_overdue with missing due_dict["date"] to cover the return False branch.
"""

from datetime import datetime, timezone

from src.main import is_task_overdue


def test_is_task_overdue_missing_date():
    """Test is_task_overdue returns False if due_dict has no 'date' key.

    Uses Spanish recurrence pattern 'cada sáb' (every Saturday) from Todoist.
    """
    tz = timezone.utc
    now = datetime(2025, 11, 21, 12, 0, 0, tzinfo=tz)
    due_dict = {"string": "cada sáb"}  # No 'date' key (Spanish: every Saturday)
    assert is_task_overdue(due_dict, now, tz) is False


def test_is_task_overdue_none_due_dict():
    """Test is_task_overdue returns False if due_dict is None."""
    tz = timezone.utc
    now = datetime(2025, 11, 21, 12, 0, 0, tzinfo=tz)
    assert is_task_overdue(None, now, tz) is False
