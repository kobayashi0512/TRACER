#!/usr/bin/env python3
"""Run a synthetic counterfactual selective-citation attack against TRACER.

This is a deterministic algorithm attack, not an LLM output and not biomedical
evidence. It removes the pre-specified contradictory item from an otherwise
complete synthetic draft, then compares full TRACER with the coverage ablation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402
from src.synthetic_suite import complete_draft_from_packet  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packet",
        type=Path,
        default=APP_ROOT / "data" / "synthetic_packets_v1" / "SYNTH-SELECTIVE-OMISSION-001.json",
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json",
    )
    parser.add_argument(
        "--output", type=Path, default=APP_ROOT / "results" / "selective_omission_attack_v1.json"
    )
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    errors = validate_packet(packet, registry)
    if errors:
        raise SystemExit("Invalid packet: " + " | ".join(errors))
    draft = complete_draft_from_packet(packet)
    draft["evidence_sources"] = [
        source for source in draft["evidence_sources"] if source["id"] != "sc-conflict"
    ]
    full = evaluate_with_evidence_graph(draft, packet, registry)
    without_coverage = evaluate_with_evidence_graph(
        draft, packet, registry, modules={"provenance_coverage": False}
    )
    output = {
        "schema": "icb-disambiguate-selective-omission-attack-v1",
        "interpretation": (
            "Deterministic synthetic counterfactual attack only. It proves an implementation-level "
            "coverage property, not model behavior or a biomedical claim."
        ),
        "omitted_evidence_id": "sc-conflict",
        "full_tracer": full,
        "without_provenance_coverage": without_coverage,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
