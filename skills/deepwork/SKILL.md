---
name: deepwork
description: Build and run Deepwork-style multi-step workflows in OpenClaw with structured Q&A, job.yml specs, step prompts, and quality-gated execution.
metadata:
  short-description: Deepwork-style workflow builder + runner
---

# Deepwork-Style Workflows (OpenClaw)

Use this skill when a user wants to define or run a repeatable, multi-step workflow ("Deepwork-like" automation) with explicit steps, file outputs, and quality checks.

## Operating Modes

Pick the smallest mode that satisfies the request.

- **Define**: interactive Q&A to design the workflow and create `job.yml`.
- **Implement**: generate step instruction files (`steps/<step_id>.md`).
- **Run**: execute a workflow end-to-end with reviews.
- **Test / Iterate / Learn**: optional improvement loops based on real runs.

If the user is vague, start with **Define**.

## Quick Start Checklist

1. Ask which repo/path should hold the workflow (default: current repo).
2. **Define** using structured questions (see `references/define_questions.md`).
   - If this is a research/evaluation request (e.g., “Is X net negative?”), use the fast path in
     `references/research_starter.md` to propose a default workflow.
   - If the user accepts the default research workflow, generate it immediately:

```bash
python3 skills/deepwork/scripts/generate_research_job.py --project-root .
```
3. Create `.deepwork/jobs/<job_name>/job.yml` using `assets/job.yml.template`.
4. **Implement** step instruction files using `assets/step_instruction.md.template`.
5. **Run** the workflow (see Execution Rules below).

## Define (Interactive Q&A)

Follow `references/define_questions.md` and capture:
- Job purpose, success criteria, audience
- Workflows + step list (including any parallel or loop patterns)
- For each step: inputs, outputs, dependencies, process, quality checks
- Review criteria for any step producing a final deliverable

Then draft `job.yml` and confirm with the user before writing it.

**Schema must be exact**: use `references/job_schema.md` (no extra fields).

## Implement (Step Instructions)

For each step in `job.yml`:
- Create `steps/<step_id>.md` using `assets/step_instruction.md.template`.
- Include an Output Format section with template or example.
- If the step has user-provided inputs, explicitly say to "ask structured questions".
- Ensure the Quality Criteria section matches the job.yml reviews.

## Run (Execution Rules)

Use job.yml as the single source of truth.

### Workflow selection
- If the user specified a workflow, use it.
- If only one workflow exists, auto-select it.
- Otherwise ask the user to choose.

### Step execution loop
For each workflow entry (step ID or concurrent array):
1. Load `common_job_info_provided_to_all_steps_at_runtime` + step instructions.
2. Gather inputs:
   - User inputs: ask structured questions.
   - File inputs: read files from previous steps.
3. Perform the step and write outputs to the declared paths.
4. Run quality reviews (if any):
   - Evaluate each criterion.
   - If any fail, revise outputs and re-review (max 3 attempts).
   - After max attempts, ask the user whether to override.
5. Mark step complete and continue.

### Concurrency
If a workflow entry is an array of step IDs, run them in parallel using subagents if available. If not, run sequentially but keep their outputs isolated.

### Looping (go_to_step)
If a step’s instructions specify a `go_to_step` loop:
- Call it with the specified `step_id`.
- Re-run the target step and all subsequent steps.
- Enforce a max iteration count (documented in the step instructions).

### Output Paths
Outputs belong in the repo (not `.deepwork/`). Follow `references/quality_and_patterns.md` for storage rules.

## Test / Iterate / Learn

Use these when the user wants to harden the workflow:
- **Test**: run a real case, critique issues, gather feedback.
- **Iterate**: update job.yml + step instructions based on test feedback.
- **Learn**: capture new patterns, pitfalls, and update instructions.

See `references/quality_and_patterns.md` for review best practices.

## Runner Script (State + Reviews)

Use the lightweight runner to track session state, enforce step order, and manage reviews:

```bash
python3 skills/deepwork/scripts/deepwork_runner.py start --job <job_name> --workflow <workflow_name> --goal "<goal>"
```

Then for each step:

```bash
python3 skills/deepwork/scripts/deepwork_runner.py finish-step --session <session_id> --step <step_id> --outputs-json '{"output.md": "path/to/output.md"}'
```

If a review is required, the runner returns a review packet path and `needs_review` status.
Read the packet, evaluate criteria, then re-run `finish-step` with `--review-pass` or `--review-fail`.

## Files & Templates

- `assets/job.yml.template` – job spec skeleton
- `assets/step_instruction.md.template` – step prompt skeleton
- `references/examples.md` – short example job spec + step instruction
- `references/job_schema.md` – schema constraints
- `references/define_questions.md` – structured question bank
- `references/quality_and_patterns.md` – reviews, storage, concurrency, loops
