"""
Test utilities for test doubles and helpers.
"""


class FakeTask:
    """Fake task for categorize_tasks and recurrence tests."""

    def __init__(self, id_, content, due_dict, labels=None):
        """Initialize FakeTask with id, content, due_dict, and optional labels."""
        self.id = id_
        self.content = content
        self.due = self
        self.labels = labels or []
        self._due_dict = due_dict

    def to_dict(self):
        """Return the due dict for this fake task."""
        return self._due_dict

    def dummy(self):
        """Dummy public method for pylint compliance."""
        return None
