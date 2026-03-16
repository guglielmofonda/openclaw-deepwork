# OpenClaw Deepwork Skill

This repo contains the `deepwork` skill for OpenClaw. It provides a Deepwork‑style workflow builder and runner, including a research fast‑path and a lightweight runner for step order + reviews.

## Install

Copy the `skills/deepwork` folder into your OpenClaw workspace `skills/` directory or add this repo path to `skills.load.extraDirs` in `~/.openclaw/openclaw.json`.

## Usage (Fast Path)

Inside OpenClaw, ask for a Deepwork‑style research workflow (e.g., “run a deepwork to see if X is net negative”). The agent will:
1. Ask structured questions
2. Autogenerate the default `research_decision` job
3. Implement steps and run with reviews

## Runner

```
python3 skills/deepwork/scripts/deepwork_runner.py start --job research_decision --workflow full_analysis --goal "<goal>"
```
