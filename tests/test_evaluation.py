import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evaluation import evaluate, validate_adjudicated_records


def records() -> list[dict]:
    return json.loads((APP_ROOT / "data" / "demo_adjudicated_outputs_v1.json").read_text(encoding="utf-8"))


def reference() -> dict:
    return json.loads((APP_ROOT / "data" / "demo_evaluation_reference_v1.json").read_text(encoding="utf-8"))


class EvaluationTests(unittest.TestCase):
    def test_paired_unsafe_escalation_is_scored_by_packet_model_pair(self) -> None:
        result = evaluate(records(), reference())
        paired = result["paired_unsafe_escalation"]
        self.assertEqual(paired["n_pairs"], 2)
        self.assertEqual(paired["free_form_rate"], 0.5)
        self.assertEqual(paired["gated_card_rate"], 0.0)
        self.assertEqual(paired["risk_difference_gated_minus_free"], -0.5)

    def test_confidence_is_calibrated_to_eligibility_not_biology(self) -> None:
        result = evaluate(records(), reference())
        calibration = result["calibration_all_outputs"]
        self.assertEqual(calibration["n"], 4)
        self.assertAlmostEqual(calibration["brier_score"], 0.2242, places=4)

    def test_duplicate_packet_model_condition_is_rejected(self) -> None:
        bad_records = records()
        bad_records.append(bad_records[0].copy())
        errors = validate_adjudicated_records(bad_records, reference())
        self.assertTrue(any("Duplicate adjudication record" in error for error in errors))
