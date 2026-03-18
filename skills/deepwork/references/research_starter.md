# Research Workflow Starter (Fast Path)

Use this when the user asks a research/evaluation question (e.g., “Is X net negative?”).
This is not a fixed questionnaire. It should behave like Deepwork's Align step:
light grounding research -> one structured question -> ingest answer -> re-rank ambiguity -> repeat.

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

## Interview Controller

Start the interview like this:

```bash
python3 skills/deepwork/scripts/deepwork_interview.py start --goal "<user prompt>" --project-root .
```

Then after each user reply:

```bash
python3 skills/deepwork/scripts/deepwork_interview.py answer --state "<state_path>" --response "<user reply>"
```

Do not generate the workflow until the script returns `ready_to_generate`.

At that point:

```bash
python3 skills/deepwork/scripts/generate_research_job.py --state "<state_path>" --project-root .
```

## Structured Questions (Must Ask, One Per Turn)

Use structured questions to capture:
- **User context**: age range, health conditions, allergies, medications, diet goals.
- **Meaning of “net negative”**: health risks vs benefits, short/long term.
- **Evidence bar**: peer-reviewed only vs mixed sources.
- **Scope limits**: what to exclude, time horizon.
- **Output style**: short summary vs detailed memo.

Always:
- ask exactly one question per turn
- use numbered options
- include `Other`
- end with `Reply with a number or 'Other: ...'`

The first question should normally be concern-led, based on light grounding. Example concern families:
- blood sugar / metabolic health
- pesticides / contaminants
- processing / chlorine wash
- gut health / digestion
- calories / body composition
- nutrient quality / vitamins

After the primary concern is known, ask the branch-specific follow-up before returning to the generic slot order.

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
