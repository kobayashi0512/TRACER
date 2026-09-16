"""Evidence-graph backbone that derives confidence inputs from registered provenance.

The model draft is intentionally not trusted for replication, perturbation,
literature, modality, or confounding fields. Those fields are re-derived from
the frozen evidence packet and cohort registry before priority grading.
"""

from __future__ import annotations

import re
from typing import Any

from src.candidate_card import validate_card
from src.confidence import assess


CAUSAL_TERMS = re.compile(
    r"\b(causes?|drives?|mediates?|determines?|proves?|establishes?)\b|导致|驱动|介导|决定|证明",
    flags=re.IGNORECASE,
)

MODULE_DEFAULTS = {
    "provenance_coverage": True,
    "transport_aware_replication": True,
    "source_independence_audit": True,
    "all_cohort_fdr": True,
}


def _resolve_modules(modules: dict[str, bool] | None) -> dict[str, bool]:
    """Resolve an explicit ablation configuration without silently accepting typos."""
    if modules is None:
        return dict(MODULE_DEFAULTS)
    unknown = sorted(set(modules) - set(MODULE_DEFAULTS))
    if unknown:
        raise ValueError(f"Unknown TRACER module override(s): {', '.join(unknown)}.")
    resolved = dict(MODULE_DEFAULTS)
    for name, enabled in modules.items():
        if not isinstance(enabled, bool):
            raise ValueError(f"TRACER module {name} must be boolean.")
        resolved[name] = enabled
    return resolved


def _as_source_list(card: dict[str, Any]) -> list[dict[str, Any]]:
    sources = card.get("evidence_sources")
    return sources if isinstance(sources, list) else []


def _non_null_fdr_by_cohort(items: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for item in items:
        fdr = item.get("fdr")
        if isinstance(fdr, (int, float)) and not isinstance(fdr, bool):
            values.setdefault(item["cohort_id"], []).append(float(fdr))
    return {cohort_id: min(cohort_values) for cohort_id, cohort_values in values.items()}


def _has_causal_language(card: dict[str, Any]) -> bool:
    hypotheses = card.get("hypotheses")
    if not isinstance(hypotheses, list):
        return False
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, dict):
            continue
        for field in ("statement", "falsifiable_prediction"):
            value = hypothesis.get(field)
            if isinstance(value, str) and CAUSAL_TERMS.search(value):
                return True
    return False


