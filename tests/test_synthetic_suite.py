import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.synthetic_suite import evaluate_complete_suite
from src.evidence_graph import evaluate_with_evidence_graph
from src.synthetic_suite import complete_draft_from_packet


class SyntheticSuiteTests(unittest.TestCase):
    def test_full_tracer_matches_frozen_synthetic_eligibility(self) -> None:
        registry = json.loads(
            (APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json").read_text(encoding="utf-8")
        )
        results = evaluate_complete_suite(APP_ROOT / "data" / "synthetic_packets_v1", registry)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(result["matches_expected_high_priority"] for result in results))
        self.assertEqual(sum(result["observed_level"] == "HIGH" for result in results), 1)
        self.assertTrue(all(result["draft_admissible_for_review"] for result in results))

    def test_provenance_coverage_blocks_synthetic_selective_omission_attack(self) -> None:
        registry = json.loads(
            (APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json").read_text(encoding="utf-8")
        )
        packet = json.loads(
            (APP_ROOT / "data" / "synthetic_packets_v1" / "SYNTH-SELECTIVE-OMISSION-001.json").read_text(
                encoding="utf-8"
            )
        )
        draft = complete_draft_from_packet(packet)
        draft["evidence_sources"] = [
            source for source in draft["evidence_sources"] if source["id"] != "sc-conflict"
        ]
        full = evaluate_with_evidence_graph(draft, packet, registry)
        without_coverage = evaluate_with_evidence_graph(
            draft, packet, registry, modules={"provenance_coverage": False}
        )
        self.assertEqual(full["assessment"]["level"], "LOW")
        self.assertFalse(full["draft_admissible_for_review"])
        self.assertEqual(without_coverage["assessment"]["level"], "HIGH")
        self.assertTrue(without_coverage["draft_admissible_for_review"])
