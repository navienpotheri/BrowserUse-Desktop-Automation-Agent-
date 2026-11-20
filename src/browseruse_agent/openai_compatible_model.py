"""OpenAI-compatible vision model backend for local or hosted endpoints."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .actions import Action, ActionKind
from .interfaces import Observation


SYSTEM_PROMPT = """You control a browser using one action per turn.
You receive a task goal, a screenshot, and sometimes an accessibility list of
visible browser controls. Return exactly one JSON object, with
no markdown or extra text, using this schema:
{"kind":"click","x":500,"y":500}
{"kind":"click","target_id":"browsergym-element-id"}
{"kind":"type","text":"text to enter"}
{"kind":"key","key":"ENTER"}
{"kind":"scroll","direction":"down","amount":400}
{"kind":"wait","amount":250}
{"kind":"finish"}
Click coordinates use the full screenshot: x=0 is left, x=1000 is right,
y=0 is top, and y=1000 is bottom. Scale the visible target's position to this
range; do not return pixel coordinates.
When an accessibility list is provided, prefer target_id from that list to
click a named control, and use coordinates only when no suitable target exists.
If the user message includes a previous action and says the screenshot did not
change, treat that action as unsuccessful. Choose a different action or a
corrected target; do not repeat the same click or key without visible progress.
Only use finish when the task appears complete. Never claim success in text."""


class OpenAICompatibleVisionModel:
    """Send goal + screenshot to a Chat Completions-compatible VLM endpoint.

    Defaults to the local Ollama server and Qwen2.5-VL 3B. Override
    MODEL_BASE_URL, MODEL_NAME, and optionally MODEL_API_KEY as needed.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("MODEL_BASE_URL", "http://localhost:11434/v1")
        ).rstrip("/")
        self.model = model or os.environ.get("MODEL_NAME", "qwen2.5vl:3b")
        self.api_key = (
            api_key if api_key is not None else os.environ.get("MODEL_API_KEY", "ollama")
        )
        self.timeout_seconds = timeout_seconds
        if not self.base_url:
            raise ValueError("Set MODEL_BASE_URL to an OpenAI-compatible /v1 endpoint")
        if not self.model:
            raise ValueError("Set MODEL_NAME to the model ID served by that endpoint")
        self.name = self.model
        self._previous_action: dict[str, object] | None = None
        self._previous_screenshot_sha256: str | None = None

    def reset_context(self) -> None:
        """Clear action feedback before starting a new task."""
        self._previous_action = None
        self._previous_screenshot_sha256 = None

    def propose(self, goal: str, observation: Observation) -> Action:
        image_path = Path(observation.screenshot)
        image_mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        image_bytes = image_path.read_bytes()
        image_data = base64.b64encode(image_bytes).decode("ascii")
        screenshot_sha256 = hashlib.sha256(image_bytes).hexdigest()
        if self._previous_action is None:
            action_context = "Previous action: none; this is the first turn."
        else:
            changed = screenshot_sha256 != self._previous_screenshot_sha256
            action_context = (
                f"Previous action: {json.dumps(self._previous_action)}\n"
                f"Visible screenshot changed since that action: {'yes' if changed else 'no'}."
            )
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 256,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_user_text(
                                goal, action_context, observation.accessibility_tree
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:{image_mime};base64,{image_data}",
                        },
                    ],
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            f"{self.base_url}/chat/completions", data=body, headers=headers, method="POST"
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Model endpoint returned HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach model endpoint: {exc.reason}") from exc

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Model endpoint response did not contain a chat message") from exc
        if not isinstance(content, str):
            raise RuntimeError("Model endpoint returned non-text action content")
        action = self._parse_action(content)
        self._previous_action = action.to_dict()
        self._previous_screenshot_sha256 = screenshot_sha256
        return action

    @staticmethod
    def _parse_action(content: str) -> Action:
        decoder = json.JSONDecoder()
        parsed: object | None = None
        for index, char in enumerate(content):
            if char != "{":
                continue
            try:
                parsed, _end = decoder.raw_decode(content[index:])
                break
            except json.JSONDecodeError:
                continue
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Model did not return a JSON action: {content[:300]}")
        try:
            kind = ActionKind(parsed["kind"])
            return Action(
                kind=kind,
                x=parsed.get("x"),
                y=parsed.get("y"),
                target_id=parsed.get("target_id"),
                text=parsed.get("text"),
                key=parsed.get("key"),
                direction=parsed.get("direction"),
                amount=parsed.get("amount"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Model returned an invalid action: {parsed}") from exc

    @staticmethod
    def _format_user_text(
        goal: str, action_context: str, accessibility_tree: str | None
    ) -> str:
        text = f"Task goal: {goal}\n\n{action_context}"
        if accessibility_tree:
            text += f"\n\nVisible browser controls (accessibility tree):\n{accessibility_tree}"
        return text
