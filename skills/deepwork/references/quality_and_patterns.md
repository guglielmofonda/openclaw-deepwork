# Quality, Storage, and Workflow Patterns

## Quality Reviews

Use reviews to validate outputs after each step.

Rules:
- Any step producing a final deliverable must have at least one review.
- Criteria are **statements** of expected state, not questions.
- `run_each: step` reviews all outputs once.
- `run_each: <output_name>` reviews a specific output (or each file for `files`).
- Use `additional_review_guidance` only when the reviewer needs extra context.
- If reviews are heavy or outputs are many, prefer `run_each: step` to avoid timeouts.

Quality loop:
1. Run reviews after outputs are written.
2. If any criterion fails, revise outputs and re-review.
3. After 3 attempts, ask user whether to override and proceed.

## Work Product Storage Guidelines

Key principle: outputs belong in the main repo, not `.deepwork/`.

Recommended patterns:
- Use job name as top-level folder for job outputs.
- Use per-entity folders when outputting many items.
- Use `_dataroom` folders for supporting materials.

Good examples:
- `competitive_research/competitors_list.md`
- `competitive_research/acme_corp/research.md`
- `operations/reports/2026-01/spending_analysis.md`
- `operations/reports/2026-01/spending_analysis_dataroom/`

Avoid:
- `.deepwork/outputs/report.md`
- `output.md`
- `temp/draft.md`

Include dates in paths when outputs are periodic and historical versions matter.
Omit dates when the document is a living, continuously updated artifact.

## Parallel Sub-Workflow Pattern

Use when a multi-step process must be repeated per item.

How:
- Create a sub-workflow that handles one item.
- In the main workflow, add a step that launches the sub-workflow once per item.
- Use parallel subagents when available.

## Iterative Loop Pattern (go_to_step)

Use when later steps might invalidate earlier work.

Rules:
- The decision step explicitly calls `go_to_step` with the target step ID.
- Progress from the target step onward is cleared and re-run.
- Include a max iteration count to avoid infinite loops.

## Concurrency Entries

Workflow steps can be arrays of step IDs to run concurrently. If subagents are unavailable, run sequentially but isolate outputs.
