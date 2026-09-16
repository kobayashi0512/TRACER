#!/usr/bin/env python3
"""Verify full TRACER on the frozen synthetic stress-test suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.synthetic_suite import evaluate_complete_suite  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, default=APP_ROOT / "data" / "synthetic_packets_v1")
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json",
    )
    parser.add_argument(
        "--output", type=Path, default=APP_ROOT / "results" / "synthetic_suite_algorithm_sanity_v1.json"
    )
    args = parser.parse_args()
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    results = evaluate_complete_suite(args.suite_dir, registry)
    output = {
        "schema": "icb-disambiguate-synthetic-suite-sanity-v1",
        "interpretation": "Synthetic algorithm verification only; not a biological, clinical, or model-performance result.",
        "n_packets": len(results),
        "n_expected_high_priority_matches": sum(result["matches_expected_high_priority"] for result in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "n_packets": len(results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
