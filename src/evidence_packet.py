"""Validate and render blinded evidence packets for LLM confidence evaluation."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_LEVEL = {"packet_id", "scope", "question", "evidence_items", "reference_standard"}
SCOPE_FIELDS = {"disease", "treatment", "analysis_unit"}
EVIDENCE_ITEM_FIELDS = {
    "id",
    "cohort_id",
    "result_type",
    "statement",
    "effect_direction",
    "source_identifier",
    "evidence_kind",
    "direction_status",
    "confounding_assessed",
    "fdr",
}
EVIDENCE_ITEM_STRING_FIELDS = {
    "id",
    "cohort_id",
    "result_type",
    "statement",
    "effect_direction",
    "source_identifier",
    "evidence_kind",
    "direction_status",
}
REFERENCE_STANDARD_FIELDS = {
    "evaluator_only",
    "eligible_for_high_priority",
    "prohibited_claim_types",
    "reason_codes",
}
MODEL_VISIBLE_FIELDS = ("packet_id", "scope", "question", "evidence_items")
EVIDENCE_KINDS = {"observational_association", "replication", "perturbation", "literature"}
DIRECTION_STATUSES = {"consistent", "mixed", "opposite", "unknown", "not_applicable"}


def _missing_nonempty_strings(value: Any, fields: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return sorted(fields)
    return sorted(
        field
        for field in fields
        if not isinstance(value.get(field), str) or not value[field].strip()
    )


def validate_packet(packet: dict[str, Any], cohort_registry: dict[str, Any]) -> list[str]:
    """Return errors. A packet cannot refer to an unregistered data cohort."""
    errors: list[str] = []
    missing_top = sorted(REQUIRED_TOP_LEVEL - set(packet))
    if missing_top:
        errors.append(f"Missing required top-level fields: {', '.join(missing_top)}.")

    missing_scope = _missing_nonempty_strings(packet.get("scope"), SCOPE_FIELDS)
    if missing_scope:
        errors.append(f"Scope lacks: {', '.join(missing_scope)}.")

    if not isinstance(packet.get("question"), str) or not packet["question"].strip():
        errors.append("Question must be a non-empty string.")

    items = packet.get("evidence_items")
    registry_cohorts = cohort_registry.get("cohorts", {})
    if not isinstance(items, list) or not items:
        errors.append("At least one evidence item is required.")
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(items, start=1):
            missing = _missing_nonempty_strings(item, EVIDENCE_ITEM_STRING_FIELDS)
            if isinstance(item, dict):
                missing.extend(sorted(field for field in EVIDENCE_ITEM_FIELDS - set(item) if field not in missing))
            if missing:
                errors.append(f"Evidence item {index} lacks: {', '.join(missing)}.")
                continue
            if item["id"] in seen_ids:
                errors.append(f"Duplicate evidence item id: {item['id']}.")
            seen_ids.add(item["id"])
            if item["cohort_id"] not in registry_cohorts:
                errors.append(
                    f"Evidence item {index} references unregistered cohort: {item['cohort_id']}."
                )
            if item["evidence_kind"] not in EVIDENCE_KINDS:
                errors.append(f"Evidence item {index} has invalid evidence_kind.")
            if item["direction_status"] not in DIRECTION_STATUSES:
                errors.append(f"Evidence item {index} has invalid direction_status.")
            if not isinstance(item["confounding_assessed"], bool):
                errors.append(f"Evidence item {index} confounding_assessed must be boolean.")
            fdr = item["fdr"]
            if fdr is not None and (
                not isinstance(fdr, (int, float))
                or isinstance(fdr, bool)
                or not 0 <= fdr <= 1
            ):
                errors.append(f"Evidence item {index} fdr must be a number in [0, 1] or null.")

    reference = packet.get("reference_standard")
    if not isinstance(reference, dict):
        errors.append("reference_standard must be an object.")
    else:
        missing_reference = sorted(REFERENCE_STANDARD_FIELDS - set(reference))
        if missing_reference:
            errors.append(f"reference_standard lacks: {', '.join(missing_reference)}.")
        elif reference.get("evaluator_only") is not True:
            errors.append("reference_standard.evaluator_only must be true to prevent label leakage.")
        for field in ("prohibited_claim_types", "reason_codes"):
            if not isinstance(reference.get(field), list) or not all(
                isinstance(value, str) and value.strip() for value in reference[field]
            ):
                errors.append(f"reference_standard.{field} must be a list of non-empty strings.")
    return errors


def render_model_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return the only fields permitted in an LLM prompt; omit evaluator labels."""
    return {field: packet[field] for field in MODEL_VISIBLE_FIELDS if field in packet}
