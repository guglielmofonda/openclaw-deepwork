# Examples

## Example job.yml (short)

```yaml
name: competitive_research
version: "1.0.0"
summary: "Systematic competitive analysis workflow"
common_job_info_provided_to_all_steps_at_runtime: |
  Analyze competitors in a given market segment and produce a clear positioning report.

workflows:
  - name: full_analysis
    summary: "End-to-end competitive research"
    steps:
      - identify_competitors
      - research_competitors
      - write_report

steps:
  - id: identify_competitors
    name: "Identify Competitors"
    description: "Find 5-7 relevant competitors"
    instructions_file: steps/identify_competitors.md
    inputs:
      - name: market_segment
        description: "Market segment to analyze"
    outputs:
      competitors_list.md:
        type: file
        description: "List of competitors with short descriptions"
        required: true
    dependencies: []
    reviews: []

  - id: research_competitors
    name: "Research Competitors"
    description: "Collect data on each competitor"
    instructions_file: steps/research_competitors.md
    inputs:
      - file: competitors_list.md
        from_step: identify_competitors
    outputs:
      research_notes.md:
        type: file
        description: "Research notes with sources"
        required: true
    dependencies:
      - identify_competitors
    reviews:
      - run_each: research_notes.md
        quality_criteria:
          "Sourced": "Claims include citations."
          "Coverage": "Each competitor has >=3 data points."

  - id: write_report
    name: "Write Report"
    description: "Synthesize into a report"
    instructions_file: steps/write_report.md
    inputs:
      - file: research_notes.md
        from_step: research_competitors
    outputs:
      competitive_research/report.md:
        type: file
        description: "Final report"
        required: true
    dependencies:
      - research_competitors
    reviews:
      - run_each: competitive_research/report.md
        quality_criteria:
          "Actionable": "Recommendations are specific and usable."
```

## Example step instruction (short)

```markdown
# Identify Competitors

## Objective
Find 5-7 competitors relevant to the provided market segment.

## Task
Ask structured questions to clarify the segment and any exclusions. Produce a concise list with one-line descriptions.

## Output Format
### competitors_list.md
```markdown
# Competitors

1. **Acme** — Short description.
2. **BetaCorp** — Short description.
```

## Quality Criteria
- 5-7 competitors listed
- Each has a one-line description
- All are relevant to the market segment
```
