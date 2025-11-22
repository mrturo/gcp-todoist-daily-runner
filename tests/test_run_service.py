"""Unit tests for `src.run_service` helpers and main runner.

These tests exercise internal helper functions; pylint warnings for
protected access and test-style classes are disabled for clarity.
"""

# pylint: disable=protected-access,missing-class-docstring,missing-function-docstring,
# pylint: disable=too-few-public-methods,import-outside-toplevel,unused-argument,
# pylint: disable=use-implicit-booleaness-not-comparison,useless-return

import asyncio
import json
import os

import pytest

from src import run_service


class DummyResponse:
    def __init__(self, media=None, body=None):
        self.media = media
        self.body = body


def test_format_result_with_media():
    r = DummyResponse(media={"a": 1})
    out = run_service._format_result(r)
    assert '"a": 1' in out


def test_format_result_with_body_json_bytes():
    payload = {"x": 2}
    r = DummyResponse(body=json.dumps(payload).encode("utf-8"))
    out = run_service._format_result(r)
    assert '"x"' in out


def test_format_result_with_body_nonjson_bytes():
    r = DummyResponse(body=b"not json")
    out = run_service._format_result(r)
    assert "not json" in out


def test_parse_result_to_dict_variants():
    r_media = DummyResponse(media={"m": 1})
    assert run_service._parse_result_to_dict(r_media) == {"m": 1}

    r_body = DummyResponse(body=json.dumps({"b": 3}).encode("utf-8"))
    assert run_service._parse_result_to_dict(r_body) == {"b": 3}

    assert run_service._parse_result_to_dict({"ok": True}) == {"ok": True}
    assert run_service._parse_result_to_dict([1, 2, 3]) == [1, 2, 3]


def test_collect_tasks_from_parsed_variants():
    parsed = {
        "overdue_tasks": [{"id": "o1"}],
        "today_tasks": [{"id": "t1"}],
        "future_tasks": [{"id": "f1"}],
    }
    all_tasks = run_service._collect_tasks_from_parsed(parsed)
    ids = {t.get("id") for t in all_tasks}
    assert ids == {"o1", "t1", "f1"}

    # legacy not_overdue_tasks as list
    parsed2 = {"overdue_tasks": [], "not_overdue_tasks": [{"id": "n1"}]}
    all2 = run_service._collect_tasks_from_parsed(parsed2)
    assert {t.get("id") for t in all2} == {"n1"}

    # legacy not_overdue_tasks as dict with today/future
    parsed3 = {
        "overdue_tasks": [],
        "not_overdue_tasks": {
            "today_tasks": [{"id": "tt"}],
            "future_tasks": [{"id": "ff"}],
        },
    }
    all3 = run_service._collect_tasks_from_parsed(parsed3)
    assert {t.get("id") for t in all3} == {"tt", "ff"}


def test_apply_title_updates_collects_pairs():
    parsed = {
        "overdue_tasks": [],
        "today_tasks": [{"id": "1", "title": {"to_replace": True, "combined": "new"}}],
    }
    pairs = run_service._apply_title_updates(parsed)
    assert pairs == [("1", "new")]


def test_write_output_file_and_main(tmp_path, monkeypatch):
    out = tmp_path / "out.json"

    # stub run_todoist_integration to return a simple dict
    async def fake_run():
        return {"overdue_tasks": [], "today_tasks": []}

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run)
    # ensure TODOIST_SECRET_ID not set so update loop is skipped
    monkeypatch.delenv("TODOIST_SECRET_ID", raising=False)
    os.environ["OUTPUT_JSON_FILE"] = str(out)

    # run main
    rc = asyncio.run(run_service.main())
    assert rc == 0
    # file should exist and be non-empty
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert content.strip() != ""


def test_format_result_dict_and_unserializable():
    # dict/list path
    assert '"k": 1' in run_service._format_result({"k": 1})

    # cause UnicodeDecodeError inside _format_result
    class BadBody:
        def __init__(self):
            self.body = b"\xff"

    got = run_service._format_result(BadBody())
    assert got.startswith("<unserializable result:")


def test_parse_result_to_dict_nonjson_bytes():
    r = DummyResponse(body=b"not json")
    assert run_service._parse_result_to_dict(r) is None


def test_main_write_error_and_todoist_update(monkeypatch, tmp_path):
    # Write will fail because directory does not exist
    out = tmp_path / "nope" / "out.json"

    async def fake_run():
        # return a dict that will parse to dict and produce to_update
        return {
            "overdue_tasks": [],
            "today_tasks": [
                {"id": "1", "title": {"to_replace": True, "combined": "new"}}
            ],
        }

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run)
    os.environ["OUTPUT_JSON_FILE"] = str(out)

    # Monkeypatch TodoistAPI to a dummy that raises in update_task to hit except branch
    class DummyAPI:
        def __init__(self, token):
            self.token = token

        def update_task(self, task_id, content=None):
            raise RuntimeError("update failed")

    monkeypatch.setenv("TODOIST_SECRET_ID", "token-value")
    monkeypatch.setattr(run_service, "TodoistAPI", DummyAPI)

    rc = asyncio.run(run_service.main())
    # main should complete and return 0 even if write failed and update failed
    assert rc == 0


