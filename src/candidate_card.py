"""Structural validation for LLM-generated ICB-Disambiguate candidate cards."""

from __future__ import annotations

from typing import Any

from src.confidence import Assessment, assess


REQUIRED_TOP_LEVEL = {
    "candidate_id",
    "scope",
    "hypotheses",
    "evidence_sources",
    "cross_cohort_replication",
    "perturbation_support",
    "orthogonal_evidence",
    "curated_literature_evidence",
    "confounding_robustness",
    "discriminating_experiment",
}
SCOPE_FIELDS = {"disease", "treatment", "analysis_unit"}
HYPOTHESIS_FIELDS = {"id", "statement", "falsifiable_prediction"}
SOURCE_FIELDS = {"id", "source_type", "identifier", "supports_or_refutes"}
EXPERIMENT_FIELDS = {
    "intervention",
    "comparator",
    "readout",
    "prediction_if_hypothesis_a",
    "prediction_if_hypothesis_b",
}
REPLICATION_FIELDS = {
    "independent_cohorts",
    "cohort_ids",
    "effect_direction_consistent",
    "same_biological_compartment",
    "same_measurement_level",
    "discovery_fdr",
    "validation_fdr",
}
SCORING_SECTION_FIELDS = {
    "perturbation_support": {"tested", "direction_consistent", "independent_studies"},
    "orthogonal_evidence": {"modalities", "direction_consistent"},
    "curated_literature_evidence": {"independent_sources", "supports_claim"},
    "confounding_robustness": {"batch_controlled", "composition_controlled"},
}


