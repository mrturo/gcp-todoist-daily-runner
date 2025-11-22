"""Tests to cover due-object normalization helper in src.main."""

from src.main import _process_due_obj


class EmptyDue:  # pylint: disable=too-few-public-methods
    """Test double representing an empty due object (returns empty dict)."""

    def to_dict(self):
        """Return an empty due dict."""
        return {}


class RecurringDue:  # pylint: disable=too-few-public-methods
    """Test double for a recurring due object."""

    def __init__(self, date_str):
        """Initialize with a date string and recurring metadata."""
        self._d = {"date": date_str, "string": "every day", "recurring": True}

    def to_dict(self):
        """Return the due dict copy."""
        return dict(self._d)


def test_process_due_obj_none_and_empty():
    """_process_due_obj returns None for None or empty due dicts."""
    assert _process_due_obj(None) is None
    assert _process_due_obj(EmptyDue()) is None


def test_process_due_obj_recurring_sets_next_and_removes_string():
    """Recurring due objects get next_recurrence_date and have `string` removed."""
    d = RecurringDue("2023-01-01")
    out = _process_due_obj(d)
    assert isinstance(out, dict)
    assert "next_recurrence_date" in out
    assert "frequency" in out
    assert "string" not in out
