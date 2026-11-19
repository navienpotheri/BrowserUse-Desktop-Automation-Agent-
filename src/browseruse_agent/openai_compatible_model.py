"""OpenAI-compatible vision model backend for local or hosted endpoints."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .actions import Action, ActionKind
from .interfaces import Observation


SYSTEM_PROMPT = """You control a browser using one action per turn.
You receive a task goal and a screenshot. Return exactly one JSON object, with
no markdown or extra text, using this schema:
{"kind":"click","x":500,"y":500}
{"kind":"type","text":"text to enter"}
{"kind":"key","key":"ENTER"}
{"kind":"scroll","direction":"down","amount":400}
{"kind":"wait","amount":250}
{"kind":"finish"}
Click coordinates are integers from 0 to 1000 relative to the screenshot.
Only use finish when the task appears complete. Never claim success in text."""


class OpenAICompatibleVisionModel:
    """Send goal + screenshot to a Chat Completions-compatible VLM endpoint.

    Configure MODEL_BASE_URL (for example http://localhost:8000/v1),
    MODEL_NAME, and optionally MODEL_API_KEY in the environment.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        self.base_url = (base_url or os.environ.get("MODEL_BASE_URL", "")).rstrip("/")
        self.model = model or os.environ.get("MODEL_NAME", "")
        self.api_key = api_key if api_key is not None else os.environ.get("MODEL_API_KEY", "")
        self.timeout_seconds = timeout_seconds
        if not self.base_url:
            raise ValueError("Set MODEL_BASE_URL to an OpenAI-compatible /v1 endpoint")
        if not self.model:
            raise ValueError("Set MODEL_NAME to the model ID served by that endpoint")
        self.name = self.model

    def propose(self, goal: str, observation: Observation) -> Action:
        image_path = Path(observation.screenshot)
        image_mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 256,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Task goal: {goal}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime};base64,{image_data}"
                            },
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
        return self._parse_action(content)

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
                text=parsed.get("text"),
                key=parsed.get("key"),
                direction=parsed.get("direction"),
                amount=parsed.get("amount"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Model returned an invalid action: {parsed}") from exc