def test_main_integration_exception(monkeypatch):
    async def bad_run():
        raise RuntimeError("boom")

    monkeypatch.setattr(run_service, "run_todoist_integration", bad_run)
    # ensure no OUTPUT_JSON_FILE so branch prints result
    monkeypatch.delenv("OUTPUT_JSON_FILE", raising=False)
    rc = asyncio.run(run_service.main())
    assert rc == 1


def test_write_output_file_failure(tmp_path):
    # file in non-existent directory should return False
    out = tmp_path / "nope" / "file.json"
    ok = run_service._write_output_file(str(out), "{}")
    assert not ok


def test_format_result_other_types():
    # custom object -> str()
    class X:
        def __str__(self):
            return "hello"

    assert run_service._format_result(X()) == "hello"


def test_run_as_script_executes_and_exits(tmp_path, monkeypatch):
    # Prepare a fake src.main module with run_todoist_integration
    import runpy
    import sys
    import types

    mod = types.ModuleType("src.main")

    async def fake_run():
        return {"overdue_tasks": [], "today_tasks": []}

    mod.run_todoist_integration = fake_run
    sys.modules["src.main"] = mod

    # Fake todoist_api_python.api.TodoistAPI so import succeeds
    api_mod = types.ModuleType("todoist_api_python.api")

    class DummyAPI2:
        def __init__(self, token):
            pass

        def update_task(self, *a, **k):
            return None

    api_mod.TodoistAPI = DummyAPI2
    sys.modules["todoist_api_python.api"] = api_mod

    # Ensure OUTPUT_JSON_FILE exists
    out = tmp_path / "out2.json"
    os.environ["OUTPUT_JSON_FILE"] = str(out)

    with pytest.raises(SystemExit) as exc:
        # Ensure any previously-imported module won't trigger runpy's
        # RuntimeWarning about modules already present in sys.modules.
        original = sys.modules.pop("src.run_service", None)
        try:
            runpy.run_module("src.run_service", run_name="__main__")
        finally:
            if original is not None:
                sys.modules["src.run_service"] = original
    assert exc.value.code == 0


def test_format_result_bytearray_and_getattr_error():
    # bytearray with JSON
    r = DummyResponse(body=bytearray(json.dumps({"z": 9}), "utf-8"))
    out = run_service._format_result(r)
    assert '"z"' in out

    # object that raises TypeError on attribute access -> outer except
    class Bad:
        def __getattribute__(self, name):
            raise TypeError("nope")

    got = run_service._format_result(Bad())
    assert got.startswith("<unserializable result:")


def test_main_to_update_token_missing(monkeypatch, tmp_path):
    async def fake_run():
        return {
            "overdue_tasks": [],
            "today_tasks": [
                {"id": "1", "title": {"to_replace": True, "combined": "new"}}
            ],
        }

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run)
    monkeypatch.delenv("TODOIST_SECRET_ID", raising=False)
    os.environ["OUTPUT_JSON_FILE"] = str(tmp_path / "out3.json")

    rc = asyncio.run(run_service.main())
    assert rc == 0


def test_main_no_output_file_prints_result(monkeypatch):
    async def fake_run2():
        return {"overdue_tasks": [], "today_tasks": []}

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run2)
    monkeypatch.delenv("OUTPUT_JSON_FILE", raising=False)
    monkeypatch.delenv("TODOIST_SECRET_ID", raising=False)

    rc = asyncio.run(run_service.main())
    assert rc == 0


def test_write_output_file_success(tmp_path):
    out = tmp_path / "ok.json"
    ok = run_service._write_output_file(str(out), '{"ok":true}')
    assert ok
    assert out.exists()


def test_parse_result_to_dict_final_none():
    assert run_service._parse_result_to_dict(object()) is None


def test_apply_title_updates_malformed_entry():
    parsed = {"overdue_tasks": [], "today_tasks": [5]}
    assert run_service._apply_title_updates(parsed) == []


def test_main_todoist_update_success(monkeypatch, tmp_path):
    async def fake_run():
        return {
            "overdue_tasks": [],
            "today_tasks": [
                {"id": "42", "title": {"to_replace": True, "combined": "ok"}}
            ],
        }

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run)
    os.environ["OUTPUT_JSON_FILE"] = str(tmp_path / "out4.json")

    class DummyAPI3:
        def __init__(self, token):
            self.token = token
            self.calls = []

        def update_task(self, task_id, content=None):
            self.calls.append((task_id, content))
            return None

    monkeypatch.setenv("TODOIST_SECRET_ID", "token")
    monkeypatch.setattr(run_service, "TodoistAPI", DummyAPI3)

    rc = asyncio.run(run_service.main())
    assert rc == 0


def test_main_update_skips_empty_values(monkeypatch, tmp_path):
    async def fake_run():
        return {
            "overdue_tasks": [],
            "today_tasks": [{"id": "", "title": {"to_replace": True, "combined": ""}}],
        }

    monkeypatch.setattr(run_service, "run_todoist_integration", fake_run)
    os.environ["OUTPUT_JSON_FILE"] = str(tmp_path / "out5.json")

    class DummyAPI4:
        def __init__(self, token):
            self.calls = []

        def update_task(self, task_id, content=None):
            self.calls.append((task_id, content))

    monkeypatch.setenv("TODOIST_SECRET_ID", "tokenx")
    monkeypatch.setattr(run_service, "TodoistAPI", DummyAPI4)

    rc = asyncio.run(run_service.main())
    assert rc == 0
