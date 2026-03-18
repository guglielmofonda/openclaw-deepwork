#!/usr/bin/env python3
import argparse
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict

import yaml

from deepwork_interview import (
    CONCERN_FAMILIES,
    extract_topic_label,
    load_interview_state,
    slugify,
    summarize_scope,
    write_scope_artifact,
)


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"File exists: {path} (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def concern_specific_review(slots: Dict[str, Any]) -> tuple[str, str]:
    concern = slots.get("primary_concern")
    if concern == "blood_sugar_metabolic":
        return (
            "Metabolic Relevance",
            "The recommendation addresses glycemic load, portion size, and metabolic caveats that matter for the stated goal.",
        )
    if concern == "pesticides_contaminants":
        return (
            "Exposure Specificity",
            "The recommendation distinguishes actual exposure risk from vague contamination fears and explains the relevant tradeoff clearly.",
        )
    if concern == "processing_chlorine":
        return (
            "Processing Specificity",
            "The recommendation distinguishes sanitizer or processing concerns from broader nutrition questions and states whether the processing materially changes the verdict.",
        )
    if concern == "gut_health":
        return (
            "Digestive Relevance",
            "The recommendation addresses digestive tolerance, fiber effects, and population-specific gut caveats where relevant.",
        )
    if concern == "calories_body_composition":
        return (
            "Body Composition Relevance",
            "The recommendation addresses calorie density, satiety, and substitution effects relevant to the user’s body-composition goal.",
        )
    if concern == "nutrient_quality_vitamin":
        return (
            "Nutrient Specificity",
            "The recommendation addresses nutrient density and any realistic vitamin-related downside without exaggeration.",
        )
    return (
        "Scope Fit",
        "The recommendation is tightly matched to the scoped concern and does not drift into unrelated issues.",
    )


def build_common_job_info(topic_label: str, scoping_artifact_path: Path, slots: Dict[str, Any]) -> str:
    concern_label = slots.get("primary_concern_label", slots.get("primary_concern", ""))
    lines = [
        f'This workflow evaluates whether "{topic_label}" is a net negative, neutral, or positive choice for the user.',
        "Use live, current sources with citations and explicitly note uncertainty.",
        "This is an informational workflow, not medical advice. For health topics, include that disclaimer in the final recommendation.",
        "",
        "Scoped inputs from the interactive define process:",
        f"- Primary concern: {concern_label}",
        f"- Specific angle: {slots.get('concern_detail', 'Not specified')}",
        f"- Decision goal: {slots.get('decision_goal', '')}",
        f"- Usage pattern: {slots.get('usage_pattern', '')}",
        f"- Personal context: {slots.get('personal_context', '')}",
        f"- Evidence bar: {slots.get('evidence_bar', '')}",
        f"- Time horizon: {slots.get('time_horizon', 'Not specified')}",
        f"- Output style: {slots.get('decision_output', '')}",
        f"- Scoping artifact path: {scoping_artifact_path}",
        "",
        "The first step must read the scoping artifact exactly and treat it as the source of truth for scope, exclusions, and success criteria.",
    ]
    return "\n".join(lines)


