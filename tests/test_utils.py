"""Test utility functions for response validation."""

# pylint: disable=duplicate-code


def assert_error_response(response, expected_detail=None):
    """Assert that a response is a 500 error with status 'error'."""
    if response.status_code != 500:
        raise AssertionError(f"Expected status_code 500, got {response.status_code}")
    data = response.json()
    if data["status"] != "error":
        raise AssertionError(f"Expected status 'error', got {data['status']}")
    if expected_detail is not None and expected_detail not in data["detail"]:
        raise AssertionError(
            f"Expected '{expected_detail}' in detail, got {data['detail']}"
        )


# pylint: disable=too-few-public-methods


class FakeDue:
    """Reusable test double for due object (single public method)."""

    def __init__(self, due_dict):
        """Initialize with a due dict."""
        self._due_dict = due_dict

    def to_dict(self):
        """Return the due dict."""
        return self._due_dict


class FakeTask:
    """Reusable test double for task object (single public method)."""

    def __init__(self, id_, content, due, labels=None):
        """Initialize with id, content, due, and labels."""
        self.id = id_
        self.content = content
        self.due = due
        self.labels = labels or []


class FakeAPI:
    """Reusable test double for TodoistAPI (single public method)."""

    def __init__(self, token, overdue_task, not_overdue_task):
        """Initialize with token, overdue_task, and not_overdue_task."""
        self.token = token
        self.updated = []
        self.fail = False
        self._overdue_task = overdue_task
        self._not_overdue_task = not_overdue_task

    def update_task(self, task_id, due_date, due_string):
        """Mock update_task method."""
        if self.fail:
            raise KeyError("fail")
        self.updated.append((task_id, due_date, due_string))

    def get_tasks(self):
        """Mock get_tasks method."""
        return [[self._overdue_task, self._not_overdue_task]]


def fake_categorize_tasks_factory(overdue_id, not_overdue_id):
    """Return a categorize_tasks function for given overdue and not overdue ids."""

    def fake_categorize_tasks(tasks, now=None):
        # pylint: disable=unused-argument
        return [
            {
                "id": t.id,
                "content": t.content,
                "due": t.due.to_dict(),
                "labels": t.labels,
            }
            for t in tasks
            if t.id == overdue_id
        ], [
            {
                "id": t.id,
                "content": t.content,
                "due": t.due.to_dict(),
                "labels": t.labels,
            }
            for t in tasks
            if t.id == not_overdue_id
        ]

    return fake_categorize_tasks


def fake_categorize_all_overdue(tasks, now=None):
    """Categorize all tasks as overdue, none as not overdue. Used for test patching."""
    # pylint: disable=unused-argument
    return [
        {"id": t.id, "content": t.content, "due": t.due.to_dict(), "labels": t.labels}
        for t in tasks
    ], []


class SimpleTask:
    """Simple mock task for categorize_tasks tests (for legacy test compatibility)."""

    def __init__(self, id_, content, due=None, labels=None):
        self.id = id_
        self.content = content
        self.due = due
        self.labels = labels or []


class SimpleDue:
    """Simple mock due object for categorize_tasks tests (for legacy test compatibility)."""

    def __init__(self, date):
        self.date = date

    def to_dict(self):
        """Return the due object as a dictionary with a 'date' key."""
        return {"date": self.date}


# pylint: enable=too-few-public-methods
