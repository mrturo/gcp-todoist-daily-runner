#!/usr/bin/env python3
"""Direct runner for the Todoist integration service without starting a server.

This module provides the helper functions used by tests (`_format_result`,
`_parse_result_to_dict`, `_collect_tasks_from_parsed`, `_apply_title_updates`,
`_write_output_file`) and an `async main()` entrypoint that calls
`src.main.run_todoist_integration`.
"""

import asyncio
import json
import logging
import os
import sys

from todoist_api_python.api import TodoistAPI

from src.main import run_todoist_integration

logger = logging.getLogger(__name__)


def _format_result(res):
    """Format the FastAPI response-like object into a readable string.

    Handles objects exposing `media` or `body` attributes as well as raw
    dict/list values.
    """
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
    """Write the human-readable JSON output to `out_file`.

    Returns True on success and False on filesystem errors.
    """
    try:
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(readable + "\n")
        return True
    except OSError as exc:
        print(f"\n❌ Failed to write result to {out_file}: {exc}", file=sys.stderr)
        return False


def _parse_result_to_dict(result):
    """Parse a FastAPI response-like object into a Python dict/list.

    Returns the parsed structure or None when parsing fails.
    """
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
    """Collect a flat list of tasks from the parsed JSON structure.

    This supports both the newer `today_tasks`/`future_tasks` shape and the
    older `not_overdue_tasks` nested shape used by previous outputs.
    """
    overdue = parsed.get("overdue_tasks", []) or []
    # Prefer top-level `today_tasks`/`future_tasks`
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
    """Return a list of (task_id, new_title) tuples for tasks to update.

    Scans tasks for `title.to_replace == True` and produces pairs used to
    update Todoist tasks' content.
    """
    all_tasks = _collect_tasks_from_parsed(parsed)
    to_update = []
    for t in all_tasks:
        try:
            if t.get("title", {}).get("to_replace"):
                to_update.append((t.get("id"), t.get("title", {}).get("combined")))
        except AttributeError:
            # Skip malformed task entries
            continue
    return to_update


async def _update_titles_in_todoist(to_update, token):
    """Update task titles in Todoist API.

    Args:
        to_update: List of (task_id, new_title) tuples
        token: Todoist API token
    """
    api = TodoistAPI(token)
    for task_id, new_title in to_update:
        if not task_id or not new_title:
            continue
        try:
            # Update the task content/title in Todoist
            api.update_task(task_id, content=new_title)
            logger.info("Updated Todoist task %s title to: %s", task_id, new_title)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logger.error("Failed to update task %s title: %s", task_id, exc)
        # pylint: enable=broad-exception-caught


async def _save_and_update_titles(result, out_file):
    """Save result and update titles if needed.

    Args:
        result: Integration result
        out_file: Output file path

    Returns:
        Updated result if titles were updated, original result otherwise
    """
    readable = _format_result(result)
    try:
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(readable + "\n")
        print(f"\nResult saved to {out_file}")
    except OSError as e:
        print(f"\n❌ Failed to write result to {out_file}: {e}", file=sys.stderr)
        print("\nResult:")
        print(readable)
        return result

    # Attempt to update Todoist tasks where title.to_replace == true
    parsed = _parse_result_to_dict(result)
    if not isinstance(parsed, dict):
        return result

    to_update = _apply_title_updates(parsed)
    if not to_update:
        return result

    token = os.getenv("TODOIST_SECRET_ID")
    if not token:
        print("\n⚠️ TODOIST_SECRET_ID not set — skipping title updates", file=sys.stderr)
        return result

    await _update_titles_in_todoist(to_update, token)

    # Re-fetch tasks after updating titles to get the updated content
    print("\n🔄 Re-fetching tasks after title updates...")
    updated_result = await run_todoist_integration()
    readable = _format_result(updated_result)
    try:
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(readable + "\n")
        print(f"✅ Updated result saved to {out_file}")
    except OSError as e:
        print(
            f"\n❌ Failed to write updated result to {out_file}: {e}", file=sys.stderr
        )

    return updated_result


async def main():
    """Run the Todoist integration and optionally write output or updates.

    This is a convenience entrypoint used by the CLI wrapper.
    """
    try:
        result = await run_todoist_integration()
        print("\n✅ Service executed successfully!")
        out_file = os.getenv("OUTPUT_JSON_FILE", "")

        if out_file:
            await _save_and_update_titles(result, out_file)
        else:
            readable = _format_result(result)
            print("\nResult:")
            print(readable)

        return 0
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n❌ Error executing service: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