def build_job_spec(topic_label: str, scoping_artifact_path: Path, slots: Dict[str, Any]) -> Dict[str, Any]:
    review_name, review_statement = concern_specific_review(slots)
    return {
        "name": "research_decision",
        "version": "1.0.0",
        "summary": f'Research workflow to evaluate "{topic_label}" and produce a recommendation',
        "common_job_info_provided_to_all_steps_at_runtime": build_common_job_info(
            topic_label=topic_label,
            scoping_artifact_path=scoping_artifact_path,
            slots=slots,
        ),
        "workflows": [
            {
                "name": "full_analysis",
                "summary": "Scope -> evidence -> analysis -> recommendation -> review",
                "steps": [
                    "define_scope",
                    "gather_sources",
                    "analyze_evidence",
                    "synthesize_recommendation",
                    "review_quality",
                ],
            }
        ],
        "steps": [
            {
                "id": "define_scope",
                "name": "Define Scope",
                "description": "Read the scoping artifact and produce a canonical scope document for the workflow.",
                "instructions_file": "steps/define_scope.md",
                "outputs": {
                    "scope_file": {
                        "type": "file",
                        "description": "Canonical scope document used by all downstream steps",
                        "required": True,
                    }
                },
                "dependencies": [],
                "reviews": [],
            },
            {
                "id": "gather_sources",
                "name": "Gather Sources",
                "description": "Collect sources and record evidence relevant to the scoped concern.",
                "instructions_file": "steps/gather_sources.md",
                "inputs": [{"file": "scope_file", "from_step": "define_scope"}],
                "outputs": {
                    "evidence_file": {
                        "type": "file",
                        "description": "Evidence log with citations and extracted findings",
                        "required": True,
                    }
                },
                "dependencies": ["define_scope"],
                "reviews": [],
            },
            {
                "id": "analyze_evidence",
                "name": "Analyze Evidence",
                "description": "Synthesize benefits, risks, and uncertainty from the gathered evidence.",
                "instructions_file": "steps/analyze_evidence.md",
                "inputs": [{"file": "evidence_file", "from_step": "gather_sources"}],
                "outputs": {
                    "analysis_file": {
                        "type": "file",
                        "description": "Balanced analysis of the relevant evidence",
                        "required": True,
                    }
                },
                "dependencies": ["gather_sources"],
                "reviews": [],
            },
            {
                "id": "synthesize_recommendation",
                "name": "Synthesize Recommendation",
                "description": "Write the final decision memo with recommendation and caveats.",
                "instructions_file": "steps/synthesize_recommendation.md",
                "inputs": [{"file": "analysis_file", "from_step": "analyze_evidence"}],
                "outputs": {
                    "decision_file": {
                        "type": "file",
                        "description": "Decision memo with recommendation, citations, and caveats",
                        "required": True,
                    }
                },
                "dependencies": ["analyze_evidence"],
                "reviews": [
                    {
                        "run_each": "decision_file",
                        "quality_criteria": {
                            "Citations Present": "Key claims are backed by citations.",
                            "Balanced": "Risks and benefits are both represented.",
                            "Uncertainty Noted": "Uncertainty and evidence gaps are explicit.",
                            review_name: review_statement,
                            "Clear Recommendation": "The recommendation is concrete and actionable for the stated decision goal.",
                        },
                    }
                ],
            },
            {
                "id": "review_quality",
                "name": "Review Quality",
                "description": "Final check for missing angles, weak evidence, or unsupported claims.",
                "instructions_file": "steps/review_quality.md",
                "inputs": [{"file": "decision_file", "from_step": "synthesize_recommendation"}],
                "outputs": {
                    "review_file": {
                        "type": "file",
                        "description": "Quality review documenting any remaining gaps or fixes",
                        "required": True,
                    }
                },
                "dependencies": ["synthesize_recommendation"],
                "reviews": [],
            },
        ],
    }


def define_scope_md(topic_label: str, scoping_artifact_path: Path, topic_slug: str) -> str:
    return dedent(
        f"""
        # Define Scope

        ## Objective

        Convert the interactive scoping artifact into a canonical workflow scope document without reopening settled questions.

        ## Task

        Read the scoping artifact at `{scoping_artifact_path}` first. Treat it as the source of truth for:
        - the topic being evaluated
        - the primary concern
        - the decision the user wants to make
        - the personal context and evidence bar

        Only add clarifying notes if the artifact leaves a material ambiguity that would affect the research.
        Do not restart a broad user interview here.

        ## Output Format

        ### research/{topic_slug}/scope.md

        **Structure**:
        ```markdown
        # Scope

        ## Topic
        {topic_label}

        ## Primary Concern
        [Concern and specific angle]

        ## Decision Goal
        [What decision this workflow should support]

        ## Personal Context
        [Context that changes the answer]

        ## Evidence Standard
        [What sources count]

        ## Time Horizon
        [Short-term, long-term, or both]

        ## Success Criteria
        - [What a good final answer must include]
        ```

        ## Quality Criteria

        - The scope matches the scoping artifact exactly on the important decisions
        - The primary concern and decision goal are explicit
        - The evidence standard is concrete enough to guide source selection
        """
    ).strip() + "\n"


