#!/usr/bin/env python3
"""Audit public processed matrices before any biological analysis.

The audit intentionally reports availability, dimensions, and metadata gaps only.
It does not infer patient response from cell labels or run differential expression.
"""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
RAW = APP_ROOT / "data" / "raw"
RESULTS = APP_ROOT / "results"


def _open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")


def audit_gse120575() -> dict:
    path = RAW / "GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz"
    with _open_text(path) as handle:
        cell_header = handle.readline().rstrip("\n\r").split("\t")
        sample_row = handle.readline().rstrip("\n\r").split("\t")
        if len(cell_header) != len(sample_row):
            raise ValueError("GSE120575 cell header and sample row have unequal field counts.")
        gene_rows = sum(1 for _ in handle)

    cells = cell_header[1:]
    sample_labels = sample_row[1:]
    if not all(cells) or not all(sample_labels):
        raise ValueError("GSE120575 has blank cell IDs or sample labels.")
    return {
        "matrix_file": path.name,
        "n_cells": len(cells),
        "n_gene_rows": gene_rows,
        "n_sample_labels": len(set(sample_labels)),
        "sample_label_counts": dict(sorted(Counter(sample_labels).items())),
        "primary_analysis_status": "BLOCKED_PENDING_RESPONSE_METADATA_AUDIT",
        "required_manual_check": (
            "Map each pre-treatment sample label to patient/lesion, therapy, timing, and response from "
            "source metadata; do not infer response from this expression matrix."
        ),
    }


def audit_gse115978() -> dict:
    matrix_path = RAW / "GSE115978_tpm.csv.gz"
    annotations_path = RAW / "GSE115978_cell.annotations.csv.gz"
    with _open_text(matrix_path) as handle:
        matrix_header = next(csv.reader(handle))
        if not matrix_header or matrix_header[0] != "":
            raise ValueError("GSE115978 TPM matrix must have an empty first header cell for gene IDs.")
        matrix_cells = matrix_header[1:]
        gene_rows = sum(1 for _ in handle)

    with _open_text(annotations_path) as handle:
        records = list(csv.DictReader(handle))
    annotation_cells = [record["cells"] for record in records]
    missing_annotations = sorted(set(matrix_cells) - set(annotation_cells))
    extra_annotations = sorted(set(annotation_cells) - set(matrix_cells))
    if missing_annotations or extra_annotations:
        raise ValueError(
            "GSE115978 matrix/annotation cell IDs mismatch: "
            f"missing={len(missing_annotations)}, extra={len(extra_annotations)}"
        )

    treatment_counts = Counter(record["treatment.group"] for record in records)
    cell_type_counts = Counter(record["cell.types"] for record in records)
    return {
        "matrix_file": matrix_path.name,
        "annotation_file": annotations_path.name,
        "n_cells": len(matrix_cells),
        "n_gene_rows": gene_rows,
        "matrix_annotation_ids_match": True,
        "treatment_group_counts": dict(sorted(treatment_counts.items())),
        "cell_type_counts": dict(sorted(cell_type_counts.items())),
        "primary_analysis_status": "BLOCKED_PENDING_RESPONSE_METADATA_AUDIT",
        "required_manual_check": (
            "The public annotation includes treatment timing but no study-ready response endpoint in this file. "
            "Recover response labels from the source study/supplements and pre-register phenotype harmonization."
        ),
    }


def main() -> None:
    manifest_path = RAW / "public_processed_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Run 02_fetch_public_processed_data.py first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = {
        "scope": "Input integrity and metadata-availability audit; not a biological result.",
        "manifest_retrieved_at_utc": manifest["retrieved_at_utc"],
        "datasets": {
            "GSE120575": audit_gse120575(),
            "GSE115978": audit_gse115978(),
        },
        "global_gate": "BLOCKED_PENDING_RESPONSE_METADATA_AUDIT",
        "next_required_action": (
            "Create a manually verified patient/lesion-level phenotype table before any response comparison, "
            "pseudo-bulk analysis, model prompting, or candidate ranking."
        ),
    }
    RESULTS.mkdir(exist_ok=True)
    output = RESULTS / "public_input_audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nWrote input audit: {output}")


if __name__ == "__main__":
    main()
