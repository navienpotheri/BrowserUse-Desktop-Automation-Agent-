# BrowserUse + Desktop Automation Agent

An experimental, model-neutral harness for browser and desktop automation research.

## Project sequence

1. Define a stable action and observation interface.
2. Run a small BrowserGym/WorkArena pilot with a fixed task list and save trajectories.
3. Compare a single-model loop with propose–verify–execute.
4. Post-train on separate interaction data and re-run held-out tasks.
5. Expand to OSWorld after browser evaluation is repeatable.

Benchmark task content and known solutions must not enter training data. Record dataset provenance and benchmark versions with each run.

## Harness contract

- Observation carries a screenshot file path and image dimensions.
- A Model receives the task goal and observation, and returns one typed Action.
- An Environment resets a task and executes one action at a time.
- AgentLoop writes each observation/action/result to JSONL for later analysis.
- The BrowserGym adapter implements the environment protocol; OSWorld and model backends are later milestones.

The first interface deliberately uses screenshots and normalized 0–1000 coordinates so the same action representation can be used for browser and desktop environments. A DOM/accessibility observation can be added later as a separate experimental condition.

## BrowserGym adapter

Install the lightweight smoke-run integration with pip install -e '.[browsergym]', then install Chromium with playwright install chromium. MiniWoB++ task pages must also be downloaded and exposed through MINIWOB_URL. For a reproducible setup, clone the official MiniWoB++ repository (https://github.com/Farama-Foundation/miniwob-plusplus) at commit 7fd85d71a4b60325c6585396ec4f48377d049838, then set MINIWOB_URL to the absolute miniwob/html/miniwob/ path using the file:// scheme, including the trailing slash. On Windows:

    git clone https://github.com/Farama-Foundation/miniwob-plusplus.git
    git -C miniwob-plusplus checkout 7fd85d71a4b60325c6585396ec4f48377d049838
    $env:MINIWOB_URL = "file:///C:/path/to/miniwob-plusplus/miniwob/html/miniwob/"

Then run a short adapter smoke check before evaluating a model. To add WorkArena dependencies, run pip install -e '.[workarena]'; for WebArena, run pip install -e '.[webarena]'. The adapter accepts registered BrowserGym task IDs such as browsergym/miniwob.choose-list or a WorkArena task ID. WorkArena also requires a configured ServiceNow developer instance; see https://browsergym.readthedocs.io/latest/environments/workarena.html.

The adapter passes only the task goal and screenshot to the model. It does not forward BrowserGym's DOM, accessibility tree, or diagnostic info fields. Coordinates are translated from the shared 0–1000 scale to the current screenshot dimensions. BrowserGym's own reward and terminal flag provide the task success signal.

## Current status

The BrowserGym adapter is implemented and has completed a two-action MiniWoB integration smoke run. This confirms task launch, screenshot capture, action translation, and trajectory logging; it is not a benchmark score. There is no model backend or desktop VM integration yet.
