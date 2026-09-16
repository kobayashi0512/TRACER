#!/usr/bin/env python3
"""Direction-check pre-specified positive controls in independent bulk GSE91061.

This is an external expression-direction check only. GSE91061 is bulk RNA, so
it cannot establish the cell type, mechanism, or causal role implied by a gene
or program. It never trains or evaluates a clinical prediction model.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
from pathlib import Path
from statistics import mean


APP_ROOT = Path(__file__).resolve().parents[1]
RAW = APP_ROOT / "data" / "raw"
DERIVED = APP_ROOT / "data" / "derived"
CONFIG = APP_ROOT / "config" / "positive_control_panel_v1.json"
RESULTS = APP_ROOT / "results"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


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
    """Return U and two-sided tie-corrected normal-approximation p-value."""
    values = responder + non_responder
    ranks = average_ranks(values)
    n1, n2 = len(responder), len(non_responder)
    u = sum(ranks[:n1]) - n1 * (n1 + 1) / 2
    expected = n1 * n2 / 2
    tie_counts: dict[float, int] = {}
    for value in values:
        tie_counts[value] = tie_counts.get(value, 0) + 1
    tie_term = sum(count**3 - count for count in tie_counts.values())
    n = n1 + n2
    variance = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    if variance == 0:
        return u, 1.0
    z = max(0.0, abs(u - expected) - 0.5) / math.sqrt(variance)
    return u, math.erfc(z / math.sqrt(2))


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


def zscore(values: dict[str, float]) -> dict[str, float]:
    center = mean(values.values())
    scale = math.sqrt(mean((value - center) ** 2 for value in values.values()))
    return {sample: 0.0 if scale == 0 else (value - center) / scale for sample, value in values.items()}


def main() -> None:
    panel = json.loads(CONFIG.read_text(encoding="utf-8"))
    cohort = read_tsv(DERIVED / "gse91061_pre_treatment_validation_v1.tsv")
    response_by_sample = {row["sample_id"]: row["response_binary"] for row in cohort}
    selected_samples = set(response_by_sample)
    gene_ids = panel["gse91061_entrez_gene_ids"]
    panel_genes = {gene for program in panel["programs"].values() for gene in program["genes"]}
    if panel_genes != set(gene_ids):
        raise ValueError("Panel gene and GSE91061 Entrez mapping sets differ.")

    expression_path = RAW / "GSE91061_BMS038109Sample.hg19KnownGene.rld.csv.gz"
    values_by_gene: dict[str, dict[str, float]] = {}
    gene_by_id = {gene_id: gene for gene, gene_id in gene_ids.items()}
    with gzip.open(expression_path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        sample_ids = header[1:]
        selected_indices = [index for index, sample_id in enumerate(sample_ids) if sample_id in selected_samples]
        if len(selected_indices) != len(selected_samples):
            raise ValueError("GSE91061 selected metadata samples do not all occur in the RLD matrix.")
        selected_ids = [sample_ids[index] for index in selected_indices]
        for row in reader:
            if not row:
                continue
            gene = gene_by_id.get(row[0])
            if gene is None:
                continue
            values_by_gene[gene] = {
                sample_id: float(row[index + 1])
                for index, sample_id in zip(selected_indices, selected_ids, strict=True)
            }

    missing = sorted(panel_genes - set(values_by_gene))
    if missing:
        raise ValueError(f"Mapped panel Entrez IDs absent from GSE91061 matrix: {missing}")

    analyses: dict[str, tuple[dict[str, float], str, str]] = {}
    for program_name, program in panel["programs"].items():
        for gene in program["genes"]:
            analyses[f"gene:{gene}"] = (values_by_gene[gene], program["expected_higher_group"], "gene")
        gene_zscores = [zscore(values_by_gene[gene]) for gene in program["genes"]]
        analyses[f"program:{program_name}"] = (
            {sample: mean(zvalues[sample] for zvalues in gene_zscores) for sample in selected_samples},
            program["expected_higher_group"],
            "program",
        )

    rows: list[dict[str, object]] = []
    for feature, (values, expected_higher_group, feature_type) in sorted(analyses.items()):
        responder = [values[sample] for sample in sorted(selected_samples) if response_by_sample[sample] == "Responder"]
        non_responder = [values[sample] for sample in sorted(selected_samples) if response_by_sample[sample] == "Non-responder"]
        u_statistic, p_value = mann_whitney_normal_approx(responder, non_responder)
        difference = mean(responder) - mean(non_responder)
        observed_higher_group = "Responder" if difference > 0 else "Non-responder" if difference < 0 else "Tie"
        rows.append(
            {
                "feature": feature,
                "feature_type": feature_type,
                "responder_mean": round(mean(responder), 6),
                "non_responder_mean": round(mean(non_responder), 6),
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

    RESULTS.mkdir(exist_ok=True)
    output = RESULTS / "gse91061_positive_control_direction_check_v1.tsv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    program_rows = [row for row in rows if row["feature_type"] == "program"]
    summary = {
        "analysis": "Independent pre-treatment bulk-RNA direction check of pre-specified GSE120575 positive controls",
        "cohort": "GSE91061",
        "n_samples": len(selected_samples),
        "response_counts": {group: sum(value == group for value in response_by_sample.values()) for group in sorted(set(response_by_sample.values()))},
        "tested_features": len(rows),
        "features_matching_expected_direction": sum(bool(row["direction_matches_positive_control"]) for row in rows),
        "program_direction_matches": {row["feature"]: row["direction_matches_positive_control"] for row in program_rows},
        "result_path": str(output.relative_to(APP_ROOT)),
        "interpretation_limit": (
            "Bulk direction check only: no inference about immune-cell identity, cell-state abundance, "
            "cell-cell interaction, causal mechanism, or clinical utility."
        ),
    }
    summary_path = RESULTS / "gse91061_positive_control_direction_check_v1.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
