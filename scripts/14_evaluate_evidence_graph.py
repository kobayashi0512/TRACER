#!/usr/bin/env python3
"""Re-derive a candidate's priority from frozen evidence provenance graph."""

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
    args = parser.parse_args()
    card = json.loads(args.card.read_text(encoding="utf-8"))
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    packet_errors = validate_packet(packet, registry)
    card_errors, _ = validate_card(card, cohort_registry=registry)
    payload = {
        "card": str(args.card),
        "packet": str(args.packet),
        "packet_errors": packet_errors,
        "card_structural_errors": card_errors,
        "evidence_graph_evaluation": None,
    }
    if not packet_errors:
        payload["evidence_graph_evaluation"] = evaluate_with_evidence_graph(card, packet, registry)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if packet_errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
