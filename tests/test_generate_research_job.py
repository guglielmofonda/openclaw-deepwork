import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "skills" / "deepwork" / "scripts" / "generate_research_job.py"


def build_state(status: str) -> dict:
    return {
        "session_id": "state-test",
        "goal": "figure out if baby carrots are a net negative for me",
        "topic_label": "baby carrots",
        "topic_slug": "baby-carrots",
        "completion_status": status,
        "quick_grounding": {"queries": [], "notes": [], "concern_candidates": [], "concern_scores": {}},
        "resolved_slots": {
            "primary_concern": "blood_sugar_metabolic",
            "primary_concern_label": "blood sugar / metabolic health",
            "concern_detail": "CGM or blood-sugar stability",
            "decision_goal": "Decide whether I should keep eating it freely",
            "usage_pattern": "Raw snack in small amounts",
            "personal_context": "Blood sugar / diabetes / prediabetes / CGM concerns",
            "evidence_bar": "Peer-reviewed studies and major medical sources only",
            "time_horizon": "Both short-term and long-term",
            "decision_output": "Concise memo with citations",
        },
    }


class GenerateResearchJobTests(unittest.TestCase):
    def test_generator_requires_ready_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            state_path = Path(tempdir) / ".deepwork" / "tmp" / "interviews" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(build_state("active")), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(GENERATOR), "--state", str(state_path), "--project-root", tempdir],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not ready", result.stderr or result.stdout)

    def test_generator_writes_customized_job_from_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            state_path = Path(tempdir) / ".deepwork" / "tmp" / "interviews" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(build_state("ready_to_generate")), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--state",
                    str(state_path),
                    "--project-root",
                    tempdir,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            job_yml = (Path(tempdir) / ".deepwork" / "jobs" / "research_decision" / "job.yml").read_text(
                encoding="utf-8"
            )
            analyze_md = (
                Path(tempdir) / ".deepwork" / "jobs" / "research_decision" / "steps" / "analyze_evidence.md"
            ).read_text(encoding="utf-8")

        self.assertIn("Generated research_decision job", result.stdout)
        self.assertIn("blood sugar / metabolic health", job_yml)
        self.assertIn("glycemic implications", analyze_md)


if __name__ == "__main__":
    unittest.main()
