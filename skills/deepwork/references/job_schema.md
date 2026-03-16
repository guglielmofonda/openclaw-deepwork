# job.yml Schema (Deepwork-Compatible)

This skill uses the Deepwork job schema. It is strict: no extra fields.

## Root Fields (required unless noted)
- `name` (string, lowercase + underscores)
- `version` (semver string like "1.0.0")
- `summary` (<=200 chars)
- `common_job_info_provided_to_all_steps_at_runtime` (multiline string)
- `workflows` (array, optional but recommended)
- `steps` (array, required)

## Workflow
Each workflow has:
- `name` (lowercase + underscores)
- `summary`
- `steps` (ordered list of step IDs OR arrays of step IDs for concurrency)
- `agent` (optional, run entire workflow in subagent)

## Step
Each step has:
- `id` (lowercase + underscores)
- `name`
- `description`
- `instructions_file` (relative path, e.g. `steps/research.md`)
- `inputs` (optional)
- `outputs` (object)
- `dependencies` (array of step IDs; default `[]`)
- `reviews` (array; can be empty)
- `agent` (optional, run step in subagent)

### Step Inputs (one of two shapes)
1. **User input**
   - `{ name: <string>, description: <string> }`
2. **File input**
   - `{ file: <string>, from_step: <step_id> }`

No other fields allowed. Do not add `type` or `path`.

### Step Outputs
Map output name to:
- `type`: `file` or `files`
- `description`: string
- `required`: boolean

### Reviews
Each review has:
- `run_each`: `step` OR output name
- `quality_criteria`: map of criterion name -> expected state statement
- `additional_review_guidance` (optional)

## Validation Rules (common failure points)
- `from_step` must appear in the step’s `dependencies` list.
- Each step must have at least one output (unless it is a pure cleanup step).
- No circular dependencies.
- Output paths should be in repo (not `.deepwork/`).
