import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_graph import evaluate_with_evidence_graph


def current_card() -> dict:
    return json.loads(
        (APP_ROOT / "data" / "demo_candidate_card_current_evidence_v1.json").read_text(encoding="utf-8")
    )


def packet() -> dict:
    return json.loads(
        (APP_ROOT / "data" / "demo_evidence_packet_cross_modality_v1.json").read_text(encoding="utf-8")
    )


def registry() -> dict:
    return json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))


class EvidenceGraphTests(unittest.TestCase):
    def test_registry_derived_features_override_model_claims(self) -> None:
        card = current_card()
        card["cross_cohort_replication"].update(
            {
                "effect_direction_consistent": True,
                "same_biological_compartment": True,
                "same_measurement_level": True,
                "discovery_fdr": 0.001,
                "validation_fdr": 0.001,
            }
        )
        card["perturbation_support"] = {
            "tested": True,
            "direction_consistent": True,
            "independent_studies": 5,
        }
        result = evaluate_with_evidence_graph(card, packet(), registry())
        canonical = result["canonical_card"]
        self.assertFalse(canonical["cross_cohort_replication"]["same_measurement_level"])
        self.assertFalse(canonical["cross_cohort_replication"]["effect_direction_consistent"])
        self.assertFalse(canonical["perturbation_support"]["tested"])
        self.assertEqual(result["assessment"]["level"], "LOW")
        self.assertFalse(result["draft_admissible_for_review"])
        self.assertEqual(result["assessment"]["operational_decision"], "REJECT_DRAFT")

    def test_omitted_packet_evidence_blocks_selective_support(self) -> None:
        card = current_card()
        card["evidence_sources"] = card["evidence_sources"][:1]
        result = evaluate_with_evidence_graph(card, packet(), registry())
        self.assertEqual(result["graph"]["uncited_packet_source_ids"], ["external-bulk-direction-check"])
        self.assertEqual(result["assessment"]["level"], "LOW")
        self.assertFalse(result["draft_admissible_for_review"])

    def test_unsupported_causal_language_is_flagged(self) -> None:
        card = current_card()
        card["hypotheses"][0]["statement"] = "The program causes anti-PD-1 resistance."
        result = evaluate_with_evidence_graph(card, packet(), registry())
        self.assertTrue(result["graph"]["draft_causal_language_detected"])
        self.assertFalse(result["assessment"]["causal_language_permitted"])
        self.assertIn(
            "Draft contains causal language without provenance-derived perturbation support.",
            result["assessment"]["hard_stops"],
        )

    def test_complete_synthetic_evidence_graph_can_reach_high(self) -> None:
        synthetic_registry = registry()
        synthetic_registry["cohorts"].update(
            {
                "SYN-SC-A": {
                    "measurement_level": "single_cell_rna",
                    "compartment": "tumor_cd45_positive_cells",
                    "baseline_ici_response_association_eligible": True,
                    "same_measurement_replication_eligible": True,
                    "source_independence_group": "synthetic_study_a",
                },
                "SYN-SC-B": {
                    "measurement_level": "single_cell_rna",
                    "compartment": "tumor_cd45_positive_cells",
                    "baseline_ici_response_association_eligible": True,
                    "same_measurement_replication_eligible": True,
                    "source_independence_group": "synthetic_study_b",
                },
                "SYN-FUNCTION": {
                    "measurement_level": "functional_assay",
                    "compartment": "ex_vivo_tumor_immune_coculture",
                    "baseline_ici_response_association_eligible": False,
                    "same_measurement_replication_eligible": False,
                    "source_independence_group": "synthetic_functional_study",
                },
                "SYN-LIT-A": {"measurement_level": "literature", "compartment": "not_applicable", "source_independence_group": "synthetic_literature_a"},
                "SYN-LIT-B": {"measurement_level": "literature", "compartment": "not_applicable", "source_independence_group": "synthetic_literature_b"},
            }
        )
        items = [
            ("obs-a", "SYN-SC-A", "observational_association", "consistent", 0.01),
            ("obs-b", "SYN-SC-B", "replication", "consistent", 0.02),
            ("perturb", "SYN-FUNCTION", "perturbation", "consistent", None),
            ("lit-a", "SYN-LIT-A", "literature", "consistent", None),
            ("lit-b", "SYN-LIT-B", "literature", "consistent", None),
        ]
        synthetic_packet = {
            "evidence_items": [
                {
                    "id": item_id,
                    "cohort_id": cohort_id,
                    "source_identifier": f"SOURCE-{item_id}",
                    "evidence_kind": kind,
                    "direction_status": direction,
                    "confounding_assessed": True,
                    "fdr": fdr,
                }
                for item_id, cohort_id, kind, direction, fdr in items
            ]
        }
        card = current_card()
        card["evidence_sources"] = [
            {
                "id": item_id,
                "source_type": kind,
                "identifier": f"SOURCE-{item_id}",
                "supports_or_refutes": "supports",
            }
            for item_id, _, kind, _, _ in items
        ]
        result = evaluate_with_evidence_graph(card, synthetic_packet, synthetic_registry)
        self.assertEqual(result["assessment"]["level"], "HIGH")
        self.assertTrue(result["assessment"]["ready_for_validation"])
        self.assertTrue(result["assessment"]["causal_language_permitted"])
        self.assertTrue(result["draft_admissible_for_review"])
        self.assertEqual(result["assessment"]["operational_decision"], "ADMIT_FOR_HUMAN_REVIEW")

        synthetic_registry["cohorts"]["SYN-SC-B"]["source_independence_group"] = "synthetic_study_a"
        source_dependent = evaluate_with_evidence_graph(card, synthetic_packet, synthetic_registry)
        self.assertEqual(source_dependent["graph"]["independent_source_count"], 1)
        self.assertEqual(source_dependent["assessment"]["level"], "LOW")
        synthetic_registry["cohorts"]["SYN-SC-B"]["source_independence_group"] = "synthetic_study_b"

        card["evidence_sources"] = card["evidence_sources"][:-1]
        with_coverage = evaluate_with_evidence_graph(card, synthetic_packet, synthetic_registry)
        without_coverage = evaluate_with_evidence_graph(
            card,
            synthetic_packet,
            synthetic_registry,
            modules={"provenance_coverage": False},
        )
        self.assertEqual(with_coverage["assessment"]["level"], "LOW")
        self.assertFalse(with_coverage["draft_admissible_for_review"])
        self.assertEqual(without_coverage["assessment"]["level"], "HIGH")
        self.assertTrue(without_coverage["draft_admissible_for_review"])

    def test_transport_ablation_exposes_cross_modality_pseudo_replication(self) -> None:
        synthetic_registry = registry()
        synthetic_registry["cohorts"].update(
            {
                "SYN-SC": {
                    "measurement_level": "single_cell_rna",
                    "compartment": "tumor_cd45_positive_cells",
                    "baseline_ici_response_association_eligible": True,
                    "same_measurement_replication_eligible": True,
                    "source_independence_group": "synthetic_study_sc",
                },
                "SYN-BULK": {
                    "measurement_level": "bulk_rna",
                    "compartment": "tumor_bulk",
                    "baseline_ici_response_association_eligible": True,
                    "same_measurement_replication_eligible": False,
                    "source_independence_group": "synthetic_study_bulk",
                },
                "SYN-FUNCTION": {
                    "measurement_level": "functional_assay",
                    "compartment": "ex_vivo_tumor_immune_coculture",
                    "baseline_ici_response_association_eligible": False,
                    "same_measurement_replication_eligible": False,
                    "source_independence_group": "synthetic_functional_study",
                },
                "SYN-LIT-A": {"measurement_level": "literature", "compartment": "not_applicable", "source_independence_group": "synthetic_literature_a"},
                "SYN-LIT-B": {"measurement_level": "literature", "compartment": "not_applicable", "source_independence_group": "synthetic_literature_b"},
            }
        )
        items = [
            ("obs-sc", "SYN-SC", "observational_association", 0.01),
            ("obs-bulk", "SYN-BULK", "replication", 0.02),
            ("perturb", "SYN-FUNCTION", "perturbation", None),
            ("lit-a", "SYN-LIT-A", "literature", None),
            ("lit-b", "SYN-LIT-B", "literature", None),
        ]
        synthetic_packet = {
            "evidence_items": [
                {
                    "id": item_id,
                    "cohort_id": cohort_id,
                    "source_identifier": f"SOURCE-{item_id}",
                    "evidence_kind": kind,
                    "direction_status": "consistent",
                    "confounding_assessed": True,
                    "fdr": fdr,
                }
                for item_id, cohort_id, kind, fdr in items
            ]
        }
        card = current_card()
        card["cross_cohort_replication"].update(
            {"cohort_ids": ["SYN-SC", "SYN-BULK"], "independent_cohorts": 2}
        )
        card["evidence_sources"] = [
            {
                "id": item_id,
                "source_type": kind,
                "identifier": f"SOURCE-{item_id}",
                "supports_or_refutes": "supports",
            }
            for item_id, _, kind, _ in items
        ]
        full = evaluate_with_evidence_graph(card, synthetic_packet, synthetic_registry)
        transport_blind = evaluate_with_evidence_graph(
            card,
            synthetic_packet,
            synthetic_registry,
            modules={"transport_aware_replication": False},
        )
        self.assertEqual(full["assessment"]["level"], "LOW")
        self.assertEqual(transport_blind["assessment"]["level"], "HIGH")
        self.assertFalse(full["graph"]["transport_eligible"])
        self.assertTrue(transport_blind["graph"]["transport_eligible"])
