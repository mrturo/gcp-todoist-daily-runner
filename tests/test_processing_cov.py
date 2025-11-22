"""
Cobertura para ramas no cubiertas en src/core/processing.py (líneas 199-234, 241-280, 462-491).
"""

from datetime import datetime

from src.core import processing
from src.utils.frequency_labels import FrequencyLabels


def test_infer_next_recurrence_invalid_due_date():
    """Cubre ValueError y TypeError en datetime.fromisoformat."""
    due_dict = {"date": "not-a-date", "string": "cada 3 días"}
    assert processing.infer_next_recurrence(due_dict) is None
    due_dict = {"date": None, "string": "cada 3 días"}
    assert processing.infer_next_recurrence(due_dict) is None


def test_infer_next_recurrence_no_pattern_match():
    """Cubre el else final (ningún patrón reconocido)."""
    due_dict = {"date": "2025-01-01", "string": "patrón desconocido"}
    assert processing.infer_next_recurrence(due_dict) is None


def test_infer_next_recurrence_cada_n_semana_no_weekday():
    """Cubre el caso donde el weekday no es reconocido."""
    due_dict = {"date": "2025-01-01", "string": "cada 2 semanas xyz"}
    assert processing.infer_next_recurrence(due_dict) is None


def test_infer_next_recurrence_nth_weekday_no_match():
    """Cubre el caso donde el weekday no es reconocido en nth weekday y nth < 1."""
    due_dict = {"date": "2025-01-01", "string": "cada 2o xyz"}
    assert processing.infer_next_recurrence(due_dict) is None
    # nth < 1
    due_dict = {"date": "2025-01-01", "string": "cada 0o lun"}
    assert processing.infer_next_recurrence(due_dict) is None


def test_infer_next_recurrence_weekday_anywhere_no_match():
    """Cubre el else del bloque 'cada <weekday>' en cualquier parte."""
    due_dict = {"date": "2025-01-01", "string": "cada xyz"}
    assert processing.infer_next_recurrence(due_dict) is None


def test__process_due_obj_none_and_empty():
    """Cubre early return None y to_dict que retorna None."""
    # pylint: disable=protected-access
    assert processing._process_due_obj(None) is None

    class Dummy:
        """Dummy para simular to_dict que retorna None."""

        def to_dict(self):
            """Retorna None para simular caso extremo."""
            return None

        def dummy_public(self):
            """Método público dummy para R0903."""
            return True

    assert processing._process_due_obj(Dummy()) is None


def test_update_next_recurrence_due_dates_parse_error(monkeypatch):
    # pylint: disable=unused-argument
    """Cubre ValueError y TypeError en datetime.fromisoformat."""
    api = type("Api", (), {"update_task": lambda *a, **kw: None})()
    overdue_tasks = [{"due": {"next_recurrence_date": "not-a-date"}}]
    assert not processing.update_next_recurrence_due_dates(api, overdue_tasks, None)
    overdue_tasks = [{"due": {"next_recurrence_date": None}}]
    assert not processing.update_next_recurrence_due_dates(api, overdue_tasks, None)


def test__split_not_overdue_tasks_typeerror():
    # pylint: disable=protected-access
    """Cubre TypeError en datetime.fromisoformat."""
    not_overdue_tasks = [{"due": {"date": 12345}}]
    today_tasks, future_tasks = processing._split_not_overdue_tasks(
        not_overdue_tasks, datetime.now().astimezone().tzinfo
    )
    assert not today_tasks and future_tasks


def test__task_sort_key_typeerror():
    # pylint: disable=protected-access
    """Cubre TypeError en datetime.fromisoformat."""
    task = {"due": {"date": 12345}, "title": {"parts": {"id": "A01", "text": "t"}}}
    key = processing._task_sort_key(task, datetime.now().astimezone().tzinfo)
    assert isinstance(key, tuple)


def test__detect_frequencies_keyerror():
    # pylint: disable=protected-access
    """Cubre KeyError en FrequencyLabels.from_label."""
    assert not processing._detect_frequencies(["no-existe"])


def test__has_non_frequency_label():
    # pylint: disable=protected-access
    """Cubre el except KeyError (no es frecuencia) y caso frecuencia válida."""
    assert processing._has_non_frequency_label(["no-existe"]) is True
    assert not processing._has_non_frequency_label([FrequencyLabels.DAILY.label])


def test__infer_next_weekday_recurrence():
    """Cubre el caso donde el weekday no es reconocido y el caso normal."""
    # pylint: disable=protected-access
    assert (
        processing._infer_next_weekday_recurrence(datetime(2025, 1, 1), "cada xyz")
        is None
    )
    assert (
        processing._infer_next_weekday_recurrence(datetime(2025, 1, 1), "cada lun")
        is not None
    )
