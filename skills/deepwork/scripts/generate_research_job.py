#!/usr/bin/env python3
import argparse
from pathlib import Path
from textwrap import dedent


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"File exists: {path} (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def job_yml() -> str:
    return dedent(
        """
        name: research_decision
        version: "1.0.0"
        summary: "Research workflow to evaluate a claim and produce a recommendation"
        common_job_info_provided_to_all_steps_at_runtime: |
          A structured research workflow for evaluating a question and producing a balanced recommendation.
          Use high-quality, current sources with citations, and explicitly note uncertainty.
          For health topics, include a brief informational-only disclaimer and encourage professional guidance.

        workflows:
          - name: full_analysis
            summary: "Scope → evidence → analysis → recommendation → review"
            steps:
              - define_scope
              - gather_sources
              - analyze_evidence
              - synthesize_recommendation
              - review_quality

        steps:
          - id: define_scope
            name: "Define Scope"
            description: "Clarify the question, context, and decision criteria"
            instructions_file: steps/define_scope.md
            inputs:
              - name: topic
                description: "The subject or question to evaluate"
              - name: user_context
                description: "Relevant personal context (health, goals, constraints)"
              - name: definition_of_net_negative
                description: "What counts as net negative vs net positive"
              - name: evidence_bar
                description: "Preferred evidence standards (peer-reviewed only, mixed sources, etc.)"
              - name: time_horizon
                description: "Short-term vs long-term focus"
              - name: output_style
                description: "Summary vs detailed memo; length preferences"
            outputs:
              scope_file:
                type: file
                description: "Scope and criteria document"
                required: true
            dependencies: []
            reviews: []

          - id: gather_sources
            name: "Gather Sources"
            description: "Collect credible sources and extract key findings"
            instructions_file: steps/gather_sources.md
            inputs:
              - file: scope_file
                from_step: define_scope
            outputs:
              evidence_file:
                type: file
                description: "Evidence log with citations"
                required: true
            dependencies:
              - define_scope
            reviews: []

          - id: analyze_evidence
            name: "Analyze Evidence"
            description: "Summarize benefits, risks, and uncertainty"
            instructions_file: steps/analyze_evidence.md
            inputs:
              - file: evidence_file
                from_step: gather_sources
            outputs:
              analysis_file:
                type: file
                description: "Balanced analysis of evidence"
                required: true
            dependencies:
              - gather_sources
            reviews: []

          - id: synthesize_recommendation
            name: "Synthesize Recommendation"
            description: "Create a decision memo with recommendation and caveats"
            instructions_file: steps/synthesize_recommendation.md
            inputs:
              - file: analysis_file
                from_step: analyze_evidence
            outputs:
              decision_file:
                type: file
                description: "Decision memo with recommendation"
                required: true
            dependencies:
              - analyze_evidence
            reviews:
              - run_each: decision_file
                quality_criteria:
                  "Citations Present": "Key claims are backed by citations."
                  "Balanced": "Risks and benefits are both represented."
                  "Uncertainty Noted": "Uncertainty and gaps are explicitly called out."
                  "Clear Recommendation": "The recommendation is concrete and actionable."

          - id: review_quality
            name: "Review Quality"
            description: "Final check for missing angles or weak evidence"
            instructions_file: steps/review_quality.md
            inputs:
              - file: decision_file
                from_step: synthesize_recommendation
            outputs:
              review_file:
                type: file
                description: "Quality review and follow-up fixes"
                required: true
            dependencies:
              - synthesize_recommendation
            reviews: []
        """
    ).lstrip()


def define_scope_md() -> str:
    return dedent(
        """
        # Define Scope

        ## Objective

        Clarify the question, user context, and decision criteria so the research stays focused.

        ## Task

        Ask structured questions to capture:
        - The exact topic or question
        - Relevant personal context (age range, health conditions, medications, diet goals)
        - What “net negative” means to the user
        - Evidence bar (peer-reviewed only vs mixed sources)
        - Time horizon (short vs long term)
        - Preferred output style (summary vs detailed memo)

        **Important:** ask structured questions and confirm the scope before writing the file.

        ## Output Format

        ### research/<topic_slug>/scope.md

        **Structure**:
        ```markdown
        # Scope

        ## Topic
        [What is being evaluated]

        ## User Context
        [Relevant health/diet context]

        ## Definition of Net Negative
        [How we judge negative vs positive]

        ## Evidence Bar
        [Source requirements]

        ## Time Horizon
        [Short vs long term]

        ## Inclusions / Exclusions
        [What to cover or ignore]

        ## Output Style
        [Summary vs detailed]

        ## Open Questions
        - [Any remaining questions]
        ```

        ## Quality Criteria

        - Scope reflects the user’s intent
        - Net negative definition is explicit
        - Evidence bar and time horizon are clear
        """
    ).lstrip()


