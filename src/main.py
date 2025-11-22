"""Main FastAPI module re-exporting core processing helpers.

This module keeps the original public API surface for tests while delegating
implementation to src.core.processing. It intentionally contains minimal
top-level logic so coverage can be measured in the implementation module.
"""

import os

import uvicorn as _uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

# Re-export implementations from core.processing (keep at module top for
# static analyzers and tests that import these names)
from src.core.processing import (_detect_frequencies, _has_non_frequency_label,
                                 _process_due_obj, _split_not_overdue_tasks,
                                 _task_sort_key,
                                 _update_next_recurrence_due_dates,
                                 build_title_object, categorize_tasks,
                                 fetch_tasks, get_timezone,
                                 infer_next_recurrence, is_task_overdue,
                                 update_overdue_daily_tasks,
                                 validate_todoist_token)

uvicorn = _uvicorn  # expose for test monkeypatching

# Expose the TodoistAPI symbol so tests can monkeypatch it. Prefer importing
# the real client when available, but fall back to None to avoid import errors
# during tests that replace this attribute.
# Expose the TodoistAPI symbol so tests can monkeypatch it. Prefer importing
# the real client when available, but fall back to None to avoid import errors
# during tests that replace this attribute.
try:
    from todoist_api_python.api import TodoistAPI  # type: ignore
except ImportError:  # pragma: no cover - runtime environment may not have the lib
    # Tests will monkeypatch `TodoistAPI` on this module when needed
    TodoistAPI = None  # pylint: disable=invalid-name

# (imports from src.core.processing are at top of module)

app = FastAPI()


def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Verify the API key from the X-API-Key header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    expected_key = os.getenv("API_KEY")

    # Skip validation if API_KEY is not configured (for backwards compatibility)
    if not expected_key:
        return None

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return x_api_key


def _collect_issue_tasks(all_groups):
    """Collect tasks with issues and their causes.

    Returns a list of dicts with task_id and issues (list of problem descriptions).
    """
    issue_tasks = []

    for grp in all_groups:
        for task in grp:
            task_id = task.get("id")
            issues = []

            # Check title.is_complete
            if not task.get("title", {}).get("is_complete", True):
                issues.append("title is incomplete")

            # Check title.duplicated_id
            if task.get("title", {}).get("duplicated_id", False):
                issues.append("duplicated ticket id")

            # Check title.sequential_id
            if task.get("title", {}).get("sequential_id") is False:
                issues.append("non-sequential ticket id")

            # Check frequency_labels.frequency_matches_label
            if not task.get("frequency_labels", {}).get(
                "frequency_matches_label", True
            ):
                issues.append("frequency emoji does not match label")

            # Check frequency_labels.has_non_frequency
            if not task.get("frequency_labels", {}).get("has_non_frequency", True):
                issues.append("missing non-frequency label")

            # Nuevo: Check is_recurring true y next_recurrence_date null
            due = task.get("due", {}) or {}
            is_recurring = due.get("recurring") or due.get("is_recurring") or False
            next_recur = due.get("next_recurrence_date", None)
            if is_recurring and next_recur is None:
                issues.append("is_recurring true but next_recurrence_date is null")

            if issues:
                issue_tasks.append({"task_id": task_id, "issues": issues})

    return issue_tasks


def _validate_sequential_id(ticket_id: str, all_ids: set) -> bool:
    """Validate if a ticket ID follows sequential rules.

    For an ID like A05-02-00, validates that these IDs exist:
    - A01-*-*, A02-*-*, A03-*-*, A04-*-* - all previous first parts
    - A05-01-* - previous second part

    Args:
        ticket_id: The ticket ID to validate (e.g., "A05-02-00")
        all_ids: Set of all existing ticket IDs (without parentheses)

    Returns:
        True if the ID follows sequential rules, False otherwise
    """
    # pylint: disable=too-many-return-statements
    if not ticket_id or not isinstance(ticket_id, str):
        return False

    # Split by dash (ID no longer has parentheses)
    parts = ticket_id.split("-")

    if len(parts) != 3:
        return False

    try:
        # Extract letter prefix and number from first part (e.g., "A05" -> "A", 5)
        first_part = parts[0]
        if not first_part or not first_part[0].isalpha():
            return False

        prefix = first_part[0]
        first_num = int(first_part[1:])
        second_num = int(parts[1])

        # Validate all previous first parts exist (A01, A02, A03, A04 for A05)
        for i in range(1, first_num):
            # Check if any ID with this first part exists (e.g., A01-*-*)
            required_prefix = f"{prefix}{i:02d}"
            found = any(id_str.startswith(required_prefix + "-") for id_str in all_ids)
            if not found:
                return False

        # Validate all previous second parts exist (A05-01 for A05-02)
        if second_num > 1:
            for j in range(1, second_num):
                # Check if any ID with this first and second part exists (e.g., A05-01-*)
                required_pattern = f"{prefix}{first_num:02d}-{j:02d}"
                found = any(
                    id_str.startswith(required_pattern + "-") for id_str in all_ids
                )
                if not found:
                    return False

        return True

    except (ValueError, IndexError):
        return False


