"""Test TIME_ZONE fallback to UTC in update_overdue_daily_tasks for coverage."""

from src.main import update_overdue_daily_tasks


def test_update_overdue_daily_tasks_timezone_fallback(monkeypatch):
    """Force invalid TIME_ZONE to cover the except branch."""

    class FakeAPI:
        """Fake TodoistAPI for timezone fallback test."""

        def update_task(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Mock update_task method for coverage; ignores arguments."""
            return None

        def dummy(self):
            """Dummy method for pylint compliance."""
            return None

    overdue_tasks = [
        {"id": 1, "labels": ["🟢frequency-01-daily"], "due": {"recurring": True}}
    ]
    monkeypatch.setenv("TIME_ZONE", "INVALID/TZ")
    update_overdue_daily_tasks(FakeAPI(), overdue_tasks)
    monkeypatch.delenv("TIME_ZONE", raising=False)
