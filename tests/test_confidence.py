import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.confidence import assess


def complete_card() -> dict:
    return {
        "candidate_id": "TEST-HIGH",
        "cross_cohort_replication": {
            "independent_cohorts": 2,
            "effect_direction_consistent": True,
            "same_biological_compartment": True,
            "same_measurement_level": True,
            "discovery_fdr": 0.01,
            "validation_fdr": 0.02,
        },
        "perturbation_support": {"tested": True, "direction_consistent": True, "independent_studies": 1},
        "orthogonal_evidence": {"modalities": 2, "direction_consistent": True},
        "curated_literature_evidence": {"independent_sources": 2, "supports_claim": True},
        "confounding_robustness": {"batch_controlled": True, "composition_controlled": True},
        "discriminating_experiment": {
            "intervention": "x",
            "comparator": "y",
            "readout": "z",
            "prediction_if_hypothesis_a": "a",
            "prediction_if_hypothesis_b": "b",
        },
    }


class ConfidenceTests(unittest.TestCase):
    def test_complete_card_is_high_and_ready(self) -> None:
        result = assess(complete_card())
        self.assertEqual(result.priority_score, 1.0)
        self.assertEqual(result.level, "HIGH")
        self.assertTrue(result.ready_for_validation)
        self.assertTrue(result.causal_language_permitted)

    def test_single_cohort_is_capped_low(self) -> None:
        card = complete_card()
        card["cross_cohort_replication"]["independent_cohorts"] = 1
        result = assess(card)
        self.assertEqual(result.level, "LOW")
        self.assertFalse(result.ready_for_validation)

    def test_missing_perturbation_prohibits_causal_language(self) -> None:
        card = complete_card()
        card["perturbation_support"]["tested"] = False
        result = assess(card)
        self.assertFalse(result.causal_language_permitted)

    def test_cross_modality_does_not_count_as_replication(self) -> None:
        card = complete_card()
        card["cross_cohort_replication"]["same_measurement_level"] = False
        result = assess(card)
        self.assertEqual(result.level, "LOW")
        self.assertFalse(result.ready_for_validation)

    def test_every_rederived_replication_cohort_must_pass_fdr(self) -> None:
        card = complete_card()
        card["cross_cohort_replication"].update(
            {
                "independent_cohorts": 3,
                "cohort_ids": ["A", "B", "C"],
                "fdr_by_cohort": {"A": 0.01, "B": 0.02, "C": 0.30},
            }
        )
        result = assess(card)
        self.assertEqual(result.level, "LOW")
        self.assertFalse(result.ready_for_validation)

    def test_missing_experiment_is_not_ready(self) -> None:
        card = complete_card()
        card["discriminating_experiment"] = {"intervention": "x"}
        result = assess(card)
        self.assertFalse(result.ready_for_validation)
        self.assertIn("No complete discriminating experiment with comparator and opposing predictions.", result.hard_stops)


if __name__ == "__main__":
    unittest.main()
