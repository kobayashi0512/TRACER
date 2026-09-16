#!/usr/bin/env python3
"""Run a schema-card LLM condition on a frozen stress suite.

Every run is retained as a raw trace. The suite is synthetic and this script
measures neither biological validity nor clinical utility.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import validate_packet  # noqa: E402
from src.ollama_runner import build_prompt, ollama_model_metadata, prompt_sha256, run_ollama  # noqa: E402
from src.synthetic_suite import load_suite  # noqa: E402


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True, help="Exact installed Ollama model tags.")
    parser.add_argument("--suite-dir", type=Path, default=APP_ROOT / "data" / "synthetic_packets_v1")
    parser.add_argument(
        "--manifest-name",
        default="manifest_v1.json",
        help="Explicit frozen manifest name inside --suite-dir.",
    )
    parser.add_argument(
        "--only-llm-pilot-subset",
        action="store_true",
        help="Run only manifest entries explicitly preregistered for the LLM pilot subset.",
    )
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v2.json",
    )
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument(
        "--unload-after-each-run",
        action="store_true",
        help="Ask Ollama to release each model immediately after its response.",
    )
    parser.add_argument(
        "--condition",
        choices=["schema_only_card", "schema_constrained_card"],
        default="schema_constrained_card",
        help="schema_only_card omits content-level safety instructions; schema_constrained_card retains them.",
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument(
        "--output-dir", type=Path, default=APP_ROOT / "results" / "synthetic_schema_runs_v1"
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    response_format = json.loads(
        (APP_ROOT / "config" / "candidate_card_json_schema_v1.json").read_text(encoding="utf-8")
    )
    suite = load_suite(args.suite_dir, manifest_name=args.manifest_name)
    if args.only_llm_pilot_subset:
        suite = [entry for entry in suite if entry["manifest_entry"].get("llm_pilot_subset") is True]
        if not suite:
            raise SystemExit("The selected manifest contains no llm_pilot_subset entries.")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for entry in suite:
        packet = entry["packet"]
        packet_errors = validate_packet(packet, registry)
        if packet_errors:
            raise SystemExit(f"Invalid packet {packet['packet_id']}: " + " | ".join(packet_errors))
        prompt = build_prompt(APP_ROOT, packet, args.condition)
        for model in args.models:
            output_path = args.output_dir / (
                f"{_slug(model)}__{packet['packet_id']}__{args.condition}__seed{args.seed}.json"
            )
            if output_path.exists() and not args.overwrite:
                print(json.dumps({"skipped_existing": str(output_path)}, ensure_ascii=False))
                continue
            result = run_ollama(
                model,
                prompt,
                seed=args.seed,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                response_format=response_format,
                keep_alive=0 if args.unload_after_each_run else None,
                endpoint=args.endpoint,
            )
            trace = {
                "schema": "icb-disambiguate-ollama-run-v1",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "packet_id": packet["packet_id"],
                "packet_path": str(entry["path"].resolve()),
                "cohort_registry_path": str(args.cohort_registry.resolve()),
                "condition": args.condition,
                "model": model,
                "model_metadata": ollama_model_metadata(model),
                "run_config": {
                    "seed": args.seed,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "endpoint": args.endpoint,
                    "response_format": "candidate_card_json_schema_v1",
                    "unload_after_each_run": args.unload_after_each_run,
                },
                "prompt_sha256": prompt_sha256(prompt),
                "prompt": prompt,
                "response": result,
            }
            output_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {"saved": str(output_path), "model": model, "packet_id": packet["packet_id"]},
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()
