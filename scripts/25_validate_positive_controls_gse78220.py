#!/usr/bin/env python3
"""Direction-check the frozen panel in audited GSE78220 pre-treatment samples.

GSE78220 is a tumor bulk-RNA cohort.  This script assesses only whether
pre-specified expression directions transfer to a second, independently
accessioned cohort.  It cannot validate a single-cell state, a causal pathway,
or a clinical prediction model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from statistics import mean
from xml.etree import ElementTree


APP_ROOT = Path(__file__).resolve().parents[1]
OOXML_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def mann_whitney_normal_approx(responder: list[float], non_responder: list[float]) -> tuple[float, float]:
    values = responder + non_responder
    ranks = average_ranks(values)
    n1, n2 = len(responder), len(non_responder)
    u_statistic = sum(ranks[:n1]) - n1 * (n1 + 1) / 2
    expected = n1 * n2 / 2
    tie_counts = Counter(values)
    tie_term = sum(count**3 - count for count in tie_counts.values())
    total = n1 + n2
    variance = n1 * n2 / 12 * ((total + 1) - tie_term / (total * (total - 1)))
    if variance == 0:
        return u_statistic, 1.0
    z_score = max(0.0, abs(u_statistic - expected) - 0.5) / math.sqrt(variance)
    return u_statistic, math.erfc(z_score / math.sqrt(2))


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    total = len(p_values)
    ordered = sorted(range(total), key=p_values.__getitem__)
    q_values = [0.0] * total
    running = 1.0
    for reverse_rank, original_index in enumerate(reversed(ordered), start=1):
        rank = total - reverse_rank + 1
        running = min(running, p_values[original_index] * total / rank)
        q_values[original_index] = min(1.0, running)
    return q_values


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in entry.iter(f"{OOXML_NS}t")) for entry in root]


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value = cell.find(f"{OOXML_NS}v")
    raw = "" if value is None or value.text is None else value.text
    return shared_strings[int(raw)] if cell.attrib.get("t") == "s" and raw else raw


def read_selected_fpkm(
    xlsx_path: Path, selected_columns: list[str], panel_genes: set[str]
) -> dict[str, dict[str, float]]:
    """Stream the OOXML sheet and retain only frozen-panel genes and samples."""
    with zipfile.ZipFile(xlsx_path) as archive:
        strings = _shared_strings(archive)
        worksheet_bytes = archive.read("xl/worksheets/sheet1.xml")
    values_by_gene: dict[str, dict[str, float]] = {}
    header: list[str] | None = None
    for _, element in ElementTree.iterparse(BytesIO(worksheet_bytes), events=("end",)):
        if element.tag != f"{OOXML_NS}row":
            continue
        cells = element.findall(f"{OOXML_NS}c")
        values = [_cell_value(cell, strings) for cell in cells]
        if header is None:
            header = values
            if not header or header[0] != "Gene":
                raise ValueError("Unexpected GSE78220 matrix header.")
            missing_columns = sorted(set(selected_columns) - set(header))
            if missing_columns:
                raise ValueError(f"Audited columns absent from GSE78220 XLSX: {missing_columns}")
            selected_indices = {column: header.index(column) for column in selected_columns}
        else:
            gene = values[0] if values else ""
            if gene in panel_genes:
                if len(values) != len(header):
                    raise ValueError(f"Malformed row for {gene}: expected {len(header)} cells, got {len(values)}.")
                values_by_gene[gene] = {
                    column: float(values[index]) for column, index in selected_indices.items()
                }
        element.clear()
    missing_genes = sorted(panel_genes - set(values_by_gene))
    if missing_genes:
        raise ValueError(f"Frozen panel genes absent from GSE78220 XLSX: {missing_genes}")
    return values_by_gene


def zscore(values: dict[str, float]) -> dict[str, float]:
    center = mean(values.values())
    scale = math.sqrt(mean((value - center) ** 2 for value in values.values()))
    return {sample: 0.0 if scale == 0 else (value - center) / scale for sample, value in values.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=APP_ROOT / "results" / "gse78220_eligibility_audit_v1.json")
    parser.add_argument("--xlsx", type=Path, default=APP_ROOT / "data" / "raw" / "GSE78220_PatientFPKM.xlsx")
    parser.add_argument("--panel", type=Path, default=APP_ROOT / "config" / "positive_control_panel_v1.json")
    parser.add_argument(
        "--output", type=Path, default=APP_ROOT / "results" / "gse78220_positive_control_direction_check_v1.tsv"
    )
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if not audit["registry_recommendation"]["baseline_ici_response_association_eligible"]:
        raise SystemExit("GSE78220 audit is ineligible; do not analyze its response association.")
    audit_hash = audit["source_files"]["xlsx"]["sha256"]
    if sha256(args.xlsx) != audit_hash:
        raise SystemExit("GSE78220 XLSX checksum differs from the audited source file.")

    baseline_records = [
        record
        for record in audit["linkage"]["columns"]
        if record["matrix_timepoint"] == "baseline" and record["geo_biopsy_time"] == "pre-treatment"
    ]
    response_by_column = {
        record["matrix_column"]: "Responder"
        if record["response_group"] == "objective_responder"
        else "Non-responder"
        for record in baseline_records
    }
    if set(response_by_column.values()) != {"Responder", "Non-responder"}:
        raise SystemExit("GSE78220 audit does not have both frozen response groups.")

    panel = json.loads(args.panel.read_text(encoding="utf-8"))
    panel_genes = {gene for program in panel["programs"].values() for gene in program["genes"]}
    values_by_gene = read_selected_fpkm(args.xlsx, sorted(response_by_column), panel_genes)
    # The source sheet contains nonnegative FPKM values.  Log2(FPKM + 1) is
    # specified here solely to reduce the scale dependence of rank summaries.
    log_values_by_gene = {
        gene: {sample: math.log2(value + 1.0) for sample, value in values.items()}
        for gene, values in values_by_gene.items()
    }

    analyses: dict[str, tuple[dict[str, float], str, str]] = {}
    for program_name, program in panel["programs"].items():
        for gene in program["genes"]:
            analyses[f"gene:{gene}"] = (log_values_by_gene[gene], program["expected_higher_group"], "gene")
        gene_zscores = [zscore(log_values_by_gene[gene]) for gene in program["genes"]]
        analyses[f"program:{program_name}"] = (
            {
                sample: mean(zvalues[sample] for zvalues in gene_zscores)
                for sample in response_by_column
            },
            program["expected_higher_group"],
            "program",
        )

    rows: list[dict[str, object]] = []
    for feature, (values, expected_higher_group, feature_type) in sorted(analyses.items()):
        responders = [values[column] for column in sorted(response_by_column) if response_by_column[column] == "Responder"]
        non_responders = [
            values[column] for column in sorted(response_by_column) if response_by_column[column] == "Non-responder"
        ]
        u_statistic, p_value = mann_whitney_normal_approx(responders, non_responders)
        difference = mean(responders) - mean(non_responders)
        observed_higher_group = "Responder" if difference > 0 else "Non-responder" if difference < 0 else "Tie"
        rows.append(
            {
                "feature": feature,
                "feature_type": feature_type,
                "responder_mean_log2_fpkm_plus_1": round(mean(responders), 6),
                "non_responder_mean_log2_fpkm_plus_1": round(mean(non_responders), 6),
                "responder_minus_non_responder": round(difference, 6),
                "mann_whitney_u": round(u_statistic, 6),
                "normal_approx_p": round(p_value, 6),
                "expected_higher_group": expected_higher_group,
                "observed_higher_group": observed_higher_group,
                "direction_matches_positive_control": observed_higher_group == expected_higher_group,
            }
        )
    q_values = benjamini_hochberg([float(row["normal_approx_p"]) for row in rows])
    for row, q_value in zip(rows, q_values, strict=True):
        row["panel_bh_q"] = round(q_value, 6)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "analysis": "Independent pre-treatment bulk-RNA direction check of frozen GSE120575 positive controls",
        "cohort": "GSE78220",
        "data_transform": "log2(FPKM + 1) per gene; program score is the mean within-cohort gene z-score.",
        "n_baseline_columns": len(response_by_column),
        "response_counts": dict(sorted(Counter(response_by_column.values()).items())),
        "tested_features": len(rows),
        "features_matching_expected_direction": sum(bool(row["direction_matches_positive_control"]) for row in rows),
        "result_path": str(args.output.relative_to(APP_ROOT)),
        "interpretation_limit": (
            "Bulk direction check only: no inference about immune-cell identity, cell-state abundance, "
            "cell-cell interaction, causal mechanism, or clinical utility. This result is one cohort-level "
            "check and does not resolve participant-level dependence in matrix labels."
        ),
    }
    summary_path = args.output.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
