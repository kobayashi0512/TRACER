#!/usr/bin/env python3
"""Build auditable real-data hard-negative packets from frozen positive controls.

All generated packets share the same GSE120575/GSE91061 sources and are marked
as one dependency cluster. They test evidence-governance behavior only; they do
not create 15 independent biomedical validations or mechanism discoveries.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import validate_packet  # noqa: E402


def _read_tsv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["feature"]: row for row in csv.DictReader(handle, delimiter="\t")}


def _as_float(row: dict[str, str], field: str) -> float:
    return float(row[field])


def _status(row: dict[str, str]) -> str:
    return "consistent" if row["direction_matches_positive_control"] == "True" else "mixed"


def _packet(feature: str, discovery: dict[str, str], external: dict[str, str]) -> dict:
    expected = discovery["expected_higher_group"]
    observed_external = external["observed_higher_group"]
    return {
        "packet_id": f"REAL-CONTROL-{feature.replace(':', '-').upper()}",
        "packet_role": "real_data_hard_negative",
        "dependency_cluster": "GSE120575_GSE91061_positive_control_panel_v1",
        "scope": {
            "disease": "Melanoma",
            "treatment": "Pre-treatment anti-PD-1 monotherapy / nivolumab direction check",
            "analysis_unit": "Lesion-level single-cell pseudo-bulk and independent bulk-RNA sample summary",
        },
        "question": (
            f"Does the observed {feature} responder/non-responder association establish a cell-state "
            "mechanism of anti-PD-1 response?"
        ),
        "evidence_items": [
            {
                "id": "gse120575-discovery",
                "cohort_id": "GSE120575",
                "result_type": "lesion_level_single_cell_pseudobulk_positive_control",
                "statement": (
                    f"For {feature}, responder minus non-responder was {discovery['responder_minus_non_responder']} "
                    f"and the observed higher group was {discovery['observed_higher_group']} "
                    f"(pre-specified expected group: {expected}; panel BH q={discovery['panel_bh_q']})."
                ),
                "effect_direction": discovery["observed_higher_group"],
                "source_identifier": f"results/positive_control_screen_v1.tsv#feature={feature}",
                "evidence_kind": "observational_association",
                "direction_status": _status(discovery),
                "confounding_assessed": False,
                "fdr": _as_float(discovery, "panel_bh_q"),
            },
            {
                "id": "gse91061-bulk-direction-check",
                "cohort_id": "GSE91061",
                "result_type": "pre_treatment_bulk_rna_direction_check",
                "statement": (
                    f"For {feature}, the bulk-RNA direction check observed {observed_external} versus the "
                    f"pre-specified expected group {expected} (panel BH q={external['panel_bh_q']})."
                ),
                "effect_direction": observed_external,
                "source_identifier": f"results/gse91061_positive_control_direction_check_v1.tsv#feature={feature}",
                "evidence_kind": "observational_association",
                "direction_status": _status(external),
                "confounding_assessed": False,
                "fdr": _as_float(external, "panel_bh_q"),
            },
        ],
        "reference_standard": {
            "evaluator_only": True,
            "eligible_for_high_priority": False,
            "prohibited_claim_types": [
                "causal cell-state mechanism",
                "same-measurement external replication",
                "clinical treatment recommendation",
            ],
            "reason_codes": [
                "shared_positive_control_dependency_cluster",
                "cross_modality_cross_compartment_transport_gap",
                "no_direction_consistent_perturbation",
                "cell_composition_not_controlled",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--discovery-tsv", type=Path, default=APP_ROOT / "results" / "positive_control_screen_v1.tsv"
    )
    parser.add_argument(
        "--external-tsv",
        type=Path,
        default=APP_ROOT / "results" / "gse91061_positive_control_direction_check_v1.tsv",
    )
    parser.add_argument(
        "--cohort-registry", type=Path, default=APP_ROOT / "config" / "cohort_registry_v2.json"
    )
    parser.add_argument("--output-dir", type=Path, default=APP_ROOT / "data" / "real_control_packets_v1")
    args = parser.parse_args()
    discovery_rows = _read_tsv(args.discovery_tsv)
    external_rows = _read_tsv(args.external_tsv)
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    shared = sorted(set(discovery_rows) & set(external_rows))
    if len(shared) != len(discovery_rows) or len(shared) != len(external_rows):
        raise SystemExit("Discovery and external positive-control feature sets do not match exactly.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for feature in shared:
        packet = _packet(feature, discovery_rows[feature], external_rows[feature])
        errors = validate_packet(packet, registry)
        if errors:
            raise SystemExit(f"Generated invalid packet {packet['packet_id']}: {' | '.join(errors)}")
        filename = f"{packet['packet_id']}.json"
        (args.output_dir / filename).write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest_entries.append(
            {
                "packet_id": packet["packet_id"],
                "file": filename,
                "feature": feature,
                "dependency_cluster": packet["dependency_cluster"],
                "role": packet["packet_role"],
            }
        )
    manifest = {
        "suite_id": "real-positive-control-hard-negative-suite-v1",
        "purpose": (
            "Auditable real-data hard-negative suite for evidence-governance testing. "
            "All entries share a source panel and are not statistically independent."
        ),
        "statistical_unit": "The entire dependency cluster, not individual feature packets.",
        "packets": manifest_entries,
    }
    (args.output_dir / "manifest_v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "saved_directory": str(args.output_dir),
                "n_packets": len(manifest_entries),
                "dependency_clusters": 1,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
