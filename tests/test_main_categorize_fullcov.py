"""
Tests for categorize_tasks to reach 100% coverage (overdue with datetime and date-only).
"""

from datetime import datetime, timezone

from src.main import categorize_tasks
from tests.test_util import FakeTask


def test_categorize_tasks_overdue_datetime():
    """Test overdue task with datetime (with time)."""
    past_dt = (datetime(2025, 11, 21, 10, 0, 0, tzinfo=timezone.utc)).isoformat()
    task = FakeTask("dt1", "Overdue datetime", {"date": past_dt}, [])
    now = datetime(2025, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    overdue, not_overdue = categorize_tasks([task], now=now)
    if len(overdue) != 1:
        raise AssertionError(f"Expected 1 overdue, got {len(overdue)}")
    if overdue[0]["id"] != "dt1":
        raise AssertionError(f"Expected id 'dt1', got {overdue[0]['id']}")
    if len(not_overdue) != 0:
        raise AssertionError(f"Expected 0 not_overdue, got {len(not_overdue)}")


def test_categorize_tasks_overdue_dateonly():
    """Test overdue task with date-only (no time)."""
    past_date = "2025-11-21"
    task = FakeTask("d1", "Overdue dateonly", {"date": past_date}, [])
    now = datetime(2025, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    overdue, not_overdue = categorize_tasks([task], now=now)
    if len(overdue) != 1:
        raise AssertionError(f"Expected 1 overdue, got {len(overdue)}")
    if overdue[0]["id"] != "d1":
        raise AssertionError(f"Expected id 'd1', got {overdue[0]['id']}")
    if len(not_overdue) != 0:
        raise AssertionError(f"Expected 0 not_overdue, got {len(not_overdue)}")
