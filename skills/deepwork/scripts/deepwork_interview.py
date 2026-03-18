#!/usr/bin/env python3
import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


REQUIRED_SLOTS = [
    "primary_concern",
    "decision_goal",
    "usage_pattern",
    "personal_context",
    "evidence_bar",
    "decision_output",
]
OPTIONAL_SLOTS = [
    "time_horizon",
    "exclusions",
    "comparison_target",
]
QUESTION_ENDING = "Reply with a number or `Other: ...`."
SEARCH_TIMEOUT_SECONDS = 4

CONCERN_FAMILIES = {
    "blood_sugar_metabolic": {
        "label": "blood sugar / metabolic health",
        "keywords": [
            "blood sugar",
            "glycemic",
            "glucose",
            "insulin",
            "diabetes",
            "prediabetes",
            "carb",
            "metabolic",
            "glycemic index",
        ],
    },
    "pesticides_contaminants": {
        "label": "pesticides / contaminants",
        "keywords": [
            "pesticide",
            "residue",
            "contaminant",
            "conventional produce",
            "organic",
            "heavy metal",
            "exposure",
        ],
    },
    "processing_chlorine": {
        "label": "processing / chlorine wash",
        "keywords": [
            "chlorine",
            "sanitizer",
            "wash",
            "processing",
            "processed",
            "preservative",
        ],
    },
    "gut_health": {
        "label": "gut health / digestion",
        "keywords": [
            "gut",
            "digestion",
            "digestive",
            "fiber",
            "bloating",
            "ibs",
            "constipation",
            "fomap",
            "fodmap",
        ],
    },
    "calories_body_composition": {
        "label": "calories / body composition",
        "keywords": [
            "calorie",
            "weight",
            "fat loss",
            "body composition",
            "satiety",
            "snack",
            "overeating",
        ],
    },
    "nutrient_quality_vitamin": {
        "label": "nutrient quality / vitamins",
        "keywords": [
            "vitamin",
            "beta-carotene",
            "vitamin a",
            "nutrient",
            "antioxidant",
            "micronutrient",
            "nutritional value",
        ],
    },
}

QUESTION_LIBRARY = {
    "decision_goal": {
        "slot": "decision_goal",
        "prompt": "What decision do you actually want this deepwork to help you make?",
        "options": [
            "Decide whether I should keep eating it freely",
            "Decide whether I should limit it",
            "Decide whether I should swap it for another option",
            "Decide whether it is net negative overall",
            "Figure out safe quantity / threshold / portion size",
            "Understand the main risk before deciding",
        ],
    },
    "usage_pattern": {
        "slot": "usage_pattern",
        "prompt": "How does this usually show up in your life right now?",
        "options": [
            "Raw snack in small amounts",
            "Raw snack in large or frequent amounts",
            "Usually with hummus or another dip",
            "Mostly cooked or mixed into meals",
            "Only occasionally",
            "I do not eat it yet; I am deciding whether to start",
        ],
    },
    "personal_context": {
        "slot": "personal_context",
        "prompt": "Which personal context matters most for the recommendation?",
        "options": [
            "No known health issue; I just want a generally optimal answer",
            "Blood sugar / diabetes / prediabetes / CGM concerns",
            "Digestion / IBS / gut sensitivity",
            "Weight loss / body composition focus",
            "Medication / vitamin / kidney / other medical context",
            "Pregnancy / child feeding / family-specific context",
        ],
    },
    "evidence_bar": {
        "slot": "evidence_bar",
        "prompt": "What evidence bar should this use?",
        "options": [
            "Peer-reviewed studies and major medical sources only",
            "Mostly peer-reviewed, but allow strong public-health summaries",
            "Pragmatic mix of high-quality summaries and reputable expert sources",
            "Strongest available evidence even if it is limited",
            "Practical guidance matters more than a strict academic bar",
            "Use the broadest reasonable evidence set",
        ],
    },
    "time_horizon": {
        "slot": "time_horizon",
        "prompt": "What time horizon matters most?",
        "options": [
            "Immediate / short-term effects",
            "Long-term health effects",
            "Both short-term and long-term",
            "Daily habit / cumulative exposure",
            "Acute reactions or side effects",
            "Not sure; cover the most decision-relevant horizon",
        ],
    },
    "decision_output": {
        "slot": "decision_output",
        "prompt": "What kind of final output do you want?",
        "options": [
            "Short verdict only",
            "Concise memo with citations",
            "Detailed research note",
            "Practical decision guide / what to do",
            "Comparison against alternatives",
            "Recommendation with caveats and next actions",
        ],
    },
    "revision_target": {
        "slot": "revision_target",
        "prompt": "What should be adjusted before the workflow is generated?",
        "options": [
            "Primary concern",
            "Decision goal",
            "Usage pattern",
            "Personal context",
            "Evidence bar / time horizon",
            "Final output style",
        ],
    },
}

