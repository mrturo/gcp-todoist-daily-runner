"""
Test para verificar que los tickets con is_recurring=True y
next_recurrence_date=None se marcan como error en issue_tasks.
"""

from fastapi.testclient import TestClient

from src import main as main_module
from src.main import app

client = TestClient(app)


def test_issue_task_is_recurring_true_next_recurrence_null(monkeypatch):
    """
    Test que verifica que un ticket con is_recurring=True y
    next_recurrence_date=None es marcado como error.
    """
    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake-token")

    class FakeDue:
        """Fake due object para simular due con recurring True y next_recurrence_date None."""

        def to_dict(self):
            """Devuelve un diccionario simulando el due."""
            return {
                "date": "2025-01-01",
                "recurring": True,
                # next_recurrence_date está ausente/null
            }

        def is_valid(self):
            """Método público adicional para cumplir R0903."""
            return True

    # pylint: disable=too-few-public-methods
    class FakeTask:
        """Fake task para simular una tarea de Todoist."""

        def __init__(self, id_, content, due=None):
            """Inicializa la tarea fake."""
            self.id = id_
            self.content = content
            self.due = due

        def is_valid(self):
            """Método público adicional para cumplir R0903."""
            return True

    class FakeTodoistAPI:
        """Fake API para simular la obtención de tareas."""

        def __init__(self, token):
            """Inicializa la API fake."""
            self.token = token

        def get_tasks(self):
            """Devuelve una lista de tareas fake."""
            return [
                [FakeTask("err-1", "🟢(A01-01-01)📝Test recurring null", FakeDue())]
            ]

        def is_valid(self):
            """Método público adicional para cumplir R0903."""
            return True

    monkeypatch.setattr(main_module, "TodoistAPI", FakeTodoistAPI)

    response = client.get("/")
    assert response.status_code == 207
    data = response.json()
    # Buscar el issue específico
    found = False
    for issue in data.get("issue_tasks", []):
        if issue["task_id"] == "err-1" and any(
            "is_recurring true but next_recurrence_date is null" in msg
            for msg in issue["issues"]
        ):
            found = True
    assert found, (
        "No se detectó el error esperado para is_recurring true y "
        "next_recurrence_date null"
    )
