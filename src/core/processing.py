"""Core processing helpers moved out of `src.main` for clarity.

This module contains the pure processing functions (date handling,
categorization, title building) and is re-exported from `src.main` to
preserve the original public API used by tests.
"""

import logging
import re
import zoneinfo
from calendar import monthrange
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from src.utils.frequency_labels import FrequencyLabels
from src.utils.validators import validate_ticket_name

logger = logging.getLogger("src.main")


# get_timezone may attempt a best-effort lookup and defensively catch
# unexpected errors during timezone resolution.
# pylint: disable=broad-exception-caught
def get_timezone():
    """Return the configured timezone or the system local timezone.

    Reads `TIME_ZONE` from the environment and returns a `zoneinfo.ZoneInfo`
    object when available. Falls back to the system local timezone or UTC in
    extreme failure cases.
    """
    tz_name = __import__("os").environ.get("TIME_ZONE")
    if tz_name:
        try:
            return zoneinfo.ZoneInfo(tz_name)
        except (
            zoneinfo.ZoneInfoNotFoundError
        ):  # pragma: no cover - hard to simulate on CI
            logger.warning(
                "Invalid TIME_ZONE '%s', falling back to system local", tz_name
            )  # pragma: no cover
    # No explicit TIME_ZONE configured: use system local timezone
    try:
        return datetime.now().astimezone().tzinfo
    except (
        Exception
    ):  # pylint: disable=broad-exception-caught  # pragma: no cover - extremely unlikely
        # Be defensive and fall back to UTC if local timezone lookup fails.
        return timezone.utc  # pragma: no cover


def validate_todoist_token(token: str) -> str:
    """Validate that a non-empty Todoist token string is provided.

    Raises RuntimeError when the token is missing.
    """
    if not token:
        logger.error("TODOIST_SECRET_ID not found in environment variables.")
        raise RuntimeError("TODOIST_SECRET_ID not found in environment variables.")
    return token


def update_overdue_daily_tasks(api, overdue_tasks):
    """Update overdue recurring tasks that have the daily frequency label.

    Returns a list of updated task ids.
    """
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

    get_timezone()
    # Use naive local date for updates so behaviour matches tests running in
    # the local system timezone.
    today_date = datetime.now().date()
    updated_task_ids = []
    for task in daily_label_and_recurring_overdue_tasks:
        try:
            due = task.get("due", {})
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


def fetch_tasks(api):
    """Fetch pending tasks from the given Todoist API client.

    Returns a flat list of task objects. Any client errors are logged and
    re-raised.
    """
    try:
        tasks_paginator = api.get_tasks()
        tasks = [task for page in tasks_paginator for task in page]
        logger.info("Fetched %d pending tasks from Todoist", len(tasks))
        return tasks
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error fetching tasks from Todoist: %s", exc)
        raise


def _normalize_recur_str(recur_str_raw):
    recur_str = re.sub(r"[!¡.,;:]", "", recur_str_raw)
    recur_str = re.sub(r"\s+", " ", recur_str).strip()
    return recur_str.lower()


def _weekday_map():
    return {
        "lun": 0,
        "mon": 0,
        "mar": 1,
        "tue": 1,
        "mié": 2,
        "mie": 2,
        "wed": 2,
        "jue": 3,
        "thu": 3,
        "vie": 4,
        "fri": 4,
        "sáb": 5,
        "sab": 5,
        "sat": 5,
        "dom": 6,
        "sun": 6,
    }


def infer_next_recurrence(due_dict):
    """Infer the next recurrence date for a due dictionary."""
    next_recurrence_date = due_dict.get("next_recurring_date")
    if next_recurrence_date:
        return next_recurrence_date
    due_date_str = due_dict.get("date")
    recur_str_raw = (due_dict.get("string") or due_dict.get("frequency") or "").strip()
    recur_str_lc = _normalize_recur_str(recur_str_raw)
    if not due_date_str:
        return None
    try:
        due_dt = datetime.fromisoformat(due_date_str)
    except (ValueError, TypeError) as exc:
        logger.warning("Could not infer next recurrence date for task: %s", exc)
        return None
    # Refactor: delega cada patrón a un helper
    for fn in [
        _recur_every_n_days,
        _recur_cada_n,
        _recur_month,
        _recur_day,
        _recur_week,
        _recur_n_weeks_weekday,
        _recur_nth_weekday,
        _recur_any_weekday,
    ]:
        result = fn(recur_str_lc, due_dt)
        if result is not None:
            return result
    return None


