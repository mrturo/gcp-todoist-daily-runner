"""
Tests for full coverage of main.py, including __main__ block and unexpected exceptions.
"""

import runpy
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src import main as main_module
from tests.test_utils import assert_error_response


def test_main_py_direct(monkeypatch):
    """Test __main__ block runs uvicorn with correct port."""
    main_path = str(Path(__file__).parent.parent / "src" / "main.py")
    called = {}

    def fake_run(*args, **kwargs):
        called["run"] = (args, kwargs)

    monkeypatch.setattr(
        main_module, "uvicorn", type("FakeUvicorn", (), {"run": staticmethod(fake_run)})
    )
    monkeypatch.setattr(
        "os.getenv", lambda key, default=None: "1234" if key == "PORT" else default
    )
    sys.modules["uvicorn"] = main_module.uvicorn
    runpy.run_path(main_path, run_name="__main__")
    if not called["run"][1]["port"] == 1234:
        raise AssertionError(f"Expected port 1234, got {called['run'][1]['port']}")


def test_run_todoist_integration_unexpected_exception(monkeypatch):
    """
    Test run_todoist_integration handles unexpected Exception.
    """
    monkeypatch.setattr(
        main_module,
        "get_todoist_token",
        lambda: (_ for _ in ()).throw(Exception("unexpected")),
    )
    client = TestClient(main_module.app)
    response = client.get("/")
    assert_error_response(response, expected_detail="unexpected")
