# BrowserUse + Desktop Automation Agent

An experimental, model-neutral harness for browser and desktop automation research.

## Project sequence

1. Define a stable action and observation interface.
2. Run a small BrowserGym/WorkArena pilot with a fixed task list and save trajectories.
3. Compare a single-model loop with propose–verify–execute.
4. Post-train on separate interaction data and re-run held-out tasks.
5. Expand to OSWorld after browser evaluation is repeatable.

Benchmark task content and known solutions must not enter training data. Record
dataset provenance and benchmark versions with each run.

## Harness contract

- `Observation` carries a screenshot file path and image dimensions.
- A `Model` receives the task goal and observation, and returns one typed `Action`.
- An `Environment` resets a task and executes one action at a time.
- `AgentLoop` writes each observation/action/result to JSONL for later analysis.
- BrowserGym and OSWorld adapters will implement the environment protocol in a
  later milestone; model backends will implement the model protocol.

The first interface deliberately uses screenshots and normalized 0–1000
coordinates so the same action representation can be used for browser and
desktop environments. A DOM/accessibility observation can be added later as a
separate experimental condition.

## BrowserGym adapter

Install the optional integration with `pip install -e '.[browsergym]'`, then
install a Chromium browser with `playwright install chromium`. The adapter
accepts a registered BrowserGym task ID such as
`browsergym/miniwob.choose-list` or a WorkArena task ID. WorkArena additionally
requires a configured ServiceNow developer instance; see the
[BrowserGym WorkArena setup guide](https://browsergym.readthedocs.io/latest/environments/workarena.html).

The adapter passes only the task goal and screenshot to the model. It does not
forward BrowserGym's DOM, accessibility tree, or diagnostic `info` fields.
Coordinates are translated from the shared 0–1000 scale to the current
screenshot dimensions. BrowserGym's own reward and terminal flag provide the
task success signal.

## Current status

This is the initial harness scaffold. It does not yet connect to a browser,
desktop VM, model server, or benchmark. Those integrations are the next steps.
