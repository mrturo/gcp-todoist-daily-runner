"""Tests for the ticket-name validator utilities.

These unit tests exercise common valid and invalid inputs for
``validate_ticket_name``.
"""

from src.utils.validators import validate_ticket_name


def test_valid_example():
    """Valid example with single emojis and a normal title."""
    s = "🟢(B01-16-00)📴Stop all phone apps"
    ok, parts = validate_ticket_name(s)
    assert ok
    assert parts["freq"].strip() == "🟢"
    assert parts["id"] == "B01-16-00"
    assert parts["ticket_emoji"].strip() == "📴"
    assert parts["text"] == "Stop all phone apps"


def test_missing_parts():
    """Missing leading emoji should be rejected."""
    s = "(B01-16-00)📴No freq emoji"
    ok, _ = validate_ticket_name(s)
    assert not ok


def test_bad_id_format():
    """ID not matching the expected pattern should be rejected."""
    s = "🟢(BAD-ID)📴Title"
    ok, _ = validate_ticket_name(s)
    assert not ok


def test_short_title():
    """Titles shorter than the minimum length should be rejected."""
    s = "🟢(B01-16-00)📴A"
    ok, _ = validate_ticket_name(s, min_title_len=2)
    assert not ok


def test_multiple_emojis_ok():
    """Multiple emojis at the start are accepted by the parser."""
    s = "🟢🔵(B01-16-00)📴Multiple emojis at start"
    ok, parts = validate_ticket_name(s)
    assert ok
    assert parts["freq"].startswith("🟢")
    assert parts["id"] == "B01-16-00"


def test_non_string_input():
    """Non-string inputs must return (False, None)."""
    ok, parts = validate_ticket_name(None)
    assert not ok and parts is None
    ok, parts = validate_ticket_name(123)
    assert not ok and parts is None


def test_title_exact_min_length():
    """Title exactly equal to min_title_len should be accepted."""
    s = "🟢(B01-16-00)📴Hey"
    ok, parts = validate_ticket_name(s, min_title_len=3)
    assert ok
    assert parts["text"] == "Hey"


def test_title_short_with_space_before():
    """Ensure branch for short title when pattern matches with a space before title."""
    s = "🟢(B01-16-00)📴 A"
    ok, parts = validate_ticket_name(s, min_title_len=2)
    assert not ok and parts is None
