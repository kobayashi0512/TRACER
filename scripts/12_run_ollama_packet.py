#!/usr/bin/env python3
"""Run one frozen evidence packet against one local model and save a full trace."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import validate_packet  # noqa: E402
from src.ollama_runner import build_prompt, ollama_model_metadata, prompt_sha256, run_ollama  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Exact installed Ollama model tag.")
    parser.add_argument(
        "--condition",
        choices=["free_form", "free_form_neutral", "gated_card", "schema_constrained_card", "schema_only_card"],
        required=True,
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
        help="Frozen registry used only to validate packet eligibility before model invocation.",
    )
    parser.add_argument("--seed", type=int, default=20260913)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument(
        "--unload-after-run",
        action="store_true",
        help="Ask Ollama to release the model immediately after this response.",
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--output", type=Path, required=True, help="New JSON trace destination.")
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    errors = validate_packet(packet, registry)
    if errors:
        raise SystemExit("Invalid evidence packet: " + " | ".join(errors))

    prompt = build_prompt(APP_ROOT, packet, args.condition)
    response_format = None
    if args.condition in {"schema_constrained_card", "schema_only_card"}:
        response_format = json.loads(
            (APP_ROOT / "config" / "candidate_card_json_schema_v1.json").read_text(encoding="utf-8")
        )
    result = run_ollama(
        args.model,
        prompt,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        response_format=response_format,
        keep_alive=0 if args.unload_after_run else None,
        endpoint=args.endpoint,
    )
    trace = {
        "schema": "icb-disambiguate-ollama-run-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_id": packet["packet_id"],
        "packet_path": str(args.packet.resolve()),
        "cohort_registry_path": str(args.cohort_registry.resolve()),
        "condition": args.condition,
        "model": args.model,
        "model_metadata": ollama_model_metadata(args.model),
        "run_config": {
            "seed": args.seed,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "endpoint": args.endpoint,
            "response_format": "candidate_card_json_schema_v1" if response_format else None,
            "unload_after_run": args.unload_after_run,
        },
        "prompt_sha256": prompt_sha256(prompt),
        "prompt": prompt,
        "response": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "packet_id": packet["packet_id"], "model": args.model, "condition": args.condition}, ensure_ascii=False))


if __name__ == "__main__":
    main()
