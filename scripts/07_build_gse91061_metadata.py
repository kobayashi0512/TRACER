#!/usr/bin/env python3
"""Parse and freeze the public GSE91061 bulk-RNA validation metadata.

Response labels are taken directly from GEO SOFT characteristics. ``PRCR`` is
defined as responder; ``PD`` and ``SD`` as non-responder; ``UNK`` is excluded.
This is a pre-specified label mapping for direction checks, not a clinical model.
"""

from __future__ import annotations

import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
RAW = APP_ROOT / "data" / "raw"
DERIVED = APP_ROOT / "data" / "derived"
RESULTS = APP_ROOT / "results"


def parse_soft() -> list[dict[str, str]]:
    path = RAW / "GSE91061_family.soft.gz"
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if line.startswith("^SAMPLE = "):
                if current is not None:
                    records.append(current)
                current = {"geo_accession": line.split(" = ", 1)[1]}
            elif current is not None and line.startswith("!Sample_title = "):
                current["sample_id"] = line.split(" = ", 1)[1]
            elif current is not None and line.startswith("!Sample_characteristics_ch1 = "):
                item = line.split(" = ", 1)[1]
                if ": " in item:
                    key, value = item.split(": ", 1)
                    current[key] = value
    if current is not None:
        records.append(current)
    required = {"geo_accession", "sample_id", "visit (pre or on treatment)", "response", "tissue"}
    for record in records:
        missing = required - set(record)
        if missing:
            raise ValueError(f"GSE91061 SOFT sample has missing fields {sorted(missing)}: {record.get('geo_accession')}")
    return records


def expression_sample_ids() -> set[str]:
    path = RAW / "GSE91061_BMS038109Sample.hg19KnownGene.rld.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        header = next(csv.reader(handle))
    if not header or header[0] != "":
        raise ValueError("Expected first GSE91061 RLD header cell to be empty (Entrez gene ID column).")
    return set(header[1:])


def patient_token(sample_id: str) -> str:
    match = re.match(r"^(Pt\d+)_(?:Pre|On)_", sample_id)
    if not match:
        raise ValueError(f"Could not parse GSE91061 patient token: {sample_id}")
    return match.group(1)


def response_binary(source_response: str) -> str:
    if source_response == "PRCR":
        return "Responder"
    if source_response in {"PD", "SD"}:
        return "Non-responder"
    if source_response == "UNK":
        return "Excluded_unknown"
    raise ValueError(f"Unexpected GSE91061 source response label: {source_response}")


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    records = parse_soft()
    matrix_ids = expression_sample_ids()
    metadata_ids = {record["sample_id"] for record in records}
    if metadata_ids != matrix_ids:
        raise ValueError(
            "GSE91061 matrix/SOFT sample-ID mismatch: "
            f"matrix_only={len(matrix_ids - metadata_ids)}, metadata_only={len(metadata_ids - matrix_ids)}"
        )

    normalized = []
    for record in records:
        normalized.append(
            {
                "sample_id": record["sample_id"],
                "geo_accession": record["geo_accession"],
                "patient_token": patient_token(record["sample_id"]),
                "visit": record["visit (pre or on treatment)"],
                "source_response": record["response"],
                "response_binary": response_binary(record["response"]),
                "tissue": record["tissue"],
            }
        )

    pre_evaluable = [
        record for record in normalized
        if record["visit"] == "Pre" and record["response_binary"] != "Excluded_unknown"
    ]
    duplicate_patients = sorted(
        patient for patient, count in Counter(record["patient_token"] for record in pre_evaluable).items() if count > 1
    )
    if duplicate_patients:
        raise ValueError(
            "GSE91061 has repeated evaluable pre-treatment patient tokens; selection needs a pre-specified rule: "
            f"{duplicate_patients}"
        )
    if set(record["response_binary"] for record in pre_evaluable) != {"Responder", "Non-responder"}:
        raise ValueError("Both evaluable response groups are required in GSE91061.")

    DERIVED.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    all_output = DERIVED / "gse91061_sample_metadata.tsv"
    external_output = DERIVED / "gse91061_pre_treatment_validation_v1.tsv"
    write_tsv(all_output, normalized)
    write_tsv(external_output, pre_evaluable)
    summary = {
        "source": "GSE91061 GEO SOFT metadata and rld expression header",
        "n_matrix_samples": len(matrix_ids),
        "n_metadata_samples": len(normalized),
        "matrix_metadata_ids_match": True,
        "pre_treatment_evaluable_n": len(pre_evaluable),
        "pre_treatment_evaluable_response_counts": dict(sorted(Counter(record["response_binary"] for record in pre_evaluable).items())),
        "excluded_pre_treatment_unknown_response_n": sum(
            record["visit"] == "Pre" and record["response_binary"] == "Excluded_unknown" for record in normalized
        ),
        "all_metadata_path": str(all_output.relative_to(APP_ROOT)),
        "validation_cohort_path": str(external_output.relative_to(APP_ROOT)),
        "interpretation_limit": (
            "This independent bulk cohort may validate a pre-specified expression-direction signal only. "
            "It cannot validate cell type, cell-cell interaction, causality, or a trained predictor."
        ),
    }
    report = RESULTS / "gse91061_metadata_build_audit.json"
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
