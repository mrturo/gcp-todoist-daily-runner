"""
Test for coverage of overdue recurring task update logic in run_todoist_integration (src/main.py).
"""

# pylint: disable=too-few-public-methods
# pylint: disable=duplicate-code

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src import main as main_module
from src.main import app
from tests.test_utils import (FakeAPI, FakeDue, FakeTask,
                              fake_categorize_tasks_factory)

client = TestClient(app)


def test_overdue_recurring_task_update(monkeypatch):
    """
    Test that overdue recurring tasks with next_recurrence_date <= today are updated.
    Covers lines 135-147, 155-156 in src/main.py.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    overdue_due = FakeDue(
        {
            "date": str(yesterday),
            "string": "every day",
            "recurring": True,
            "next_recurrence_date": str(yesterday),
        }
    )
    overdue_task = FakeTask("ov1", "Overdue recurring", overdue_due)
    not_overdue_due = FakeDue(
        {
            "date": str(today + timedelta(days=1)),
            "string": "every day",
            "recurring": True,
            "next_recurrence_date": str(today + timedelta(days=1)),
        }
    )
    not_overdue_task = FakeTask("nv1", "Not overdue recurring", not_overdue_due)
    # pylint: enable=too-few-public-methods

    api = FakeAPI("fake-token", overdue_task, not_overdue_task)
    monkeypatch.setattr(main_module, "TodoistAPI", lambda token: api)
    monkeypatch.setattr(
        main_module, "categorize_tasks", fake_categorize_tasks_factory("ov1", "nv1")
    )

    # First, test update success
    api.fail = False
    response = client.get("/")
    # Tasks have invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    assert ("ov1", today, "every day") in api.updated

    # Now, test update error path
    api.updated.clear()
    api.fail = True
    response = client.get("/")
    # Still expect 207 due to invalid ticket format
    assert response.status_code == 207
    # No update should be recorded due to error
    assert not api.updated
