"""Portable action vocabulary shared by browser and desktop environments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionKind(StrEnum):
    CLICK = "click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    WAIT = "wait"
    FINISH = "finish"


@dataclass(frozen=True, slots=True)
class Action:
    """One environment action; coordinates are normalized to the 0–1000 range."""

    kind: ActionKind
    x: int | None = None
    y: int | None = None
    text: str | None = None
    key: str | None = None
    direction: str | None = None
    amount: int | None = None

    def __post_init__(self) -> None:
        if self.kind is ActionKind.CLICK:
            self._require_coordinates()
        elif self.kind is ActionKind.TYPE and not self.text:
            raise ValueError("type action requires non-empty text")
        elif self.kind is ActionKind.KEY and not self.key:
            raise ValueError("key action requires a key name")
        elif self.kind is ActionKind.SCROLL:
            if self.direction not in {"up", "down", "left", "right"}:
                raise ValueError("scroll direction must be up, down, left, or right")
            if self.amount is None or self.amount <= 0:
                raise ValueError("scroll action requires a positive amount")
        elif self.kind is ActionKind.WAIT:
            if self.amount is None or self.amount <= 0:
                raise ValueError("wait action requires a positive duration in ms")

    def _require_coordinates(self) -> None:
        if self.x is None or self.y is None:
            raise ValueError("click action requires x and y")
        if not (0 <= self.x <= 1000 and 0 <= self.y <= 1000):
            raise ValueError("click coordinates must be in the 0–1000 range")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "key": self.key,
            "direction": self.direction,
            "amount": self.amount,
        }
