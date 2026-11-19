# BrowserUse + Desktop Automation Agent

An experimental, model-neutral research harness for browser and desktop automation.

## Project sequence

1. Establish a repeatable BrowserGym pilot, including WorkArena where configured.
2. Compare single-model control with propose–verify–execute.
3. Post-train on separate interaction data and evaluate on held-out benchmark tasks.
4. Extend the same action interface to OSWorld after browser evaluation is stable.

Benchmark tasks and known solutions stay out of training data. Record data sources, benchmark versions, task IDs, seeds, step limits, and model settings for every run.

## Harness

- Observation contains a screenshot path and image dimensions.
- A Model receives the task goal and screenshot, and returns one typed Action.
- An Environment resets a task, executes actions, and reports benchmark-verified success.
- AgentLoop logs observations, proposed actions, execution results, and a run summary as JSONL.
- The shared action schema uses normalized 0–1000 screen coordinates so the same model interface can serve browser and desktop environments.

## BrowserGym adapter

For the lightweight MiniWoB smoke run, install with pip install -e '.[browsergym]' and install Chromium with playwright install chromium. Add the larger WorkArena dependencies with pip install -e '.[workarena]' or WebArena with pip install -e '.[webarena]'.

BrowserGymEnvironment accepts registered task IDs such as browsergym/miniwob.choose-list, browsergym/webarena.10, or a WorkArena task ID. WorkArena also requires a configured ServiceNow developer instance; follow the BrowserGym setup guide: https://browsergym.readthedocs.io/latest/environments/workarena.html.

The adapter passes only the task goal and screenshot to the model. It does not pass BrowserGym's DOM, accessibility tree, or diagnostic info. It maps normalized clicks, typing, keypresses, scrolling, and waits into BrowserGym's action language. BrowserGym reward and termination provide the success signal.

## Current scope

The shared loop and BrowserGym adapter are implemented. Model backends, a fixed pilot task manifest, propose–verify–execute, and the OSWorld adapter are still to come. The first integration smoke run validates the adapter contract; benchmark comparisons begin after a model backend is connected.
