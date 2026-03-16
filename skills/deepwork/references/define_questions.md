# Define Phase Question Bank

Use these structured questions to design a workflow before writing `job.yml`.
Keep the conversation interactive and confirm each major decision.

## Step 1: Job Purpose

Ask in structured form:
1. **Overall goal**
   - What complex task are you trying to automate?
   - What domain is this in (research, marketing, engineering, ops, etc.)?
   - How often will you run it?

If the request is research/evaluation (e.g., “Is X net negative?”), propose the
default workflow in `references/research_starter.md` and confirm it before customizing.
2. **Success criteria**
   - What is the final deliverable?
   - Who is the audience?
   - What quality criteria matter most?
3. **Major phases**
   - What are the distinct stages from start to finish?
   - Any dependencies between phases?

## Step 2: Define Each Step

For each phase/step, ask:
1. **Step purpose**
   - What does this step accomplish?
2. **Inputs**
   - What user-provided parameters are needed (names + descriptions)?
   - What files from previous steps are required?
3. **Outputs**
   - What files/artifacts should this step produce?
   - Format (md, yaml, json, pdf, etc.)?
   - Where should outputs live (paths, subfolders)?
4. **Dependencies**
   - Which previous steps must complete first?
5. **Process & quality**
   - Key activities in this step?
   - What makes the output good vs. bad?

## Step 2b: Capability Considerations

If a step involves browsing, scraping, form filling, or UI interactions:
- Ask what browser/automation tool is available.
- Do not assume one.

## Step 2c: Patterns to Detect

- **Parallel sub-workflows**: If the workflow repeats a multi-step process per item, define a sub-workflow and run it in parallel per item.
- **Iterative loops**: If steps need to loop based on feedback, mark a decision step that can call `go_to_step`.

(See `references/quality_and_patterns.md` for pattern details.)

## Step 3: Validate the Workflow

1. Summarize the full flow and confirm with the user.
2. Check for gaps:
   - Any step without clear inputs or outputs?
   - Any outputs not used later?
   - Any circular dependencies?
3. Confirm metadata:
   - Job name (lowercase, underscores)
   - Job summary (<=200 chars)
   - Common job info (shared context for all steps)
   - Version (start at 1.0.0)

## Step 4: Define Reviews

For steps producing final deliverables, define at least one review with criteria.
- Criteria are statements (not questions).
- Use `run_each: step` for many files, or a specific output for single-file checks.

(See `references/quality_and_patterns.md` for review rules.)