def gather_sources_md(topic_slug: str, slots: Dict[str, Any]) -> str:
    concern_label = slots.get("primary_concern_label", slots.get("primary_concern", ""))
    evidence_bar = slots.get("evidence_bar", "Use the strongest credible evidence available")
    return dedent(
        f"""
        # Gather Sources

        ## Objective

        Collect evidence relevant to the scoped concern: {concern_label}.

        ## Task

        Read the scope file first. Then gather live sources that match this evidence bar:
        `{evidence_bar}`

        Prioritize:
        - peer-reviewed or primary research when available
        - public-health or medical institution summaries
        - reputable expert or industry summaries only when they add practical context

        Capture enough evidence to support both the upside and downside of the topic.

        ## Output Format

        ### research/{topic_slug}/evidence.md

        **Structure**:
        ```markdown
        # Evidence Log

        ## Source 1
        - Title: [title]
        - URL: [url]
        - Type: [study, guideline, review, expert summary]
        - Relevant finding: [short quote or paraphrase]
        - Why it matters: [why it changes the answer]
        ```

        ## Quality Criteria

        - Sources are live and cited with URLs
        - Both benefits and risks have evidence coverage
        - Source quality matches the scoped evidence bar
        """
    ).strip() + "\n"


def analyze_evidence_md(topic_slug: str, slots: Dict[str, Any]) -> str:
    concern = slots.get("primary_concern")
    detail = slots.get("concern_detail", "Not specified")
    angle_guidance = {
        "blood_sugar_metabolic": "Compare glycemic implications, portion size, fiber effects, and any population-specific metabolic caveats.",
        "pesticides_contaminants": "Separate actual exposure magnitude from vague contamination fear and note whether washing or produce choice materially changes the risk.",
        "processing_chlorine": "Separate sanitizer or processing concerns from the broader nutritional verdict and identify whether the processing materially changes the answer.",
        "gut_health": "Assess tolerance, fiber effects, satiety, and any relevant digestive tradeoffs.",
        "calories_body_composition": "Assess calorie density, satiety, substitution effects, and likelihood of overconsumption in the stated use pattern.",
        "nutrient_quality_vitamin": "Assess nutrient density, realistic upside, and any plausible downside from excess or nutrient loss.",
    }.get(concern, "Assess the main benefit, risk, uncertainty, and any population-specific caveat tied to the scoped concern.")
    return dedent(
        f"""
        # Analyze Evidence

        ## Objective

        Turn the evidence log into a decision-ready analysis.

        ## Task

        Focus on this specific angle: `{detail}`.

        {angle_guidance}

        Do not just summarize sources independently. Synthesize them into the actual decision tension the user cares about.

        ## Output Format

        ### research/{topic_slug}/analysis.md

        **Structure**:
        ```markdown
        # Analysis

        ## What Looks Positive
        - [Finding + source support]

        ## What Looks Negative
        - [Finding + source support]

        ## What Is Unclear
        - [Gap or conflicting evidence]

        ## Decision-Relevant Take
        [One short section translating the analysis into the user's actual decision]
        ```

        ## Quality Criteria

        - The analysis is balanced rather than one-sided
        - Claims are tied back to the evidence log
        - Uncertainty is explicit and decision-relevant
        """
    ).strip() + "\n"


def synthesize_recommendation_md(topic_slug: str, slots: Dict[str, Any]) -> str:
    decision_goal = slots.get("decision_goal", "Make a practical decision")
    output_style = slots.get("decision_output", "Concise memo with citations")
    return dedent(
        f"""
        # Synthesize Recommendation

        ## Objective

        Produce the final decision memo for this goal: `{decision_goal}`.

        ## Task

        Use the requested output style: `{output_style}`.

        The final answer must:
        - state a verdict (`net positive`, `neutral`, or `net negative`, or an equivalent recommendation)
        - explain the main reasoning in plain language
        - cite key claims
        - state what would change the answer
        - include a brief informational-only disclaimer for health topics

        ## Output Format

        ### research/{topic_slug}/decision.md

        **Structure**:
        ```markdown
        # Decision Memo

        ## Verdict
        [net positive / neutral / net negative]

        ## Short Answer
        [1-2 paragraph explanation]

        ## Why
        - [Key point + citation]

        ## Caveats
        - [When the answer changes]

        ## Sources
        - [source list]

        ## Disclaimer
        Informational only; consult a qualified professional for medical advice.
        ```

        ## Quality Criteria

        - The verdict is explicit
        - The reasoning supports the verdict directly
        - Citations are attached to the important claims
        """
    ).strip() + "\n"


