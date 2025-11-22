"""Frequency label definitions for Todoist tasks."""

from dataclasses import dataclass
from typing import ClassVar, Dict


@dataclass(frozen=True)
class Frequency:
    """Represents a Todoist task frequency with emoji, name, and number."""

    emoji: str
    name: str
    number: int

    @property
    def label(self) -> str:
        """Build the label dynamically from emoji, number, and name."""
        return f"{self.emoji}frequency-{self.number:02d}-{self.name}"


class FrequencyLabels:
    """Frequency label objects for Todoist tasks."""

    DAILY: ClassVar[Frequency] = Frequency(emoji="🟢", name="daily", number=1)
    MULTIWEEKLY: ClassVar[Frequency] = Frequency(
        emoji="🔵", name="multiweekly", number=2
    )
    WEEKLY: ClassVar[Frequency] = Frequency(emoji="🟡", name="weekly", number=3)
    MULTIMONTHLY: ClassVar[Frequency] = Frequency(
        emoji="🟠", name="multimonthly", number=4
    )
    MONTHLY: ClassVar[Frequency] = Frequency(emoji="🔴", name="monthly", number=5)

    _LABEL_MAP: ClassVar[Dict[str, Frequency]] = {
        DAILY.label: DAILY,
        MULTIWEEKLY.label: MULTIWEEKLY,
        WEEKLY.label: WEEKLY,
        MONTHLY.label: MONTHLY,
        MULTIMONTHLY.label: MULTIMONTHLY,
    }

    @classmethod
    def from_label(cls, label: str) -> Frequency:
        """Get Frequency object from label string."""
        return cls._LABEL_MAP[label]

    @classmethod
    def all_labels(cls) -> list:
        """Return all frequency label strings."""
        return list(cls._LABEL_MAP.keys())
