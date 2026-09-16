#!/usr/bin/env python3
"""Write or verify checksums for the frozen factorial-v2 TRACER safety suite."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_freeze(
    *, suite_dir: Path, registry_path: Path, sanity_result_path: Path
) -> dict[str, Any]:
    manifest_path = suite_dir / "manifest_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["suite_id"] != "tracer-factorized-synthetic-safety-suite-v2":
        raise ValueError(f"Unexpected suite id: {manifest['suite_id']}")
    if len(manifest["packets"]) != 32:
        raise ValueError("The freeze requires exactly 32 factorial-v2 packets.")
    packet_entries = []
    for entry in manifest["packets"]:
        packet_path = suite_dir / entry["file"]
        if not packet_path.exists():
            raise FileNotFoundError(f"Missing packet listed by manifest: {packet_path}")
        packet_entries.append(
            {
                "packet_id": entry["packet_id"],
                "file": entry["file"],
                "sha256": sha256_file(packet_path),
            }
        )
    return {
        "schema": "tracer-factorized-safety-freeze-v1",
        "freeze_id": "TRACER-FACTORIAL-SAFETY-V2-FREEZE-20260915",
        "interpretation": (
            "Checksum manifest for a deterministic synthetic safety suite. "
            "This freeze does not certify biomedical truth, clinical performance, "
            "or language-model generalization."
        ),
        "suite_id": manifest["suite_id"],
        "protocol": {
            "complete_factorial_packets": 32,
            "factor_order": manifest["factor_order"],
            "omission_attack": manifest["omission_attack"],
        },
        "files": {
            "suite_manifest": {
                "path": str(manifest_path.relative_to(APP_ROOT)),
                "sha256": sha256_file(manifest_path),
            },
            "cohort_registry": {
                "path": str(registry_path.relative_to(APP_ROOT)),
                "sha256": sha256_file(registry_path),
            },
            "algorithm_sanity_result": {
                "path": str(sanity_result_path.relative_to(APP_ROOT)),
                "sha256": sha256_file(sanity_result_path),
            },
        },
        "packets": packet_entries,
    }


def verify_freeze(freeze: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if freeze.get("schema") != "tracer-factorized-safety-freeze-v1":
        errors.append("Unknown freeze schema.")
    if len(freeze.get("packets", [])) != 32:
        errors.append("Freeze must list exactly 32 packets.")
    for key, entry in freeze.get("files", {}).items():
        path = APP_ROOT / entry["path"]
        if not path.exists():
            errors.append(f"Missing frozen {key}: {entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"Checksum mismatch for {key}: {entry['path']}")
    for entry in freeze.get("packets", []):
        path = APP_ROOT / "data" / "synthetic_packets_v2" / entry["file"]
        if not path.exists():
            errors.append(f"Missing frozen packet: {entry['file']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"Checksum mismatch for packet: {entry['packet_id']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify an existing freeze without rewriting it.")
    parser.add_argument(
        "--freeze-file",
        type=Path,
        default=APP_ROOT / "config" / "factorized_safety_benchmark_freeze_v1.json",
    )
    parser.add_argument(
        "--suite-dir", type=Path, default=APP_ROOT / "data" / "synthetic_packets_v2"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v3.json",
    )
    parser.add_argument(
        "--sanity-result",
        type=Path,
        default=APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json",
    )
    args = parser.parse_args()
    if args.verify:
        freeze = json.loads(args.freeze_file.read_text(encoding="utf-8"))
        errors = verify_freeze(freeze)
        if errors:
            raise SystemExit("Freeze verification failed: " + " | ".join(errors))
        print(json.dumps({"verified": str(args.freeze_file), "n_packets": len(freeze["packets"])}))
        return
    freeze = build_freeze(
        suite_dir=args.suite_dir,
        registry_path=args.registry,
        sanity_result_path=args.sanity_result,
    )
    args.freeze_file.parent.mkdir(parents=True, exist_ok=True)
    args.freeze_file.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.freeze_file), "n_packets": len(freeze["packets"])}))


if __name__ == "__main__":
    main()
