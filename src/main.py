"""FastAPI service to list all pending Todoist tasks on Cloud Run."""

import logging
import os
import zoneinfo
from datetime import datetime, timezone

import uvicorn as _uvicorn
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from todoist_api_python.api import TodoistAPI

from src.frequency_labels import FrequencyLabels

uvicorn = _uvicorn  # Expose for test monkeypatching

load_dotenv()

# Logging configuration for Cloud Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_todoist_token() -> str:
    """
    Retrieves the Todoist API token from environment variables.
    Looks for TODOIST_SECRET_ID in the environment.
    """
    token = os.getenv("TODOIST_SECRET_ID")
    return validate_todoist_token(token)


def _handle_due_date_parse_error(task, exc):
    """Handle due date parse errors for categorize_tasks (for testable coverage)."""
    logger.warning("Could not parse due date for task %s: %s", task.id, exc)


def get_timezone():
    """Get the timezone from the TIME_ZONE environment variable, fallback to UTC if invalid."""
    tz_name = os.getenv("TIME_ZONE", "UTC")
    try:
        return zoneinfo.ZoneInfo(tz_name)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning("Invalid TIME_ZONE '%s', falling back to UTC", tz_name)
        return timezone.utc


def update_overdue_daily_tasks(api, overdue_tasks):
    """Update due date to today for all overdue, recurring daily tasks. Returns updated task ids."""
    label_name = FrequencyLabels.DAILY.label
    daily_label_and_recurring_overdue_tasks = []
    for task in overdue_tasks:
        labels = task.get("labels", [])
        due = task.get("due", {})
        is_recurring = due.get("recurring", True)
        if label_name in labels and is_recurring:
            daily_label_and_recurring_overdue_tasks.append(task)

    logger.info(
        "Overdue, recurring tasks with daily frequency label: %d",
        len(daily_label_and_recurring_overdue_tasks),
    )

    tz = get_timezone()
    today_date = datetime.now(tz).date()
    updated_task_ids = []
    for task in daily_label_and_recurring_overdue_tasks:
        try:
            due = task.get("due", {})
            # Use the original recurrence string if available, else default to 'every day'
            due_string = due.get("string") or "every day"
            api.update_task(task["id"], due_date=today_date, due_string=due_string)
            updated_task_ids.append(task["id"])  # pragma: no cover
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Failed to update due date for task %s: %s",
                task.get("id", "?"),
                exc,
            )
    logger.info(
        "Updated due date to today for %d tasks: %s",
        len(updated_task_ids),
        updated_task_ids,
    )
    return updated_task_ids


app = FastAPI()


def validate_todoist_token(token: str) -> str:
    """
    Validates the Todoist API token value.
    Raises RuntimeError if the token is missing or empty.
    """
    if not token:
        logger.error("TODOIST_SECRET_ID not found in environment variables.")
        raise RuntimeError("TODOIST_SECRET_ID not found in environment variables.")
    return token


@app.get("/", response_class=JSONResponse)
async def run_todoist_integration():
    """
    Main endpoint called by Cloud Scheduler or HTTP GET.

    - Reads the Todoist API token from environment variables.
    - Initializes the Todoist client.
    - Fetches all active (pending) tasks from Todoist.
    - Returns a JSON with the list of tasks.
    """
    try:
        token = get_todoist_token()
        api = TodoistAPI(token)
        tasks = fetch_tasks(api)

        overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        update_overdue_daily_tasks(api, overdue_tasks)

        # Refresh overdue_tasks and not_overdue_tasks after updates
        tasks = fetch_tasks(api)
        overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        # For any overdue task, if next_recurrence_date is today or in the past, update due date
        tz = get_timezone()
        today = datetime.now(tz).date()
        updated_any = False
        for task in overdue_tasks:
            due = task.get("due", {})
            next_recur = due.get("next_recurrence_date")
            if next_recur:
                try:
                    next_recur_date = datetime.fromisoformat(next_recur).date()
                except (ValueError, TypeError):
                    continue
                if next_recur_date <= today:
                    due_string = due.get("string") or "every day"
                    try:
                        api.update_task(
                            task["id"], due_date=today, due_string=due_string
                        )
                        updated_any = True
                    except (KeyError, AttributeError) as exc:
                        logger.error(
                            "Failed to update due date for recurring overdue task %s: %s",
                            task.get("id", "?"),
                            exc,
                        )

        # If any were updated, refresh again
        if updated_any:
            tasks = fetch_tasks(api)
            overdue_tasks, not_overdue_tasks = categorize_tasks(tasks)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "overdue_tasks": overdue_tasks,
                "not_overdue_tasks": not_overdue_tasks,
            },
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected error in endpoint: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "detail": str(exc)},
        )


