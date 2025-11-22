"""
Test para cubrir el bucle y el break en la rama 'cada N semanas <weekday>' de infer_next_recurrence.
"""

from src.core.processing import infer_next_recurrence


def test_infer_next_recurrence_cada_n_semanas_weekday_break():
    """Test that 'cada N semanas <weekday>' finds the correct next weekday."""
    # due_date: lunes 5 de enero de 2026
    due_date = "2026-01-05"  # lunes
    # Queremos "cada 2 semanas mar" (martes)
    # El candidato será lunes 19, el primer martes después es 20
    recur_str = "cada 2 semanas mar"
    due_dict = {"date": due_date, "string": recur_str}
    result = infer_next_recurrence(due_dict)
    # El próximo martes después de lunes 19 es martes 20
    assert result == "2026-01-20"
