"""Extra tests for `validate_ticket_name` covering edge cases.

These tests exercise leading-emoji handling, stripping Markdown
asterisk markers, and trimming invisible/variation selector characters.
"""

from src.utils.validators import validate_ticket_name


def test_leading_emoji_in_title_appended_to_ticket_emoji():
    """Leading emoji in the title should be appended to `ticket_emoji`."""
    s = "🟢(B01-16-00)📴📊Stop with emoji"
    ok, parts = validate_ticket_name(s)
    assert ok
    assert parts["id"] == "B01-16-00"
    # ticket_emoji should include both the original and the leading title emoji
    assert parts["ticket_emoji"].strip() == "📴📊"
    assert parts["text"] == "Stop with emoji"


def test_strip_asterisks_from_title():
    """Asterisks used for Markdown emphasis should be removed from title text."""
    s = "🟢(B01-16-00)📴**Bold Title**"
    ok, parts = validate_ticket_name(s)
    assert ok
    assert parts["id"] == "B01-16-00"
    assert parts["text"] == "Bold Title"


def test_trim_invisible_edge_chars():
    """Invisible/variation selector characters around the title are trimmed."""
    invisible = "\ufe0f"
    s = f"🟢(B01-16-00)📴{invisible}Visible Title"
    ok, parts = validate_ticket_name(s)
    assert ok
    assert parts["id"] == "B01-16-00"
    assert parts["text"] == "Visible Title"
