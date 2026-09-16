"""Synthetic stress-test helpers for TRACER algorithm verification only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evidence_graph import evaluate_with_evidence_graph
from src.evidence_packet import validate_packet


def complete_draft_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Create a deliberately complete, non-LLM draft for algorithm sanity checks."""
    items = packet["evidence_items"]
    replication_cohorts = list(
        dict.fromkeys(
            item["cohort_id"]
            for item in items
            if item["evidence_kind"] in {"observational_association", "replication"}
        )
    )
    return {
        "candidate_id": f"COMPLETE-DRAFT-{packet['packet_id']}",
        "scope": packet["scope"],
        "hypotheses": [
            {
                "id": "A",
                "statement": "The observed association primarily reflects a composition-dependent signal.",
                "falsifiable_prediction": "The association attenuates after a pre-specified composition-aware analysis.",
            },
            {
                "id": "B",
                "statement": "The observed association persists within a pre-specified immune state.",
                "falsifiable_prediction": "The association remains directionally consistent within that immune state.",
            },
        ],
        "evidence_sources": [
            {
                "id": item["id"],
                "source_type": item["result_type"],
                "identifier": item["source_identifier"],
                "supports_or_refutes": (
                    "supports" if item["direction_status"] == "consistent" else "mixed"
                ),
            }
            for item in items
        ],
        # These declarations are intentionally conservative and are ignored by TRACER.
        "cross_cohort_replication": {
            "independent_cohorts": len(replication_cohorts),
            "cohort_ids": replication_cohorts,
            "effect_direction_consistent": False,
            "same_biological_compartment": False,
            "same_measurement_level": False,
            "discovery_fdr": None,
            "validation_fdr": None,
        },
        "perturbation_support": {
            "tested": False,
            "direction_consistent": False,
            "independent_studies": 0,
        },
        "orthogonal_evidence": {"modalities": 0, "direction_consistent": False},
        "curated_literature_evidence": {"independent_sources": 0, "supports_claim": False},
        "confounding_robustness": {"batch_controlled": False, "composition_controlled": False},
        "discriminating_experiment": {
            "intervention": "Pre-specified composition-aware reanalysis followed by a matched functional perturbation",
            "comparator": "Composition-dependent versus within-state persistence models",
            "readout": "Direction and magnitude of the lesion-level signal",
            "prediction_if_hypothesis_a": "The signal attenuates after composition-aware reanalysis.",
            "prediction_if_hypothesis_b": "The signal persists within the pre-specified immune state.",
        },
    }


def load_suite(
    suite_dir: Path, *, manifest_name: str = "manifest_v1.json"
) -> list[dict[str, Any]]:
    """Load one explicitly named frozen synthetic-suite manifest.

    The manifest name is an argument rather than an auto-detected file so that
    historical v1 results remain reproducible when later stress suites live in
    the same project.
    """
    manifest = json.loads((suite_dir / manifest_name).read_text(encoding="utf-8"))
    packets = []
    for entry in manifest["packets"]:
        packet_path = suite_dir / entry["file"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packets.append({"manifest_entry": entry, "path": packet_path, "packet": packet})
    return packets


def evaluate_complete_suite(
    suite_dir: Path,
    registry: dict[str, Any],
    *,
    manifest_name: str = "manifest_v1.json",
) -> list[dict[str, Any]]:
    """Check full TRACER against evaluator-only synthetic eligibility labels."""
    results = []
    for entry in load_suite(suite_dir, manifest_name=manifest_name):
        packet = entry["packet"]
        packet_errors = validate_packet(packet, registry)
        if packet_errors:
            raise ValueError(f"Invalid synthetic packet {packet.get('packet_id')}: {' | '.join(packet_errors)}")
        evaluated = evaluate_with_evidence_graph(complete_draft_from_packet(packet), packet, registry)
        expected_high = packet["reference_standard"]["eligible_for_high_priority"]
        observed_high = evaluated["assessment"]["level"] == "HIGH"
        results.append(
            {
                "packet_id": packet["packet_id"],
                "category": entry["manifest_entry"]["category"],
                "expected_high_priority": expected_high,
                "observed_level": evaluated["assessment"]["level"],
                "matches_expected_high_priority": observed_high == expected_high,
                "draft_admissible_for_review": evaluated["draft_admissible_for_review"],
                "hard_stops": evaluated["assessment"]["hard_stops"],
            }
        )
    return results
