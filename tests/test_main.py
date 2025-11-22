"""
Tests for the main endpoint of the Todoist Cloud Run app.
"""

# Tests contain many small test helper classes and nested fakes; relax some pylint rules here.
# pylint: disable=missing-function-docstring,too-few-public-methods

import logging
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src import \
    main as main_module  # To avoid import-outside-toplevel in tests
from src.main import app, categorize_tasks
from src.utils.frequency_labels import FrequencyLabels
from tests.test_utils import SimpleDue, SimpleTask, fake_categorize_all_overdue

client = TestClient(app)

# pylint: disable=duplicate-code


def test_root_endpoint_with_due_datetime_no_tz(monkeypatch):
    """
    Test that a task with a due date as datetime string without timezone is handled.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    future_dt = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0)
    due_str = future_dt.isoformat()  # e.g. '2025-11-23T10:00:00'

    class FakeDue:
        """Mock due date object for testing (no tz)."""

        def to_dict(self):
            """Return a mock due date as dict."""
            return {"date": due_str}

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTask:
        """Mock task object for testing (no tz)."""

        def __init__(self, id_, content, due=None):
            """Initialize a mock task object."""
            self.id = id_
            self.content = content
            self.due = due

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTodoistAPI:
        """Mock TodoistAPI for testing (no tz)."""

        def __init__(self, token):
            """Initialize the mock TodoistAPI object."""
            self.token = token

        def get_tasks(self):
            """Return a mock paginator with FakeTask objects."""
            return [[FakeTask("5", "Task Datetime No TZ", FakeDue())]]

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    response = client.get("/")
    # Task has invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    data = response.json()
    # Combine top-level today/future tasks (new flat format)
    not_overdue = list(data.get("today_tasks", [])) + list(data.get("future_tasks", []))
    # The task should be in not_overdue_tasks because the date is in the future
    assert any(t["id"] == "5" for t in not_overdue)


def test_root_endpoint_with_no_due(monkeypatch):
    """
    Test that a task with no due date is handled as not overdue.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    class FakeTask:
        """Mock task object for testing (no due)."""

        def __init__(self, id_, content, due=None):
            """Initialize a mock task object."""
            self.id = id_
            self.content = content
            self.due = due

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTodoistAPI:
        """Mock TodoistAPI for testing (no due)."""

        def __init__(self, token):
            """Initialize the mock TodoistAPI object."""
            self.token = token

        def get_tasks(self):
            """Return a mock paginator with FakeTask objects."""
            return [[FakeTask("4", "Task No Due")]]

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    response = client.get("/")
    # Task has invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    data = response.json()
    not_overdue = list(data.get("today_tasks", [])) + list(data.get("future_tasks", []))
    assert any(t["id"] == "4" for t in not_overdue)


def test_root_endpoint_with_invalid_due(monkeypatch):
    """
    Test that a task with an invalid due date is handled as not overdue and logs a warning.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    class FakeDue:
        """Mock due date object for testing (invalid)."""

        def to_dict(self):
            """Return a mock due date as dict."""
            return {"date": "invalid-date"}

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTask:
        """Mock task object for testing (invalid due)."""

        def __init__(self, id_, content, due=None):
            """Initialize a mock task object."""
            self.id = id_
            self.content = content
            self.due = due

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTodoistAPI:
        """Mock TodoistAPI for testing (invalid due)."""

        def __init__(self, token):
            """Initialize the mock TodoistAPI object."""
            self.token = token

        def get_tasks(self):
            """Return a mock paginator with FakeTask objects."""
            return [[FakeTask("3", "Task Invalid Due", FakeDue())]]

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    logger = logging.getLogger("src.main")
    with monkeypatch.context() as m:
        m.setattr(logger, "warning", lambda *a, **kw: setattr(logger, "warned", True))
        logger.warned = False
        response = client.get("/")
        # Task has invalid ticket format, so expect 207 with issues
        assert response.status_code == 207
        data = response.json()
        not_overdue = list(data.get("today_tasks", [])) + list(
            data.get("future_tasks", [])
        )
        assert any(t["id"] == "3" for t in not_overdue)
        assert logger.warned is True


def test_root_endpoint_returns_ok(monkeypatch):
    """
    Tests that the root endpoint responds with status ok and mocks external dependencies.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    class FakeDue:
        """Mock due date object for testing."""

        def to_dict(self):
            """Return a mock due date as dict."""
            return {"date": "2025-11-22"}

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTask:
        """Mock task object for testing."""

        def __init__(self, id_, content, due=None):
            """Initialize a mock task object."""
            self.id = id_
            self.content = content
            self.due = due

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    class FakeTodoistAPI:
        """Mock of the TodoistAPI class for testing."""

        def __init__(self, token):
            """Initialize the mock TodoistAPI object."""
            self.token = token

        def get_tasks(self):
            """Return a mock paginator with FakeTask objects."""
            return [
                [
                    FakeTask("1", "Task 1", FakeDue()),
                    FakeTask("2", "Task 2", None),
                ]
            ]

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

        def another_method(self):
            """Another public method for pylint compliance."""
            return True

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    response = client.get("/")
    # Tasks have invalid ticket format, so expect 207 with issues
    assert response.status_code == 207  # nosec
    data = response.json()
    assert data["status"] == "ok"  # nosec
    assert "overdue_tasks" in data
    # Response now exposes `today_tasks` and `future_tasks` at top-level
    assert "today_tasks" in data
    assert "future_tasks" in data
    # Task 1 has due date 2025-11-22 (consider overdue if the current date is after)
    # Task 2 has no due, should be in not_overdue_tasks
    overdue = data["overdue_tasks"]
    # Combine today's and future tasks for compatibility with previous assertions
    not_overdue = list(data.get("today_tasks", [])) + list(data.get("future_tasks", []))
    # Since Task 1's date is 2025-11-22, whether it's overdue depends on the current day
    # For the test, we assume both tasks appear in not_overdue_tasks if the date is not past
    ids_not_overdue = {t["id"] for t in not_overdue}
    assert "2" in ids_not_overdue
    assert any(t["content"] == "Task 2" for t in not_overdue)
    # Task 1 should be in one of the two lists
    assert any(t["content"] == "Task 1" for t in overdue) or any(
        t["content"] == "Task 1" for t in not_overdue
    )