def gather_sources_md() -> str:
    return dedent(
        """
        # Gather Sources

        ## Objective

        Collect credible sources and extract key evidence relevant to the scope.

        ## Task

        Use web search to find high-quality sources. Prioritize:
        - Peer-reviewed studies
        - Government/public health agencies
        - Reputable medical organizations

        For each source, capture a concise summary and the specific claim it supports.

        ## Output Format

        ### research/<topic_slug>/evidence.md

        **Structure**:
        ```markdown
        # Evidence Log

        ## Sources

        1. **[Source Title]** — [Publisher], [Year]
           - URL: [link]
           - Key finding: [one-line summary]
           - Relevance: [why this matters]

        2. **[Source Title]** — [Publisher], [Year]
           - URL: [link]
           - Key finding: [one-line summary]
           - Relevance: [why this matters]
        ```

        ## Quality Criteria

        - Sources are credible and current
        - Each source has a clear, relevant takeaway
        - URLs are included
        """
    ).lstrip()


def analyze_evidence_md() -> str:
    return dedent(
        """
        # Analyze Evidence

        ## Objective

        Summarize benefits, risks, and uncertainty from the collected evidence.

        ## Task

        Read the evidence log and synthesize:
        - Potential benefits
        - Potential risks
        - Contradictions or gaps
        - Any population-specific caveats

        ## Output Format

        ### research/<topic_slug>/analysis.md

        **Structure**:
        ```markdown
        # Evidence Analysis

        ## Benefits
        - [Benefit + supporting sources]

        ## Risks / Concerns
        - [Risk + supporting sources]

        ## Uncertainty / Gaps
        - [Where evidence is weak or conflicting]

        ## Population-Specific Notes
        - [Who this may affect differently]
        ```

        ## Quality Criteria

        - Both risks and benefits are covered
        - Claims map to evidence
        - Uncertainty is explicit
        """
    ).lstrip()


def synthesize_recommendation_md() -> str:
    return dedent(
        """
        # Synthesize Recommendation

        ## Objective

        Produce a decision memo with a recommendation, backed by evidence.

        ## Task

        Write a recommendation that is:
        - Clear and actionable
        - Balanced across risks and benefits
        - Explicit about uncertainty

        Include a brief disclaimer for health topics (informational only).

        ## Output Format

        ### research/<topic_slug>/decision.md

        **Structure**:
        ```markdown
        # Decision Memo

        ## Recommendation (Short)
        [One-paragraph recommendation]

        ## Rationale
        - [Key reasoning point + citation]

        ## Risks & Benefits
        - Benefits: [summary]
        - Risks: [summary]

        ## Uncertainty & Gaps
        - [Known gaps]

        ## Sources
        - [Cited sources]

        ## Disclaimer
        Informational only; consult a qualified professional for medical advice.
        ```

        ## Quality Criteria

        - Recommendation is concrete
        - Claims are cited
        - Risks and benefits are balanced
        - Uncertainty is stated
        """
    ).lstrip()


def review_quality_md() -> str:
    return dedent(
        """
        # Review Quality

        ## Objective

        Perform a final check for missing angles, weak evidence, or unclear recommendations.

        ## Task

        Review the decision memo and identify:
        - Missing angles or populations
        - Unsupported claims
        - Overconfident conclusions

        If issues exist, note fixes required.

        ## Output Format

        ### research/<topic_slug>/review.md

        **Structure**:
        ```markdown
        # Quality Review

        ## Issues Found
        - [Issue + fix]

        ## Overall Assessment
        [Pass / Needs Fixes]
        ```

        ## Quality Criteria

        - Issues are specific and actionable
        - Final assessment is clear
        """
    ).lstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate default research_decision job")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    job_dir = project_root / ".deepwork" / "jobs" / "research_decision"

    write_file(job_dir / "job.yml", job_yml(), args.force)
    write_file(job_dir / "steps" / "define_scope.md", define_scope_md(), args.force)
    write_file(job_dir / "steps" / "gather_sources.md", gather_sources_md(), args.force)
    write_file(job_dir / "steps" / "analyze_evidence.md", analyze_evidence_md(), args.force)
    write_file(job_dir / "steps" / "synthesize_recommendation.md", synthesize_recommendation_md(), args.force)
    write_file(job_dir / "steps" / "review_quality.md", review_quality_md(), args.force)

    print(f"Generated research_decision job at {job_dir}")


if __name__ == "__main__":
    main()