def _recur_every_n_days(recur_str_lc, due_dt):
    m = re.search(r"(cada|every)\s*(\d+)\s*d[ií]as?", recur_str_lc) or re.search(
        r"(cada|every)\s*(\d+)\s*days?", recur_str_lc
    )
    if m:
        n = int(m.group(2))
        return (due_dt + relativedelta(days=n)).date().isoformat()
    return None


def _recur_cada_n(recur_str_lc, due_dt):
    m_cada_n = re.match(r"cada\s*(\d{1,2})$", recur_str_lc)
    result = None
    if not m_cada_n:
        return result

    dia = int(m_cada_n.group(1))

    def _date_str(dt, day):
        return dt.replace(day=day).date().isoformat()

    if due_dt.day < dia:
        try:
            result = _date_str(due_dt, dia)
        except ValueError:
            last_day = monthrange(due_dt.year, due_dt.month)[1]
            if last_day < dia:
                result = f"{due_dt.year:04d}-{due_dt.month:02d}-{last_day:02d}"
            else:
                result = _date_str(due_dt, last_day)
        return result

    next_month = due_dt.replace(day=1) + relativedelta(months=1)
    last_day = monthrange(next_month.year, next_month.month)[1]
    if last_day < dia:
        result = f"{next_month.year:04d}-{next_month.month:02d}-{last_day:02d}"
    else:
        use_day = last_day if dia > last_day else dia
        result = _date_str(next_month, use_day)
    return result


def _recur_month(recur_str_lc, due_dt):
    if "cada mes" in recur_str_lc or "every month" in recur_str_lc:
        return (due_dt + relativedelta(months=1)).date().isoformat()
    return None


def _recur_day(recur_str_lc, due_dt):
    if "cada día" in recur_str_lc or "every day" in recur_str_lc:
        return (due_dt + relativedelta(days=1)).date().isoformat()
    return None


def _recur_week(recur_str_lc, due_dt):
    if (
        "cada semana" in recur_str_lc
        or "every week" in recur_str_lc
        or re.match(r"(cada|every) ?1 semana", recur_str_lc)
        or re.match(r"(cada|every) ?1 week", recur_str_lc)
    ):
        return (due_dt + relativedelta(weeks=1)).date().isoformat()
    return None


def _recur_n_weeks_weekday(recur_str_lc, due_dt):
    m = re.match(
        r"(cada|every) ?(\d+) semanas? ?([a-zá]{3,})", recur_str_lc
    ) or re.match(r"(cada|every) ?(\d+) weeks? ?([a-zá]{3,})", recur_str_lc)
    if m:
        n = int(m.group(2))
        wd = m.group(3).lower()
        wd_idx = _weekday_map().get(wd)
        if wd_idx is not None:
            candidate = due_dt + relativedelta(weeks=n)
            for i in range(7):
                test_date = candidate + relativedelta(days=i)
                if test_date.weekday() == wd_idx:
                    return test_date.date().isoformat()
    return None


def _recur_nth_weekday(recur_str_lc, due_dt):
    m = re.match(
        r"(cada|every) ?(\d+)(º|o|st|nd|rd|th)? ?([a-zá]{3,})",
        recur_str_lc,
        flags=re.IGNORECASE,
    )
    if m:
        nth = int(m.group(2))
        wd = m.group(4).lower()
        wd_idx = _weekday_map().get(wd)
        if wd_idx is not None and nth >= 1:
            next_month = due_dt.replace(day=1) + relativedelta(months=1)
            count = 0
            for i in range(31):
                candidate = next_month + relativedelta(days=i)
                if candidate.month != next_month.month:
                    break
                if candidate.weekday() == wd_idx:
                    count += 1
                    if count == nth:
                        return candidate.date().isoformat()
    return None