def _missing_fields(value: Any, expected: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return sorted(expected)
    return sorted(field for field in expected if not isinstance(value.get(field), str) or not value[field].strip())


def _validate_replication(
    card: dict[str, Any], cohort_registry: dict[str, Any] | None
) -> list[str]:
    """Check cardinality and, when supplied, eligibility against a frozen registry."""
    errors: list[str] = []
    replication = card.get("cross_cohort_replication")
    if not isinstance(replication, dict):
        return ["cross_cohort_replication must be an object."]
    missing = sorted(REPLICATION_FIELDS - set(replication))
    if missing:
        return [f"cross_cohort_replication lacks: {', '.join(missing)}."]

    cohort_ids = replication.get("cohort_ids")
    independent_cohorts = replication.get("independent_cohorts")
    if not isinstance(cohort_ids, list) or not all(isinstance(value, str) and value.strip() for value in cohort_ids):
        errors.append("cross_cohort_replication.cohort_ids must be a non-empty list of strings.")
        return errors
    if len(set(cohort_ids)) != len(cohort_ids):
        errors.append("cross_cohort_replication.cohort_ids must be unique.")
    if not isinstance(independent_cohorts, int) or independent_cohorts < 0:
        errors.append("cross_cohort_replication.independent_cohorts must be a non-negative integer.")
    elif independent_cohorts != len(cohort_ids):
        errors.append("cross_cohort_replication.independent_cohorts must equal the number of cohort_ids.")

    if cohort_registry is None:
        return errors
    registered = cohort_registry.get("cohorts", {})
    unknown = sorted(cohort_id for cohort_id in cohort_ids if cohort_id not in registered)
    if unknown:
        errors.append(f"Cohort ids are absent from the frozen registry: {', '.join(unknown)}.")
        return errors

    records = [registered[cohort_id] for cohort_id in cohort_ids]
    claims_same_measurement = replication.get("same_measurement_level") is True
    claims_same_compartment = replication.get("same_biological_compartment") is True
    claims_replication = replication.get("effect_direction_consistent") is True or claims_same_measurement or claims_same_compartment
    if claims_replication:
        ineligible = [
            cohort_id
            for cohort_id, record in zip(cohort_ids, records)
            if record.get("baseline_ici_response_association_eligible") is not True
        ]
        if ineligible:
            errors.append(
                "Cohorts lack audited baseline ICI-response eligibility and cannot support a replication claim: "
                + ", ".join(ineligible)
                + "."
            )
        independence_groups = [record.get("source_independence_group") for record in records]
        if not all(isinstance(group, str) and group.strip() for group in independence_groups):
            errors.append(
                "Cohort source-independence audit is incomplete; a replication claim is not permitted."
            )
        elif len(set(independence_groups)) < 2:
            errors.append(
                "Cohorts share one audited source-independence group and cannot support a replication claim."
            )

    if claims_same_measurement:
        levels = {record.get("measurement_level") for record in records}
        disallowed = [
            cohort_id
            for cohort_id, record in zip(cohort_ids, records)
            if record.get("same_measurement_replication_eligible") is not True
        ]
        if len(levels) != 1 or disallowed:
            errors.append(
                "same_measurement_level cannot be claimed for these registered cohorts."
            )

    if claims_same_compartment:
        compartments = {record.get("compartment") for record in records}
        if len(compartments) != 1:
            errors.append(
                "same_biological_compartment cannot be claimed for these registered cohorts."
            )
    return errors


def _validate_scoring_sections(card: dict[str, Any]) -> list[str]:
    """Reject malformed evidence fields before the deterministic grader reads them."""
    errors: list[str] = []
    for section, required_fields in SCORING_SECTION_FIELDS.items():
        value = card.get(section)
        if not isinstance(value, dict):
            errors.append(f"{section} must be an object.")
            continue
        missing = sorted(required_fields - set(value))
        if missing:
            errors.append(f"{section} lacks: {', '.join(missing)}.")

    perturbation = card.get("perturbation_support")
    if isinstance(perturbation, dict):
        for field in ("tested", "direction_consistent"):
            if field in perturbation and not isinstance(perturbation[field], bool):
                errors.append(f"perturbation_support.{field} must be boolean.")
        if "independent_studies" in perturbation and (
            not isinstance(perturbation["independent_studies"], int)
            or isinstance(perturbation["independent_studies"], bool)
            or perturbation["independent_studies"] < 0
        ):
            errors.append("perturbation_support.independent_studies must be a non-negative integer.")

    for section, integer_field in (
        ("orthogonal_evidence", "modalities"),
        ("curated_literature_evidence", "independent_sources"),
    ):
        value = card.get(section)
        if isinstance(value, dict):
            if "direction_consistent" in value and section == "orthogonal_evidence" and not isinstance(value["direction_consistent"], bool):
                errors.append("orthogonal_evidence.direction_consistent must be boolean.")
            if "supports_claim" in value and section == "curated_literature_evidence" and not isinstance(value["supports_claim"], bool):
                errors.append("curated_literature_evidence.supports_claim must be boolean.")
            if integer_field in value and (
                not isinstance(value[integer_field], int)
                or isinstance(value[integer_field], bool)
                or value[integer_field] < 0
            ):
                errors.append(f"{section}.{integer_field} must be a non-negative integer.")

    confounding = card.get("confounding_robustness")
    if isinstance(confounding, dict):
        for field in ("batch_controlled", "composition_controlled"):
            if field in confounding and not isinstance(confounding[field], bool):
                errors.append(f"confounding_robustness.{field} must be boolean.")
    return errors


def validate_card(
    card: dict[str, Any], cohort_registry: dict[str, Any] | None = None
) -> tuple[list[str], Assessment | None]:
    """Return structural errors and deterministic priority assessment.

    The LLM's narrative is not trusted. This function validates the minimum
    schema needed for a reviewer to inspect provenance, alternatives, and an
    experiment capable of discriminating them.
    """
    errors: list[str] = []
    missing_top = sorted(REQUIRED_TOP_LEVEL - set(card))
    if missing_top:
        errors.append(f"Missing required top-level fields: {', '.join(missing_top)}.")

    missing_scope = _missing_fields(card.get("scope"), SCOPE_FIELDS)
    if missing_scope:
        errors.append(f"Scope lacks: {', '.join(missing_scope)}.")

    hypotheses = card.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        errors.append("At least two competing hypotheses are required.")
    else:
        hypothesis_ids = []
        for index, hypothesis in enumerate(hypotheses, start=1):
            missing = _missing_fields(hypothesis, HYPOTHESIS_FIELDS)
            if missing:
                errors.append(f"Hypothesis {index} lacks: {', '.join(missing)}.")
            elif hypothesis["id"] in hypothesis_ids:
                errors.append(f"Duplicate hypothesis id: {hypothesis['id']}.")
            else:
                hypothesis_ids.append(hypothesis["id"])

    sources = card.get("evidence_sources")
    if not isinstance(sources, list) or not sources:
        errors.append("At least one evidence source is required.")
    else:
        source_ids = []
        for index, source in enumerate(sources, start=1):
            missing = _missing_fields(source, SOURCE_FIELDS)
            if missing:
                errors.append(f"Evidence source {index} lacks: {', '.join(missing)}.")
            elif source["supports_or_refutes"] not in {"supports", "refutes", "mixed", "context_only"}:
                errors.append(f"Evidence source {index} has invalid supports_or_refutes value.")
            elif source["id"] in source_ids:
                errors.append(f"Duplicate evidence source id: {source['id']}.")
            else:
                source_ids.append(source["id"])

    errors.extend(_validate_replication(card, cohort_registry))
    errors.extend(_validate_scoring_sections(card))

    experiment = card.get("discriminating_experiment")
    missing_experiment = _missing_fields(experiment, EXPERIMENT_FIELDS)
    if missing_experiment:
        errors.append(f"Discriminating experiment lacks: {', '.join(missing_experiment)}.")
    elif experiment["prediction_if_hypothesis_a"] == experiment["prediction_if_hypothesis_b"]:
        errors.append("Discriminating experiment must specify different predictions for the two hypotheses.")

    if errors:
        return errors, None
    return [], assess(card)
