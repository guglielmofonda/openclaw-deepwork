#!/usr/bin/env python3
import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

STATE_VERSION = 1
MAX_REVIEW_ATTEMPTS = 3
MAX_INSTRUCTIONS_CHARS = 8000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_job(project_root: Path, job_name: str) -> Dict[str, Any]:
    job_dir = project_root / ".deepwork" / "jobs" / job_name
    job_path = job_dir / "job.yml"
    if not job_path.exists():
        raise SystemExit(f"job.yml not found at {job_path}")
    data = yaml.safe_load(read_text(job_path))
    if not isinstance(data, dict):
        raise SystemExit("job.yml must parse to a YAML object")

    required = ["name", "version", "summary", "common_job_info_provided_to_all_steps_at_runtime", "steps"]
    missing = [k for k in required if k not in data]
    if missing:
        raise SystemExit(f"job.yml missing required fields: {', '.join(missing)}")

    if data.get("name") != job_name:
        raise SystemExit(f"job name mismatch: expected {job_name}, found {data.get('name')}")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise SystemExit("job.yml steps must be a non-empty list")

    step_ids = [s.get("id") for s in steps if isinstance(s, dict)]
    if len(step_ids) != len(set(step_ids)):
        raise SystemExit("duplicate step ids detected in job.yml")

    step_map = {s["id"]: s for s in steps}
    data["_job_dir"] = str(job_dir)
    data["_step_map"] = step_map
    return data


def select_workflow(job: Dict[str, Any], workflow_name: str | None) -> Dict[str, Any]:
    workflows = job.get("workflows") or []
    if workflows:
        if workflow_name:
            for wf in workflows:
                if wf.get("name") == workflow_name:
                    return wf
            available = ", ".join(w.get("name", "<unknown>") for w in workflows)
            raise SystemExit(f"workflow '{workflow_name}' not found. Available: {available}")
        if len(workflows) == 1:
            return workflows[0]
        available = ", ".join(w.get("name", "<unknown>") for w in workflows)
        raise SystemExit(f"workflow required. Available: {available}")

    # No workflows defined: synthesize a default workflow from steps order
    return {
        "name": job["name"],
        "summary": job.get("summary", ""),
        "steps": [s["id"] for s in job["steps"]],
    }


def normalize_workflow_steps(steps: List[Any]) -> List[List[str]]:
    normalized: List[List[str]] = []
    for entry in steps:
        if isinstance(entry, list):
            normalized.append([str(s) for s in entry])
        else:
            normalized.append([str(entry)])
    return normalized


def ensure_workflow_steps_exist(step_map: Dict[str, Any], workflow_steps: List[List[str]]) -> None:
    for entry in workflow_steps:
        for step_id in entry:
            if step_id not in step_map:
                raise SystemExit(f"workflow references unknown step_id: {step_id}")


def validate_dependencies(step_map: Dict[str, Any]) -> None:
    for step_id, step in step_map.items():
        deps = step.get("dependencies") or []
        inputs = step.get("inputs") or []
        for inp in inputs:
            if not isinstance(inp, dict):
                continue
            if "from_step" in inp:
                from_step = inp.get("from_step")
                if from_step not in deps:
                    raise SystemExit(
                        f"step '{step_id}' has file input from '{from_step}' but missing it in dependencies"
                    )


def state_path(project_root: Path, session_id: str) -> Path:
    return project_root / ".deepwork" / "tmp" / "sessions" / "openclaw" / f"session-{session_id}" / "state.json"


def read_state(project_root: Path, session_id: str) -> Dict[str, Any]:
    path = state_path(project_root, session_id)
    if not path.exists():
        raise SystemExit(f"state not found for session {session_id}")
    return json.loads(read_text(path))