def derive_canonical_card(
    card: dict[str, Any],
    packet: dict[str, Any],
    cohort_registry: dict[str, Any],
    *,
    modules: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Return an auditable re-derived card and graph diagnostics.

    The returned ``canonical_card`` is the only object passed to the existing
    priority grader. It cannot inherit a model's self-declared evidence counts.
    """
    enabled = _resolve_modules(modules)
    packet_items = packet.get("evidence_items") if isinstance(packet.get("evidence_items"), list) else []
    packet_by_id = {item.get("id"): item for item in packet_items if isinstance(item, dict)}
    registry = cohort_registry.get("cohorts", {})
    provenance_errors: list[str] = []
    matched_items: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()

    for source in _as_source_list(card):
        if not isinstance(source, dict):
            provenance_errors.append("Draft contains a non-object evidence source entry.")
            continue
        source_id = source.get("id") if isinstance(source, dict) else None
        if not isinstance(source_id, str) or source_id not in packet_by_id:
            provenance_errors.append(f"Draft cites evidence source not present in packet: {source_id!r}.")
            continue
        if source_id in seen_source_ids:
            provenance_errors.append(f"Draft cites the same evidence source more than once: {source_id}.")
            continue
        seen_source_ids.add(source_id)
        packet_item = packet_by_id[source_id]
        if source.get("identifier") != packet_item.get("source_identifier"):
            provenance_errors.append(f"Draft source identifier does not match frozen packet for {source_id}.")
            continue
        if packet_item.get("cohort_id") not in registry:
            provenance_errors.append(f"Frozen packet cohort is absent from registry: {packet_item.get('cohort_id')!r}.")
            continue
        matched_items.append(packet_item)

    if not matched_items:
        provenance_errors.append("No draft evidence source could be grounded to the frozen packet and cohort registry.")

    replication_items = [
        item for item in matched_items
        if item.get("evidence_kind") in {"observational_association", "replication"}
    ]
    analysis_items = [item for item in matched_items if item.get("evidence_kind") != "literature"]
    cohort_ids = list(dict.fromkeys(item["cohort_id"] for item in replication_items))
    cohort_records = [registry[cohort_id] for cohort_id in cohort_ids]
    measurement_levels = {record.get("measurement_level") for record in cohort_records}
    compartments = {record.get("compartment") for record in cohort_records}
    independence_groups = [record.get("source_independence_group") for record in cohort_records]
    registered_independence_audit_complete = all(
        isinstance(group, str) and group.strip() for group in independence_groups
    )
    if enabled["source_independence_audit"]:
        independence_audit_complete = registered_independence_audit_complete
        independent_source_count = (
            len(set(independence_groups)) if independence_audit_complete else 0
        )
    else:
        # Ablation comparator: accession labels are naively counted as independent.
        # This is never an admissible deployment configuration.
        independence_audit_complete = registered_independence_audit_complete
        independent_source_count = len(cohort_ids)
    baseline_eligible = bool(cohort_records) and all(
        record.get("baseline_ici_response_association_eligible") is True for record in cohort_records
    )
    if enabled["transport_aware_replication"]:
        same_measurement = (
            independent_source_count >= 2
            and len(measurement_levels) == 1
            and baseline_eligible
            and all(record.get("same_measurement_replication_eligible") is True for record in cohort_records)
        )
        same_compartment = independent_source_count >= 2 and len(compartments) == 1
    else:
        # Ablation: a transport-blind comparator pools registered baseline cohorts
        # as if their assay level and compartment were exchangeable.
        same_measurement = independent_source_count >= 2 and baseline_eligible
        same_compartment = independent_source_count >= 2 and baseline_eligible
    replication_direction_consistent = bool(replication_items) and all(
        item.get("direction_status") == "consistent" for item in replication_items
    )
    analysis_direction_consistent = bool(analysis_items) and all(
        item.get("direction_status") == "consistent" for item in analysis_items
    )
    audited_fdr_by_cohort = _non_null_fdr_by_cohort(replication_items)
    # In the comparator, the legacy two-slot representation remains but a
    # third or later cohort is not passed to the priority grader.
    fdr_by_cohort = audited_fdr_by_cohort if enabled["all_cohort_fdr"] else None
    replication_fdrs = [audited_fdr_by_cohort.get(cohort_id) for cohort_id in cohort_ids]
    discovery_fdr = replication_fdrs[0] if replication_fdrs else None
    validation_fdr = replication_fdrs[1] if len(replication_fdrs) > 1 else None

    perturbation_items = [
        item for item in matched_items
        if item.get("evidence_kind") == "perturbation" and item.get("direction_status") == "consistent"
    ]
    literature_items = [
        item for item in matched_items
        if item.get("evidence_kind") == "literature" and item.get("direction_status") == "consistent"
    ]
    analysis_measurement_levels = {
        registry[item["cohort_id"]].get("measurement_level") for item in analysis_items
    }
    modalities = len(analysis_measurement_levels)
    canonical_card = {
        "candidate_id": card.get("candidate_id", "UNSPECIFIED"),
        "cross_cohort_replication": {
            "independent_cohorts": independent_source_count,
            "cohort_ids": cohort_ids,
            "effect_direction_consistent": replication_direction_consistent,
            "same_biological_compartment": same_compartment,
            "same_measurement_level": same_measurement,
            "discovery_fdr": discovery_fdr,
            "validation_fdr": validation_fdr,
            "fdr_by_cohort": fdr_by_cohort,
        },
        "perturbation_support": {
            "tested": bool(perturbation_items),
            "direction_consistent": bool(perturbation_items),
            "independent_studies": len({item["source_identifier"] for item in perturbation_items}),
        },
        "orthogonal_evidence": {
            "modalities": modalities,
            "direction_consistent": analysis_direction_consistent,
        },
        "curated_literature_evidence": {
            "independent_sources": len({item["source_identifier"] for item in literature_items}),
            "supports_claim": bool(literature_items),
        },
        "confounding_robustness": {
            "batch_controlled": bool(analysis_items) and all(item.get("confounding_assessed") is True for item in analysis_items),
            "composition_controlled": bool(analysis_items) and all(item.get("confounding_assessed") is True for item in analysis_items),
        },
        "discriminating_experiment": card.get("discriminating_experiment", {}),
    }
    return {
        "canonical_card": canonical_card,
        "graph": {
            "grounded_source_count": len(matched_items),
            "replication_source_count": len(replication_items),
            "packet_source_count": len(packet_items),
            "cohort_ids": cohort_ids,
            "source_independence_groups": independence_groups,
            "independence_audit_complete": independence_audit_complete,
            "independent_source_count": independent_source_count,
            "measurement_levels": sorted(str(level) for level in measurement_levels),
            "compartments": sorted(str(compartment) for compartment in compartments),
            "baseline_response_eligible": baseline_eligible,
            "modules": enabled,
            "transport_eligible": same_measurement and same_compartment,
            "provenance_errors": provenance_errors,
            "uncited_packet_source_ids": sorted(
                source_id for source_id in packet_by_id if source_id not in seen_source_ids
            ),
            "draft_causal_language_detected": _has_causal_language(card),
        },
    }


def evaluate_with_evidence_graph(
    card: dict[str, Any],
    packet: dict[str, Any],
    cohort_registry: dict[str, Any],
    *,
    modules: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Grade a model draft using provenance-derived rather than self-declared evidence."""
    enabled = _resolve_modules(modules)
    derived = derive_canonical_card(card, packet, cohort_registry, modules=enabled)
    structural_errors, _ = validate_card(card, cohort_registry=cohort_registry)
    assessment = assess(derived["canonical_card"]).as_dict()
    hard_stops = list(assessment["hard_stops"])
    graph = derived["graph"]
    if graph["provenance_errors"]:
        hard_stops.append("Frozen-evidence provenance check failed; the draft cannot be prioritized.")
    if enabled["provenance_coverage"] and graph["uncited_packet_source_ids"]:
        hard_stops.append("Draft omitted one or more frozen evidence items and cannot selectively claim support.")
    if graph["draft_causal_language_detected"] and not assessment["causal_language_permitted"]:
        hard_stops.append("Draft contains causal language without provenance-derived perturbation support.")
    rejection_reasons = [*structural_errors, *graph["provenance_errors"]]
    if enabled["provenance_coverage"] and graph["uncited_packet_source_ids"]:
        rejection_reasons.append(
            "Draft omitted one or more frozen evidence items and cannot selectively claim support."
        )
    draft_admissible_for_review = not rejection_reasons
    assessment["hard_stops"] = hard_stops
    assessment["level"] = (
        "LOW"
        if graph["provenance_errors"]
        or (enabled["provenance_coverage"] and graph["uncited_packet_source_ids"])
        else assessment["level"]
    )
    assessment["ready_for_validation"] = assessment["level"] == "HIGH" and assessment["ready_for_validation"]
    assessment["causal_language_permitted"] = (
        assessment["causal_language_permitted"]
        and draft_admissible_for_review
    )
    assessment["ready_for_validation"] = assessment["ready_for_validation"] and draft_admissible_for_review
    assessment["operational_decision"] = (
        "ADMIT_FOR_HUMAN_REVIEW" if draft_admissible_for_review else "REJECT_DRAFT"
    )
    assessment["interpretation"] = (
        "Evidence-graph-derived research priority, not a causal probability, clinical prediction, or treatment recommendation."
    )
    return {
        "assessment": assessment,
        "canonical_card": derived["canonical_card"],
        "graph": graph,
        "draft_admissible_for_review": draft_admissible_for_review,
        "draft_rejection_reasons": rejection_reasons,
    }
