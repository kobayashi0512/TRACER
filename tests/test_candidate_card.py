import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.candidate_card import validate_card


def demo_card() -> dict:
    return json.loads((APP_ROOT / "data" / "demo_candidate_card_contract_v1.json").read_text(encoding="utf-8"))


def current_evidence_card() -> dict:
    return json.loads(
        (APP_ROOT / "data" / "demo_candidate_card_current_evidence_v1.json").read_text(encoding="utf-8")
    )


def cohort_registry() -> dict:
    return json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))


class CandidateCardTests(unittest.TestCase):
    def test_complete_synthetic_card_is_valid(self) -> None:
        errors, assessment = validate_card(demo_card())
        self.assertEqual(errors, [])
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.level, "HIGH")

    def test_requires_competing_hypotheses(self) -> None:
        card = demo_card()
        card["hypotheses"] = card["hypotheses"][:1]
        errors, assessment = validate_card(card)
        self.assertIsNone(assessment)
        self.assertIn("At least two competing hypotheses are required.", errors)

    def test_requires_opposite_predictions(self) -> None:
        card = demo_card()
        card["discriminating_experiment"]["prediction_if_hypothesis_b"] = "Direction A"
        errors, assessment = validate_card(card)
        self.assertIsNone(assessment)
        self.assertIn("Discriminating experiment must specify different predictions for the two hypotheses.", errors)

    def test_registered_current_evidence_card_is_explicitly_low_priority(self) -> None:
        errors, assessment = validate_card(current_evidence_card(), cohort_registry=cohort_registry())
        self.assertEqual(errors, [])
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.level, "LOW")
        self.assertFalse(assessment.ready_for_validation)

    def test_registry_rejects_false_same_measurement_claim(self) -> None:
        card = current_evidence_card()
        card["cross_cohort_replication"]["same_measurement_level"] = True
        errors, assessment = validate_card(card, cohort_registry=cohort_registry())
        self.assertIsNone(assessment)
        self.assertIn("same_measurement_level cannot be claimed for these registered cohorts.", errors)

    def test_malformed_scoring_sections_are_rejected_before_grading(self) -> None:
        card = demo_card()
        card["perturbation_support"] = None
        card["confounding_robustness"] = {"batch_controlled": "yes"}
        errors, assessment = validate_card(card)
        self.assertIsNone(assessment)
        self.assertIn("perturbation_support must be an object.", errors)
        self.assertIn("confounding_robustness lacks: composition_controlled.", errors)
        self.assertIn("confounding_robustness.batch_controlled must be boolean.", errors)
