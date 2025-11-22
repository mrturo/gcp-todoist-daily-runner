"""Tests for frequency detection on tasks' labels."""

from src.main import categorize_tasks
from src.utils.frequency_labels import FrequencyLabels


class SimpleTask:  # pylint: disable=too-few-public-methods
    """Minimal task-like object for categorize_tasks tests."""

    def __init__(self, id_, content, labels=None):
        self.id = id_
        self.content = content
        self.due = None
        self.labels = labels or []


def test_categorize_tasks_includes_frequency_for_frequency_labels():
    """A task with a frequency label should include `frequency` with properties."""
    label = FrequencyLabels.DAILY.label
    t = SimpleTask("1", "irrelevant", labels=[label])
    _overdue, not_overdue = categorize_tasks([t])
    assert len(not_overdue) == 1
    entry = not_overdue[0]
    assert "frequency_labels" in entry
    freq_obj = entry["frequency_labels"]
    assert isinstance(freq_obj, dict)
    freq_list = freq_obj["list"]
    assert isinstance(freq_list, list)
    assert len(freq_list) == 1
    freq = freq_list[0]
    assert freq["emoji"] == FrequencyLabels.DAILY.emoji
    assert freq["name"] == FrequencyLabels.DAILY.name
    assert freq["number"] == FrequencyLabels.DAILY.number
    assert "count" in freq_obj
    assert freq_obj["count"] == 1
    # When one frequency label is present and parsed title freq equals the label
    # emoji, `valid` should be True. `SimpleTask` here does not
    # include a parsed title, so `parts.freq` will be None; in this test we only
    # assert the flag exists and is a boolean. Matching behavior is tested
    # separately below.
    assert "frequency_matches_label" in freq_obj
    assert isinstance(freq_obj["frequency_matches_label"], bool)


def test_valid_true_when_label_matches_title_freq():
    """When one frequency label exists and title freq equals label emoji."""
    label = FrequencyLabels.DAILY.label
    # Build a content string that validate_ticket_name will parse: freq + id + ticket emoji + text
    freq = FrequencyLabels.DAILY.emoji
    content = freq + "(A01-01-00)" + "📌" + "DoThing"
    t = SimpleTask("2", content, labels=[label])
    _overdue, not_overdue = categorize_tasks([t])
    entry = not_overdue[0]
    assert entry["frequency_labels"]["count"] == 1
    assert entry["frequency_labels"]["frequency_matches_label"] is True
