"""
Test para cubrir la rama days_ahead == 0 en 'cada <weekday>' (línea defensiva).
"""

from src.core.processing import infer_next_recurrence


def test_infer_next_recurrence_weekday_anywhere_same_day():
    """Cubre el caso donde days_ahead == 0 en el cálculo de próximo weekday (mismo día)."""
    # due_date: lunes 2026-01-05
    due_date = "2026-01-05"  # lunes
    # recur_str: "cada lun" (mismo día de la semana)
    recur_str = "cada lun"
    due_dict = {"date": due_date, "string": recur_str}
    result = infer_next_recurrence(due_dict)
    # Debe devolver el lunes siguiente: 2026-01-12
    assert result == "2026-01-12"
