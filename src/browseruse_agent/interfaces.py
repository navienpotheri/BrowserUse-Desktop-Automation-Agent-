"""Protocols shared by model backends and benchmark environment adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .actions import Action


@dataclass(frozen=True, slots=True)
class Observation:
    screenshot: Path
    width: int
    height: int
    step_index: int
    accessibility_tree: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StepResult:
    observation: Observation
    terminated: bool = False
    truncated: bool = False
    info: dict[str, object] = field(default_factory=dict)


class Model(Protocol):
    """A model backend that proposes exactly one action per observation."""

    name: str

    def propose(self, goal: str, observation: Observation) -> Action:
        """Return the next action using the current screenshot and task goal."""


class Environment(Protocol):
    """An environment adapter for BrowserGym, OSWorld, or a local simulator."""

    name: str

    def reset(self, task_id: str) -> tuple[str, Observation]:
        """Reset to a benchmark task and return its goal and initial screenshot."""

    def step(self, action: Action) -> StepResult:
        """Execute one action and return the resulting observation."""

    def evaluate(self) -> bool | None:
        """Return benchmark-verified success, or None if the task is unscored."""

    def close(self) -> None:
        """Release browser, VM, or other environment resources."""
