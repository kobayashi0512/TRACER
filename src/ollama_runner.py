"""Reproducible local-Ollama execution for frozen evidence packets."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.evidence_packet import render_model_packet


VALID_CONDITIONS = {
    "free_form",
    "free_form_neutral",
    "gated_card",
    "schema_constrained_card",
    "schema_only_card",
}


def build_prompt(app_root: Path, packet: dict[str, Any], condition: str) -> str:
    """Render a fixed prompt without ever exposing evaluator-only labels."""
    if condition not in VALID_CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    template_name = {
        "free_form": "free_form_v1.txt",
        "free_form_neutral": "free_form_neutral_v2.txt",
        "gated_card": "gated_candidate_card_v1.txt",
        "schema_constrained_card": "gated_candidate_card_v1.txt",
        "schema_only_card": "schema_only_card_v1.txt",
    }[condition]
    template = (app_root / "prompts" / template_name).read_text(encoding="utf-8")
    visible_packet = render_model_packet(packet)
    prompt = template.replace(
        "{{MODEL_VISIBLE_PACKET_JSON}}", json.dumps(visible_packet, ensure_ascii=False, indent=2)
    )
    if condition in {"gated_card", "schema_constrained_card"}:
        contract = json.loads(
            (app_root / "config" / "candidate_card_contract_v1.json").read_text(encoding="utf-8")
        )
        prompt = prompt.replace(
            "{{CANDIDATE_CARD_CONTRACT_JSON}}", json.dumps(contract, ensure_ascii=False, indent=2)
        )
    return prompt


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def ollama_model_metadata(model: str) -> str:
    """Capture local model metadata verbatim for run reproducibility."""
    completed = subprocess.run(
        ["ollama", "show", model],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def run_ollama(
    model: str,
    prompt: str,
    *,
    seed: int,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, Any] | None = None,
    keep_alive: int | str | None = None,
    endpoint: str = "http://127.0.0.1:11434/api/generate",
) -> dict[str, Any]:
    """Call the local Ollama API once with a fully recorded deterministic setup."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "seed": seed,
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if response_format is not None:
        body["format"] = response_format
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=1800) as response:  # nosec B310: endpoint is explicit local benchmark config
        return json.loads(response.read().decode("utf-8"))