def _mark_duplicated_ids(all_groups):
    """Mark tasks with duplicated IDs across all groups.

    Args:
        all_groups: List of task groups (overdue, today, future)
    """
    _id_counts = {}
    for grp in all_groups:
        for t in grp:
            pid = (t.get("title", {}).get("parts") or {}).get("id")
            if pid:
                _id_counts[pid] = _id_counts.get(pid, 0) + 1
    for grp in all_groups:
        for t in grp:
            pid = (t.get("title", {}).get("parts") or {}).get("id")
            t.setdefault("title", {})["duplicated_id"] = bool(
                pid and _id_counts.get(pid, 0) > 1
            )


def _mark_sequential_ids(all_groups):
    """Mark tasks with non-sequential IDs across all groups.

    Args:
        all_groups: List of task groups (overdue, today, future)
    """
    _all_ids = set()
    for grp in all_groups:
        for t in grp:
            pid = (t.get("title", {}).get("parts") or {}).get("id")
            if pid:
                _all_ids.add(pid)

    for grp in all_groups:
        for t in grp:
            pid = (t.get("title", {}).get("parts") or {}).get("id")
            t.setdefault("title", {})["sequential_id"] = _validate_sequential_id(
                pid, _all_ids
            )


async def run_todoist_integration():
    """Run the integration flow and return a JSONResponse.

    This function orchestrates fetching tasks, categorizing them, updating
    overdue daily tasks and recurring next-recurrence dates, and producing
    the JSONResponse returned by the FastAPI endpoint. Tests patch parts of
    this function in order to exercise error handling paths.
    """
    try:
        # Allow tests to monkeypatch `get_todoist_token` to control token
        token = get_todoist_token()
        # Use module-level TodoistAPI (may be monkeypatched in tests)
        if TodoistAPI is None:
            # Last-resort dynamic import if not set (keeps behaviour unchanged
            # when running for real).
            todoist_api_cls = __import__(
                "todoist_api_python"
            ).api.TodoistAPI  # pragma: no cover - dynamic import fallback
        else:
            todoist_api_cls = TodoistAPI
        api = todoist_api_cls(token)
        tasks = fetch_tasks(api)

        overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        update_overdue_daily_tasks(api, overdue_tasks)

        # Refresh overdue_tasks and not_overdue_tasks after updates
        tasks = fetch_tasks(api)
        overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        # For any overdue task, if next_recurrence_date is today or in the past, update due date
        tz = get_timezone()
        if _update_next_recurrence_due_dates(api, overdue_tasks, tz):
            tasks = fetch_tasks(api)
            overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        # Split not_overdue_tasks into `today_tasks` and `future_tasks` for JSON output
        today_tasks, future_tasks = _split_not_overdue_tasks(not_overdue_tasks, tz)

        # Mark duplicated and sequential IDs across all task lists
        all_groups = [overdue_tasks, today_tasks, future_tasks]
        _mark_duplicated_ids(all_groups)
        _mark_sequential_ids(all_groups)

        # Sort each list by due.date, title.parts.id, title.parts.text
        overdue_tasks = sorted(overdue_tasks, key=lambda t: _task_sort_key(t, tz))
        today_tasks = sorted(today_tasks, key=lambda t: _task_sort_key(t, tz))
        future_tasks = sorted(future_tasks, key=lambda t: _task_sort_key(t, tz))

        # Collect tasks with issues
        issue_tasks = _collect_issue_tasks(all_groups)

        # Use 207 Multi-Status when there are issues, 200 OK otherwise
        status_code = 207 if issue_tasks else 200

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ok",
                "overdue_tasks": overdue_tasks,
                "today_tasks": today_tasks,
                "future_tasks": future_tasks,
                "issue_tasks": issue_tasks,
            },
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )


# Convenience wrapper expected by tests
# Convenience wrapper expected by tests
def get_todoist_token() -> str:
    """Retrieve the Todoist API token from environment and validate it."""
    token = __import__("os").environ.get("TODOIST_SECRET_ID")
    return validate_todoist_token(token)


# Re-exported public symbols expected by tests (explicit aliases help static
# analyzers and make it obvious which names are part of this module API).
__all__ = [
    "run_todoist_integration",
    "get_todoist_token",
    "_process_due_obj",
    "_detect_frequencies",
    "_has_non_frequency_label",
    "_split_not_overdue_tasks",
    "_task_sort_key",
    "_update_next_recurrence_due_dates",
    "categorize_tasks",
    "fetch_tasks",
    "get_timezone",
    "update_overdue_daily_tasks",
    "validate_todoist_token",
    "build_title_object",
    "is_task_overdue",
    "infer_next_recurrence",
    "TodoistAPI",
]


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    # Use the module-level uvicorn for test monkeypatching
    _uvicorn.run(
        "src.main:app", host="0.0.0.0", port=port, reload=True
    )  # pragma: no cover

# Register the endpoint using the implementation defined above
app.get("/", response_class=JSONResponse, dependencies=[Depends(verify_api_key)])(
    run_todoist_integration
)
