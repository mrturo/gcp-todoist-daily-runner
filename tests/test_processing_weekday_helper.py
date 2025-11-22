"""
Test explícito para _infer_next_weekday_recurrence cubriendo days_ahead == 0.
"""

from datetime import datetime

from src.core.processing import _infer_next_weekday_recurrence


def test_infer_next_weekday_recurrence_days_ahead_zero():
    """Test that days_ahead == 0 returns the next week (not same day)."""
    # due_dt: lunes 2026-01-05
    due_dt = datetime(2026, 1, 5)
    recur_str = "cada lun"
    # days_ahead == 0, debe devolver el lunes siguiente
    result = _infer_next_weekday_recurrence(due_dt, recur_str)
    assert result == "2026-01-12"
