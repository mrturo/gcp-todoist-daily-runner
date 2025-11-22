"""
Unit tests for src/frequency_labels.py to achieve 100% coverage.
"""

import pytest

from src.utils.frequency_labels import Frequency, FrequencyLabels


def test_frequency_labels_property():
    """Test the label property of Frequency."""
    freq = Frequency(emoji="🟢", name="daily", number=1)
    if not freq.label == "🟢frequency-01-daily":
        raise AssertionError(f"Expected label '🟢frequency-01-daily', got {freq.label}")


def test_frequency_labels_all_labels():
    """Test that all_labels returns all frequency label strings."""
    labels = FrequencyLabels.all_labels()
    if not isinstance(labels, list):
        raise AssertionError(f"Expected labels to be list, got {type(labels)}")
    if not all(isinstance(label, str) for label in labels):
        raise AssertionError("All labels should be strings")
    # Should contain all defined labels
    if not FrequencyLabels.DAILY.label in labels:
        raise AssertionError("DAILY label missing in labels")
    if not FrequencyLabels.MULTIWEEKLY.label in labels:
        raise AssertionError("MULTIWEEKLY label missing in labels")
    if not FrequencyLabels.WEEKLY.label in labels:
        raise AssertionError("WEEKLY label missing in labels")
    if not FrequencyLabels.MONTHLY.label in labels:
        raise AssertionError("MONTHLY label missing in labels")
    if not FrequencyLabels.MULTIMONTHLY.label in labels:
        raise AssertionError("MULTIMONTHLY label missing in labels")


def test_frequencylabels_from_label_returns_frequency():
    """Test from_label returns the correct Frequency object."""
    label = FrequencyLabels.DAILY.label
    freq = FrequencyLabels.from_label(label)
    if not isinstance(freq, Frequency):
        raise AssertionError(f"Expected freq to be Frequency, got {type(freq)}")
    if not freq.name == "daily":
        raise AssertionError(f"Expected freq.name 'daily', got {freq.name}")


def test_frequencylabels_from_label_invalid():
    """Test from_label raises KeyError for invalid label."""
    with pytest.raises(KeyError):
        FrequencyLabels.from_label("invalid-label")