CONCERN_DETAIL_QUESTIONS = {
    "blood_sugar_metabolic": {
        "slot": "concern_detail",
        "question_id": "concern_detail_blood_sugar_metabolic",
        "prompt": "Which metabolic angle is the main one to optimize for?",
        "options": [
            "Diabetes / prediabetes risk",
            "CGM or blood-sugar stability",
            "Body composition / carbohydrate load",
            "General metabolic health / insulin response",
            "Energy crash / satiety after eating it",
            "I am mostly curious rather than managing a diagnosed issue",
        ],
    },
    "pesticides_contaminants": {
        "slot": "concern_detail",
        "question_id": "concern_detail_pesticides_contaminants",
        "prompt": "Which contaminant angle matters most?",
        "options": [
            "Residue on conventional produce",
            "Whether washing removes the concern",
            "Organic vs conventional decision",
            "Cumulative exposure over time",
            "Contaminants beyond pesticides",
            "I am mostly curious rather than acting on a specific exposure concern",
        ],
    },
    "processing_chlorine": {
        "slot": "concern_detail",
        "question_id": "concern_detail_processing_chlorine",
        "prompt": "Which processing concern should the workflow focus on?",
        "options": [
            "Chlorine / sanitizer toxicity",
            "Nutrient degradation from processing",
            "Whether baby carrots count as a processed food problem",
            "Packaging / storage / additive concerns",
            "Taste / texture changes as a proxy for quality",
            "I mostly want a sanity check on whether the processing matters at all",
        ],
    },
    "gut_health": {
        "slot": "concern_detail",
        "question_id": "concern_detail_gut_health",
        "prompt": "Which digestion angle is most relevant?",
        "options": [
            "Bloating or discomfort",
            "IBS / FODMAP-type concerns",
            "Constipation / fiber adequacy",
            "Satiety / appetite control",
            "How it interacts with dips or other foods",
            "I mostly want a broad gut-health answer",
        ],
    },
    "calories_body_composition": {
        "slot": "concern_detail",
        "question_id": "concern_detail_calories_body_composition",
        "prompt": "Which body-composition angle matters most?",
        "options": [
            "Calorie density",
            "Overeating / mindless snacking",
            "Satiety versus other snacks",
            "Whether it is a good substitution food",
            "Macro quality / carb quality",
            "I mostly want the broad body-composition verdict",
        ],
    },
    "nutrient_quality_vitamin": {
        "slot": "concern_detail",
        "question_id": "concern_detail_nutrient_quality_vitamin",
        "prompt": "Which nutrient angle matters most?",
        "options": [
            "Vitamin A / beta-carotene excess",
            "Nutrient loss versus whole carrots",
            "Whether the nutrients are meaningfully beneficial",
            "Micronutrient balance in the broader diet",
            "Antioxidant quality / nutrient density",
            "I mostly want a general nutrient-quality answer",
        ],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "research-topic"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(read_text(path))


def interview_state_path(project_root: Path, session_id: str) -> Path:
    return project_root / ".deepwork" / "tmp" / "interviews" / f"{session_id}.json"


def extract_topic_label(goal: str) -> str:
    patterns = [
        r"if\s+(.+?)\s+(?:is|are)\s+",
        r"whether\s+(.+?)\s+(?:is|are)\s+",
        r"about\s+(.+?)\s+(?:is|are)\s+",
    ]
    lowered = goal.strip()
    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            topic = match.group(1).strip(" .?!,")
            if topic:
                return topic
    cleaned = re.sub(
        r"^(can you|please|run a deepwork to|figure out if|tell me if|determine if)\s+",
        "",
        goal.strip(),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+(due to|for|or not).*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .?!,") or goal.strip()


def build_search_queries(goal: str) -> List[str]:
    return [
        f"{goal} health concerns",
        f"{goal} benefits risks",
        f"{goal} safety processing contamination",
        f"{goal} blood sugar calories digestion",
    ]


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def search_duckduckgo(query: str, max_snippets: int = 3) -> List[str]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
        html = response.read().decode("utf-8", "ignore")
    snippets = re.findall(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>|<div[^>]*class="result__snippet"[^>]*>(.*?)</div>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned: List[str] = []
    for first, second in snippets:
        candidate = strip_html(first or second)
        if candidate:
            cleaned.append(candidate)
        if len(cleaned) >= max_snippets:
            break
    if cleaned:
        return cleaned

    titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    for title in titles:
        candidate = strip_html(title)
        if candidate:
            cleaned.append(candidate)
        if len(cleaned) >= max_snippets:
            break
    return cleaned


def default_concern_candidates() -> List[Dict[str, str]]:
    return [
        {"key": "blood_sugar_metabolic", "label": CONCERN_FAMILIES["blood_sugar_metabolic"]["label"]},
        {"key": "pesticides_contaminants", "label": CONCERN_FAMILIES["pesticides_contaminants"]["label"]},
        {"key": "processing_chlorine", "label": CONCERN_FAMILIES["processing_chlorine"]["label"]},
        {"key": "gut_health", "label": CONCERN_FAMILIES["gut_health"]["label"]},
        {"key": "calories_body_composition", "label": CONCERN_FAMILIES["calories_body_composition"]["label"]},
        {"key": "nutrient_quality_vitamin", "label": CONCERN_FAMILIES["nutrient_quality_vitamin"]["label"]},
    ]


def run_quick_grounding(goal: str) -> Dict[str, Any]:
    queries = build_search_queries(goal)
    concern_scores = {key: 0 for key in CONCERN_FAMILIES}
    notes: List[str] = []
    executed_queries: List[str] = []

    for query in queries:
        try:
            snippets = search_duckduckgo(query)
        except Exception:
            snippets = []
        if not snippets:
            continue
        executed_queries.append(query)
        for snippet in snippets:
            lowered = snippet.lower()
            notes.append(snippet)
            for key, family in CONCERN_FAMILIES.items():
                for keyword in family["keywords"]:
                    if keyword in lowered:
                        concern_scores[key] += 1

    ranked = sorted(
        default_concern_candidates(),
        key=lambda item: (concern_scores.get(item["key"], 0), item["label"]),
        reverse=True,
    )
    if not any(concern_scores.values()):
        ranked = default_concern_candidates()

    return {
        "queries": executed_queries or queries[:3],
        "notes": notes[:8],
        "concern_candidates": ranked[:6],
        "concern_scores": concern_scores,
    }


def compute_unresolved_slots(resolved_slots: Dict[str, Any], slots: List[str]) -> List[str]:
    unresolved: List[str] = []
    for slot in slots:
        if not resolved_slots.get(slot):
            unresolved.append(slot)
    return unresolved


def question_payload(question_id: str, prompt: str, options: List[str], slot: str, allow_other: bool = True) -> Dict[str, Any]:
    rendered_options: List[Dict[str, Any]] = []
    for index, option in enumerate(options, start=1):
        rendered_options.append({"index": index, "value": option})
    if allow_other:
        rendered_options.append({"index": len(options) + 1, "value": "Other"})
    return {
        "question_id": question_id,
        "slot": slot,
        "prompt": prompt,
        "options": rendered_options,
        "allow_other": allow_other,
    }


def render_question_markdown(question: Dict[str, Any], state: Dict[str, Any]) -> str:
    lines = [question["prompt"], ""]
    if question["question_id"] == "primary_concern" and state["quick_grounding"].get("notes"):
        lines.append("From a quick grounding pass, these look like the most likely concern areas:")
        lines.append("")
    for option in question["options"]:
        label = option["value"]
        if label == "Other":
            lines.append(f"{option['index']}. Other")
        else:
            lines.append(f"{option['index']}. {label}")
    lines.append("")
    lines.append(QUESTION_ENDING)
    return "\n".join(lines)


def parse_answer(question: Dict[str, Any], response: str) -> Dict[str, Any]:
    cleaned = response.strip()
    if not cleaned:
        raise SystemExit("response cannot be empty")

    other_match = re.match(r"(?i)^other\s*:\s*(.+)$", cleaned)
    if other_match:
        if not question.get("allow_other"):
            raise SystemExit("this question does not accept a freeform Other response")
        return {"kind": "other", "raw": other_match.group(1).strip()}

    number_match = re.match(r"^\s*(\d+)\s*$", cleaned)
    if number_match:
        choice = int(number_match.group(1))
        for option in question["options"]:
            if option["index"] == choice:
                if option["value"] == "Other":
                    raise SystemExit("if you pick Other, reply as `Other: ...` so the concern can be captured")
                return {"kind": "option", "value": option["value"], "index": choice}
        raise SystemExit(f"choice {choice} is not valid for question '{question['question_id']}'")

    lowered = cleaned.lower()
    for option in question["options"]:
        if option["value"] != "Other" and lowered == option["value"].lower():
            return {"kind": "option", "value": option["value"], "index": option["index"]}
    return {"kind": "other", "raw": cleaned}


def map_primary_concern_freeform(value: str) -> str | None:
    lowered = value.lower()
    for key, family in CONCERN_FAMILIES.items():
        if any(keyword in lowered for keyword in family["keywords"]):
            return key
    return None


def build_primary_concern_question(state: Dict[str, Any]) -> Dict[str, Any]:
    options = [candidate["label"] for candidate in state["quick_grounding"]["concern_candidates"]]
    return question_payload(
        question_id="primary_concern",
        prompt=f'What is the main concern you want this deepwork to evaluate about "{state["topic_label"]}"?',
        options=options,
        slot="primary_concern",
    )


def build_concern_detail_question(primary_concern: str) -> Dict[str, Any] | None:
    config = CONCERN_DETAIL_QUESTIONS.get(primary_concern)
    if not config:
        return None
    return question_payload(
        question_id=config["question_id"],
        prompt=config["prompt"],
        options=config["options"],
        slot=config["slot"],
    )


def build_library_question(question_id: str) -> Dict[str, Any]:
    config = QUESTION_LIBRARY[question_id]
    return question_payload(
        question_id=question_id,
        prompt=config["prompt"],
        options=config["options"],
        slot=config["slot"],
        allow_other=question_id != "revision_target",
    )


def build_confirmation_question(state: Dict[str, Any]) -> Dict[str, Any]:
    summary = summarize_scope(state)
    prompt = "\n".join(
        [
            "This is the scope I am about to turn into a workflow:",
            "",
            summary,
            "",
            "Is this scope correct?",
        ]
    )
    return question_payload(
        question_id="confirm_scope",
        prompt=prompt,
        options=["Yes, generate the workflow", "No, I want to revise something"],
        slot="confirmation",
        allow_other=False,
    )


def summarize_scope(state: Dict[str, Any]) -> str:
    slots = state["resolved_slots"]
    lines = [
        f"- **Topic:** {state['topic_label']}",
        f"- **Primary concern:** {slots.get('primary_concern_label', slots.get('primary_concern', ''))}",
    ]
    if slots.get("concern_detail"):
        lines.append(f"- **Specific angle:** {slots['concern_detail']}")
    lines.extend(
        [
            f"- **Decision goal:** {slots.get('decision_goal', '')}",
            f"- **Usage pattern:** {slots.get('usage_pattern', '')}",
            f"- **Personal context:** {slots.get('personal_context', '')}",
            f"- **Evidence bar:** {slots.get('evidence_bar', '')}",
            f"- **Time horizon:** {slots.get('time_horizon', 'Not specified')}",
            f"- **Output style:** {slots.get('decision_output', '')}",
        ]
    )
    if slots.get("exclusions"):
        lines.append(f"- **Exclusions:** {slots['exclusions']}")
    if slots.get("comparison_target"):
        lines.append(f"- **Comparison target:** {slots['comparison_target']}")
    return "\n".join(lines)


def next_question(state: Dict[str, Any]) -> Dict[str, Any] | None:
    slots = state["resolved_slots"]
    if not slots.get("primary_concern"):
        return build_primary_concern_question(state)
    if slots.get("primary_concern") != "custom" and not slots.get("concern_detail"):
        return build_concern_detail_question(slots["primary_concern"])
    if not slots.get("decision_goal"):
        return build_library_question("decision_goal")
    if not slots.get("usage_pattern"):
        return build_library_question("usage_pattern")
    if not slots.get("personal_context"):
        return build_library_question("personal_context")
    if not slots.get("evidence_bar"):
        return build_library_question("evidence_bar")
    if not slots.get("time_horizon"):
        return build_library_question("time_horizon")
    if not slots.get("decision_output"):
        return build_library_question("decision_output")
    if state.get("awaiting_confirmation"):
        return build_confirmation_question(state)
    state["awaiting_confirmation"] = True
    return build_confirmation_question(state)


def public_state_payload(state: Dict[str, Any], question: Dict[str, Any] | None, status: str) -> Dict[str, Any]:
    payload = {
        "status": status,
        "state_path": state["state_path"],
        "session_id": state["session_id"],
        "resolved_slots": state["resolved_slots"],
        "unresolved_slots": compute_unresolved_slots(state["resolved_slots"], REQUIRED_SLOTS),
        "open_optional_slots": compute_unresolved_slots(state["resolved_slots"], OPTIONAL_SLOTS),
    }
    if question is not None:
        payload["question_id"] = question["question_id"]
        payload["question_markdown"] = render_question_markdown(question, state)
    if status == "ready_to_generate":
        payload["scope_summary"] = summarize_scope(state)
    return payload


def start_interview(
    goal: str,
    project_root: Path,
    grounding_data: Dict[str, Any] | None = None,
    session_id: str | None = None,
) -> Dict[str, Any]:
    topic_label = extract_topic_label(goal)
    session_id = session_id or f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    state_path = interview_state_path(project_root, session_id)
    quick_grounding = grounding_data or run_quick_grounding(goal)
    state = {
        "version": 1,
        "session_id": session_id,
        "goal": goal,
        "topic_label": topic_label,
        "topic_slug": slugify(topic_label),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "quick_grounding": quick_grounding,
        "resolved_slots": {},
        "answers": [],
        "awaiting_confirmation": False,
        "completion_status": "active",
        "state_path": str(state_path),
    }
    question = next_question(state)
    if question is None:
        raise SystemExit("failed to generate the initial interview question")
    state["current_question"] = question
    write_json(state_path, state)
    return public_state_payload(state, question, "question")


def reset_for_revision(state: Dict[str, Any], target: str) -> None:
    if target == "Primary concern":
        for slot in ["primary_concern", "primary_concern_label", "primary_concern_other", "concern_detail"]:
            state["resolved_slots"].pop(slot, None)
    elif target == "Decision goal":
        state["resolved_slots"].pop("decision_goal", None)
    elif target == "Usage pattern":
        state["resolved_slots"].pop("usage_pattern", None)
    elif target == "Personal context":
        state["resolved_slots"].pop("personal_context", None)
    elif target == "Evidence bar / time horizon":
        state["resolved_slots"].pop("evidence_bar", None)
        state["resolved_slots"].pop("time_horizon", None)
    elif target == "Final output style":
        state["resolved_slots"].pop("decision_output", None)
    state["awaiting_confirmation"] = False


def apply_answer(state: Dict[str, Any], response: str) -> Dict[str, Any]:
    question = state["current_question"]
    parsed = parse_answer(question, response)
    slots = state["resolved_slots"]
    question_id = question["question_id"]

    if question_id == "confirm_scope":
        if parsed["kind"] == "option" and parsed["index"] == 1:
            state["completion_status"] = "ready_to_generate"
            return public_state_payload(state, None, "ready_to_generate")
        if parsed["kind"] == "option" and parsed["index"] == 2:
            next_q = build_library_question("revision_target")
            state["current_question"] = next_q
            state["awaiting_confirmation"] = False
            return public_state_payload(state, next_q, "question")
        raise SystemExit("confirmation requires choosing 1 or 2")

    if question_id == "revision_target":
        if parsed["kind"] != "option":
            raise SystemExit("revision target must be selected by number")
        reset_for_revision(state, parsed["value"])
        next_q = next_question(state)
        if next_q is None:
            raise SystemExit("failed to produce a revision question")
        state["current_question"] = next_q
        return public_state_payload(state, next_q, "question")

    if question_id == "primary_concern":
        if parsed["kind"] == "option":
            label = parsed["value"]
            key = None
            for candidate in state["quick_grounding"]["concern_candidates"]:
                if candidate["label"] == label:
                    key = candidate["key"]
                    break
            if key is None:
                key = map_primary_concern_freeform(label) or "custom"
            slots["primary_concern"] = key
            slots["primary_concern_label"] = label
        else:
            mapped = map_primary_concern_freeform(parsed["raw"])
            if mapped:
                slots["primary_concern"] = mapped
                slots["primary_concern_label"] = CONCERN_FAMILIES[mapped]["label"]
                slots["primary_concern_other"] = parsed["raw"]
            else:
                slots["primary_concern"] = "custom"
                slots["primary_concern_label"] = parsed["raw"]
                slots["primary_concern_other"] = parsed["raw"]
                slots["concern_detail"] = parsed["raw"]
    elif question_id.startswith("concern_detail_"):
        slots["concern_detail"] = parsed["raw"] if parsed["kind"] == "other" else parsed["value"]
    elif question_id in QUESTION_LIBRARY:
        slot = QUESTION_LIBRARY[question_id]["slot"]
        slots[slot] = parsed["raw"] if parsed["kind"] == "other" else parsed["value"]
    else:
        raise SystemExit(f"unsupported question_id: {question_id}")

    state["answers"].append(
        {
            "question_id": question_id,
            "response": response,
            "normalized": parsed,
            "timestamp": now_iso(),
        }
    )
    next_q = next_question(state)
    if next_q is None:
        state["completion_status"] = "ready_to_generate"
        return public_state_payload(state, None, "ready_to_generate")
    state["current_question"] = next_q
    return public_state_payload(state, next_q, "question")


def load_interview_state(path: Path) -> Dict[str, Any]:
    state = read_json(path)
    state["state_path"] = str(path)
    return state


def write_scope_artifact(project_root: Path, state: Dict[str, Any]) -> Path:
    artifact_path = project_root / ".deepwork" / "tmp" / "interviews" / f"{state['session_id']}.scope.md"
    lines = [
        "# Scoping Artifact",
        "",
        f"## Original Ask\n{state['goal']}",
        "",
        "## Scope Summary",
        summarize_scope(state),
        "",
        "## Grounding Notes",
    ]
    for note in state["quick_grounding"].get("notes", []):
        lines.append(f"- {note}")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return artifact_path


def cmd_start(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    payload = start_interview(goal=args.goal, project_root=project_root)
    print(json.dumps(payload, indent=2))


def cmd_answer(args: argparse.Namespace) -> None:
    state_path = Path(args.state).resolve()
    state = load_interview_state(state_path)
    payload = apply_answer(state, args.response)
    state["updated_at"] = now_iso()
    write_json(state_path, state)
    print(json.dumps(payload, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    state_path = Path(args.state).resolve()
    state = load_interview_state(state_path)
    payload = public_state_payload(state, state.get("current_question"), state.get("completion_status", "active"))
    payload["goal"] = state["goal"]
    payload["quick_grounding"] = state["quick_grounding"]
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Deepwork-style scoping for research workflows")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="start a new scoping interview")
    p_start.add_argument("--goal", required=True)
    p_start.add_argument("--project-root", default=".")
    p_start.set_defaults(func=cmd_start)

    p_answer = sub.add_parser("answer", help="answer the current interview question")
    p_answer.add_argument("--state", required=True)
    p_answer.add_argument("--response", required=True)
    p_answer.set_defaults(func=cmd_answer)

    p_status = sub.add_parser("status", help="show current interview state")
    p_status.add_argument("--state", required=True)
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
