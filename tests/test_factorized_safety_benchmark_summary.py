import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = APP_ROOT / "scripts" / "29_summarize_factorized_safety_benchmark_v2.py"
SPEC = importlib.util.spec_from_file_location("factorized_benchmark_summary", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FactorizedSafetyBenchmarkSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        result_path = APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json"
        source_bytes = result_path.read_bytes()
        self.source = json.loads(source_bytes.decode("utf-8"))
        self.summary = MODULE.build_summary(self.source, "test-sha256")

    def test_protocol_has_four_predeclared_critical_cells_and_full_factorial_remainder(self) -> None:
        self.assertEqual(
            self.summary["category_counts"],
            {
                "eligible_positive_control": 1,
                "cross_measurement_only_failure": 1,
                "same_source_only_failure": 1,
                "all_cohort_fdr_only_failure": 1,
                "multi_factor_safety_stress": 28,
            },
        )
        self.assertEqual(len(self.summary["critical_cell_packet_ids"]), 4)
        self.assertEqual(self.summary["protocol"]["n_complete_draft_cases"], 32)
        self.assertEqual(self.summary["protocol"]["n_expected_HIGH"], 1)
        self.assertEqual(self.summary["protocol"]["n_expected_LOW"], 31)

    def test_complete_draft_ablation_counts_are_fixed(self) -> None:
        by_method = {row["method"]: row for row in self.summary["complete_draft_comparison"]}
        self.assertEqual(by_method["Full TRACER"]["unsafe_high_n"], 0)
        self.assertEqual(by_method["TRACER without transport gate"]["unsafe_high_n"], 1)
        self.assertEqual(by_method["TRACER without source-independence gate"]["unsafe_high_n"], 1)
        self.assertEqual(by_method["TRACER without all-cohort FDR gate"]["unsafe_high_n"], 1)
        self.assertEqual(by_method["Naive counting baseline"]["unsafe_high_n"], 7)
        self.assertEqual(by_method["Full TRACER"]["exact_priority_decision_n"], 32)
        self.assertEqual(by_method["Naive counting baseline"]["exact_priority_decision_n"], 25)

    def test_provenance_attack_is_reported_separately_from_complete_drafts(self) -> None:
        by_method = {row["method"]: row for row in self.summary["provenance_omission_comparison"]}
        self.assertEqual(by_method["Full TRACER"]["unsafe_high_n"], 0)
        self.assertEqual(by_method["TRACER without provenance coverage"]["unsafe_high_n"], 1)
        self.assertEqual(by_method["Full TRACER"]["n_expected_low"], 32)

    def test_cli_outputs_auditable_table_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json"
            output_json = root / "summary.json"
            output_tsv = root / "table.tsv"
            output_markdown = root / "table.md"
            import subprocess
            import sys

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--input",
                    str(input_path),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                    "--output-markdown",
                    str(output_markdown),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("saved_json", completed.stdout)
            self.assertTrue(output_json.exists())
            self.assertTrue(output_tsv.exists())
            markdown = output_markdown.read_text(encoding="utf-8")
            self.assertIn("Naive counting baseline", markdown)
            self.assertNotIn("{eligible_positive_control}", markdown)


if __name__ == "__main__":
    unittest.main()
