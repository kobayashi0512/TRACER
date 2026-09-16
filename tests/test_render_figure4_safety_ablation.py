import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
FIGURE_ROOT = APP_ROOT / "figures" / "tracer_safety_ablation_figure4_20260915_1130"
SCRIPT_PATH = FIGURE_ROOT / "03_scripts" / "render_figure4_safety_ablation.py"
SPEC = importlib.util.spec_from_file_location("render_figure4", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderFigure4SafetyAblationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary_path = APP_ROOT / "results" / "factorized_safety_benchmark_summary_v1.json"
        self.summary = json.loads(self.summary_path.read_text(encoding="utf-8"))

    def test_figure_values_match_the_frozen_summary(self) -> None:
        values = MODULE.collect_plot_data(self.summary)
        self.assertEqual(values["complete_values"], [0, 1, 1, 1, 7])
        self.assertEqual(values["provenance_values"], [0, 1])
        self.assertEqual(values["critical_matrix"].tolist(), [[1, 1, 1, 1, 1], [0, 1, 0, 0, 1], [0, 0, 1, 0, 1], [0, 0, 0, 1, 1]])

    def test_renderer_exports_vector_and_print_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = MODULE.render_figure(self.summary_path, Path(temp_dir))
            self.assertEqual({path.suffix for path in outputs}, {".png", ".pdf", ".svg"})
            self.assertTrue(all(path.exists() and path.stat().st_size > 0 for path in outputs))


if __name__ == "__main__":
    unittest.main()
