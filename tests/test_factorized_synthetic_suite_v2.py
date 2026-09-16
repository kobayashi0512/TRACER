import json
import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))


class FactorizedSyntheticSuiteV2Tests(unittest.TestCase):
    def test_generated_factorial_suite_has_complete_factor_coverage(self) -> None:
        suite_dir = APP_ROOT / "data" / "synthetic_packets_v2"
        manifest_path = suite_dir / "manifest_v2.json"
        self.assertTrue(manifest_path.exists(), "Run scripts/27_build_factorized_synthetic_suite_v2.py first.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest["packets"]
        self.assertEqual(len(entries), 32)
        observed = {
            tuple(entry["factors"][factor] for factor in manifest["factor_order"])
            for entry in entries
        }
        self.assertEqual(len(observed), 32)
        self.assertEqual(sum(entry["llm_pilot_subset"] for entry in entries), 12)

    def test_deterministic_factorial_evaluation_matches_protocol(self) -> None:
        result_path = APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json"
        self.assertTrue(result_path.exists(), "Run scripts/28_run_factorized_synthetic_suite_v2.py first.")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["n_packets"], 32)
        self.assertEqual(result["n_deterministic_draft_evaluations"], 96)
        self.assertEqual(result["n_factor_derivations_matching_fixture"], 32)
        self.assertEqual(result["n_complete_matches_expected"], 32)
        self.assertEqual(result["n_omissions_blocked_by_coverage"], 32)
        self.assertEqual(result["n_coverage_ablation_matches_non_provenance_factors"], 32)
        self.assertEqual(result["n_transport_ablation_matches_non_transport_factors"], 32)
        self.assertEqual(result["n_transport_gate_unsafe_high_counterfactuals"], 1)
        self.assertEqual(result["n_source_independence_ablation_matches_non_source_factors"], 32)
        self.assertEqual(result["n_source_independence_gate_unsafe_high_counterfactuals"], 1)
        self.assertEqual(result["n_all_cohort_fdr_ablation_matches_non_fdr_factors"], 32)
        self.assertEqual(result["n_all_cohort_fdr_gate_unsafe_high_counterfactuals"], 1)
        self.assertEqual(result["n_naive_counting_matches_predeclared_rule"], 32)
        self.assertEqual(result["n_naive_counting_unsafe_high_counterfactuals"], 7)


if __name__ == "__main__":
    unittest.main()
