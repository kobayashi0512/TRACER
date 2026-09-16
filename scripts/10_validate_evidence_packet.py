#!/usr/bin/env python3
"""Validate an evidence packet and print the blinded model-visible payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import render_model_packet, validate_packet  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=APP_ROOT / "data" / "demo_evidence_packet_cross_modality_v1.json",
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "cohort_registry_v2.json",
    )
    args = parser.parse_args()
    packet = json.loads(args.input.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    errors = validate_packet(packet, registry)
    payload = {
        "input": str(args.input),
        "valid": not errors,
        "errors": errors,
        "model_visible_packet": render_model_packet(packet) if not errors else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
