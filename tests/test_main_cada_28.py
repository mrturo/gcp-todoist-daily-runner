"""
Test para frecuencia 'cada 28' (día 28 de cada mes).
"""

from src.core.processing import _process_due_obj
from tests.test_utils import FakeDue


def test_cada_28_next_recurrence():
    """Test next recurrence calculation for 'cada 28' and similar frequencies."""
    # Caso: hoy es 2026-01-25, frecuencia: cada 28
    due = FakeDue(
        {
            "date": "2026-01-25",
            "lang": "es",
            "is_recurring": True,
            "timezone": None,
            "next_recurrence_date": None,
            "frequency": "cada 28",
        }
    )
    result = _process_due_obj(due)
    # Debe calcular el 2026-01-28 (mismo mes, aún no pasó)
    assert result["next_recurrence_date"] == "2026-01-28"

    # Caso: hoy es 2026-01-29, frecuencia: cada 28
    due2 = FakeDue(
        {
            "date": "2026-01-29",
            "lang": "es",
            "is_recurring": True,
            "timezone": None,
            "next_recurrence_date": None,
            "frequency": "cada 28",
        }
    )
    result2 = _process_due_obj(due2)
    # Debe calcular el 2026-02-28 (mes siguiente)
    assert result2["next_recurrence_date"] == "2026-02-28"

    # Caso: hoy es 2026-01-31, frecuencia: cada 30 (mes siguiente no tiene 30, debe dar último día)
    due3 = FakeDue(
        {
            "date": "2026-01-31",
            "lang": "es",
            "is_recurring": True,
            "timezone": None,
            "next_recurrence_date": None,
            "frequency": "cada 30",
        }
    )
    result3 = _process_due_obj(due3)
    # Febrero 2026 tiene 28 días
    assert result3["next_recurrence_date"] == "2026-02-28"
