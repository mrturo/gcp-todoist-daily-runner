#!/usr/bin/env python3
"""Direct runner for the Todoist integration service without starting a server.

This is the real implementation moved under `src.scripts`; a thin wrapper
remains at `src/run_service.py` for backward compatibility with imports.
"""

import json
import logging
import os
import sys

from todoist_api_python.api import TodoistAPI

# Ensure repository root is on sys.path so `from src import ...` works when
# executing this file directly (e.g. `python src/run_service.py`).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)  # pragma: no cover

from src.main import \
    run_todoist_integration  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


def _format_result(res):
    try:
        media = getattr(res, "media", None)
        if media is not None:
            return json.dumps(media, indent=2, ensure_ascii=False)
        body = getattr(res, "body", None)
        if isinstance(body, (bytes, bytearray)):
            s = body.decode("utf-8")
            try:
                return json.dumps(json.loads(s), indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return s
        if isinstance(res, (dict, list)):
            return json.dumps(res, indent=2, ensure_ascii=False)
        return str(res)
    except (TypeError, AttributeError, UnicodeDecodeError) as e:
        return f"<unserializable result: {e}>"


def _write_output_file(out_file, readable):
    try:
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(readable + "\n")
        return True
    except OSError as exc:
        print(f"\n❌ Failed to write result to {out_file}: {exc}", file=sys.stderr)
        return False


def _parse_result_to_dict(result):
    media = getattr(result, "media", None)
    if media is not None:
        return media
    body = getattr(result, "body", None)
    if isinstance(body, (bytes, bytearray)):
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    if isinstance(result, (dict, list)):
        return result
    return None


def _collect_tasks_from_parsed(parsed):
    overdue = parsed.get("overdue_tasks", []) or []
    today = parsed.get("today_tasks")
    future = parsed.get("future_tasks")
    if today is not None or future is not None:
        today = today or []
        future = future or []
        not_overdue = list(today) + list(future)
    else:
        not_overdue_raw = parsed.get("not_overdue_tasks", []) or []
        if isinstance(not_overdue_raw, dict):
            t = not_overdue_raw.get("today_tasks", []) or []
            f = not_overdue_raw.get("future_tasks", []) or []
            not_overdue = list(t) + list(f)
        else:
            not_overdue = not_overdue_raw
    return list(overdue) + list(not_overdue)


def _apply_title_updates(parsed):
    all_tasks = _collect_tasks_from_parsed(parsed)
    to_update = []
    for t in all_tasks:
        try:
            if t.get("title", {}).get("to_replace"):
                to_update.append((t.get("id"), t.get("title", {}).get("combined")))
        except AttributeError:
            continue
    return to_update


async def main():
    try:
        result = await run_todoist_integration()
        print("\n✅ Service executed successfully!")
        readable = _format_result(result)
        out_file = os.getenv("OUTPUT_JSON_FILE", "")
        if out_file:
            try:
                with open(out_file, "w", encoding="utf-8") as fh:
                    fh.write(readable + "\n")
                print(f"\nResult saved to {out_file}")
            except OSError as e:
                print(
                    f"\n❌ Failed to write result to {out_file}: {e}", file=sys.stderr
                )
                print("\nResult:")
                print(readable)
            parsed = _parse_result_to_dict(result)
            if isinstance(parsed, dict):
                to_update = _apply_title_updates(parsed)
                if to_update:
                    token = os.getenv("TODOIST_SECRET_ID")
                    if not token:
                        print(
                            "\n⚠️ TODOIST_SECRET_ID not set — skipping title updates",
                            file=sys.stderr,
                        )
                    else:
                        api = TodoistAPI(token)
                        for task_id, new_title in to_update:
                            if not task_id or not new_title:
                                continue
                            try:
                                api.update_task(task_id, content=new_title)
                                logger.info(
                                    "Updated Todoist task %s title to: %s",
                                    task_id,
                                    new_title,
                                )
                            except Exception as exc:
                                logger.error(
                                    "Failed to update task %s title: %s", task_id, exc
                                )
        else:
            print("\nResult:")
            print(readable)
        return 0
    except Exception:
        from src.run_service import *
