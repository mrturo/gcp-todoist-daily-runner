"""
Test categorize_tasks exception branches for 100% coverage.
"""

from datetime import datetime, timezone

from src.main import categorize_tasks


class FakeTask:
    """Fake task with a due object that will raise ValueError or TypeError."""

    def __init__(self, id_, content, due_dict, labels):
        """Initialize FakeTask with id, content, due_dict, and labels."""
        self.id = id_
        self.content = content
        self.due = self
        self.labels = labels
        self._due_dict = due_dict

    def to_dict(self):
        """Return the due dict for this fake task."""
        return self._due_dict

    def dummy(self):
        """Dummy public method for pylint compliance."""
        return None


def test_categorize_tasks_value_error():
    """Test categorize_tasks handles ValueError when due date is not a valid isoformat string."""
    tasks = [FakeTask("1", "bad date", {"date": "not-a-date"}, ["label"])]
    fixed_now = datetime(2025, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    overdue, not_overdue = categorize_tasks(tasks, now=fixed_now)
    if len(overdue) != 0:
        raise AssertionError(f"Expected 0 overdue, got {len(overdue)}")
    if len(not_overdue) != 1:
        raise AssertionError(f"Expected 1 not_overdue, got {len(not_overdue)}")
    if not_overdue[0]["id"] != "1":
        raise AssertionError(f"Expected id '1', got {not_overdue[0]['id']}")


def test_categorize_tasks_type_error():
    """Test categorize_tasks handles TypeError when due date is None."""
    tasks = [FakeTask("2", "none date", {"date": None}, ["label"])]
    fixed_now = datetime(2025, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    overdue, not_overdue = categorize_tasks(tasks, now=fixed_now)
    if len(overdue) != 0:
        raise AssertionError(f"Expected 0 overdue, got {len(overdue)}")
    if len(not_overdue) != 1:
        raise AssertionError(f"Expected 1 not_overdue, got {len(not_overdue)}")
    if not_overdue[0]["id"] != "2":
        raise AssertionError(f"Expected id '2', got {not_overdue[0]['id']}")
