"""
Cobertura final para ramas no cubiertas en src/core/processing.py (líneas 228-234, 270-280, 488).
"""

from src.core import processing


def test_infer_next_recurrence_cada_n_mes_febrero():
    """Cubre el caso donde el mes siguiente no tiene ese día (ej: 31 de enero + 1 mes)."""
    due_dict = {"date": "2025-01-31", "string": "cada 31"}
    # Febrero 2025 tiene 28 días, debe devolver 2025-02-28
    assert processing.infer_next_recurrence(due_dict) == "2025-02-28"


def test_infer_next_recurrence_nth_weekday_no_nth_found():
    """Cubre el caso donde no se encuentra el n-ésimo día de la semana en el mes siguiente."""
    due_dict = {
        "date": "2025-01-01",
        "string": "cada 6o lun",
    }  # Solo hay 4-5 lunes por mes
    assert processing.infer_next_recurrence(due_dict) is None


def test_infer_next_recurrence_weekday_anywhere_no_pattern():
    """Cubre el else final del bloque 'cada <weekday>' en cualquier parte (no hay patrón)."""
    due_dict = {"date": "2025-01-01", "string": "sin patron de dia"}
    assert processing.infer_next_recurrence(due_dict) is None


def test__process_due_obj_is_recurring_false():
    # pylint: disable=protected-access
    """Cubre el caso donde is_recurring es False."""

    class Dummy:
        """Dummy para simular to_dict con recurring False."""

        def to_dict(self):
            """Return a dict with recurring False and a date."""
            return {"recurring": False, "date": "2025-01-01"}

        def dummy_public(self):
            """Dummy public method for pylint compliance."""
            return True

    result = processing._process_due_obj(Dummy())
    assert result["recurring"] is False and "next_recurrence_date" not in result
