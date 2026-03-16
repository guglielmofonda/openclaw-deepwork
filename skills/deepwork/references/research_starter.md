# Research Workflow Starter (Fast Path)

Use this when the user asks a research/evaluation question (e.g., “Is X net negative?”).
You should still ask structured questions, but you can propose this default workflow to speed up scoping.

## Suggested Workflow (Default)

**Job name**: `research_decision`

**Workflows**:
- `full_analysis`: end-to-end research + recommendation

**Steps**:
1. `define_scope`
   - Gather context, constraints, and what “net negative” means.
   - Output: `research/<topic>/scope.md`
2. `gather_sources`
   - Web search and source collection.
   - Output: `research/<topic>/evidence.md`
3. `analyze_evidence`
   - Summarize benefits/risks and uncertainties.
   - Output: `research/<topic>/analysis.md`
4. `synthesize_recommendation`
   - Decision memo with recommendation + caveats.
   - Output: `research/<topic>/decision.md`
5. `review_quality`
   - Check citations, balance, and missing angles.
   - Output: `research/<topic>/review.md`

## Autostart Generator

If the user accepts this default workflow, generate the job immediately:

```bash
python3 skills/deepwork/scripts/generate_research_job.py --project-root .
```

## Structured Questions (Must Ask)

Use structured questions to capture:
- **User context**: age range, health conditions, allergies, medications, diet goals.
- **Meaning of “net negative”**: health risks vs benefits, short/long term.
- **Evidence bar**: peer-reviewed only vs mixed sources.
- **Scope limits**: what to exclude, time horizon.
- **Output style**: short summary vs detailed memo.

## Health Topics (Safety)

For health topics:
- Always use live web sources and cite them.
- Include a brief disclaimer: informational only, not medical advice.
- Encourage professional guidance for personal health decisions.

## Review Criteria Suggestions

For `synthesize_recommendation`:
- “Citations are present for key claims.”
- “Recommendation reflects both risks and benefits.”
- “Uncertainty and gaps are explicitly noted.”

For `review_quality`:
- “No major missing angles remain.”
- “Claims match cited sources.”
