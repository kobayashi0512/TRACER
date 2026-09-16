#!/usr/bin/env python3
"""Run deterministic grading on the synthetic demo cards."""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.confidence import assess  # noqa: E402


def main() -> None:
    cards_path = APP_ROOT / "data" / "demo_candidate_cards.json"
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    assessments = [assess(card).as_dict() for card in cards]
    output = APP_ROOT / "results" / "demo_assessments.json"
    output.write_text(json.dumps(assessments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(assessments, ensure_ascii=False, indent=2))
    print(f"\nWrote synthetic demonstration only: {output}")


if __name__ == "__main__":
    main()
