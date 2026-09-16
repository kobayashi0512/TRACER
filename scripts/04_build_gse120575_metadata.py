#!/usr/bin/env python3
"""Build auditable GSE120575 cell and lesion metadata from the GEO source file.

This preserves source lesion labels (for example, ``Post_P10_T_enriched``) and
does not collapse multiple lesions or enrichment fractions into independent
patients. It creates metadata only; no expression analysis is performed.
"""

from __future__ import annotations

import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
RAW = APP_ROOT / "data" / "raw"
DERIVED = APP_ROOT / "data" / "derived"
RESULTS = APP_ROOT / "results"


def load_matrix_cells() -> set[str]:
    path = RAW / "GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz"
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        return set(handle.readline().rstrip("\n\r").split("\t")[1:])


def source_rows() -> list[dict[str, str]]:
    path = RAW / "GSE120575_patient_ID_single_cells.txt.gz"
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        rows = csv.reader(handle, delimiter="\t")
        header: list[str] | None = None
        output: list[dict[str, str]] = []
        for row in rows:
            if header is None:
                if row and row[0] == "Sample name":
                    header = row
                continue
            if not row or not row[0].startswith("Sample "):
                if output:
                    break
                continue
            padded = row + [""] * (len(header) - len(row))
            output.append(dict(zip(header, padded, strict=True)))
    if not output:
        raise ValueError("No sample rows found in GEO metadata template.")
    return output


def timepoint(lesion_id: str) -> str:
    if lesion_id.startswith("Pre_"):
        return "pre_treatment"
    if lesion_id.startswith("Post_"):
        return "on_treatment"
    return "unknown"


def patient_token(lesion_id: str) -> str:
    match = re.match(r"(?:Pre|Post)_(P\d+)", lesion_id)
    return match.group(1) if match else "UNPARSED"


def main() -> None:
    rows = source_rows()
    matrix_cells = load_matrix_cells()
    # In this GEO template, ``title`` holds the per-cell identifier while
    # ``source name`` is the shared text "Melanoma single cell".
    metadata_cells = {row["title"] for row in rows}
    if metadata_cells != matrix_cells:
        raise ValueError(
            "GSE120575 matrix/source-metadata cell-ID mismatch: "
            f"matrix_only={len(matrix_cells - metadata_cells)}, "
            f"metadata_only={len(metadata_cells - matrix_cells)}"
        )

    patient_column = "characteristics: patinet ID (Pre=baseline; Post= on treatment)"
    response_column = "characteristics: response"
    therapy_column = "characteristics: therapy"
    expected = {patient_column, response_column, therapy_column, "title"}
    absent = expected - set(rows[0])
    if absent:
        raise ValueError(f"Expected GEO metadata columns missing: {sorted(absent)}")

    normalized = []
    for row in rows:
        lesion_id = row[patient_column]
        normalized.append(
            {
                "cell_id": row["title"],
                "lesion_id": lesion_id,
                "patient_token": patient_token(lesion_id),
                "timepoint": timepoint(lesion_id),
                "response": row[response_column],
                "therapy": row[therapy_column],
                "geo_sample_row": row["Sample name"],
            }
        )

    by_lesion: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in normalized:
        by_lesion[row["lesion_id"]].append(row)
    lesions = []
    for lesion_id, cells in sorted(by_lesion.items()):
        fields = {key: {cell[key] for cell in cells} for key in ("patient_token", "timepoint", "response", "therapy")}
        inconsistent = {key: sorted(values) for key, values in fields.items() if len(values) != 1}
        if inconsistent:
            raise ValueError(f"Within-lesion metadata conflicts for {lesion_id}: {inconsistent}")
        lesions.append(
            {
                "lesion_id": lesion_id,
                "patient_token": next(iter(fields["patient_token"])),
                "timepoint": next(iter(fields["timepoint"])),
                "response": next(iter(fields["response"])),
                "therapy": next(iter(fields["therapy"])),
                "n_cells": len(cells),
            }
        )

    DERIVED.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    cell_output = DERIVED / "gse120575_cell_metadata.tsv"
    lesion_output = DERIVED / "gse120575_lesion_metadata.tsv"
    fieldnames = list(normalized[0])
    with cell_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(normalized)
    with lesion_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(lesions[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(lesions)

    summary = {
        "source": "GSE120575 GEO supplementary metadata",
        "n_cells": len(normalized),
        "n_lesions": len(lesions),
        "n_patient_tokens": len({row["patient_token"] for row in lesions}),
        "cell_metadata_path": str(cell_output.relative_to(APP_ROOT)),
        "lesion_metadata_path": str(lesion_output.relative_to(APP_ROOT)),
        "lesions_by_timepoint": dict(sorted(Counter(row["timepoint"] for row in lesions).items())),
        "lesions_by_response": dict(sorted(Counter(row["response"] for row in lesions).items())),
        "lesions_by_therapy": dict(sorted(Counter(row["therapy"] for row in lesions).items())),
        "analysis_guardrail": (
            "Use lesion/patient pseudo-bulk or paired models; do not use cell count as clinical sample size. "
            "Primary analysis must restrict to pre-treatment lesions and a frozen anti-PD-1-based therapy definition."
        ),
    }
    audit_output = RESULTS / "gse120575_metadata_build_audit.json"
    audit_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
