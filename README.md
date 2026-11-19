# BrowserUse + Desktop Automation Agent

An experimental, model-neutral harness for browser and desktop automation research.

## Project sequence

1. Define a stable action and observation interface.
2. Run BrowserGym tasks and save trajectories.
3. Compare a single-model loop with propose–verify–execute.
4. Post-train on separate interaction data and evaluate held-out tasks.
5. Expand to OSWorld after browser evaluation is repeatable.

Benchmark task content and known solutions must not enter training data. Record dataset provenance and benchmark versions with each run.

## Harness contract

- An Observation contains a screenshot path and dimensions.
- A Model receives the task goal and screenshot, then returns one typed Action.
- An Environment resets a task and executes one action at a time.
- AgentLoop logs observations, proposed actions, execution results, and summaries as JSONL.

The initial interface uses screenshots and normalized 0–1000 coordinates. The BrowserGym adapter passes only the goal and screenshot to the model; it does not forward the page DOM, accessibility tree, or diagnostic info.

## Local model: Ollama + Qwen2.5-VL 3B

The model backend defaults to the local Ollama endpoint and qwen2.5vl:3b. Ollama lists this quantized model at about 3.2 GB. Install Ollama from https://ollama.com/download, then open a PowerShell window and download the model:

    ollama pull qwen2.5vl:3b

Ollama runs its local API at http://localhost:11434. The backend uses its OpenAI-compatible vision endpoint. Configure the runner if you use a different local model or endpoint:

    $env:MODEL_BASE_URL = "http://localhost:11434/v1"
    $env:MODEL_NAME = "qwen2.5vl:3b"
    $env:MODEL_API_KEY = "ollama"

## BrowserGym setup

Install the project and browser dependencies:

    pip install -e ".[browsergym]"
    playwright install chromium

MiniWoB++ task pages must also be downloaded and exposed through MINIWOB_URL. For a reproducible setup, clone the official https://github.com/Farama-Foundation/miniwob-plusplus repository at commit 7fd85d71a4b60325c6585396ec4f48377d049838. Set MINIWOB_URL to the absolute miniwob/html/miniwob/ path using the file:// scheme, including the trailing slash. On Windows:

    git clone https://github.com/Farama-Foundation/miniwob-plusplus.git
    git -C miniwob-plusplus checkout 7fd85d71a4b60325c6585396ec4f48377d049838
    $env:MINIWOB_URL = "file:///C:/path/to/miniwob-plusplus/miniwob/html/miniwob/"

Run one task with the local model:

    python -m browseruse_agent.run_browsergym --task browsergym/miniwob.choose-list --max-steps 30

The runner writes a JSONL trajectory to .agent_runs/trajectory.jsonl. A short smoke run confirms wiring only; benchmark comparisons need a fixed task manifest and recorded model settings. WorkArena additionally needs a configured ServiceNow developer instance; see https://browsergym.readthedocs.io/latest/environments/workarena.html.

## Current status

The BrowserGym adapter completed a two-action MiniWoB smoke run using a no-op model. An OpenAI-compatible local vision backend and task runner are now in the repo. They still need to be run against the local Ollama server before we can report a model baseline or benchmark score.
