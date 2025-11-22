"""
Unit tests for recurrence logic in categorize_tasks (src/main.py) to reach 100% coverage.
"""

from datetime import datetime

from src.main import categorize_tasks
from tests.test_util import FakeTask


def test_next_recurrence_weekday():
    """Test next_recurrence_date for 'cada sáb' (Spanish: every Saturday) pattern.

    Todoist returns recurrence strings in the user's language.
    This tests Spanish-language pattern support.
    """
    due = {"date": "2025-11-21", "string": "cada sáb", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r1", "Cada sab", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-11-22"


def test_next_recurrence_month():
    """Test next_recurrence_date for 'cada mes' (Spanish: every month) pattern.

    Todoist returns recurrence strings in the user's language.
    This tests Spanish-language pattern support.
    """
    due = {"date": "2025-11-21", "string": "cada mes", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r2", "Cada mes", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-12-21"


def test_next_recurrence_day():
    """Test next_recurrence_date for 'cada día' (Spanish: every day) pattern.

    Todoist returns recurrence strings in the user's language.
    This tests Spanish-language pattern support.
    """
    due = {"date": "2025-11-21", "string": "cada día", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r3", "Cada dia", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-11-22"


def test_next_recurrence_week():
    """Test next_recurrence_date for 'cada semana' (Spanish: every week) pattern.

    Todoist returns recurrence strings in the user's language.
    This tests Spanish-language pattern support.
    """
    due = {"date": "2025-11-21", "string": "cada semana", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r4", "Cada semana", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-11-28"


def test_next_recurrence_english():
    """Test next_recurrence_date for 'every fri' pattern."""
    due = {"date": "2025-11-21", "string": "every fri", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r5", "Every fri", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] == "2025-11-28"


def test_next_recurrence_invalid_date():
    """Test next_recurrence_date for invalid date string.

    Uses Spanish pattern 'cada sáb' (every Saturday) with invalid date.
    """
    due = {"date": "not-a-date", "string": "cada sáb", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r6", "Invalid date", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] is None


def test_next_recurrence_unknown_pattern():
    """Test next_recurrence_date for unknown recurrence pattern.

    Uses Spanish pattern 'cada quincena' (every two weeks) which is not supported.
    """
    due = {"date": "2025-11-21", "string": "cada quincena", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r7", "Unknown pattern", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] is None


def test_next_recurrence_missing_date():
    """Test next_recurrence_date for missing date field.

    Uses Spanish pattern 'cada sáb' (every Saturday) without date field.
    """
    due = {"string": "cada sáb", "recurring": True}
    _, not_overdue = categorize_tasks(
        [FakeTask("r8", "Missing date", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert not_overdue[0]["due"]["next_recurrence_date"] is None


def test_next_recurrence_not_recurring():
    """Test that next_recurrence_date is not set if not recurring.

    Uses Spanish pattern 'cada sáb' (every Saturday) but recurring=False.
    """
    due = {"date": "2025-11-21", "string": "cada sáb"}
    _, not_overdue = categorize_tasks(
        [FakeTask("r9", "Not recurring", due)], now=datetime(2025, 11, 21, 12, 0, 0)
    )
    assert "next_recurrence_date" not in not_overdue[0]["due"]
