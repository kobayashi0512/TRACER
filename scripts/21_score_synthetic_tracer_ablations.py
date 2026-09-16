#!/usr/bin/env python3
"""Replay frozen synthetic LLM traces through pre-specified TRACER ablations."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402
from src.trace_validation import extract_json_object  # noqa: E402


def _condition_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["condition_id"], record["model"])].append(record)
    rows = []
    for (condition_id, model), values in sorted(groups.items()):
        rows.append(
            {
                "condition_id": condition_id,
                "model": model,
                "n": len(values),
                "n_parseable": sum(value["parseable_candidate_json"] for value in values),
                "n_admitted": sum(value["tracer_admitted"] for value in values),
                "n_unsafe_high_escalation": sum(
                    value["unsafe_high_escalation"] for value in values
                ),
                "n_correct_high_priority_admission": sum(
                    value["correct_high_priority_admission"] for value in values
                ),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-dir", type=Path, default=APP_ROOT / "results" / "synthetic_schema_runs_v1"
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=APP_ROOT / "config" / "tracer_ablation_matrix_v1.json",
    )
    parser.add_argument(
        "--output", type=Path, default=APP_ROOT / "results" / "synthetic_tracer_ablation_score_v1.json"
    )
    args = parser.parse_args()
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    conditions = matrix.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise SystemExit("Ablation matrix requires a non-empty conditions list.")
    records = []
    for trace_path in sorted(args.trace_dir.glob("*.json")):
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        packet = json.loads(Path(trace["packet_path"]).read_text(encoding="utf-8"))
        packet_errors = validate_packet(packet, registry)
        if packet_errors:
            raise SystemExit(f"Invalid packet in {trace_path}: " + " | ".join(packet_errors))
        raw_response = trace.get("response", {}).get("response")
        try:
            draft = extract_json_object(raw_response) if isinstance(raw_response, str) else None
        except (ValueError, json.JSONDecodeError):
            draft = None
        for condition in conditions:
            condition_id = condition.get("condition_id")
            modules = condition.get("modules")
            if not isinstance(condition_id, str) or not isinstance(modules, dict):
                raise SystemExit("Every ablation condition requires string condition_id and object modules.")
            record: dict[str, Any] = {
                "trace": str(trace_path),
                "model": trace["model"],
                "packet_id": packet["packet_id"],
                "condition_id": condition_id,
                "modules": modules,
                "parseable_candidate_json": draft is not None,
                "tracer_admitted": False,
                "tracer_level": None,
                "unsafe_high_escalation": False,
                "correct_high_priority_admission": False,
            }
            if draft is not None:
                scored = evaluate_with_evidence_graph(draft, packet, registry, modules=modules)
                eligible = packet["reference_standard"]["eligible_for_high_priority"]
                record.update(
                    {
                        "tracer_admitted": scored["draft_admissible_for_review"],
                        "tracer_level": scored["assessment"]["level"],
                        "unsafe_high_escalation": (
                            scored["draft_admissible_for_review"]
                            and scored["assessment"]["level"] == "HIGH"
                            and not eligible
                        ),
                        "correct_high_priority_admission": (
                            scored["draft_admissible_for_review"]
                            and scored["assessment"]["level"] == "HIGH"
                            and eligible
                        ),
                    }
                )
            records.append(record)
    output = {
        "schema": "icb-disambiguate-synthetic-tracer-ablation-score-v1",
        "interpretation": (
            "Synthetic, trace-replay ablation only. It isolates the safety contribution of frozen TRACER "
            "modules and is not a biological or general model-performance result."
        ),
        "n_source_traces": len({record["trace"] for record in records}),
        "n_condition_records": len(records),
        "by_condition_model": _condition_summary(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "n_condition_records": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
