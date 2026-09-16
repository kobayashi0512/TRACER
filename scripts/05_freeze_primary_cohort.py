#!/usr/bin/env python3
"""Freeze the pre-treatment anti-PD-1 monotherapy discovery cohort.

The script makes cohort selection auditable before any expression analysis. It
does not fit a model or calculate differential expression.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
DERIVED = APP_ROOT / "data" / "derived"
RESULTS = APP_ROOT / "results"
INPUT = DERIVED / "gse120575_lesion_metadata.tsv"
OUTPUT = DERIVED / "gse120575_primary_cohort_v1.tsv"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError("Run 04_build_gse120575_metadata.py before freezing this cohort.")
    rows = read_tsv(INPUT)
    primary = [
        row for row in rows
        if row["timepoint"] == "pre_treatment"
        and row["therapy"] == "anti-PD1"
        and row["response"] in {"Responder", "Non-responder"}
    ]
    if not primary:
        raise ValueError("Primary cohort selection returned zero lesions.")
    patients = [row["patient_token"] for row in primary]
    if len(patients) != len(set(patients)):
        raise ValueError("Primary cohort contains repeated patient tokens; use a paired/dependent design instead.")
    class_counts = Counter(row["response"] for row in primary)
    if set(class_counts) != {"Responder", "Non-responder"}:
        raise ValueError(f"Both response classes are required, received {dict(class_counts)}")
    write_tsv(OUTPUT, primary)

    combination = [
        row for row in rows
        if row["timepoint"] == "pre_treatment" and row["therapy"] == "anti-CTLA4+PD1"
    ]
    summary = {
        "cohort_id": "gse120575-primary-v1",
        "input_sha256": file_sha256(INPUT),
        "output_sha256": file_sha256(OUTPUT),
        "primary_n_lesions": len(primary),
        "primary_response_counts": dict(sorted(class_counts.items())),
        "primary_n_unique_patients": len(set(patients)),
        "sensitivity_only_combination_n_lesions": len(combination),
        "selection": "pre-treatment lesions; anti-PD1 monotherapy; source response labels only",
        "interpretation_limit": (
            "Small discovery cohort. Do not train an LLM, estimate patient-level clinical utility, "
            "or claim a causal mechanism from this cohort alone."
        ),
    }
    RESULTS.mkdir(exist_ok=True)
    report = RESULTS / "primary_cohort_freeze_v1.json"
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