def fetch_tasks(api):
    """Fetch all tasks from Todoist API, flattening paginated results."""
    try:
        tasks_paginator = api.get_tasks()
        tasks = [task for page in tasks_paginator for task in page]
        logger.info("Fetched %d pending tasks from Todoist", len(tasks))
        return tasks
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error fetching tasks from Todoist: %s", exc)
        raise


def infer_next_recurrence(due_dict):
    """Infer next recurrence date for recurring tasks."""
    result = None
    next_recurrence_date = due_dict.get("next_recurring_date")
    if next_recurrence_date:
        result = next_recurrence_date
    else:
        due_date_str = due_dict.get("date")
        recur_str = due_dict.get("string", "").lower()
        if not due_date_str:
            result = None
        else:
            try:
                due_dt = datetime.fromisoformat(due_date_str)
            except (ValueError, TypeError) as exc:
                logger.warning("Could not infer next recurrence date for task: %s", exc)
                due_dt = None
            if due_dt:
                # Check for monthly, daily, weekly recurrences first
                if "cada mes" in recur_str or "every month" in recur_str:
                    result = (due_dt + relativedelta(months=1)).date().isoformat()
                elif "cada día" in recur_str or "every day" in recur_str:
                    result = (due_dt + relativedelta(days=1)).date().isoformat()
                elif "cada semana" in recur_str or "every week" in recur_str:
                    result = (due_dt + relativedelta(weeks=1)).date().isoformat()
                elif recur_str.startswith("cada ") or recur_str.startswith("every "):
                    result = _infer_next_weekday_recurrence(due_dt, recur_str)
    return result


def _infer_next_weekday_recurrence(due_dt, recur_str):
    """Helper for infer_next_recurrence: handle weekday recurrences."""
    weekday_map = {
        "lun": 0,
        "mar": 1,
        "mié": 2,
        "mie": 2,
        "jue": 3,
        "vie": 4,
        "sáb": 5,
        "sab": 5,
        "dom": 6,
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }
    result = None
    parts = recur_str.split()
    if len(parts) >= 2:
        wd = parts[1][:3]
        wd_idx = weekday_map.get(wd)
        if wd_idx is not None:
            days_ahead = (wd_idx - due_dt.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_dt = due_dt + relativedelta(days=days_ahead)
            result = next_dt.date().isoformat()
    return result


def is_task_overdue(due_dict, now, tz):
    """Determine if a task is overdue based on due_dict and current time."""
    if not due_dict or not due_dict.get("date"):
        return False
    due_date = due_dict["date"]
    today = now.date()
    try:
        if "T" in due_date:
            due_dt = datetime.fromisoformat(due_date)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=tz)
            return due_dt < now
        due_dt = datetime.fromisoformat(due_date)
        due_dt = due_dt.replace(tzinfo=tz)
        return due_dt.date() < today
    except (ValueError, TypeError):
        return None  # Will be handled in main loop


def categorize_tasks(tasks, now=None):
    """Categorize tasks into overdue and not overdue."""
    overdue_tasks = []
    not_overdue_tasks = []
    tz = get_timezone()
    now = datetime.now(tz) if now is None else now
    for task in tasks:
        due_obj = getattr(task, "due", None)
        due_dict = due_obj.to_dict() if due_obj else None
        labels = getattr(task, "labels", [])
        is_recurring = False
        if due_dict:
            is_recurring = (
                due_dict.get("recurring") or due_dict.get("is_recurring") or False
            )
            if is_recurring:
                due_dict = dict(due_dict)
                due_dict["next_recurrence_date"] = infer_next_recurrence(due_dict)
        task_data = {
            "id": task.id,
            "content": task.content,
            "due": due_dict,
            "labels": labels,
        }
        if due_dict and due_dict.get("date"):
            overdue = is_task_overdue(due_dict, now, tz)
            if overdue is None:
                _handle_due_date_parse_error(task, Exception("Invalid due date"))
                not_overdue_tasks.append(task_data)
            elif overdue:
                overdue_tasks.append(task_data)
            else:
                not_overdue_tasks.append(task_data)
        else:
            not_overdue_tasks.append(task_data)
    return overdue_tasks, not_overdue_tasks


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    # Use the module-level uvicorn for test monkeypatching
    _uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)  # nosec
