# pylint: disable=duplicate-code
"""
Test for coverage of ValueError/TypeError in next_recurrence_date parsing
(src/main.py lines 137-138).
"""

# pylint: disable=too-few-public-methods

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src import main as main_module
from src.main import app
from tests.test_utils import (FakeAPI, FakeDue, FakeTask,
                              fake_categorize_tasks_factory)

client = TestClient(app)


def test_next_recurrence_date_parse_error(monkeypatch):
    """
    Test that a task with an invalid next_recurrence_date triggers the except block and continue.
    Covers lines 137-138 in src/main.py.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    overdue_due = FakeDue(
        {
            "date": str(yesterday),
            "string": "every day",
            "recurring": True,
            "next_recurrence_date": "not-a-date",
        }
    )
    overdue_task = FakeTask("ov2", "Overdue recurring invalid next_recur", overdue_due)
    not_overdue_due = FakeDue(
        {
            "date": str(today + timedelta(days=1)),
            "string": "every day",
            "recurring": True,
            "next_recurrence_date": str(today + timedelta(days=1)),
        }
    )
    not_overdue_task = FakeTask("nv2", "Not overdue recurring", not_overdue_due)
    # pylint: enable=too-few-public-methods

    api = FakeAPI("fake-token", overdue_task, not_overdue_task)
    monkeypatch.setattr(main_module, "TodoistAPI", lambda token: api)
    monkeypatch.setattr(
        main_module, "categorize_tasks", fake_categorize_tasks_factory("ov2", "nv2")
    )

    response = client.get("/")
    # Tasks have invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    # The invalid next_recurrence_date should not trigger an update
    assert not api.updated
