#!/usr/bin/env python3
"""Build real hard-negative packets with one scRNA discovery and two bulk checks.

The packet construction deliberately makes a tempting but invalid argument:
multiple response-associated cohorts are present, yet neither bulk cohort can
replicate a single-cell cell-state claim at the same measurement level or
compartment.  Every packet belongs to one source-dependence cluster.
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


CLUSTER = "GSE120575_GSE91061_GSE78220_positive_control_panel_v2"


def read_tsv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["feature"]: row for row in csv.DictReader(handle, delimiter="\t")}


def as_float(row: dict[str, str], field: str) -> float:
    return float(row[field])


def direction_status(row: dict[str, str]) -> str:
    return "consistent" if row["direction_matches_positive_control"] == "True" else "mixed"


def build_packet(
    feature: str,
    discovery: dict[str, str],
    gse91061: dict[str, str],
    gse78220: dict[str, str],
) -> dict:
    expected = discovery["expected_higher_group"]
    return {
        "packet_id": f"REAL-TRANSPORT-{feature.replace(':', '-').upper()}",
        "packet_role": "real_data_multi_cohort_transport_hard_negative",
        "dependency_cluster": CLUSTER,
        "scope": {
            "disease": "Melanoma",
            "treatment": "Pre-treatment anti-PD-1 monotherapy across audited cohorts",
            "analysis_unit": "Discovery lesion-level single-cell summary plus two independent bulk-RNA sample summaries",
        },
        "question": (
            f"Do the observed {feature} directions across one single-cell discovery and two bulk "
            "response cohorts establish a replicated cell-state mechanism of anti-PD-1 response?"
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
                "direction_status": direction_status(discovery),
                "confounding_assessed": False,
                "fdr": as_float(discovery, "panel_bh_q"),
            },
            {
                "id": "gse91061-bulk-direction-check",
                "cohort_id": "GSE91061",
                "result_type": "pre_treatment_bulk_rna_direction_check",
                "statement": (
                    f"For {feature}, GSE91061 bulk RNA observed {gse91061['observed_higher_group']} versus "
                    f"the pre-specified expected group {expected} (panel BH q={gse91061['panel_bh_q']})."
                ),
                "effect_direction": gse91061["observed_higher_group"],
                "source_identifier": f"results/gse91061_positive_control_direction_check_v1.tsv#feature={feature}",
                "evidence_kind": "observational_association",
                "direction_status": direction_status(gse91061),
                "confounding_assessed": False,
                "fdr": as_float(gse91061, "panel_bh_q"),
            },
            {
                "id": "gse78220-bulk-direction-check",
                "cohort_id": "GSE78220",
                "result_type": "pre_treatment_bulk_rna_direction_check",
                "statement": (
                    f"For {feature}, GSE78220 bulk RNA observed {gse78220['observed_higher_group']} versus "
                    f"the pre-specified expected group {expected} (panel BH q={gse78220['panel_bh_q']})."
                ),
                "effect_direction": gse78220["observed_higher_group"],
                "source_identifier": f"results/gse78220_positive_control_direction_check_v1.tsv#feature={feature}",
                "evidence_kind": "observational_association",
                "direction_status": direction_status(gse78220),
                "confounding_assessed": False,
                "fdr": as_float(gse78220, "panel_bh_q"),
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
                "single_cell_to_bulk_transport_gap",
                "no_direction_consistent_perturbation",
                "cell_composition_not_controlled",
                "shared_positive_control_dependency_cluster",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--discovery-tsv", type=Path, default=APP_ROOT / "results" / "positive_control_screen_v1.tsv"
    )
    parser.add_argument(
        "--gse91061-tsv",
        type=Path,
        default=APP_ROOT / "results" / "gse91061_positive_control_direction_check_v1.tsv",
    )
    parser.add_argument(
        "--gse78220-tsv",
        type=Path,
        default=APP_ROOT / "results" / "gse78220_positive_control_direction_check_v1.tsv",
    )
    parser.add_argument(
        "--cohort-registry", type=Path, default=APP_ROOT / "config" / "cohort_registry_v2.json"
    )
    parser.add_argument("--output-dir", type=Path, default=APP_ROOT / "data" / "real_control_packets_v2")
    args = parser.parse_args()

    discovery = read_tsv(args.discovery_tsv)
    gse91061 = read_tsv(args.gse91061_tsv)
    gse78220 = read_tsv(args.gse78220_tsv)
    common_features = sorted(set(discovery) & set(gse91061) & set(gse78220))
    if not common_features or any(
        set(table) != set(common_features) for table in (discovery, gse91061, gse78220)
    ):
        raise SystemExit("All three frozen positive-control files must contain exactly the same feature set.")
    registry = json.loads(args.cohort_registry.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for feature in common_features:
        packet = build_packet(feature, discovery[feature], gse91061[feature], gse78220[feature])
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
                "dependency_cluster": CLUSTER,
                "role": packet["packet_role"],
            }
        )
    manifest = {
        "suite_id": "real-multicohort-transport-hard-negative-suite-v2",
        "purpose": (
            "Real-data hard-negative suite for testing that multiple bulk direction checks do not "
            "become a same-measurement single-cell replication claim."
        ),
        "statistical_unit": "The entire dependency cluster, not individual feature packets or model traces.",
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
