"""Test coverage for exception handling in update_next_recurrence_due_dates."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src import main as main_module

client = TestClient(main_module.app)


class FakeDue:  # pylint: disable=too-few-public-methods
    """Mock due object for testing."""

    def __init__(self, due_dict):
        self._due_dict = due_dict

    def to_dict(self):
        """Return due dict."""
        return self._due_dict


class FakeTask:  # pylint: disable=too-few-public-methods
    """Mock task for testing."""

    def __init__(self, id_, content, due, labels=None):
        self.id = id_
        self.content = content
        self.due = due
        self.labels = labels or []


def test_update_next_recurrence_key_error(monkeypatch):
    """Test that KeyError is caught during next recurrence update.

    This covers lines 207-208 in src/core/processing.py where
    api.update_task raises KeyError.
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
    overdue_task = FakeTask("ov_key_err", "Overdue task", overdue_due)

    class FakeAPI:
        """Fake API that raises KeyError on update_task."""

        def __init__(self, token):
            self.token = token

        def get_tasks(self):
            """Return fake tasks."""
            return [[overdue_task]]

        def update_task(self, task_id, due_date, due_string):
            """Raise KeyError to trigger exception handling."""
            raise KeyError("Simulated KeyError")

    monkeypatch.setattr(main_module, "TodoistAPI", FakeAPI)

    # Categorize tasks so overdue_task is in overdue list
    def fake_categorize(tasks, now=None):  # pylint: disable=unused-argument
        return [
            {
                "id": t.id,
                "content": t.content,
                "due": t.due.to_dict(),
                "labels": t.labels,
            }
            for t in tasks
        ], []

    monkeypatch.setattr(main_module, "categorize_tasks", fake_categorize)

    response = client.get("/")
    # Expect 207 due to invalid ticket format
    assert response.status_code == 207
    data = response.json()
    assert data["status"] == "ok"


def test_update_next_recurrence_attribute_error(monkeypatch):
    """Test that AttributeError is caught during next recurrence update.

    This covers lines 207-208 in src/core/processing.py where
    api.update_task raises AttributeError.
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
    overdue_task = FakeTask("ov_attr_err", "Overdue task", overdue_due)

    class FakeAPI:
        """Fake API that raises AttributeError on update_task."""

        def __init__(self, token):
            self.token = token

        def get_tasks(self):
            """Return fake tasks."""
            return [[overdue_task]]

        def update_task(self, task_id, due_date, due_string):
            """Raise AttributeError to trigger exception handling."""
            raise AttributeError("Simulated AttributeError")

    monkeypatch.setattr(main_module, "TodoistAPI", FakeAPI)

    # Categorize tasks so overdue_task is in overdue list
    def fake_categorize(tasks, now=None):  # pylint: disable=unused-argument
        return [
            {
                "id": t.id,
                "content": t.content,
                "due": t.due.to_dict(),
                "labels": t.labels,
            }
            for t in tasks
        ], []

    monkeypatch.setattr(main_module, "categorize_tasks", fake_categorize)

    response = client.get("/")
    # Expect 207 due to invalid ticket format
    assert response.status_code == 207
    data = response.json()
    assert data["status"] == "ok"