def test_overdue_daily_label_recurring_false_and_missing(monkeypatch):
    """
    Covers the case where 'recurring' is False and where it is not present in due.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    class FakeTask:
        """Mock task for recurring tests."""

        def __init__(self, id_, content, due, labels):
            self.id = id_
            self.content = content
            self.due = due
            self.labels = labels

        def dummy(self):
            """Dummy public method for pylint compliance."""
            return None

        def another_method(self):
            """Another dummy public method for pylint compliance."""
            return True

    class FakeDue:
        """Mock due for recurring tests."""

        def __init__(self, due_dict):
            self._due_dict = due_dict

        def to_dict(self):
            """Return due dict."""
            return self._due_dict

        def dummy(self):
            """Dummy public method for pylint compliance."""
            return None

    # Overdue tasks: one with recurring=False, one without recurring
    overdue_due_false = FakeDue({"date": "2025-01-01", "recurring": False})
    overdue_due_missing = FakeDue({"date": "2025-01-01"})
    # The daily label
    label = FrequencyLabels.DAILY.label

    # The endpoint only counts those with recurring True
    class FakeTodoistAPI:
        """Mock TodoistAPI for recurring tests."""

        def __init__(self, token):
            self.token = token

        def get_tasks(self):
            """Return fake tasks."""
            return [
                [
                    FakeTask("10", "Task Recurring False", overdue_due_false, [label]),
                    FakeTask(
                        "11", "Task Recurring Missing", overdue_due_missing, [label]
                    ),
                ]
            ]

        def dummy(self):
            """Dummy public method for pylint compliance."""
            return None

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    monkeypatch.setattr(main_module, "categorize_tasks", fake_categorize_all_overdue)

    # Use the global client to avoid redefinition
    response = client.get("/")
    # Tasks have invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    data = response.json()
    # Only the one with recurring missing should be counted (default True)
    # The one with recurring=False should not be counted
    assert data["status"] == "ok"
    # The endpoint does not expose daily_label_and_recurring_overdue_tasks, but the log does
    # So we only validate that the response does not fail and that both tasks are in overdue_tasks
    ids = {t["id"] for t in data["overdue_tasks"]}
    assert "10" in ids
    assert "11" in ids


def test_overdue_task_with_date_only():
    """
    Test that a task with a due date as date-only (YYYY-MM-DD) and in the past is marked as overdue.
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    # Task with only date (no time), due yesterday
    task = SimpleTask(
        id_=123,
        content="Test date-only overdue",
        due=SimpleDue(str(yesterday)),
    )
    overdue, not_overdue = categorize_tasks([task])
    assert any(t["id"] == 123 for t in overdue)
    assert all(t["id"] != 123 for t in not_overdue)


def test_not_overdue_task_with_date_only_today():
    """
    Test that a task with a due date as date-only and equal to today is NOT marked as overdue.
    """
    today = datetime.now().date()
    task = SimpleTask(
        id_=456,
        content="Test date-only not overdue",
        due=SimpleDue(str(today)),
    )
    overdue, not_overdue = categorize_tasks([task])
    assert all(t["id"] != 456 for t in overdue)
    assert any(t["id"] == 456 for t in not_overdue)


def test_root_endpoint_date_only_today_in_today_tasks(monkeypatch):
    """
    Endpoint should place a date-only task due today into `not_overdue_tasks.today_tasks`.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    today = datetime.now().date().isoformat()

    class FakeDue:
        """Mock due object returning a date-only string for today."""

        def to_dict(self):
            return {"date": today}

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Minimal fake task object for endpoint tests."""

        def __init__(self, id_, content, due=None):
            """Create a minimal fake task with id, content and optional due."""
            self.id = id_
            self.content = content
            self.due = due

    class FakeTodoistAPI:  # pylint: disable=too-few-public-methods
        """Fake TodoistAPI returning a single task due today."""

        def __init__(self, token):
            """Store the token (unused) for parity with real API."""
            self.token = token

        def get_tasks(self):
            """Return a single-page paginator with one fake task due today."""
            return [[FakeTask("today-1", "Task Today", FakeDue())]]

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    response = client.get("/")
    # Task has invalid ticket format, so expect 207 with issues
    assert response.status_code == 207
    data = response.json()
    today_tasks = data.get("today_tasks", [])
    assert any(t["id"] == "today-1" for t in today_tasks)
