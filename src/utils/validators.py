"""Validator utilities for ticket-like names.

Provides a single function `validate_ticket_name` that checks a string
contains: a leading frequency emoji, an ID like ``(B01-16-00)``, a ticket
emoji, and a non-empty title. The implementation is intentionally
permissive with emoji detection to avoid depending on exhaustive Unicode
ranges; it enforces a strict ID format and a minimum title length.
"""

import re
from typing import Dict, Optional, Tuple

# Pattern: <emoji-like-group> (ID) <emoji-like-group> <title>
# Use a permissive non-whitespace token for emoji groups so modern emoji
# and variants are accepted without depending on exhaustive Unicode ranges.
_PATTERN = (
    r"^\s*"
    r"(?P<freq>\S+?)\s*"
    r"(?P<id>\([A-Z]\d{2}-\d{2}-\d{2}\))\s*"
    r"(?P<ticket_emoji>\W)\s*"
    r"(?P<title>.+\S)\s*$"
)

_RE = re.compile(_PATTERN, flags=re.UNICODE)

# Regex to detect leading emoji characters in the title.
# Covers common emoji Unicode ranges (pictographs, emoticons, symbols).
_EMOJI_RANGES = (
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U00002600-\U000026ff"
    "\U00002700-\U000027bf"
    "\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff"
)
# Compile a pattern that captures leading emoji sequence and the rest of the title.
_LEADING_EMOJI_RE = re.compile(
    rf"^(?P<lead>[{_EMOJI_RANGES}]+)\s*(?P<rest>.*)$", flags=re.UNICODE
)

# Characters to trim from the ends of titles (invisible / variation selectors)
_INVISIBLE_EDGE_CHARS_RE = re.compile(
    r"^[\uFE0E\uFE0F\u200D\u200B\uFEFF]+|[\uFE0E\uFE0F\u200D\u200B\uFEFF]+$"
)


def validate_ticket_name(
    s: str, min_title_len: int = 3
) -> Tuple[bool, Optional[Dict[str, str]]]:
    """Return (ok, parts) if ``s`` matches the ticket-name pattern.

    ``parts`` contains the keys: ``freq``, ``id``, ``ticket_emoji`` and
    ``text``. If validation fails the function returns ``(False, None)``.
    """
    if not isinstance(s, str):
        return False, None
    m = _RE.match(s)
    if not m:
        return False, None
    parts = m.groupdict()
    title = parts.get("title", "").strip()
    # If title starts with one or more emoji, move them into ticket_emoji
    m2 = _LEADING_EMOJI_RE.match(title)
    if m2:
        lead = m2.group("lead")
        rest = m2.group("rest").strip()
        # Append lead emoji(s) to the extracted ticket_emoji
        parts["ticket_emoji"] = (parts.get("ticket_emoji", "") or "") + lead
        title = rest

    # Remove any asterisks (e.g., Markdown bold/italic markers) from title
    if isinstance(title, str) and "*" in title:
        title = title.replace("*", "").strip()

    # Trim invisible edge characters (variation selectors, zero-width joiners, BOM)
    if isinstance(title, str) and title:
        title = _INVISIBLE_EDGE_CHARS_RE.sub("", title).strip()

    if len(title) < min_title_len:
        return False, None
    # Use `text` as the canonical key for the extracted title text
    parts["text"] = title
    # Remove the original regex group name to avoid duplication
    if "title" in parts:
        parts.pop("title", None)
    # Store ID without parentheses
    if "id" in parts and parts["id"]:
        parts["id"] = parts["id"].strip("()")
    return True, parts
