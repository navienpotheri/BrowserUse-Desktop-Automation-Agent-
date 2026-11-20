"""Run a BrowserGym task with an OpenAI-compatible vision model endpoint."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .browsergym_adapter import BrowserGymEnvironment
from .loop import AgentLoop
from .openai_compatible_model import OpenAICompatibleVisionModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="browsergym/miniwob.choose-list")
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log", type=Path, default=Path(".agent_runs/trajectory.jsonl"))
    args = parser.parse_args()

    model = OpenAICompatibleVisionModel()
    environment = BrowserGymEnvironment(task_id=args.task, seed=args.seed)
    try:
        summary = AgentLoop(model, environment, max_steps=args.max_steps).run(
            args.task, args.log
        )
    finally:
        environment.close()
    print(json.dumps(asdict(summary), indent=2, default=str))


if __name__ == "__main__":
    main()
