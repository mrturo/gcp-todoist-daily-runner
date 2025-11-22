"""Tests for duplicate title.parts.id detection in `src.main`.

These tests exercise internal behavior and therefore disable some pylint
rules that are not useful for lightweight test helpers.
"""

# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,
# pylint: disable=too-few-public-methods

from datetime import datetime, timedelta

from src import main as main_module
from tests.conftest import make_test_client


def test_title_duplicated_id_marked(monkeypatch):
    """If two tasks across overdue/today/future share the same title.parts.id,
    both should have `title.duplicated_id` set to True in the response."""
    # Prepare two tasks: one overdue (yesterday), one today; same ticket id
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    class FakeDueDate:
        def __init__(self, date_str):
            self._d = date_str

        def to_dict(self):
            return {"date": self._d}

    class FakeTask:
        def __init__(self, id_, content, due=None):
            self.id = id_
            self.content = content
            self.due = due

    # Both contents include the same ticket id (A01-01-01)
    content = "🔥 (A01-01-01) 🔖 Duplicate title"

    overdue_task = FakeTask("t1", content, FakeDueDate(str(yesterday)))
    today_task = FakeTask("t2", content, FakeDueDate(str(today)))

    class FakeAPI:
        def __init__(self, token):
            pass

        def get_tasks(self):
            # return as a single page paginator
            return [[overdue_task, today_task]]

    _, data = make_test_client(monkeypatch, main_module, FakeAPI)

    all_tasks = data["overdue_tasks"] + data["today_tasks"] + data["future_tasks"]
    # Find tasks with that id and assert duplicated_id True
    # Note: IDs are now stored without parentheses in parts.id
    dup_flags = [
        t["title"].get("duplicated_id")
        for t in all_tasks
        if (t.get("title", {}).get("parts") or {}).get("id") == "A01-01-01"
    ]
    assert dup_flags, "No tasks with the expected ticket id found"
    assert all(dup_flags), "Expected duplicated_id True for all tasks with same id"
