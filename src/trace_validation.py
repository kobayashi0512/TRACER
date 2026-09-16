"""Extract candidate-card JSON from a raw model trace and validate it deterministically."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Accept raw JSON or one fenced JSON object; reject ambiguous prose."""
    candidate = text.strip()
    if candidate.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
        if not match:
            raise ValueError("Model response is not exactly one fenced JSON object.")
        candidate = match.group(1)
    decoded = json.loads(candidate)
    if not isinstance(decoded, dict):
        raise ValueError("Model response must decode to one JSON object.")
    return decoded
