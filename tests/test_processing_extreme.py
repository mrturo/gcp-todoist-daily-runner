"""
Cobertura de ramas de protección extrema en src/core/processing.py:
- get_timezone: excepción inesperada en datetime.now().astimezone().tzinfo
- infer_next_recurrence: excepción ValueError/TypeError en datetime.fromisoformat
    para due_date_str=None
"""

import os

from src.core import processing


def test_get_timezone_extreme_exception(monkeypatch):
    """Fuerza excepción inesperada en datetime.now().astimezone().tzinfo."""

    class DummyDatetime:
        """Simula datetime con fallo extremo en astimezone."""

        @staticmethod
        def now():
            """Devuelve un Dummy que falla en astimezone (para cobertura extrema)."""

            class Dummy:
                """Simula objeto con astimezone que falla."""

                def astimezone(self):
                    """Simula fallo extremo en astimezone."""
                    raise RuntimeError("extreme tz fail")

                def dummy(self):
                    """Método público dummy para R0903."""
                    return None

            return Dummy()

        def dummy(self):
            """Método público dummy para R0903."""
            return None

    monkeypatch.setattr(processing, "datetime", DummyDatetime)
    monkeypatch.setattr(os, "environ", {})
    tz = processing.get_timezone()
    assert tz == processing.timezone.utc


def test_infer_next_recurrence_due_date_none():
    """Fuerza ValueError/TypeError en datetime.fromisoformat con due_date_str=None."""
    due_dict = {"date": None, "string": "cada 3 días"}
    assert processing.infer_next_recurrence(due_dict) is None
