"""
Test para el caso real: frecuencia 'every! 6 days' debe calcular next_recurrence_date correctamente.
"""

from src.core.processing import _process_due_obj
from tests.test_utils import FakeDue


def test_every_exclam_6_days_next_recurrence():
    """Test that 'every! 6 days' calculates next_recurrence_date correctly."""
    # Fecha base: 2026-01-20, frecuencia: every! 6 days
    due = FakeDue(
        {
            "date": "2026-01-20",
            "lang": "en",
            "is_recurring": True,
            "timezone": None,
            "next_recurrence_date": None,
            "frequency": "every! 6 days",
        }
    )
    result = _process_due_obj(due)
    # Debe calcular correctamente la próxima recurrencia: 2026-01-26
    assert (
        result["next_recurrence_date"] == "2026-01-26"
    ), f"next_recurrence_date incorrecto: {result['next_recurrence_date']}"
