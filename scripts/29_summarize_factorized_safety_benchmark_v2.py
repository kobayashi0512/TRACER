#!/usr/bin/env python3
"""Summarize the frozen factorial-v2 safety suite for Table 1.

This script deliberately summarizes a finite, fully enumerated protocol.  It
does not estimate LLM accuracy, biomedical validity, a population rate, or a
statistical confidence interval.  Its purpose is to make the already-tested
32-case deterministic gate ablations easy to audit and cite in the manuscript.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


APP_ROOT = Path(__file__).resolve().parents[1]


MAIN_METHODS = (
    ("Full TRACER", "complete_draft"),
    ("TRACER without transport gate", "transport_gate_ablation"),
    ("TRACER without source-independence gate", "source_independence_ablation"),
    ("TRACER without all-cohort FDR gate", "all_cohort_fdr_ablation"),
    ("Naive counting baseline", "naive_counting_baseline"),
)


def _is_high_and_admitted(result: dict[str, Any]) -> bool:
    return result["level"] == "HIGH" and result["draft_admissible_for_review"] is True


def _rate(count: int, denominator: int) -> str:
    if denominator == 0:
        return "not applicable"
    return f"{count}/{denominator} ({100 * count / denominator:.1f}%)"


def _require_exactly_one(records: Iterable[dict[str, Any]], label: str) -> dict[str, Any]:
    matches = list(records)
    if len(matches) != 1:
        raise ValueError(f"Expected one {label} packet, found {len(matches)}.")
    return matches[0]


def _factor_category(factors: dict[str, bool]) -> str:
    if all(factors.values()):
        return "eligible_positive_control"
    if (
        not factors["transport_eligible"]
        and all(value for name, value in factors.items() if name != "transport_eligible")
    ):
        return "cross_measurement_only_failure"
    if (
        not factors["source_independent"]
        and all(value for name, value in factors.items() if name != "source_independent")
    ):
        return "same_source_only_failure"
    if (
        not factors["all_replication_fdr_pass"]
        and all(value for name, value in factors.items() if name != "all_replication_fdr_pass")
    ):
        return "all_cohort_fdr_only_failure"
    return "multi_factor_safety_stress"


def _summarize_method(
    records: list[dict[str, Any]], *, method_name: str, result_key: str
) -> dict[str, Any]:
    expected_high = [record["expected_complete_draft_high_priority"] for record in records]
    observed_high = [_is_high_and_admitted(record[result_key]) for record in records]
    unsafe_ids = [
        record["packet_id"]
        for record, expected, observed in zip(records, expected_high, observed_high)
        if not expected and observed
    ]
    retained_ids = [
        record["packet_id"]
        for record, expected, observed in zip(records, expected_high, observed_high)
        if expected and observed
    ]
    exact_ids = [
        record["packet_id"]
        for record, expected, observed in zip(records, expected_high, observed_high)
        if expected == observed
    ]
    n_expected_low = sum(not value for value in expected_high)
    n_expected_high = sum(expected_high)
    return {
        "method": method_name,
        "evaluation_set": "complete frozen draft",
        "n_cases": len(records),
        "n_expected_low": n_expected_low,
        "n_expected_high": n_expected_high,
        "unsafe_high_n": len(unsafe_ids),
        "unsafe_high_rate": _rate(len(unsafe_ids), n_expected_low),
        "unsafe_high_packet_ids": unsafe_ids,
        "eligible_retained_n": len(retained_ids),
        "eligible_retention": _rate(len(retained_ids), n_expected_high),
        "eligible_retained_packet_ids": retained_ids,
        "exact_priority_decision_n": len(exact_ids),
        "exact_priority_decision_rate": _rate(len(exact_ids), len(records)),
        "exact_priority_packet_ids": exact_ids,
    }


def _summarize_provenance_omission(
    records: list[dict[str, Any]], *, method_name: str, result_key: str
) -> dict[str, Any]:
    observed_high = [
        _is_high_and_admitted(record["omission_attack"][result_key]) for record in records
    ]
    unsafe_ids = [
        record["packet_id"] for record, observed in zip(records, observed_high) if observed
    ]
    return {
        "method": method_name,
        "evaluation_set": "provenance-omission attack",
        "n_cases": len(records),
        "n_expected_low": len(records),
        "n_expected_high": 0,
        "unsafe_high_n": len(unsafe_ids),
        "unsafe_high_rate": _rate(len(unsafe_ids), len(records)),
        "unsafe_high_packet_ids": unsafe_ids,
        "eligible_retained_n": None,
        "eligible_retention": "not applicable: every omission draft is ineligible by protocol",
        "eligible_retained_packet_ids": [],
        "exact_priority_decision_n": len(records) - len(unsafe_ids),
        "exact_priority_decision_rate": _rate(len(records) - len(unsafe_ids), len(records)),
        "exact_priority_packet_ids": [
            record["packet_id"] for record, observed in zip(records, observed_high) if not observed
        ],
    }


def _tsv_rows(summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in summary["complete_draft_comparison"] + summary["provenance_omission_comparison"]:
        rows.append(
            {
                "evaluation_set": row["evaluation_set"],
                "method": row["method"],
                "unsafe_HIGH": row["unsafe_high_rate"],
                "eligible_retention": row["eligible_retention"],
                "exact_priority_decision": row["exact_priority_decision_rate"],
                "unsafe_packet_ids": ";".join(row["unsafe_high_packet_ids"]),
            }
        )
    return rows


def _markdown_table(rows: list[dict[str, str]]) -> str:
    header = [
        "Evaluation set",
        "Method",
        "Unsafe HIGH",
        "Eligible retention",
        "Exact priority decision",
    ]
    lines = ["| " + " | ".join(header) + " |", "|---|---|---:|---:|---:|"]
    for row in rows:
        lines.append(
            "| {evaluation_set} | {method} | {unsafe_HIGH} | {eligible_retention} | {exact_priority_decision} |".format(
                **row
            )
        )
    return "\n".join(lines)


def build_summary(source: dict[str, Any], source_sha256: str) -> dict[str, Any]:
    records = source["records"]
    if len(records) != 32:
        raise ValueError(f"This protocol requires 32 frozen factorial packets, found {len(records)}.")
    if not all(record["complete_matches_expected"] for record in records):
        raise ValueError("Full TRACER does not match every frozen reference label.")
    category_counts: dict[str, int] = {}
    for record in records:
        category = _factor_category(record["factors"])
        category_counts[category] = category_counts.get(category, 0) + 1
    if category_counts != {
        "eligible_positive_control": 1,
        "cross_measurement_only_failure": 1,
        "same_source_only_failure": 1,
        "all_cohort_fdr_only_failure": 1,
        "multi_factor_safety_stress": 28,
    }:
        raise ValueError(f"Unexpected factorial category coverage: {category_counts}")
    critical_cells = {
        "eligible_positive_control": _require_exactly_one(
            (record for record in records if _factor_category(record["factors"]) == "eligible_positive_control"),
            "eligible positive control",
        )["packet_id"],
        "cross_measurement_only_failure": _require_exactly_one(
            (record for record in records if _factor_category(record["factors"]) == "cross_measurement_only_failure"),
            "cross-measurement-only failure",
        )["packet_id"],
        "same_source_only_failure": _require_exactly_one(
            (record for record in records if _factor_category(record["factors"]) == "same_source_only_failure"),
            "same-source-only failure",
        )["packet_id"],
        "all_cohort_fdr_only_failure": _require_exactly_one(
            (record for record in records if _factor_category(record["factors"]) == "all_cohort_fdr_only_failure"),
            "all-cohort-FDR-only failure",
        )["packet_id"],
    }
    summary = {
        "schema": "tracer-factorized-safety-benchmark-summary-v1",
        "suite_id": source["suite_id"],
        "source_results_sha256": source_sha256,
        "interpretation": (
            "Finite deterministic implementation verification on a frozen synthetic factorial suite. "
            "It supports gate-attribution claims only; it is not an LLM benchmark, biomedical "
            "finding, clinical-utility result, or population safety estimate."
        ),
        "protocol": {
            "design": "complete 2^5 enumeration of transport, source independence, all-cohort FDR, perturbation, and confounding factors",
            "n_complete_draft_cases": len(records),
            "n_expected_HIGH": sum(record["expected_complete_draft_high_priority"] for record in records),
            "n_expected_LOW": sum(not record["expected_complete_draft_high_priority"] for record in records),
            "statistical_policy": "Report exact finite-suite counts and rates. Do not attach p-values or population confidence intervals to this deterministic enumeration.",
            "omission_attack": "One cited evidence item is withheld from each draft; all 32 omission drafts are ineligible by the frozen protocol.",
        },
        "critical_cell_packet_ids": critical_cells,
        "category_counts": category_counts,
        "complete_draft_comparison": [
            _summarize_method(records, method_name=method, result_key=result_key)
            for method, result_key in MAIN_METHODS
        ],
        "provenance_omission_comparison": [
            _summarize_provenance_omission(
                records, method_name="Full TRACER", result_key="full_tracer"
            ),
            _summarize_provenance_omission(
                records,
                method_name="TRACER without provenance coverage",
                result_key="without_provenance_coverage",
            ),
        ],
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=APP_ROOT / "results" / "factorized_safety_benchmark_summary_v1.json",
    )
    parser.add_argument(
        "--output-tsv",
        type=Path,
        default=APP_ROOT / "results" / "tables" / "table1_factorized_safety_benchmark_v1.tsv",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        default=APP_ROOT / "docs" / "table1_factorized_safety_benchmark_v1.md",
    )
    args = parser.parse_args()
    source_bytes = args.input.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    summary = build_summary(source, hashlib.sha256(source_bytes).hexdigest())
    rows = _tsv_rows(summary)
    for output in (args.output_json, args.output_tsv, args.output_markdown):
        output.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    args.output_markdown.write_text(
        "# Table 1. Factorized synthetic safety benchmark\n\n"
        "This is a finite deterministic gate-verification suite, not an LLM leaderboard or biomedical validation. "
        "`Unsafe HIGH` counts an ineligible frozen packet that a comparator elevated to HIGH. "
        "`Eligible retention` is defined only for the one frozen all-pass control.\n\n"
        + _markdown_table(rows)
        + (
            "\n\n## Predeclared critical cells\n\n"
            "- Eligible positive control: `{eligible_positive_control}`\n"
            "- Cross-measurement-only failure: `{cross_measurement_only_failure}`\n"
            "- Same-source-only failure: `{same_source_only_failure}`\n"
            "- All-cohort-FDR-only failure: `{all_cohort_fdr_only_failure}`\n\n"
        ).format(**summary["critical_cell_packet_ids"])
        + "The remaining 28 cells contain two or more factor failures and test compositional safety stress. "
        + "All 32 provenance-omission cards are separate draft-integrity attacks; their expected label is LOW.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "saved_json": str(args.output_json),
                "saved_tsv": str(args.output_tsv),
                "saved_markdown": str(args.output_markdown),
                "complete_draft_methods": len(summary["complete_draft_comparison"]),
                "provenance_omission_methods": len(summary["provenance_omission_comparison"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
