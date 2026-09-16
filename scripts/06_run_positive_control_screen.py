#!/usr/bin/env python3
"""Run a lesion-level, composition-sensitive positive-control screen.

This program intentionally uses published immune-state panels as a data-pipeline
sanity check. It is not candidate discovery. The processed source matrix contains
log2(TPM+1)-scale expression, so lesion values are mean log expression across
cells, not count-scale pseudo-bulk values.
"""

from __future__ import annotations

import csv
import gzip
import itertools
import json
import math
from collections import defaultdict
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def average_ranks(values: list[float]) -> list[float]:
    """Return average ranks with exact tie handling, ranks starting at one."""
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


def exact_rank_sum_test(responder_values: list[float], non_responder_values: list[float]) -> tuple[float, float]:
    """Two-sided exact randomization p-value from all label assignments.

    With 4 vs 8 lesions there are only 495 assignments; no asymptotic clinical
    inference is implied.
    """
    values = responder_values + non_responder_values
    ranks = average_ranks(values)
    n_responder = len(responder_values)
    observed = sum(ranks[:n_responder])
    expected = n_responder * (len(values) + 1) / 2
    observed_distance = abs(observed - expected)
    all_sums = [sum(ranks[index] for index in group) for group in itertools.combinations(range(len(values)), n_responder)]
    p_value = sum(abs(rank_sum - expected) >= observed_distance - 1e-12 for rank_sum in all_sums) / len(all_sums)
    u_statistic = observed - n_responder * (n_responder + 1) / 2
    return u_statistic, p_value


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


def zscore_by_lesion(values: dict[str, float]) -> dict[str, float]:
    center = mean(values.values())
    variance = mean((value - center) ** 2 for value in values.values())
    if variance == 0:
        return {lesion: 0.0 for lesion in values}
    scale = math.sqrt(variance)
    return {lesion: (value - center) / scale for lesion, value in values.items()}


def main() -> None:
    cohort = read_tsv(DERIVED / "gse120575_primary_cohort_v1.tsv")
    cell_metadata = read_tsv(DERIVED / "gse120575_cell_metadata.tsv")
    panel = read_json(CONFIG)
    lesion_response = {row["lesion_id"]: row["response"] for row in cohort}
    primary_lesions = set(lesion_response)
    cell_to_lesion = {
        row["cell_id"]: row["lesion_id"]
        for row in cell_metadata
        if row["lesion_id"] in primary_lesions
    }
    panel_genes = {gene for program in panel["programs"].values() for gene in program["genes"]}

    matrix = RAW / "GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz"
    with gzip.open(matrix, "rt", encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n\r").split("\t")
        handle.readline()  # source lesion labels; cell metadata is the authoritative join.
        matrix_cells = header[1:]
        selected_indices = [index for index, cell in enumerate(matrix_cells) if cell in cell_to_lesion]
        if len(selected_indices) != len(cell_to_lesion):
            raise ValueError(
                f"Primary metadata/matrix mismatch: metadata={len(cell_to_lesion)}, matrix_selected={len(selected_indices)}"
            )
        selected_lesions = [cell_to_lesion[matrix_cells[index]] for index in selected_indices]
        cell_counts = defaultdict(int)
        for lesion in selected_lesions:
            cell_counts[lesion] += 1
        if set(cell_counts) != primary_lesions:
            raise ValueError("At least one selected lesion has zero cells in the matrix.")

        gene_lesion_means: dict[str, dict[str, float]] = {}
        for line in handle:
            gene, separator, values = line.partition("\t")
            if not separator or gene not in panel_genes:
                continue
            fields = values.rstrip("\n\r").split("\t")
            sums = defaultdict(float)
            for index, lesion in zip(selected_indices, selected_lesions, strict=True):
                sums[lesion] += float(fields[index])
            gene_lesion_means[gene] = {lesion: sums[lesion] / cell_counts[lesion] for lesion in primary_lesions}

    missing_genes = sorted(panel_genes - set(gene_lesion_means))
    if missing_genes:
        raise ValueError(f"Positive-control genes absent from matrix: {missing_genes}")

    rows: list[dict[str, object]] = []
    analyses: dict[str, tuple[dict[str, float], str, str]] = {}
    for gene, values in sorted(gene_lesion_means.items()):
        expected_group = next(
            program["expected_higher_group"]
            for program in panel["programs"].values()
            if gene in program["genes"]
        )
        analyses[f"gene:{gene}"] = (values, expected_group, "gene")

    for program_name, program in panel["programs"].items():
        standardized = [zscore_by_lesion(gene_lesion_means[gene]) for gene in program["genes"]]
        program_values = {
            lesion: mean(gene_values[lesion] for gene_values in standardized)
            for lesion in primary_lesions
        }
        analyses[f"program:{program_name}"] = (program_values, program["expected_higher_group"], "program")

    for feature, (values, expected_group, feature_type) in analyses.items():
        responder = [values[lesion] for lesion in sorted(primary_lesions) if lesion_response[lesion] == "Responder"]
        non_responder = [values[lesion] for lesion in sorted(primary_lesions) if lesion_response[lesion] == "Non-responder"]
        u_statistic, p_value = exact_rank_sum_test(responder, non_responder)
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
                "exact_randomization_p": round(p_value, 6),
                "expected_higher_group": expected_group,
                "observed_higher_group": observed_higher_group,
                "direction_matches_positive_control": observed_higher_group == expected_group,
            }
        )

    q_values = benjamini_hochberg([float(row["exact_randomization_p"]) for row in rows])
    for row, q_value in zip(rows, q_values, strict=True):
        row["panel_bh_q"] = round(q_value, 6)

    RESULTS.mkdir(exist_ok=True)
    output = RESULTS / "positive_control_screen_v1.tsv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "analysis": "Lesion-level mean log2(TPM+1) positive-control screen",
        "cohort": "gse120575-primary-v1",
        "n_lesions": len(primary_lesions),
        "response_counts": {group: sum(value == group for value in lesion_response.values()) for group in sorted(set(lesion_response.values()))},
        "n_selected_cells": len(selected_indices),
        "cell_counts_by_lesion": dict(sorted(cell_counts.items())),
        "tested_features": len(rows),
        "features_matching_expected_direction": sum(bool(row["direction_matches_positive_control"]) for row in rows),
        "result_path": str(output.relative_to(APP_ROOT)),
        "interpretation_limit": panel["analysis_limit"],
        "prohibited_claim": "No result in this file is a novel mechanism, cell-intrinsic association, causal effect, or clinical prediction.",
    }
    summary_path = RESULTS / "positive_control_screen_v1.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
