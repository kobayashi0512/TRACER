#!/usr/bin/env python3
"""Summarize raw LLM traces without turning a one-packet pilot into a result claim.

This is a trace-quality audit: parseability, candidate-card admissibility, and
the provenance-derived TRACER disposition. It intentionally does not infer
model quality, biological correctness, or comparative statistical significance.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
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


def _safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(APP_ROOT))
    except ValueError:
        return str(path)


def _condition_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["model"], record["condition"])].append(record)
    summaries = []
    for (model, condition), group in sorted(groups.items()):
        summaries.append(
            {
                "model": model,
                "condition": condition,
                "n_traces": len(group),
                "n_parseable_candidate_json": sum(record["candidate_json_parseable"] for record in group),
                "n_structurally_admissible": sum(record["structurally_admissible"] for record in group),
                "n_tracer_admitted": sum(record["tracer_admitted"] for record in group),
                "n_tracer_low_priority": sum(record["tracer_level"] == "LOW" for record in group),
            }
        )
    return summaries


def _summarize_trace(
    trace_path: Path, registry: dict[str, Any], fallback_packet_path: Path
) -> dict[str, Any]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    record: dict[str, Any] = {
        "trace": _safe_relative(trace_path),
        "packet_id": trace.get("packet_id"),
        "model": trace.get("model"),
        "condition": trace.get("condition"),
        "candidate_json_parseable": False,
        "structurally_admissible": False,
        "tracer_admitted": False,
        "tracer_level": None,
        "tracer_priority_score": None,
        "structural_error_count": None,
        "draft_rejection_reason_count": None,
        "parse_or_runtime_error": None,
    }
    raw_response = trace.get("response", {}).get("response")
    if not isinstance(raw_response, str):
        record["parse_or_runtime_error"] = "Trace has no string response.response field."
        return record
    raw_packet_path = trace.get("packet_path")
    packet_path = Path(raw_packet_path) if isinstance(raw_packet_path, str) else fallback_packet_path
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        record["parse_or_runtime_error"] = f"Cannot load trace packet: {exc}"
        return record
    packet_errors = validate_packet(packet, registry)
    if packet_errors:
        record["parse_or_runtime_error"] = "Invalid trace packet: " + " | ".join(packet_errors)
        return record
    record["packet_id"] = packet.get("packet_id")
    try:
        draft = extract_json_object(raw_response)
    except (ValueError, json.JSONDecodeError) as exc:
        record["parse_or_runtime_error"] = str(exc)
        return record
    record["candidate_json_parseable"] = True
    structural_errors, _ = validate_card(draft, cohort_registry=registry)
    tracer = evaluate_with_evidence_graph(draft, packet, registry)
    assessment = tracer["assessment"]
    record.update(
        {
            "structurally_admissible": not structural_errors,
            "tracer_admitted": tracer["draft_admissible_for_review"],
            "tracer_level": assessment["level"],
            "tracer_priority_score": assessment["priority_score"],
            "structural_error_count": len(structural_errors),
            "draft_rejection_reason_count": len(tracer["draft_rejection_reasons"]),
        }
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-dir", type=Path, default=APP_ROOT / "results" / "llm_runs"
    )
    parser.add_argument(
        "--packet",
        type=Path,
        default=APP_ROOT / "data" / "demo_evidence_packet_cross_modality_v1.json",
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "cohort_registry_v2.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "results" / "pilot_trace_quality_summary_v1.json",
    )
    args = parser.parse_args()
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    trace_paths = sorted(args.trace_dir.glob("*.json"))
    if not trace_paths:
        raise SystemExit(f"No JSON trace files found in {args.trace_dir}.")
    records = [_summarize_trace(path, registry, args.packet) for path in trace_paths]
    summary = {
        "schema": "icb-disambiguate-trace-quality-pilot-v1",
        "interpretation": (
            "Descriptive trace-quality audit on frozen evidence packet(s) and one run per model-condition. "
            "It is not a biological result, a model ranking, a calibration estimate, or a statistical comparison."
        ),
        "packet_ids": sorted(
            {record["packet_id"] for record in records if isinstance(record["packet_id"], str)}
        ),
        "n_traces": len(records),
        "by_model_condition": _condition_summary(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "n_traces": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
