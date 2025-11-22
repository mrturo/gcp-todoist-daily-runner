"""
Cubre el bucle, el if y el break en la rama 'cada Nº <weekday>' de infer_next_recurrence.
"""

from src.core.processing import infer_next_recurrence


def test_infer_next_recurrence_nth_weekday_break():
    """Test that infer_next_recurrence finds the Nth weekday in next month."""
    # due_date: 2026-01-01 (miércoles)
    due_date = "2026-01-01"
    # Queremos el 3er viernes del mes siguiente (febrero 2026)
    recur_str = "cada 3 vie"  # 3er viernes
    due_dict = {"date": due_date, "string": recur_str}
    result = infer_next_recurrence(due_dict)
    # Febrero 2026: viernes 6, 13, 20. El tercero es 20
    assert result == "2026-02-20"