def write_state(project_root: Path, session_id: str, state: Dict[str, Any]) -> None:
    path = state_path(project_root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def build_step_info(project_root: Path, job: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    step = job["_step_map"][step_id]
    job_dir = Path(job["_job_dir"])
    instr_path = job_dir / step["instructions_file"]
    instructions = None
    if instr_path.exists():
        content = read_text(instr_path)
        if len(content) > MAX_INSTRUCTIONS_CHARS:
            content = content[:MAX_INSTRUCTIONS_CHARS] + "\n\n...[truncated]"
        instructions = content

    outputs = []
    for name, spec in (step.get("outputs") or {}).items():
        outputs.append(
            {
                "name": name,
                "type": spec.get("type"),
                "description": spec.get("description"),
                "required": bool(spec.get("required", True)),
            }
        )

    return {
        "step_id": step_id,
        "name": step.get("name"),
        "description": step.get("description"),
        "instructions_path": str(instr_path),
        "instructions": instructions,
        "inputs": step.get("inputs") or [],
        "outputs": outputs,
        "reviews": step.get("reviews") or [],
    }


def validate_outputs(project_root: Path, step: Dict[str, Any], outputs: Dict[str, Any]) -> None:
    declared = step.get("outputs") or {}
    declared_names = set(declared.keys())
    provided_names = set(outputs.keys())

    extra = provided_names - declared_names
    if extra:
        raise SystemExit(f"unknown output names provided: {', '.join(sorted(extra))}")

    required = {k for k, v in declared.items() if v.get("required", True)}
    missing = required - provided_names
    if missing:
        raise SystemExit(f"missing required outputs: {', '.join(sorted(missing))}")

    for name, spec in declared.items():
        if name not in outputs:
            continue
        expected_type = spec.get("type")
        value = outputs[name]

        if expected_type == "file":
            if not isinstance(value, str):
                raise SystemExit(f"output '{name}' must be a single string path")
            path = Path(value)
            full = path if path.is_absolute() else project_root / path
            if not full.exists():
                raise SystemExit(f"output '{name}' file not found at: {value}")

        elif expected_type == "files":
            if not isinstance(value, list):
                raise SystemExit(f"output '{name}' must be a list of paths")
            for item in value:
                if not isinstance(item, str):
                    raise SystemExit(f"output '{name}' must be a list of string paths")
                path = Path(item)
                full = path if path.is_absolute() else project_root / path
                if not full.exists():
                    raise SystemExit(f"output '{name}' file not found at: {item}")


def write_review_packet(
    project_root: Path,
    session_id: str,
    job: Dict[str, Any],
    step_id: str,
    outputs: Dict[str, Any],
    attempt: int,
) -> str:
    step = job["_step_map"][step_id]
    reviews = step.get("reviews") or []

    review_dir = project_root / ".deepwork" / "tmp" / "reviews" / f"session-{session_id}" / step_id
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"review_attempt_{attempt}.md"

    lines: List[str] = []
    lines.append(f"# Review Packet: {job['name']} / {step_id}")
    lines.append("")
    lines.append("## Quality Criteria")
    for review in reviews:
        criteria = review.get("quality_criteria") or {}
        for name, statement in criteria.items():
            lines.append(f"- **{name}**: {statement}")
    lines.append("")

    for review in reviews:
        guidance = review.get("additional_review_guidance")
        if guidance:
            lines.append("## Additional Review Guidance")
            lines.append(guidance)
            lines.append("")
            break

    lines.append("## Outputs")
    for name, value in outputs.items():
        lines.append("")
        lines.append(f"### {name}")
        if isinstance(value, list):
            for path_str in value:
                lines.extend(_embed_output(project_root, path_str))
        else:
            lines.extend(_embed_output(project_root, value))

    review_path.write_text("\n".join(lines), encoding="utf-8")
    return str(review_path)


def _embed_output(project_root: Path, path_str: str) -> List[str]:
    path = Path(path_str)
    full = path if path.is_absolute() else project_root / path
    if not full.exists():
        return [f"- Missing file: {path_str}"]
    try:
        content = read_text(full)
    except Exception:
        return [f"- Could not read file: {path_str}"]

    return [f"**File:** `{path_str}`", "", "```", content, "```", ""]


def cmd_start(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    job = load_job(project_root, args.job)
    validate_dependencies(job["_step_map"])

    workflow = select_workflow(job, args.workflow)
    workflow_steps = normalize_workflow_steps(workflow.get("steps") or [])
    if not workflow_steps:
        raise SystemExit("workflow has no steps")
    ensure_workflow_steps_exist(job["_step_map"], workflow_steps)

    session_id = args.session or f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    state = {
        "version": STATE_VERSION,
        "created_at": now_iso(),
        "session_id": session_id,
        "job_name": job["name"],
        "workflow_name": workflow.get("name"),
        "goal": args.goal or "",
        "job_dir": job["_job_dir"],
        "workflow_steps": workflow_steps,
        "current_entry_index": 0,
        "current_entry_pending": list(workflow_steps[0]),
        "completed_steps": [],
        "step_progress": {},
        "outputs": {},
    }

    for step_id in job["_step_map"].keys():
        state["step_progress"][step_id] = {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "review_attempts": 0,
        }

    for step_id in state["current_entry_pending"]:
        state["step_progress"][step_id]["status"] = "started"
        state["step_progress"][step_id]["started_at"] = now_iso()

    write_state(project_root, session_id, state)

    response = {
        "status": "started",
        "session_id": session_id,
        "job_name": job["name"],
        "workflow_name": workflow.get("name"),
        "goal": args.goal or "",
        "current_entry_index": state["current_entry_index"],
        "current_steps": [build_step_info(project_root, job, s) for s in state["current_entry_pending"]],
        "common_job_info": job.get("common_job_info_provided_to_all_steps_at_runtime"),
    }
    print(json.dumps(response, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    state = read_state(project_root, args.session)
    response = {
        "session_id": state["session_id"],
        "job_name": state["job_name"],
        "workflow_name": state["workflow_name"],
        "goal": state.get("goal"),
        "current_entry_index": state["current_entry_index"],
        "current_entry_pending": state["current_entry_pending"],
        "completed_steps": state["completed_steps"],
    }
    print(json.dumps(response, indent=2))


def cmd_finish_step(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    job = load_job(project_root, args.job)
    state = read_state(project_root, args.session)

    step_id = args.step
    if step_id not in state["current_entry_pending"]:
        raise SystemExit(f"step '{step_id}' is not in the current pending entry")

    step = job["_step_map"].get(step_id)
    if not step:
        raise SystemExit(f"unknown step id: {step_id}")

    outputs = {}
    if args.outputs_json:
        outputs = json.loads(args.outputs_json)
    elif args.outputs_file:
        outputs = json.loads(read_text(Path(args.outputs_file)))

    validate_outputs(project_root, step, outputs)

    reviews = step.get("reviews") or []
    progress = state["step_progress"].get(step_id)
    if progress is None:
        raise SystemExit(f"missing progress state for step: {step_id}")

    review_decision = None
    if args.review_pass:
        review_decision = "pass"
    elif args.review_fail:
        review_decision = "fail"

    if reviews and not args.skip_reviews and not args.override:
        if review_decision is None:
            review_path = write_review_packet(
                project_root,
                state["session_id"],
                job,
                step_id,
                outputs,
                progress["review_attempts"] + 1,
            )
            response = {
                "status": "needs_review",
                "session_id": state["session_id"],
                "step_id": step_id,
                "review_packet": review_path,
                "review_attempts": progress["review_attempts"],
            }
            print(json.dumps(response, indent=2))
            return

        progress["review_attempts"] += 1
        if review_decision == "fail":
            if progress["review_attempts"] >= MAX_REVIEW_ATTEMPTS and not args.override:
                response = {
                    "status": "max_attempts_reached",
                    "session_id": state["session_id"],
                    "step_id": step_id,
                    "review_attempts": progress["review_attempts"],
                    "message": "Max review attempts reached. Use --override to proceed.",
                }
                print(json.dumps(response, indent=2))
                return
            response = {
                "status": "review_failed",
                "session_id": state["session_id"],
                "step_id": step_id,
                "review_attempts": progress["review_attempts"],
            }
            print(json.dumps(response, indent=2))
            return

    # Mark step complete
    state["outputs"][step_id] = outputs
    progress["status"] = "completed"
    progress["completed_at"] = now_iso()
    if step_id not in state["completed_steps"]:
        state["completed_steps"].append(step_id)

    state["current_entry_pending"] = [s for s in state["current_entry_pending"] if s != step_id]

    # If entry done, advance to next entry
    if not state["current_entry_pending"]:
        next_index = state["current_entry_index"] + 1
        if next_index >= len(state["workflow_steps"]):
            state["current_entry_index"] = next_index
            write_state(project_root, state["session_id"], state)
            response = {
                "status": "workflow_complete",
                "session_id": state["session_id"],
                "completed_steps": state["completed_steps"],
            }
            print(json.dumps(response, indent=2))
            return

        state["current_entry_index"] = next_index
        state["current_entry_pending"] = list(state["workflow_steps"][next_index])
        for s in state["current_entry_pending"]:
            progress = state["step_progress"][s]
            if progress["status"] == "pending":
                progress["status"] = "started"
                progress["started_at"] = now_iso()

    write_state(project_root, state["session_id"], state)

    response = {
        "status": "in_progress",
        "session_id": state["session_id"],
        "current_entry_index": state["current_entry_index"],
        "current_steps": [build_step_info(project_root, job, s) for s in state["current_entry_pending"]],
    }
    print(json.dumps(response, indent=2))


def cmd_go_to_step(args: argparse.Namespace) -> None:
    project_root = Path(args.project_root).resolve()
    job = load_job(project_root, args.job)
    state = read_state(project_root, args.session)

    target = args.step
    workflow_steps: List[List[str]] = state["workflow_steps"]
    target_index = None
    for i, entry in enumerate(workflow_steps):
        if target in entry:
            target_index = i
            break
    if target_index is None:
        raise SystemExit(f"step '{target}' not found in workflow")

    # Reset steps from target entry onward
    for i in range(target_index, len(workflow_steps)):
        for step_id in workflow_steps[i]:
            state["step_progress"][step_id] = {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "review_attempts": 0,
            }
            state["outputs"].pop(step_id, None)
            if step_id in state["completed_steps"]:
                state["completed_steps"].remove(step_id)

    state["current_entry_index"] = target_index
    state["current_entry_pending"] = list(workflow_steps[target_index])
    for step_id in state["current_entry_pending"]:
        state["step_progress"][step_id]["status"] = "started"
        state["step_progress"][step_id]["started_at"] = now_iso()

    write_state(project_root, state["session_id"], state)

    response = {
        "status": "rewound",
        "session_id": state["session_id"],
        "current_entry_index": state["current_entry_index"],
        "current_steps": [build_step_info(project_root, job, s) for s in state["current_entry_pending"]],
    }
    print(json.dumps(response, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Deepwork-style workflow runner (OpenClaw)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="start a workflow session")
    p_start.add_argument("--job", required=True)
    p_start.add_argument("--workflow", required=False)
    p_start.add_argument("--goal", required=False)
    p_start.add_argument("--session", required=False)
    p_start.add_argument("--project-root", default=".")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="show session status")
    p_status.add_argument("--session", required=True)
    p_status.add_argument("--project-root", default=".")
    p_status.set_defaults(func=cmd_status)

    p_finish = sub.add_parser("finish-step", help="finish a step and advance workflow")
    p_finish.add_argument("--job", required=True)
    p_finish.add_argument("--session", required=True)
    p_finish.add_argument("--step", required=True)
    p_finish.add_argument("--outputs-json", required=False)
    p_finish.add_argument("--outputs-file", required=False)
    p_finish.add_argument("--review-pass", action="store_true")
    p_finish.add_argument("--review-fail", action="store_true")
    p_finish.add_argument("--skip-reviews", action="store_true")
    p_finish.add_argument("--override", action="store_true")
    p_finish.add_argument("--project-root", default=".")
    p_finish.set_defaults(func=cmd_finish_step)

    p_goto = sub.add_parser("go-to-step", help="rewind workflow to a prior step")
    p_goto.add_argument("--job", required=True)
    p_goto.add_argument("--session", required=True)
    p_goto.add_argument("--step", required=True)
    p_goto.add_argument("--project-root", default=".")
    p_goto.set_defaults(func=cmd_go_to_step)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
