"""BrowserGym adapter that exposes screenshot-only observations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .actions import Action, ActionKind
from .interfaces import Observation, StepResult


class BrowserGymEnvironment:
    """Wrap a BrowserGym task behind the project Environment protocol.

    BrowserGym returns richer observations than this agent currently uses.
    This adapter deliberately exposes only the goal and screenshot, keeping
    DOM and accessibility information out of the model input for the initial
    screenshot-only condition.
    """

    name = "browsergym"

    def __init__(
        self,
        task_id: str,
        screenshot_dir: Path = Path(".agent_runs/screenshots"),
        seed: int = 0,
        headless: bool = True,
    ) -> None:
        self.task_id = task_id
        self.screenshot_dir = screenshot_dir
        self.seed = seed
        self.headless = headless
        self._env: Any | None = None
        self._goal = ""
        self._step_index = 0
        self._width = 0
        self._height = 0
        self._last_success: bool | None = None

    def reset(self, task_id: str) -> tuple[str, Observation]:
        import gymnasium as gym

        if self._env is not None:
            self.close()
        self.task_id = task_id
        self._register_task_family(task_id)
        self._env = gym.make(task_id, headless=self.headless)
        raw_observation, _info = self._env.reset(seed=self.seed)
        self._goal = str(raw_observation.get("goal", ""))
        self._step_index = 0
        self._last_success = None
        return self._goal, self._make_observation(raw_observation)

    def step(self, action: Action) -> StepResult:
        if self._env is None:
            raise RuntimeError("call reset(task_id) before step(action)")
        if action.kind is ActionKind.FINISH:
            raise ValueError("finish is a runner-level action, not a BrowserGym action")

        browsergym_action = self._encode_action(action)
        raw_observation, reward, terminated, truncated, _info = self._env.step(
            browsergym_action
        )
        self._step_index += 1
        if terminated:
            self._last_success = float(reward) > 0.0
        result_info: dict[str, object] = {"reward": float(reward)}
        if terminated:
            result_info["success"] = self._last_success
        return StepResult(
            observation=self._make_observation(raw_observation),
            terminated=bool(terminated),
            truncated=bool(truncated),
            info=result_info,
        )

    def evaluate(self) -> bool | None:
        """Return BrowserGym's terminal reward-derived success, if available."""
        return self._last_success

    def close(self) -> None:
        if self._env is not None:
            self._env.close()
            self._env = None

    def _make_observation(self, raw: dict[str, Any]) -> Observation:
        from PIL import Image

        screenshot = raw.get("screenshot")
        if screenshot is None:
            raise ValueError("BrowserGym observation did not include a screenshot")
        height, width = screenshot.shape[:2]
        self._width, self._height = int(width), int(height)
        safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.task_id)
        image_path = self.screenshot_dir / safe_task_id / f"step-{self._step_index:04d}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(screenshot).save(image_path)
        return Observation(
            screenshot=image_path,
            width=self._width,
            height=self._height,
            step_index=self._step_index,
        )

    def _encode_action(self, action: Action) -> str:
        if action.kind is ActionKind.CLICK:
            x = self._pixel(action.x, self._width)
            y = self._pixel(action.y, self._height)
            return f"mouse_click({x}, {y}, 'left')"
        if action.kind is ActionKind.TYPE:
            return f"keyboard_type({action.text!r})"
        if action.kind is ActionKind.KEY:
            return f"keyboard_press({action.key!r})"
        if action.kind is ActionKind.SCROLL:
            amount = int(action.amount or 0)
            dx, dy = {
                "up": (0, -amount),
                "down": (0, amount),
                "left": (-amount, 0),
                "right": (amount, 0),
            }[action.direction or "down"]
            return f"scroll({dx}, {dy})"
        if action.kind is ActionKind.WAIT:
            # BrowserGym advances on each action; noop provides a safe turn.
            return "noop()"
        raise ValueError(f"unsupported BrowserGym action: {action.kind}")

    @staticmethod
    def _pixel(coordinate: int | None, extent: int) -> int:
        if coordinate is None:
            raise ValueError("click action requires x and y coordinates")
        if extent <= 0:
            raise RuntimeError("reset the environment before sending coordinates")
        return round((coordinate / 1000) * (extent - 1))

    @staticmethod
    def _register_task_family(task_id: str) -> None:
        """Import the relevant package so Gymnasium registers task IDs."""
        if task_id.startswith("browsergym/workarena"):
            import browsergym.workarena  # noqa: F401
        elif task_id.startswith("browsergym/miniwob"):
            import browsergym.miniwob  # noqa: F401
        elif task_id.startswith("browsergym/webarena"):
            import browsergym.webarena  # noqa: F401
        else:
            import browsergym.core  # noqa: F401
