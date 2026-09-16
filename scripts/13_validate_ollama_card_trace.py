#!/usr/bin/env python3
"""Validate the raw candidate-card response preserved in an Ollama run trace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.candidate_card import validate_card  # noqa: E402
from src.trace_validation import extract_json_object  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "cohort_registry_v2.json",
    )
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    raw_response = trace.get("response", {}).get("response")
    if not isinstance(raw_response, str):
        raise SystemExit("Trace has no string response.response field.")
    try:
        card = extract_json_object(raw_response)
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"trace": str(args.trace), "parseable_json_card": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    errors, assessment = validate_card(card, cohort_registry=registry)
    print(
        json.dumps(
            {
                "trace": str(args.trace),
                "parseable_json_card": True,
                "valid_card": not errors,
                "errors": errors,
                "assessment": assessment.as_dict() if assessment else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
