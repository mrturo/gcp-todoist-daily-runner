"""Tests for small helper functions in src.main."""

from datetime import datetime, timedelta

from src.main import _split_not_overdue_tasks, build_title_object, get_timezone


def test_build_title_object_with_parts_and_matching_content():
    """Build title object when parts are provided and content matches combined."""
    parts = {
        "freq": "🟢",
        "id": "A01-01-00",
        "ticket_emoji": "📌",
        "text": "DoThing",
    }
    title_is_valid = True
    # Content should have parentheses around the ID
    content = "🟢(A01-01-00)📌DoThing"
    obj = build_title_object(parts, title_is_valid, content)
    assert obj["is_complete"] is True
    assert "combined" in obj and obj["combined"] == content
    # Current implementation sets `to_replace` when content differs from combined,
    # so when content == combined it should be False.
    assert obj["to_replace"] is False
    assert obj["parts"] is parts


def test_build_title_object_with_no_parts():
    """Ensure build_title_object handles None parts and returns sensible defaults."""
    parts = None
    title_is_valid = False
    content = "random"
    obj = build_title_object(parts, title_is_valid, content)
    assert obj["is_complete"] is False
    assert "combined" not in obj
    assert obj["to_replace"] is False
    assert obj["parts"] is None


def test_split_not_overdue_tasks_detects_today_and_future():
    """_split_not_overdue_tasks should classify date-only and datetime due correctly."""
    tz = get_timezone()
    now = datetime.now(tz)
    today_date = now.date()

    # date-only equal to today -> goes to today_tasks
    t1 = {"id": "t1", "due": {"date": today_date.isoformat()}}
    # datetime string without tz equal to today -> should be treated as today (tz added)
    dt_str = now.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    t2 = {"id": "t2", "due": {"date": dt_str}}
    # future date-only -> goes to future_tasks
    future_date = (today_date + timedelta(days=1)).isoformat()
    t3 = {"id": "t3", "due": {"date": future_date}}

    today_tasks, future_tasks = _split_not_overdue_tasks([t1, t2, t3], tz)
    assert any(t["id"] == "t1" for t in today_tasks)
    assert any(t["id"] == "t2" for t in today_tasks)
    assert any(t["id"] == "t3" for t in future_tasks)
