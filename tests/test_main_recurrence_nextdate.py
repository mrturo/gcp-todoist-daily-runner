"""
Test for next_recurring_date shortcut coverage in categorize_tasks (src/main.py).
"""

from datetime import datetime

from src.main import categorize_tasks
from tests.test_util import FakeTask


def test_next_recurring_date_shortcut():
    """Test that next_recurring_date shortcut is used if present.

    Uses Spanish recurrence pattern 'cada sáb' (every Saturday) from Todoist.
    """
    due = {
        "date": "2025-11-21",
        "string": "cada sáb",  # Spanish: every Saturday
        "recurring": True,
        "next_recurring_date": "2025-12-01",
    }
    task = FakeTask("r10", "Shortcut next date", due)
    _, not_overdue = categorize_tasks([task], now=datetime(2025, 11, 21, 12, 0, 0))
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-12-01"
