# OpenClaw Deepwork Skill

This repo contains the `deepwork` skill for OpenClaw. It provides a Deepwork-style workflow builder and runner, including a research fast-path and a lightweight runner for step order and reviews.

## Install

Recommended install path if your OpenClaw workspace is `~/clawd`:

```bash
cd ~
git clone https://github.com/guglielmofonda/openclaw-deepwork.git
python3 -m pip install --user -r ~/openclaw-deepwork/requirements.txt
mkdir -p ~/clawd/skills
rsync -a ~/openclaw-deepwork/skills/deepwork/ ~/clawd/skills/deepwork/
```

Add this routing block to `~/clawd/AGENTS.md`:

```md
## Deepwork Routing

When the user asks to "run a deepwork", "create a workflow", or requests a complex multi-step automation:
- Use the `deepwork` skill.
- Start in **Define** mode and ask structured questions before doing any work.
- Only after the workflow is fully scoped: generate `job.yml`, implement step instructions, then execute.
- For health/medical topics, always use web search and provide citations.
```

Then start a new OpenClaw session.

## Usage

Inside OpenClaw, ask for a Deepwork-style research workflow, for example:

`can you please run a deepwork to figure out if baby carrots are a net negative for me due to health concerns or not`

The agent should:
1. Ask structured scoping questions.
2. Auto-generate the default `research_decision` job.
3. Implement the step files.
4. Run the workflow with reviews.

## Runner

```bash
python3 skills/deepwork/scripts/deepwork_runner.py start --job research_decision --workflow full_analysis --goal "<goal>"
```