def _recur_any_weekday(recur_str_lc, due_dt):
    m = re.search(r"(?:cada|every)\s+([a-zá]{3,})", recur_str_lc)
    if m:
        wd = m.group(1).lower()
        wd_idx = _weekday_map().get(wd)
        if wd_idx is not None:
            days_ahead = (wd_idx - due_dt.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_dt = due_dt + relativedelta(days=days_ahead)
            return next_dt.date().isoformat()
    return None


def _process_due_obj(due_obj):
    """Normalize a Todoist due object to a plain dictionary.

    This extracts recurrence metadata and computes `next_recurrence_date`
    when applicable.
    """
    if not due_obj:
        return None
    due_dict = due_obj.to_dict()
    if not due_dict:
        return None
    is_recurring = due_dict.get("recurring") or due_dict.get("is_recurring") or False
    if is_recurring:
        due_dict = dict(due_dict)
        due_dict["next_recurrence_date"] = infer_next_recurrence(due_dict)
        if "string" in due_dict and "frequency" not in due_dict:
            due_dict["frequency"] = due_dict.get("string")
        if "string" in due_dict:
            due_dict.pop("string", None)
    return due_dict


def update_next_recurrence_due_dates(api, overdue_tasks, tz):
    """Update due dates for overdue tasks when their next recurrence is due.

    Returns True when any updates were performed.
    """
    # The tz parameter is accepted for API compatibility; keep a local
    # reference to avoid unused-argument lint warnings.
    _ = tz
    # Use naive local date for comparison to match tests' expectations.
    today = datetime.now().date()
    updated_any = False
    for task in overdue_tasks:
        due = task.get("due", {})
        next_recur = due.get("next_recurrence_date")
        if not next_recur:
            continue
        try:
            next_recur_date = datetime.fromisoformat(next_recur).date()
        except (ValueError, TypeError):
            continue
        if next_recur_date <= today:
            due_string = due.get("string") or "every day"
            try:
                api.update_task(task["id"], due_date=today, due_string=due_string)
                updated_any = True
            except (KeyError, AttributeError) as exc:
                logger.error(
                    "Failed to update due date for recurring overdue task %s: %s",
                    task.get("id", "?"),
                    exc,
                )
    return updated_any


def _split_not_overdue_tasks(not_overdue_tasks, tz):
    """Split not-overdue tasks into those due today and those in the future.

    Uses the provided timezone to compute the current local date.
    """
    # Use tz-aware 'today' based on provided tz so callers can control the
    # timezone used for classification.
    today = datetime.now(tz).date()
    today_tasks = []
    future_tasks = []
    for t in not_overdue_tasks:
        due = t.get("due") or {}
        due_date = due.get("date")
        try:
            if (
                due_date
                and "T" not in due_date
                and datetime.fromisoformat(due_date).date() == today
            ):
                today_tasks.append(t)
            elif due_date and "T" in due_date:
                dt = datetime.fromisoformat(due_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                if dt.date() == today:
                    today_tasks.append(t)
                else:
                    future_tasks.append(t)
            else:
                future_tasks.append(t)
        except (ValueError, TypeError):
            future_tasks.append(t)
    return today_tasks, future_tasks


def _task_sort_key(task, tz):
    """Return a tuple key used to sort tasks by due date, id and text."""
    due = task.get("due") or {}
    due_date = due.get("date")
    try:
        if due_date:
            if "T" in due_date:
                dt = datetime.fromisoformat(due_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                date_key = dt.date()
            else:
                date_key = datetime.fromisoformat(due_date).date()
        else:
            date_key = datetime.max.date()
    except (ValueError, TypeError):
        date_key = datetime.max.date()

    parts = task.get("title", {}).get("parts", {}) or {}
    id_key = parts.get("id") or ""
    text_key = (parts.get("text") or "").lower()
    return (date_key, id_key, text_key)


def _detect_frequencies(labels):
    """Return detected frequency label objects for a list of labels.

    Labels which are not recognized are ignored.
    """
    result = []
    for lab in labels:
        try:
            freq_obj = FrequencyLabels.from_label(lab)
        except KeyError:
            continue
        result.append(
            {"emoji": freq_obj.emoji, "name": freq_obj.name, "number": freq_obj.number}
        )
    return result


def _has_non_frequency_label(labels):
    """Return True if any label is not a recognized frequency label."""
    for lab in labels:
        try:
            _ = FrequencyLabels.from_label(lab)
        except KeyError:
            return True
    return False


def _infer_next_weekday_recurrence(due_dt, recur_str):
    """Infer the next weekday recurrence date from a recurrence string.

    Expects a recurrence string containing a weekday name (short form).
    Supports both Spanish and English weekday names from Todoist.
    Returns an ISO date string for the next occurrence or None.
    """
    # Weekday mapping: Spanish and English short forms to Python weekday index (0=Monday)
    # Spanish: lun, mar, mié, jue, vie, sáb, dom
    # English: mon, tue, wed, thu, fri, sat, sun
    weekday_map = {
        "lun": 0,  # Monday (lunes)
        "mar": 1,  # Tuesday (martes)
        "mié": 2,  # Wednesday (miércoles)
        "mie": 2,  # Wednesday (alternate spelling)
        "jue": 3,  # Thursday (jueves)
        "vie": 4,  # Friday (viernes)
        "sáb": 5,  # Saturday (sábado)
        "sab": 5,  # Saturday (alternate spelling)
        "dom": 6,  # Sunday (domingo)
        "mon": 0,  # Monday
        "tue": 1,  # Tuesday
        "wed": 2,  # Wednesday
        "thu": 3,  # Thursday
        "fri": 4,  # Friday
        "sat": 5,  # Saturday
        "sun": 6,  # Sunday
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


def build_title_object(parts_of_the_title, title_is_valid, content):
    """Build a title metadata object used by the JSON output."""
    combined = None
    if isinstance(parts_of_the_title, dict):
        # Add parentheses to ID when building combined
        ticket_id = parts_of_the_title.get("id") or ""
        if ticket_id:
            ticket_id = f"({ticket_id})"
        combined = (
            (parts_of_the_title.get("freq") or "")
            + ticket_id
            + (parts_of_the_title.get("ticket_emoji") or "")
            + (parts_of_the_title.get("text") or "")
        )
    title_obj = {"is_complete": title_is_valid}
    if combined is not None:
        title_obj["combined"] = combined
    to_replace = bool(
        combined is not None
        and title_is_valid
        and isinstance(content, str)
        and content != combined
    )
    title_obj["to_replace"] = to_replace
    title_obj["parts"] = parts_of_the_title
    return title_obj


def is_task_overdue(due_dict, now, tz):
    """Return whether the given due dictionary represents an overdue task.

    Returns True/False when evaluation succeeds, or None when the due value
    cannot be parsed.
    """
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
        return None


def categorize_tasks(tasks, now=None):
    """Categorize a list of Todoist task objects into overdue and not overdue.

    Returns a tuple of (overdue_tasks, not_overdue_tasks) where each item is a
    list of plain dictionaries suitable for JSON serialization.
    """
    overdue_tasks = []
    not_overdue_tasks = []
    tz = get_timezone()
    # Use naive local now by default so date-only comparisons match tests that
    # use `datetime.now().date()` (which is naive/local time).
    now = datetime.now() if now is None else now
    for task in tasks:
        labels = getattr(task, "labels", [])
        due_dict = _process_due_obj(getattr(task, "due", None))
        task_data = {
            "id": task.id,
            "content": task.content,
            "due": due_dict,
            "labels": labels,
        }
        freq_list = _detect_frequencies(labels)
        freq_count = len(freq_list)
        title_is_valid, parts_of_the_title = validate_ticket_name(task.content)
        task_data["title"] = build_title_object(
            parts_of_the_title, title_is_valid, task.content
        )
        is_valid = False
        if isinstance(parts_of_the_title, dict) and freq_count == 1:
            is_valid = bool(
                freq_list[0].get("emoji") is not None
                and parts_of_the_title.get("freq") is not None
                and freq_list[0].get("emoji") == parts_of_the_title.get("freq")
            )
        task_data["frequency_labels"] = {
            "list": freq_list,
            "count": freq_count,
            "frequency_matches_label": is_valid,
            "has_non_frequency": _has_non_frequency_label(labels),
        }
        if not title_is_valid:
            logger.warning(
                "Task %s has invalid ticket format: %s",
                task.id if hasattr(task, "id") else "?",
                task.content,
            )
        if due_dict and due_dict.get("date"):
            overdue = is_task_overdue(due_dict, now, tz)
            if overdue is None:
                logger.warning(
                    "Could not parse due date for task %s", getattr(task, "id", "?")
                )
                not_overdue_tasks.append(task_data)
            elif overdue:
                overdue_tasks.append(task_data)
            else:
                not_overdue_tasks.append(task_data)
        else:
            not_overdue_tasks.append(task_data)
    return overdue_tasks, not_overdue_tasks


# Public aliases matching original names in `src.main`
process_due_obj = _process_due_obj
_update_next_recurrence_due_dates = update_next_recurrence_due_dates
