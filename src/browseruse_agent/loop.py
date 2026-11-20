"""Single-model observe–propose–execute loop with JSONL trajectory logging."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO
from uuid import uuid4

from .actions import Action, ActionKind
from .interfaces import Environment, Model, Observation


@dataclass(frozen=True, slots=True)
class RunSummary:
    run_id: str
    task_id: str
    goal: str
    model: str
    environment: str
    steps: int
    elapsed_seconds: float
    terminated: bool
    truncated: bool
    success: bool | None
    stop_reason: str | None


class AgentLoop:
    def __init__(self, model: Model, environment: Environment, max_steps: int = 30):
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.model = model
        self.environment = environment
        self.max_steps = max_steps

    def run(self, task_id: str, log_path: Path) -> RunSummary:
        run_id = str(uuid4())
        started = time.monotonic()
        reset_context = getattr(self.model, "reset_context", None)
        if callable(reset_context):
            reset_context()
        goal, observation = self.environment.reset(task_id)
        steps = 0
        terminated = False
        truncated = False
        success: bool | None = None
        stop_reason: str | None = None
        previous_action: dict[str, object] | None = None
        previous_observation_sha256: str | None = None

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            self._write(log, self._event("run_started", run_id, task_id, goal, observation))
            for step_index in range(self.max_steps):
                proposed = self.model.propose(goal, observation)
                self._write(
                    log,
                    self._event(
                        "action_proposed", run_id, task_id, goal, observation,
                        action=proposed.to_dict(), step_index=step_index,
                    ),
                )
                steps += 1
                observation_sha256 = hashlib.sha256(
                    observation.screenshot.read_bytes()
                ).hexdigest()
                if (
                    proposed.kind is not ActionKind.WAIT
                    and proposed.to_dict() == previous_action
                    and observation_sha256 == previous_observation_sha256
                ):
                    stop_reason = "repeated_action_without_visual_change"
                    truncated = True
                    success = False
                    self._write(
                        log,
                        self._event(
                            "action_skipped", run_id, task_id, goal, observation,
                            action=proposed.to_dict(),
                            step_index=step_index,
                            reason=stop_reason,
                        ),
                    )
                    break
                if proposed.kind is ActionKind.FINISH:
                    terminated = True
                    break

                result = self.environment.step(proposed)
                previous_action = proposed.to_dict()
                previous_observation_sha256 = observation_sha256
                observation = result.observation
                terminated = result.terminated
                truncated = result.truncated
                if "success" in result.info:
                    success = bool(result.info["success"])
                self._write(
                    log,
                    self._event(
                        "action_executed", run_id, task_id, goal, observation,
                        action=proposed.to_dict(),
                        step_index=step_index,
                        terminated=terminated,
                        truncated=truncated,
                        info=result.info,
                    ),
                )
                if terminated or truncated:
                    break
            else:
                truncated = True

        if success is None:
            success = self.environment.evaluate()

        summary = RunSummary(
            run_id=run_id,
            task_id=task_id,
            goal=goal,
            model=self.model.name,
            environment=self.environment.name,
            steps=steps,
            elapsed_seconds=time.monotonic() - started,
            terminated=terminated,
            truncated=truncated,
            success=success,
            stop_reason=stop_reason,
        )
        with log_path.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "run_finished",
                        **asdict(summary),
                    },
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )
        return summary

    @staticmethod
    def _event(
        event: str,
        run_id: str,
        task_id: str,
        goal: str,
        observation: Observation,
        **fields: object,
    ) -> dict[str, object]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "run_id": run_id,
            "task_id": task_id,
            "goal": goal,
            "observation": {
                "screenshot": str(observation.screenshot),
                "width": observation.width,
                "height": observation.height,
                "step_index": observation.step_index,
                "metadata": observation.metadata,
            },
            **fields,
        }

    @staticmethod
    def _write(log: TextIO, event: dict[str, object]) -> None:
        log.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        log.flush()
