"""Tests for non-frequency label detection helpers.

These ensure we can detect when a task has labels that are not
recognized as frequency labels.
"""

from src.main import _detect_frequencies, _has_non_frequency_label
from src.utils.frequency_labels import FrequencyLabels


def test_has_non_frequency_label_true_and_false():
    """Return False when only frequency labels present, True otherwise."""
    labels_with_freq = [FrequencyLabels.DAILY.label]
    assert not _has_non_frequency_label(labels_with_freq)

    labels_with_other = [FrequencyLabels.DAILY.label, "urgent"]
    assert _has_non_frequency_label(labels_with_other)


def test_detect_frequencies_returns_list():
    """Detect frequency labels and ignore non-frequency labels."""
    labs = [FrequencyLabels.WEEKLY.label, "misc"]
    freqs = _detect_frequencies(labs)
    assert isinstance(freqs, list)
    assert len(freqs) == 1
    assert freqs[0]["name"] == FrequencyLabels.WEEKLY.name
