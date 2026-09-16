#!/usr/bin/env python3
"""Run the frozen TRACER module ablations on one candidate card and evidence packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--card",
        type=Path,
        default=APP_ROOT / "data" / "demo_candidate_card_current_evidence_v1.json",
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
        "--matrix",
        type=Path,
        default=APP_ROOT / "config" / "tracer_ablation_matrix_v1.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    card = json.loads(args.card.read_text(encoding="utf-8"))
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    packet_errors = validate_packet(packet, registry)
    if packet_errors:
        raise SystemExit("Invalid evidence packet: " + " | ".join(packet_errors))
    conditions = matrix.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise SystemExit("Ablation matrix requires a non-empty conditions list.")
    results = []
    for condition in conditions:
        condition_id = condition.get("condition_id")
        modules = condition.get("modules")
        if not isinstance(condition_id, str) or not isinstance(modules, dict):
            raise SystemExit("Every ablation condition requires string condition_id and object modules.")
        results.append(
            {
                "condition_id": condition_id,
                "modules": modules,
                "evaluation": evaluate_with_evidence_graph(card, packet, registry, modules=modules),
            }
        )
    output = {
        "schema": "icb-disambiguate-tracer-ablation-run-v1",
        "matrix_id": matrix.get("matrix_id"),
        "card": str(args.card),
        "packet": str(args.packet),
        "results": results,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(json.dumps({"saved": str(args.output), "n_conditions": len(results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
