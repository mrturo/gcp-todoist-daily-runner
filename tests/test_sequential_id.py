"""Tests for sequential_id validation in task titles."""

from unittest.mock import MagicMock

import src.main as main_module
from src.main import _validate_sequential_id


def test_validate_sequential_id_first_id():
    """Test that the first ID (A01-01-00) is always valid."""
    all_ids = {"A01-01-00"}
    assert _validate_sequential_id("A01-01-00", all_ids) is True


def test_validate_sequential_id_with_prerequisites():
    """Test that IDs with proper prerequisites are valid."""
    all_ids = {
        "A01-01-00",
        "A01-02-00",
        "A02-01-00",
    }
    # A02-01-00 should be valid because A01-* exists
    assert _validate_sequential_id("A02-01-00", all_ids) is True
    # A01-02-00 should be valid because A01-01-* exists
    assert _validate_sequential_id("A01-02-00", all_ids) is True


def test_validate_sequential_id_missing_first_part_prerequisites():
    """Test that IDs without proper first part prerequisites are invalid."""
    all_ids = {
        "C01-01-00",
        "C03-01-00",  # Missing C02-*
    }
    # C03-01-00 should be invalid because C02-* is missing
    assert _validate_sequential_id("C03-01-00", all_ids) is False


def test_validate_sequential_id_missing_second_part_prerequisites():
    """Test that IDs without proper second part prerequisites are invalid."""
    all_ids = {
        "D01-01-00",
        "D01-03-00",  # Missing D01-02-*
    }
    # D01-03-00 should be invalid because D01-02-* is missing
    assert _validate_sequential_id("D01-03-00", all_ids) is False


def test_validate_sequential_id_complex_case():
    """Test a complex case with multiple prerequisites."""
    all_ids = {
        "A01-01-00",
        "A01-02-00",
        "A02-01-00",
        "A02-02-00",
        "A03-01-00",
        "A03-02-00",
        "A03-03-00",
    }
    # A03-03-00 should be valid: has A01-*, A02-*, A03-01-*, A03-02-*
    assert _validate_sequential_id("A03-03-00", all_ids) is True


def test_validate_sequential_id_invalid_format():
    """Test that invalid ID formats return False."""
    all_ids = {"A01-01-00"}
    assert _validate_sequential_id("", all_ids) is False
    assert _validate_sequential_id(None, all_ids) is False
    assert _validate_sequential_id("invalid", all_ids) is False
    assert _validate_sequential_id("A01-01", all_ids) is False
    assert _validate_sequential_id("01-01-00", all_ids) is False


def test_validate_sequential_id_real_world_data():
    """Test with real-world data from the log file."""
    all_ids = {
        "C03-03-00",
        "C04-01-00",
        "C04-02-00",
        "D01-02-00",
        "D01-03-00",
        "D01-05-00",
        "D01-06-00",
        "D01-08-00",
        "D01-09-00",
        "D01-11-00",
        "D03-01-00",
        "D03-03-00",
        "D03-05-00",
        "D03-07-00",
        "D05-02-00",
        "C03-02-00",
        "A01-01-00",
        "A01-02-00",
        "A01-03-00",
        "A02-01-00",
        "A02-02-00",
    }

    # These should be valid
    assert _validate_sequential_id("A01-01-00", all_ids) is True
    assert _validate_sequential_id("A01-02-00", all_ids) is True
    assert _validate_sequential_id("A01-03-00", all_ids) is True
    assert _validate_sequential_id("A02-01-00", all_ids) is True
    assert _validate_sequential_id("A02-02-00", all_ids) is True

    # These should be invalid (missing prerequisites)
    assert (
        _validate_sequential_id("C03-03-00", all_ids) is False
    )  # Missing C01-*, C02-*
    assert (
        _validate_sequential_id("C04-01-00", all_ids) is False
    )  # Missing C01-*, C02-*, C03-*
    assert _validate_sequential_id("D01-05-00", all_ids) is False  # Missing D01-04-*
    assert (
        _validate_sequential_id("D05-02-00", all_ids) is False
    )  # Missing D02-*, D04-*


def test_sequential_id_in_integration_response(monkeypatch):
    """Test that sequential_id is included in the integration response."""
    # This test will verify that the response structure includes sequential_id
    # after duplicated_id
    mock_api = MagicMock()
    mock_tasks = [
        {
            "id": "task1",
            "content": "🟡(A01-01-00)📝First Task",
            "due": {"date": "2026-01-01", "is_recurring": False},
            "labels": ["🟡frequency-03-weekly"],
        },
        {
            "id": "task2",
            "content": "🟡(A01-02-00)📝Second Task",
            "due": {"date": "2026-01-01", "is_recurring": False},
            "labels": ["🟡frequency-03-weekly"],
        },
    ]

    monkeypatch.setattr(main_module, "get_todoist_token", lambda: "fake_token")
    monkeypatch.setattr(main_module, "TodoistAPI", lambda token: mock_api)
    monkeypatch.setattr(main_module, "fetch_tasks", lambda api: mock_tasks)
