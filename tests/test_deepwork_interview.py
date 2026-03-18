import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "skills" / "deepwork" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import deepwork_interview as interview


GROUNDING = {
    "queries": ["baby carrots health concerns", "baby carrots benefits risks"],
    "notes": [
        "Search results discuss blood sugar impact, pesticide residue, and beta-carotene intake.",
        "Several summaries contrast snack usefulness with processing concerns.",
    ],
    "concern_candidates": interview.default_concern_candidates(),
    "concern_scores": {
        "blood_sugar_metabolic": 5,
        "pesticides_contaminants": 3,
        "processing_chlorine": 2,
        "gut_health": 1,
        "calories_body_composition": 2,
        "nutrient_quality_vitamin": 4,
    },
}


class DeepworkInterviewTests(unittest.TestCase):
    def test_start_returns_concern_led_first_question(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = interview.start_interview(
                goal="figure out if baby carrots are a net negative for me due to health concerns or not",
                project_root=Path(tempdir),
                grounding_data=GROUNDING,
                session_id="test-session",
            )

        self.assertEqual(payload["question_id"], "primary_concern")
        self.assertIn("What is the main concern", payload["question_markdown"])
        self.assertIn("1. blood sugar / metabolic health", payload["question_markdown"])
        self.assertIn("7. Other", payload["question_markdown"])

    def test_blood_sugar_branch_asks_metabolic_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = interview.start_interview(
                goal="figure out if baby carrots are a net negative for me",
                project_root=Path(tempdir),
                grounding_data=GROUNDING,
                session_id="test-session",
            )
            state = interview.load_interview_state(Path(payload["state_path"]))
            next_payload = interview.apply_answer(state, "1")

        self.assertEqual(next_payload["question_id"], "concern_detail_blood_sugar_metabolic")
        self.assertIn("Which metabolic angle", next_payload["question_markdown"])

    def test_other_vitamin_a_maps_to_nutrient_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = interview.start_interview(
                goal="figure out if baby carrots are a net negative for me",
                project_root=Path(tempdir),
                grounding_data=GROUNDING,
                session_id="test-session",
            )
            state = interview.load_interview_state(Path(payload["state_path"]))
            next_payload = interview.apply_answer(state, "Other: vitamin A excess")

        self.assertEqual(state["resolved_slots"]["primary_concern"], "nutrient_quality_vitamin")
        self.assertEqual(next_payload["question_id"], "concern_detail_nutrient_quality_vitamin")
        self.assertIn("Which nutrient angle", next_payload["question_markdown"])


if __name__ == "__main__":
    unittest.main()
