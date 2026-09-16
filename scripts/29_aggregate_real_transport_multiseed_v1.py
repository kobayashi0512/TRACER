#!/usr/bin/env python3
"""Create a dependency-aware descriptive summary of frozen transport traces.

It accepts score files produced by script 20.  Its units are retained raw
generations nested in one dependent positive-control panel, never independent
biomedical or independent model-comparison samples.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))


DEFAULT_SCORE_FILES = [
    APP_ROOT / "results" / "real_transport_schema_only_score_v2_seed20260914.json",
    APP_ROOT / "results" / "real_transport_schema_constrained_score_v2_seed20260914.json",
    APP_ROOT / "results" / "real_transport_schema_only_score_v2_seed20260915.json",
    APP_ROOT / "results" / "real_transport_schema_constrained_score_v2_seed20260915.json",
    APP_ROOT / "results" / "real_transport_schema_only_score_v2_seed20260916.json",
    APP_ROOT / "results" / "real_transport_schema_constrained_score_v2_seed20260916.json",
]


def _group_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (record.get("seed"), record.get("condition"), record.get("model"))
        groups[key].append(record)
    summaries = []
    for (seed, condition, model), rows in sorted(groups.items(), key=lambda pair: str(pair[0])):
        structural_counts = Counter(
            error for row in rows for error in row.get("structural_errors", [])
        )
        hard_stop_counts = Counter(
            stop for row in rows for stop in row.get("tracer_hard_stops", [])
        )
        clusters = sorted({row.get("dependency_cluster") for row in rows})
        summaries.append(
            {
                "seed": seed,
                "condition": condition,
                "model": model,
                "n_traces": len(rows),
                "dependency_clusters": clusters,
                "n_parseable": sum(row["parseable_candidate_json"] for row in rows),
                "n_structurally_admissible": sum(row["structurally_admissible"] for row in rows),
                "n_false_same_measurement_claim": sum(
                    row["false_same_measurement_claim"] for row in rows
                ),
                "n_tracer_admitted": sum(row["tracer_admitted"] for row in rows),
                "n_tracer_high": sum(
                    row["tracer_admitted"] and row["tracer_level"] == "HIGH" for row in rows
                ),
                "n_tracer_unsafe_high_escalation": sum(
                    row["tracer_unsafe_high_escalation"] for row in rows
                ),
                "structural_error_counts": dict(sorted(structural_counts.items())),
                "tracer_hard_stop_counts": dict(sorted(hard_stop_counts.items())),
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--score-files",
        type=Path,
        nargs="+",
        default=DEFAULT_SCORE_FILES,
        help="Six score files: 3 seeds × 2 frozen conditions.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "results" / "real_transport_multiseed_descriptive_summary_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=APP_ROOT / "config" / "real_transport_multiseed_protocol_v1.json",
    )
    args = parser.parse_args()
    missing = [str(path) for path in args.score_files if not path.exists()]
    if missing:
        raise SystemExit("Missing required score files: " + ", ".join(missing))
    score_files = [json.loads(path.read_text(encoding="utf-8")) for path in args.score_files]
    records = [record for score_file in score_files for record in score_file["records"]]
    summaries = _group_records(records)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    expected_seeds = {20260914, *protocol["new_seeds"]}
    expected_keys = {
        (seed, condition, model)
        for seed in expected_seeds
        for condition in protocol["conditions"]
        for model in protocol["models"]
    }
    actual_keys = {(summary["seed"], summary["condition"], summary["model"]) for summary in summaries}
    if actual_keys != expected_keys:
        missing_keys = sorted(expected_keys - actual_keys, key=str)
        extra_keys = sorted(actual_keys - expected_keys, key=str)
        raise SystemExit(
            "Score files do not match the frozen seed-condition-model design. "
            f"Missing: {missing_keys}; extra: {extra_keys}."
        )
    wrong_cell_sizes = [
        (summary["seed"], summary["condition"], summary["model"], summary["n_traces"])
        for summary in summaries
        if summary["n_traces"] != protocol["n_frozen_packets"]
    ]
    if wrong_cell_sizes:
        raise SystemExit(f"Incomplete or duplicated trace cells: {wrong_cell_sizes}")
    unexpected_clusters = sorted(
        {
            cluster
            for summary in summaries
            for cluster in summary["dependency_clusters"]
            if cluster != "GSE120575_GSE91061_GSE78220_positive_control_panel_v2"
        }
    )
    if unexpected_clusters:
        raise SystemExit("Unexpected dependency clusters: " + ", ".join(unexpected_clusters))
    output = {
        "schema": "icb-disambiguate-real-transport-multiseed-descriptive-summary-v1",
        "interpretation": (
            "Descriptive generation audit only. All packet rows originate from one dependent "
            "positive-control panel; no row count is an independent biomedical sample size or a model ranking statistic."
        ),
        "protocol_id": protocol["protocol_id"],
        "n_score_files": len(score_files),
        "n_raw_trace_records": len(records),
        "n_seed_condition_model_cells": len(summaries),
        "unexpected_dependency_clusters": unexpected_clusters,
        "by_seed_condition_model": summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "saved": str(args.output),
                "n_raw_trace_records": len(records),
                "n_seed_condition_model_cells": len(summaries),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
