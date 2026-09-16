#!/usr/bin/env python3
"""Audit whether GSE78220's expression columns can be linked to GEO response metadata.

This is a cohort-eligibility audit, not a differential-expression analysis.  It
reads the public XLSX as OOXML so that the audit has no dependency on a
spreadsheet application's cached view and never modifies the source workbook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


APP_ROOT = Path(__file__).resolve().parents[1]
OOXML_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_soft(path: Path) -> dict[str, dict[str, str]]:
    """Return sample records keyed by the GEO sample title (e.g., ``Pt1``)."""
    import gzip

    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith("^SAMPLE = "):
                if current is not None:
                    records.append(current)
                current = {"geo_series_sample_id": line.removeprefix("^SAMPLE = ")}
                continue
            if current is None:
                continue
            if line.startswith("!Sample_title = "):
                current["sample_title"] = line.removeprefix("!Sample_title = ")
            elif line.startswith("!Sample_geo_accession = "):
                current["gsm"] = line.removeprefix("!Sample_geo_accession = ")
            elif line.startswith("!Sample_characteristics_ch1 = "):
                key, value = line.removeprefix("!Sample_characteristics_ch1 = ").split(": ", 1)
                current[key] = value
    if current is not None:
        records.append(current)
    missing_titles = [record["geo_series_sample_id"] for record in records if "sample_title" not in record]
    if missing_titles:
        raise ValueError(f"GEO records missing !Sample_title: {missing_titles}")
    indexed = {record["sample_title"]: record for record in records}
    if len(indexed) != len(records):
        raise ValueError("GEO sample titles are not unique.")
    return indexed


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in entry.iter(f"{OOXML_NS}t")) for entry in root]


def parse_xlsx_header(path: Path) -> dict[str, object]:
    """Read only the sheet name, dimensions, and expression-matrix header row."""
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationship_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships = {
            node.attrib["Id"]: node.attrib["Target"] for node in relationship_root
        }
        sheets = workbook.find(f"{OOXML_NS}sheets")
        if sheets is None or len(sheets) != 1:
            raise ValueError("Expected exactly one expression sheet in GSE78220 workbook.")
        sheet = sheets[0]
        sheet_name = sheet.attrib["name"]
        target = relationships[sheet.attrib[f"{rel_ns}id"]]
        worksheet = ElementTree.fromstring(archive.read(f"xl/{target}"))
        dimension = worksheet.find(f"{OOXML_NS}dimension")
        first_row = worksheet.find(f"{OOXML_NS}sheetData/{OOXML_NS}row")
        if dimension is None or first_row is None:
            raise ValueError("Expression workbook lacks an accessible first row.")
        strings = _shared_strings(archive)
        header: list[str] = []
        for cell in first_row.findall(f"{OOXML_NS}c"):
            value = cell.find(f"{OOXML_NS}v")
            raw_value = "" if value is None or value.text is None else value.text
            if cell.attrib.get("t") == "s" and raw_value:
                header.append(strings[int(raw_value)])
            else:
                header.append(raw_value)
    return {
        "sheet_name": sheet_name,
        "dimension": dimension.attrib["ref"],
        "header": header,
    }


def response_group(response: str) -> str | None:
    normalized = response.strip().casefold()
    if normalized in {"complete response", "partial response"}:
        return "objective_responder"
    if normalized in {"progressive disease", "stable disease"}:
        return "non_objective_responder"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, default=APP_ROOT / "data" / "raw" / "GSE78220_PatientFPKM.xlsx")
    parser.add_argument("--soft", type=Path, default=APP_ROOT / "data" / "raw" / "GSE78220_family.soft.gz")
    parser.add_argument(
        "--output", type=Path, default=APP_ROOT / "results" / "gse78220_eligibility_audit_v1.json"
    )
    args = parser.parse_args()

    xlsx = parse_xlsx_header(args.xlsx)
    soft = parse_soft(args.soft)
    matrix_labels = list(xlsx["header"])[1:]
    if xlsx["header"][0] != "Gene":
        raise SystemExit("Unexpected first expression-matrix header; expected `Gene`.")

    column_records = []
    unmatched_columns = []
    for matrix_label in matrix_labels:
        match = re.fullmatch(r"(?P<title>Pt[0-9]+[A-Z]?)\.(?P<timepoint>baseline|OnTx)", matrix_label)
        if match is None:
            unmatched_columns.append(matrix_label)
            continue
        title = match.group("title")
        metadata = soft.get(title)
        if metadata is None:
            unmatched_columns.append(matrix_label)
            continue
        response = metadata.get("anti-pd-1 response", "")
        column_records.append(
            {
                "matrix_column": matrix_label,
                "geo_sample_title": title,
                "gsm": metadata.get("gsm"),
                "matrix_timepoint": match.group("timepoint"),
                "geo_biopsy_time": metadata.get("biopsy time"),
                "treatment": metadata.get("treatment"),
                "response": response,
                "response_group": response_group(response),
                "study_site": metadata.get("study site"),
                "previous_mapki": metadata.get("previous mapki"),
                "anatomical_location": metadata.get("anatomical location"),
            }
        )

    baseline = [
        record
        for record in column_records
        if record["matrix_timepoint"] == "baseline" and record["geo_biopsy_time"] == "pre-treatment"
    ]
    on_treatment = [record for record in column_records if record["matrix_timepoint"] == "OnTx"]
    timepoint_mismatches = [
        record["matrix_column"]
        for record in column_records
        if (record["matrix_timepoint"] == "baseline" and record["geo_biopsy_time"] != "pre-treatment")
        or (record["matrix_timepoint"] == "OnTx" and record["geo_biopsy_time"] == "pre-treatment")
    ]
    unknown_response_baseline = [
        record["matrix_column"] for record in baseline if record["response_group"] is None
    ]
    response_counts = Counter(record["response"] for record in baseline)
    group_counts = Counter(record["response_group"] for record in baseline)
    treatment_counts = Counter(record["treatment"] for record in baseline)
    all_labels_matched = not unmatched_columns and len(column_records) == len(matrix_labels)
    binary_endpoint_complete = not unknown_response_baseline and {
        "objective_responder",
        "non_objective_responder",
    }.issubset(group_counts)
    baseline_response_eligible = (
        all_labels_matched
        and not timepoint_mismatches
        and len(baseline) > 0
        and binary_endpoint_complete
        and set(treatment_counts) <= {"Pembrolizumab", "Nivolumab"}
    )

    audit = {
        "audit_id": "gse78220-public-processed-eligibility-audit-v1",
        "scope": "Read-only linkage audit; no differential expression, mechanism inference, or model evaluation.",
        "source_files": {
            "xlsx": {"path": str(args.xlsx), "sha256": sha256(args.xlsx)},
            "soft": {"path": str(args.soft), "sha256": sha256(args.soft)},
        },
        "workbook": {
            "sheet_name": xlsx["sheet_name"],
            "dimension": xlsx["dimension"],
            "n_expression_columns": len(matrix_labels),
            "matrix_columns": matrix_labels,
        },
        "linkage": {
            "n_geo_samples": len(soft),
            "n_matrix_columns_linked": len(column_records),
            "unmatched_matrix_columns": unmatched_columns,
            "timepoint_mismatches": timepoint_mismatches,
            "n_verified_pre_treatment_columns": len(baseline),
            "n_on_treatment_columns": len(on_treatment),
            "baseline_response_categories": dict(sorted(response_counts.items())),
            "baseline_response_group_counts": dict(sorted(group_counts.items())),
            "baseline_treatment_counts": dict(sorted(treatment_counts.items())),
            "baseline_unknown_response_columns": unknown_response_baseline,
            "columns": column_records,
        },
        "registry_recommendation": {
            "role": "external_direction_check_only",
            "disease": "melanoma",
            "compartment": "tumor_bulk",
            "measurement_level": "bulk_rna",
            "baseline_ici_response_association_eligible": baseline_response_eligible,
            "same_measurement_replication_eligible": False,
            "reason": (
                "Eligibility requires exact XLSX-to-SOFT linkage, pre-treatment timing, an auditable "
                "objective-response grouping, and anti-PD-1 monotherapy. Bulk tumor RNA remains "
                "ineligible as same-measurement replication of a single-cell cell-state claim."
            ),
            "caveats": [
                "The GEO matrix represents sample-level bulk RNA, not cell-state-resolved measurements.",
                "The audit does not establish whether labels such as Pt27A and Pt27B represent independent participants; do not use matrix columns as independent patient observations without a source-level participant audit.",
                "No composition, clinical-covariate, batch, or treatment-history adjustment is performed here.",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "eligible_for_baseline_association": baseline_response_eligible,
                "verified_pre_treatment_columns": len(baseline),
                "response_groups": dict(sorted(group_counts.items())),
                "unmatched_columns": unmatched_columns,
                "timepoint_mismatches": timepoint_mismatches,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
