#!/usr/bin/env python3
"""Validate a candidate card before it is shown as an LLM research output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.candidate_card import validate_card  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=APP_ROOT / "data" / "demo_candidate_card_contract_v1.json",
        help="Candidate-card JSON to validate.",
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=None,
        help=(
            "Optional frozen registry used to verify dataset eligibility claims. "
            "Use for any non-synthetic card."
        ),
    )
    args = parser.parse_args()
    card = json.loads(args.input.read_text(encoding="utf-8"))
    registry = (
        json.loads(args.cohort_registry.read_text(encoding="utf-8"))
        if args.cohort_registry
        else None
    )
    errors, assessment = validate_card(card, cohort_registry=registry)
    payload = {
        "input": str(args.input),
        "cohort_registry": str(args.cohort_registry) if args.cohort_registry else None,
        "valid_structure": not errors,
        "errors": errors,
        "assessment": assessment.as_dict() if assessment else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