def review_quality_md(topic_slug: str, slots: Dict[str, Any]) -> str:
    concern_label = slots.get("primary_concern_label", slots.get("primary_concern", ""))
    return dedent(
        f"""
        # Review Quality

        ## Objective

        Do a final quality pass on the recommendation with emphasis on the scoped concern: {concern_label}.

        ## Task

        Review the decision memo for:
        - unsupported claims
        - missing angles that would matter to the scoped concern
        - overconfident wording where the evidence is thin
        - mismatch between the scoped decision goal and the final answer

        ## Output Format

        ### research/{topic_slug}/review.md

        **Structure**:
        ```markdown
        # Quality Review

        ## Issues Found
        - [Issue and concrete fix]

        ## Final Assessment
        [Pass / Needs Fixes]
        ```

        ## Quality Criteria

        - Issues are specific and actionable
        - The final assessment matches the actual evidence quality
        """
    ).strip() + "\n"


def build_default_state(goal: str) -> Dict[str, Any]:
    topic_label = extract_topic_label(goal)
    return {
        "session_id": "manual-bootstrap",
        "goal": goal,
        "topic_label": topic_label,
        "topic_slug": slugify(topic_label),
        "resolved_slots": {
            "primary_concern": "custom",
            "primary_concern_label": "general evaluation",
            "decision_goal": "Decide whether the topic is net negative overall",
            "usage_pattern": "Not specified",
            "personal_context": "No specific context provided",
            "evidence_bar": "Peer-reviewed studies and major medical sources only",
            "time_horizon": "Both short-term and long-term",
            "decision_output": "Concise memo with citations",
        },
        "completion_status": "ready_to_generate",
    }


def load_generation_state(args: argparse.Namespace) -> tuple[Dict[str, Any], Path | None]:
    if args.state:
        state_path = Path(args.state).resolve()
        state = load_interview_state(state_path)
        if state.get("completion_status") != "ready_to_generate":
            raise SystemExit("interview state is not ready to generate a workflow yet")
        return state, state_path

    if not args.goal:
        raise SystemExit("either --state or --goal is required")
    return build_default_state(args.goal), None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the research_decision job from scoped interview state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--state", required=False)
    parser.add_argument("--goal", required=False)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    state, state_path = load_generation_state(args)
    topic_label = state["topic_label"]
    topic_slug = state["topic_slug"]
    slots = state["resolved_slots"]

    if state_path is not None:
        scoping_artifact_path = write_scope_artifact(project_root, state)
    else:
        scoping_artifact_path = project_root / ".deepwork" / "tmp" / "interviews" / "manual-bootstrap.scope.md"
        scoping_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        scoping_artifact_path.write_text(
            "# Scoping Artifact\n\n" + summarize_scope(state) + "\n",
            encoding="utf-8",
        )

    job_dir = project_root / ".deepwork" / "jobs" / "research_decision"
    job_spec = build_job_spec(topic_label=topic_label, scoping_artifact_path=scoping_artifact_path, slots=slots)
    job_yml = yaml.safe_dump(job_spec, sort_keys=False, allow_unicode=False)

    write_file(job_dir / "job.yml", job_yml, args.force)
    write_file(job_dir / "steps" / "define_scope.md", define_scope_md(topic_label, scoping_artifact_path, topic_slug), args.force)
    write_file(job_dir / "steps" / "gather_sources.md", gather_sources_md(topic_slug, slots), args.force)
    write_file(job_dir / "steps" / "analyze_evidence.md", analyze_evidence_md(topic_slug, slots), args.force)
    write_file(
        job_dir / "steps" / "synthesize_recommendation.md",
        synthesize_recommendation_md(topic_slug, slots),
        args.force,
    )
    write_file(job_dir / "steps" / "review_quality.md", review_quality_md(topic_slug, slots), args.force)

    print(f"Generated research_decision job at {job_dir}")
    print(f"Scoping artifact: {scoping_artifact_path}")


if __name__ == "__main__":
    main()
