"""
Cubre else del except ValueError en _recur_cada_n: primer replace falla, segundo funciona.
"""

from datetime import datetime

from src.core.processing import _recur_cada_n


def test_recur_cada_n_except_valueerror_else_success(monkeypatch):
    """Cubre el else del except ValueError en _recur_cada_n."""
    recur_str = "cada 28"

    class DummyDate(datetime):
        """Subclase de datetime para simular ValueError en replace la primera vez."""

        def __new__(cls, *args, **kwargs):
            return datetime.__new__(cls, *args, **kwargs)

        def __init__(self, *_, **__):
            self._fail_next = True

        def replace(self, *_, **kwargs):
            if getattr(self, "_fail_next", False):
                self._fail_next = False
                raise ValueError("day is out of range")
            day = kwargs.get("day", self.day)
            return datetime(self.year, self.month, day)

    dummy_dt = DummyDate(2026, 2, 1)
    monkeypatch.setattr("calendar.monthrange", lambda y, m: (0, 28))
    result = _recur_cada_n(recur_str, dummy_dt)
    assert result == "2026-02-28"
