#!/usr/bin/env python3
"""Score adjudicated benchmark outputs; default inputs are synthetic logic checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evaluation import evaluate, validate_adjudicated_records  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--records",
        type=Path,
        default=APP_ROOT / "data" / "demo_adjudicated_outputs_v1.json",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=APP_ROOT / "data" / "demo_evaluation_reference_v1.json",
    )
    args = parser.parse_args()
    records = json.loads(args.records.read_text(encoding="utf-8"))
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    errors = validate_adjudicated_records(records, reference)
    payload = {"records": str(args.records), "reference": str(args.reference), "errors": errors}
    if not errors:
        payload["evaluation"] = evaluate(records, reference)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
