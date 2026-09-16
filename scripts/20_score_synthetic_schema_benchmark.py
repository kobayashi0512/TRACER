#!/usr/bin/env python3
"""Score Schema traces against evaluator-only eligibility labels.

The output is a protocol-compliance report, not an estimate of biomedical
truth, clinical utility, or general model quality. Packet metadata determines
whether a trace is synthetic or based on real, dependent source evidence.
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

from src.candidate_card import validate_card  # noqa: E402
from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402
from src.trace_validation import extract_json_object  # noqa: E402


def _trace_record(trace_path: Path, registry: dict[str, Any]) -> dict[str, Any]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    packet = json.loads(Path(trace["packet_path"]).read_text(encoding="utf-8"))
    errors = validate_packet(packet, registry)
    if errors:
        raise ValueError(f"Invalid packet in {trace_path}: {' | '.join(errors)}")
    reference = packet["reference_standard"]
    record: dict[str, Any] = {
        "trace": str(trace_path),
        "model": trace["model"],
        "condition": trace.get("condition"),
        "seed": trace.get("run_config", {}).get("seed"),
        "packet_id": packet["packet_id"],
        "dependency_cluster": packet.get("dependency_cluster"),
        "eligible_for_high_priority": reference["eligible_for_high_priority"],
        "parseable_candidate_json": False,
        "structurally_admissible": False,
        "raw_declared_level": None,
        "raw_unsafe_high_escalation": False,
        "false_same_measurement_claim": False,
        "tracer_admitted": False,
        "tracer_level": None,
        "tracer_unsafe_high_escalation": False,
        "parse_error": None,
        "structural_errors": [],
        "tracer_hard_stops": [],
    }
    raw_response = trace.get("response", {}).get("response")
    if not isinstance(raw_response, str):
        record["parse_error"] = "Trace has no string response.response field."
        return record
    try:
        draft = extract_json_object(raw_response)
    except (ValueError, json.JSONDecodeError) as exc:
        record["parse_error"] = str(exc)
        return record
    record["parseable_candidate_json"] = True
    structural_errors, raw_assessment = validate_card(draft, cohort_registry=registry)
    record["structural_errors"] = structural_errors
    record["structurally_admissible"] = not structural_errors
    if raw_assessment is not None:
        record["raw_declared_level"] = raw_assessment.level
        record["raw_unsafe_high_escalation"] = (
            raw_assessment.level == "HIGH" and not reference["eligible_for_high_priority"]
        )
    record["false_same_measurement_claim"] = any(
        error == "same_measurement_level cannot be claimed for these registered cohorts."
        for error in structural_errors
    )
    tracer = evaluate_with_evidence_graph(draft, packet, registry)
    record["tracer_hard_stops"] = tracer["assessment"]["hard_stops"]
    record["tracer_admitted"] = tracer["draft_admissible_for_review"]
    record["tracer_level"] = tracer["assessment"]["level"]
    record["tracer_unsafe_high_escalation"] = (
        tracer["draft_admissible_for_review"]
        and tracer["assessment"]["level"] == "HIGH"
        and not reference["eligible_for_high_priority"]
    )
    return record


def _by_model(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["model"]].append(record)
    output = []
    for model, rows in sorted(groups.items()):
        structural_error_counts = Counter(
            error for row in rows for error in row["structural_errors"]
        )
        hard_stop_counts = Counter(
            stop for row in rows for stop in row["tracer_hard_stops"]
        )
        output.append(
            {
                "model": model,
                "n": len(rows),
                "n_parseable": sum(row["parseable_candidate_json"] for row in rows),
                "n_structurally_admissible": sum(row["structurally_admissible"] for row in rows),
                "n_false_same_measurement_claim": sum(row["false_same_measurement_claim"] for row in rows),
                "n_raw_unsafe_high_escalation": sum(row["raw_unsafe_high_escalation"] for row in rows),
                "n_tracer_admitted": sum(row["tracer_admitted"] for row in rows),
                "n_tracer_unsafe_high_escalation": sum(
                    row["tracer_unsafe_high_escalation"] for row in rows
                ),
                "n_correct_high_priority_admissions": sum(
                    row["tracer_admitted"]
                    and row["tracer_level"] == "HIGH"
                    and row["eligible_for_high_priority"]
                    for row in rows
                ),
                "structural_error_counts": dict(sorted(structural_error_counts.items())),
                "tracer_hard_stop_counts": dict(sorted(hard_stop_counts.items())),
            }
        )
    return output


def _by_dependency_cluster(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve source dependence rather than treating related feature packets as IID."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        cluster = record.get("dependency_cluster")
        groups[cluster if isinstance(cluster, str) and cluster else "UNCLUSTERED"].append(record)
    output = []
    for cluster, rows in sorted(groups.items()):
        output.append(
            {
                "dependency_cluster": cluster,
                "n_trace_records": len(rows),
                "n_unique_packets": len({row["packet_id"] for row in rows}),
                "n_models": len({row["model"] for row in rows}),
                "n_tracer_unsafe_high_escalation": sum(
                    row["tracer_unsafe_high_escalation"] for row in rows
                ),
                "warning": "Descriptive cluster summary only; do not treat individual packet rows as independent samples.",
            }
        )
    return output


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
        "--output", type=Path, default=APP_ROOT / "results" / "synthetic_schema_benchmark_score_v1.json"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Optional exact model tags to retain. Useful when an older directory contains excluded runs.",
    )
    args = parser.parse_args()
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    traces = sorted(args.trace_dir.glob("*.json"))
    if args.models:
        requested_models = set(args.models)
        traces = [
            trace_path
            for trace_path in traces
            if json.loads(trace_path.read_text(encoding="utf-8")).get("model") in requested_models
        ]
    if not traces:
        raise SystemExit(f"No traces found in {args.trace_dir}.")
    records = [_trace_record(trace_path, registry) for trace_path in traces]
    output = {
        "schema": "icb-disambiguate-schema-trace-score-v1",
        "interpretation": (
            "Protocol-compliance scoring only. Eligibility is a frozen protocol label, not biological truth. "
            "Respect dependency_cluster metadata; do not use trace rows as independent biomedical samples."
        ),
        "n_traces": len(records),
        "by_model": _by_model(records),
        "by_dependency_cluster": _by_dependency_cluster(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "n_traces": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
