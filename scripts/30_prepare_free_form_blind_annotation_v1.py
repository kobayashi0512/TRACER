#!/usr/bin/env python3
"""Build a blinded human-annotation package from neutral free-form traces.

This intentionally does not score prose with another LLM.  Reviewers receive
only the model-visible frozen packet and raw response; model and condition
linkage are saved separately for post-adjudication analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import render_model_packet  # noqa: E402


BLINDING_SALT = "icb-disambiguate-free-form-blinding-v1"


def _review_id(trace: dict[str, Any]) -> str:
    material = "|".join(
        str(value)
        for value in (
            trace.get("packet_id"),
            trace.get("model"),
            trace.get("condition"),
            trace.get("run_config", {}).get("seed"),
        )
    )
    return hashlib.sha256(f"{BLINDING_SALT}|{material}".encode("utf-8")).hexdigest()[:16]


def _empty_annotation() -> dict[str, Any]:
    return {
        "unsupported_causal_language": None,
        "unsupported_same_measurement_replication": None,
        "selective_evidence_omission": None,
        "appropriate_uncertainty_or_abstention": None,
        "next_step_is_discriminating": None,
        "treatment_recommendation_present": None,
        "notes": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dirs", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--rubric",
        type=Path,
        default=APP_ROOT / "config" / "free_form_blind_annotation_rubric_v1.json",
    )
    parser.add_argument(
        "--annotation-output",
        type=Path,
        required=True,
        help="Reviewer-visible package; do not distribute the linkage file with it.",
    )
    parser.add_argument(
        "--private-linkage-output",
        type=Path,
        required=True,
        help="Private mapping from review ID to model/configuration metadata.",
    )
    args = parser.parse_args()
    traces = sorted(
        trace_path for directory in args.trace_dirs for trace_path in directory.glob("*.json")
    )
    if not traces:
        raise SystemExit("No trace JSON files found.")
    seen_ids: set[str] = set()
    blinded_records = []
    linkage = []
    for trace_path in traces:
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace.get("condition") != "free_form_neutral":
            raise SystemExit(f"Trace is not free_form_neutral: {trace_path}")
        raw_response = trace.get("response", {}).get("response")
        if not isinstance(raw_response, str) or not raw_response.strip():
            raise SystemExit(f"Trace lacks a non-empty raw response: {trace_path}")
        packet_path = Path(trace["packet_path"])
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        review_id = _review_id(trace)
        if review_id in seen_ids:
            raise SystemExit(f"Non-unique review ID; duplicate run configuration: {review_id}")
        seen_ids.add(review_id)
        blinded_records.append(
            {
                "review_id": review_id,
                "evidence_packet": render_model_packet(packet),
                "model_output": raw_response,
                "reviewer_1": _empty_annotation(),
                "reviewer_2": _empty_annotation(),
                "adjudicated": _empty_annotation(),
            }
        )
        linkage.append(
            {
                "review_id": review_id,
                "trace_path": str(trace_path.resolve()),
                "packet_id": trace.get("packet_id"),
                "model": trace.get("model"),
                "condition": trace.get("condition"),
                "seed": trace.get("run_config", {}).get("seed"),
                "prompt_sha256": trace.get("prompt_sha256"),
            }
        )
    random.Random(BLINDING_SALT).shuffle(blinded_records)
    rubric = json.loads(args.rubric.read_text(encoding="utf-8"))
    annotation_package = {
        "schema": "icb-disambiguate-free-form-blind-annotation-package-v1",
        "rubric_id": rubric["rubric_id"],
        "n_records": len(blinded_records),
        "records": blinded_records,
    }
    private_linkage = {
        "schema": "icb-disambiguate-free-form-private-linkage-v1",
        "warning": "Do not share with reviewers before adjudicated labels are frozen.",
        "n_records": len(linkage),
        "records": linkage,
    }
    args.annotation_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_linkage_output.parent.mkdir(parents=True, exist_ok=True)
    args.annotation_output.write_text(
        json.dumps(annotation_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.private_linkage_output.write_text(
        json.dumps(private_linkage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "annotation_output": str(args.annotation_output),
                "private_linkage_output": str(args.private_linkage_output),
                "n_records": len(blinded_records),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
