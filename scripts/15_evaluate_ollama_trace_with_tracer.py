#!/usr/bin/env python3
"""Apply TRACER to an untrusted raw candidate-card response in an Ollama trace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.candidate_card import validate_card  # noqa: E402
from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402
from src.trace_validation import extract_json_object  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
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
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    raw_response = trace.get("response", {}).get("response")
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    if not isinstance(raw_response, str):
        raise SystemExit("Trace has no string response.response field.")
    try:
        draft = extract_json_object(raw_response)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Trace response is not a single parseable JSON card: {exc}")
    packet_errors = validate_packet(packet, registry)
    if packet_errors:
        raise SystemExit("Invalid packet: " + " | ".join(packet_errors))
    structural_errors, _ = validate_card(draft, cohort_registry=registry)
    output = {
        "trace": str(args.trace),
        "draft_structural_errors": structural_errors,
        "tracer": evaluate_with_evidence_graph(draft, packet, registry),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
