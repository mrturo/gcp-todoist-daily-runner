"""
Cobertura específica para el bloque except ValueError en _recur_cada_n.
"""

from datetime import datetime

from src.core.processing import _recur_cada_n


def test_recur_cada_n_except_valueerror(monkeypatch):
    """Test except ValueError branch in _recur_cada_n (day out of range)."""
    # Fuerza ValueError en dt.replace(day=dia)
    recur_str = "cada 31"

    def fake_replace(day):
        """Raise ValueError for out-of-range day."""
        raise ValueError("day is out of range")

    class DummyDate(datetime):
        """Dummy datetime subclass to override replace for test coverage."""

        # pylint: disable=too-many-arguments,too-many-positional-arguments
        def replace(
            self,
            year=None,
            month=None,
            day=None,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
            *,
            fold=0
        ):
            """Override replace to raise ValueError when day is out of range."""
            return fake_replace(day)

        # pylint: enable=too-many-arguments,too-many-positional-arguments

    dummy_dt = DummyDate(2026, 2, 1)

    # Parchea monthrange para devolver 28 días
    monkeypatch.setattr("calendar.monthrange", lambda y, m: (0, 28))

    # Parchea _date_str para forzar el ValueError
    result = _recur_cada_n(recur_str, dummy_dt)
    # Debe devolver el último día del mes (2026-02-28)
    assert result == "2026-02-28"
