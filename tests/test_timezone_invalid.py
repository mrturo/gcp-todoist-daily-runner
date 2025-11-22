"""Tests around timezone handling in the core processing module.

These tests intentionally import `src.core.processing` after setting the
environment to exercise import-time behaviour.
"""

import logging

# Pylint complains about imports inside the test function, but this import is
# intentional so we can set the environment variable before importing the
# module under test.
# pylint: disable=import-outside-toplevel


def test_get_timezone_invalid(monkeypatch, caplog):
    """Simulate an invalid TIME_ZONE to exercise the fallback logging path."""
    monkeypatch.setenv("TIME_ZONE", "Invalid/Timezone")
    import src.core.processing as proc

    caplog.set_level(logging.WARNING)
    tz = proc.get_timezone()
    assert tz is not None
    assert any("Invalid TIME_ZONE" in r.getMessage() for r in caplog.records)
