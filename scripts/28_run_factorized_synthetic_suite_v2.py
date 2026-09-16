#!/usr/bin/env python3
"""Evaluate all factorial-v2 packets and their provenance-omission drafts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_graph import evaluate_with_evidence_graph  # noqa: E402
from src.evidence_packet import validate_packet  # noqa: E402
from src.synthetic_suite import complete_draft_from_packet, load_suite  # noqa: E402


def _high_and_admitted(result: dict[str, Any]) -> bool:
    return (
        result["assessment"]["level"] == "HIGH"
        and result["draft_admissible_for_review"] is True
    )


def _omit_source(draft: dict[str, Any], omitted_id: str) -> dict[str, Any]:
    omitted = dict(draft)
    omitted["evidence_sources"] = [
        source for source in draft["evidence_sources"] if source["id"] != omitted_id
    ]
    if len(omitted["evidence_sources"]) == len(draft["evidence_sources"]):
        raise ValueError(f"Requested omitted evidence id is absent: {omitted_id}")
    return omitted


def _compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": result["assessment"]["level"],
        "priority_score": result["assessment"]["priority_score"],
        "draft_admissible_for_review": result["draft_admissible_for_review"],
        "hard_stops": result["assessment"]["hard_stops"],
        "transport_eligible": result["graph"]["transport_eligible"],
        "independent_source_count": result["graph"]["independent_source_count"],
        "uncited_packet_source_ids": result["graph"]["uncited_packet_source_ids"],
    }


def _compact_high_and_admitted(result: dict[str, Any]) -> bool:
    return result["level"] == "HIGH" and result["draft_admissible_for_review"] is True


def _observed_factor_state(
    result: dict[str, Any], packet: dict[str, Any], registry: dict[str, Any]
) -> dict[str, bool]:
    """Expose factor-level gate attribution without trusting draft declarations."""
    replication_cohorts = list(
        dict.fromkeys(
            item["cohort_id"]
            for item in packet["evidence_items"]
            if item["evidence_kind"] in {"observational_association", "replication"}
        )
    )
    records = [registry["cohorts"][cohort_id] for cohort_id in replication_cohorts]
    fdr_by_cohort = result["canonical_card"]["cross_cohort_replication"]["fdr_by_cohort"]
    return {
        "transport_eligible": (
            len({record["measurement_level"] for record in records}) == 1
            and len({record["compartment"] for record in records}) == 1
            and all(record["same_measurement_replication_eligible"] is True for record in records)
        ),
        "source_independent": result["graph"]["independent_source_count"] >= 2,
        "all_replication_fdr_pass": bool(fdr_by_cohort) and all(
            fdr <= 0.05 for fdr in fdr_by_cohort.values()
        ),
        "perturbation_present": result["canonical_card"]["perturbation_support"]["tested"] is True,
        "confounding_controlled": (
            result["canonical_card"]["confounding_robustness"]["batch_controlled"] is True
            and result["canonical_card"]["confounding_robustness"]["composition_controlled"] is True
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir", type=Path, default=APP_ROOT / "data" / "synthetic_packets_v2"
    )
    parser.add_argument("--manifest-name", default="manifest_v2.json")
    parser.add_argument(
        "--cohort-registry",
        type=Path,
        default=APP_ROOT / "config" / "synthetic_benchmark_cohort_registry_v3.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "results" / "factorized_synthetic_suite_algorithm_sanity_v2.json",
    )
    args = parser.parse_args()
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    manifest = json.loads((args.suite_dir / args.manifest_name).read_text(encoding="utf-8"))
    omitted_id = manifest["omission_attack"]["omitted_evidence_id"]
    records = []
    for entry in load_suite(args.suite_dir, manifest_name=args.manifest_name):
        packet = entry["packet"]
        metadata = entry["manifest_entry"]
        errors = validate_packet(packet, registry)
        if errors:
            raise SystemExit(f"Invalid packet {packet['packet_id']}: {' | '.join(errors)}")
        draft = complete_draft_from_packet(packet)
        full = evaluate_with_evidence_graph(draft, packet, registry)
        transport_without_gate = evaluate_with_evidence_graph(
            draft, packet, registry, modules={"transport_aware_replication": False}
        )
        source_without_gate = evaluate_with_evidence_graph(
            draft, packet, registry, modules={"source_independence_audit": False}
        )
        fdr_without_gate = evaluate_with_evidence_graph(
            draft, packet, registry, modules={"all_cohort_fdr": False}
        )
        naive_counting_baseline = evaluate_with_evidence_graph(
            draft,
            packet,
            registry,
            modules={
                "provenance_coverage": False,
                "transport_aware_replication": False,
                "source_independence_audit": False,
                "all_cohort_fdr": False,
            },
        )
        omission_draft = _omit_source(draft, omitted_id)
        omission_full = evaluate_with_evidence_graph(omission_draft, packet, registry)
        omission_without_coverage = evaluate_with_evidence_graph(
            omission_draft, packet, registry, modules={"provenance_coverage": False}
        )
        expected_high = packet["reference_standard"]["eligible_for_high_priority"]
        expected_without_transport_gate = all(
            value
            for name, value in metadata["factors"].items()
            if name != "transport_eligible"
        )
        expected_without_source_gate = all(
            value
            for name, value in metadata["factors"].items()
            if name != "source_independent"
        )
        expected_without_fdr_gate = all(
            value
            for name, value in metadata["factors"].items()
            if name != "all_replication_fdr_pass"
        )
        # The comparator counts accession labels, trusts the first two FDRs,
        # and pools transport-mismatched cohorts. Literature and experiment
        # fields are fixed positive in every factorial packet, so only the
        # perturbation and confounding factors remain decisive.
        expected_naive_counting_high = (
            metadata["factors"]["perturbation_present"]
            and metadata["factors"]["confounding_controlled"]
        )
        observed_factors = _observed_factor_state(full, packet, registry)
        record = {
            "packet_id": packet["packet_id"],
            "factors": metadata["factors"],
            "llm_pilot_subset": metadata["llm_pilot_subset"],
            "expected_complete_draft_high_priority": expected_high,
            "observed_factor_state": observed_factors,
            "factor_derivation_matches": observed_factors == metadata["factors"],
            "complete_draft": _compact(full),
            "transport_gate_ablation": _compact(transport_without_gate),
            "source_independence_ablation": _compact(source_without_gate),
            "all_cohort_fdr_ablation": _compact(fdr_without_gate),
            "naive_counting_baseline": _compact(naive_counting_baseline),
            "omission_attack": {
                "omitted_evidence_id": omitted_id,
                "full_tracer": _compact(omission_full),
                "without_provenance_coverage": _compact(omission_without_coverage),
            },
            "complete_matches_expected": _high_and_admitted(full) == expected_high,
            "coverage_blocks_omission": not _high_and_admitted(omission_full),
            "coverage_ablation_matches_non_provenance_factors": (
                _high_and_admitted(omission_without_coverage) == expected_high
            ),
            "transport_ablation_matches_non_transport_factors": (
                _high_and_admitted(transport_without_gate) == expected_without_transport_gate
            ),
            "source_ablation_matches_non_source_factors": (
                _high_and_admitted(source_without_gate) == expected_without_source_gate
            ),
            "fdr_ablation_matches_non_fdr_factors": (
                _high_and_admitted(fdr_without_gate) == expected_without_fdr_gate
            ),
            "naive_counting_matches_predeclared_rule": (
                _high_and_admitted(naive_counting_baseline) == expected_naive_counting_high
            ),
        }
        records.append(record)
    output = {
        "schema": "icb-disambiguate-factorized-synthetic-suite-sanity-v2",
        "interpretation": (
            "Deterministic synthetic implementation verification only. It is not evidence of a "
            "biomedical mechanism, clinical utility, LLM performance, or population safety."
        ),
        "suite_id": manifest["suite_id"],
        "n_packets": len(records),
        "n_deterministic_draft_evaluations": len(records) * 3,
        "n_complete_matches_expected": sum(record["complete_matches_expected"] for record in records),
        "n_factor_derivations_matching_fixture": sum(
            record["factor_derivation_matches"] for record in records
        ),
        "n_omissions_blocked_by_coverage": sum(record["coverage_blocks_omission"] for record in records),
        "n_coverage_ablation_matches_non_provenance_factors": sum(
            record["coverage_ablation_matches_non_provenance_factors"] for record in records
        ),
        "n_transport_ablation_matches_non_transport_factors": sum(
            record["transport_ablation_matches_non_transport_factors"] for record in records
        ),
        "n_transport_gate_unsafe_high_counterfactuals": sum(
            not record["expected_complete_draft_high_priority"]
            and _compact_high_and_admitted(record["transport_gate_ablation"])
            for record in records
        ),
        "n_source_independence_ablation_matches_non_source_factors": sum(
            record["source_ablation_matches_non_source_factors"] for record in records
        ),
        "n_source_independence_gate_unsafe_high_counterfactuals": sum(
            not record["expected_complete_draft_high_priority"]
            and _compact_high_and_admitted(record["source_independence_ablation"])
            for record in records
        ),
        "n_all_cohort_fdr_ablation_matches_non_fdr_factors": sum(
            record["fdr_ablation_matches_non_fdr_factors"] for record in records
        ),
        "n_all_cohort_fdr_gate_unsafe_high_counterfactuals": sum(
            not record["expected_complete_draft_high_priority"]
            and _compact_high_and_admitted(record["all_cohort_fdr_ablation"])
            for record in records
        ),
        "n_naive_counting_matches_predeclared_rule": sum(
            record["naive_counting_matches_predeclared_rule"] for record in records
        ),
        "n_naive_counting_unsafe_high_counterfactuals": sum(
            not record["expected_complete_draft_high_priority"]
            and _compact_high_and_admitted(record["naive_counting_baseline"])
            for record in records
        ),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "saved": str(args.output),
                "n_packets": len(records),
                "n_complete_matches_expected": output["n_complete_matches_expected"],
                "n_omissions_blocked_by_coverage": output["n_omissions_blocked_by_coverage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
