"""Tests for issue_tasks collection in the response."""

from datetime import datetime

import src.main as main_module
from src.main import _collect_issue_tasks
from tests.conftest import make_test_client


def test_issue_tasks_included_in_response(monkeypatch):
    """Test that issue_tasks is included in the response."""
    today = datetime.now().date()

    class FakeDueDate:  # pylint: disable=missing-class-docstring,too-few-public-methods
        def __init__(self, date_str):
            self._d = date_str

        def to_dict(self):
            """Convert to dict representation."""
            return {"date": self._d, "is_recurring": False}

    class FakeTask:  # pylint: disable=missing-class-docstring,too-few-public-methods
        def __init__(self, id_, content, due=None):
            self.id = id_
            self.content = content
            self.due = due

    # Task with duplicated ID
    task1 = FakeTask("task1", "🟢(A01-01-00)📌First Task", FakeDueDate(str(today)))
    task2 = FakeTask("task2", "🟢(A01-01-00)📌Second Task", FakeDueDate(str(today)))

    class FakeAPI:  # pylint: disable=missing-class-docstring,too-few-public-methods
        def __init__(self, token):
            pass

        def get_tasks(self):
            """Return fake tasks."""
            return [[task1, task2]]

    _, data = make_test_client(monkeypatch, main_module, FakeAPI)

    # Check that issue_tasks is present
    assert "issue_tasks" in data
    assert isinstance(data["issue_tasks"], list)

    # Both tasks should have duplicated_id issue
    issue_ids = [issue["task_id"] for issue in data["issue_tasks"]]
    assert "task1" in issue_ids
    assert "task2" in issue_ids

    # Check that the issue is correctly identified
    for issue in data["issue_tasks"]:
        assert "issues" in issue
        assert "duplicated ticket id" in issue["issues"]


def test_issue_tasks_with_multiple_problems():
    """Test that a task with multiple problems lists all issues."""
    tasks = [
        {
            "id": "task1",
            "title": {
                "is_complete": False,
                "duplicated_id": True,
                "sequential_id": False,
            },
            "frequency_labels": {
                "frequency_matches_label": False,
                "has_non_frequency": False,
            },
        }
    ]

    issue_tasks = _collect_issue_tasks([tasks])

    assert len(issue_tasks) == 1
    assert issue_tasks[0]["task_id"] == "task1"
    assert len(issue_tasks[0]["issues"]) == 5
    assert "title is incomplete" in issue_tasks[0]["issues"]
    assert "duplicated ticket id" in issue_tasks[0]["issues"]
    assert "non-sequential ticket id" in issue_tasks[0]["issues"]
    assert "frequency emoji does not match label" in issue_tasks[0]["issues"]
    assert "missing non-frequency label" in issue_tasks[0]["issues"]


def test_issue_tasks_with_no_problems():
    """Test that tasks with no problems are not included."""
    tasks = [
        {
            "id": "task1",
            "title": {
                "is_complete": True,
                "duplicated_id": False,
                "sequential_id": True,
            },
            "frequency_labels": {
                "frequency_matches_label": True,
                "has_non_frequency": True,
            },
        }
    ]

    issue_tasks = _collect_issue_tasks([tasks])

    assert len(issue_tasks) == 0


def test_issue_tasks_with_partial_problems():
    """Test that only specific issues are reported."""

    tasks = [
        {
            "id": "task1",
            "title": {
                "is_complete": True,
                "duplicated_id": True,  # Only this is a problem
                "sequential_id": True,
            },
            "frequency_labels": {
                "frequency_matches_label": True,
                "has_non_frequency": True,
            },
        }
    ]

    issue_tasks = _collect_issue_tasks([tasks])

    assert len(issue_tasks) == 1
    assert issue_tasks[0]["task_id"] == "task1"
    assert len(issue_tasks[0]["issues"]) == 1
    assert "duplicated ticket id" in issue_tasks[0]["issues"]
