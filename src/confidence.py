"""Deterministic evidence grading for ICB-Disambiguate candidate cards.

The output is a research-priority assessment, not a probability of causality,
clinical benefit, or treatment response. All inputs must be independently
audited before use with real evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


WEIGHTS = {
    "cross_cohort_replication": 0.25,
    "perturbation_support": 0.30,
    "orthogonal_evidence": 0.15,
    "curated_literature_evidence": 0.10,
    "confounding_robustness": 0.10,
    "discriminating_experiment": 0.10,
}


@dataclass(frozen=True)
class Assessment:
    candidate_id: str
    priority_score: float
    level: str
    ready_for_validation: bool
    causal_language_permitted: bool
    reasons: list[str]
    hard_stops: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "priority_score": self.priority_score,
            "level": self.level,
            "ready_for_validation": self.ready_for_validation,
            "causal_language_permitted": self.causal_language_permitted,
            "reasons": self.reasons,
            "hard_stops": self.hard_stops,
            "interpretation": (
                "Research-priority evidence assessment only; it is not a causal "
                "probability, clinical prediction, or treatment recommendation."
            ),
        }


EXPERIMENT_FIELDS = {
    "intervention",
    "comparator",
    "readout",
    "prediction_if_hypothesis_a",
    "prediction_if_hypothesis_b",
}


def _complete_experiment(experiment: dict[str, Any]) -> bool:
    return all(isinstance(experiment.get(field), str) and experiment[field].strip() for field in EXPERIMENT_FIELDS)


def _fdr_passes(value: Any) -> bool:
    return isinstance(value, (int, float)) and 0 <= value <= 0.05


def _replication_fdrs_pass(replication: dict[str, Any]) -> bool:
    """Require every re-derived replication cohort to meet the FDR threshold.

    Older, manually authored cards expose only a discovery/validation pair.
    TRACER's canonical card additionally contains ``fdr_by_cohort``.  When
    that auditable mapping is present, a third or later cohort cannot be
    silently ignored merely because the legacy card schema has two FDR slots.
    """
    fdr_by_cohort = replication.get("fdr_by_cohort")
    cohort_ids = replication.get("cohort_ids")
    if isinstance(fdr_by_cohort, dict) and isinstance(cohort_ids, list):
        if not cohort_ids or any(cohort_id not in fdr_by_cohort for cohort_id in cohort_ids):
            return False
        return all(_fdr_passes(fdr_by_cohort[cohort_id]) for cohort_id in cohort_ids)
    return _fdr_passes(replication.get("discovery_fdr")) and _fdr_passes(
        replication.get("validation_fdr")
    )


def assess(card: dict[str, Any]) -> Assessment:
    """Score one independently curated candidate card.

    Score components require positive evidence, so unavailable data never gains
    credit. Hard stops intentionally cap apparent confidence when independent
    replication or confounding control is absent.
    """
    candidate_id = str(card.get("candidate_id", "UNSPECIFIED"))
    reasons: list[str] = []
    hard_stops: list[str] = []
    score = 0.0

    replication = card.get("cross_cohort_replication", {})
    n_cohorts = replication.get("independent_cohorts", 0)
    replicated = (
        isinstance(n_cohorts, int)
        and n_cohorts >= 2
        and replication.get("effect_direction_consistent") is True
        and replication.get("same_biological_compartment") is True
        and replication.get("same_measurement_level") is True
        and _replication_fdrs_pass(replication)
    )
    if replicated:
        score += WEIGHTS["cross_cohort_replication"]
        reasons.append("Direction and FDR thresholds replicate across at least two independent cohorts.")
    else:
        hard_stops.append(
            "Independent same-compartment, same-measurement-level replication is absent, inconsistent, or not significant."
        )

    perturbation = card.get("perturbation_support", {})
    perturbation_supported = (
        perturbation.get("tested") is True
        and perturbation.get("direction_consistent") is True
        and isinstance(perturbation.get("independent_studies"), int)
        and perturbation["independent_studies"] >= 1
    )
    if perturbation_supported:
        score += WEIGHTS["perturbation_support"]
        reasons.append("At least one independent perturbation result supports the proposed direction.")
    else:
        hard_stops.append("No direction-consistent perturbation evidence; causal language is prohibited.")

    orthogonal = card.get("orthogonal_evidence", {})
    if orthogonal.get("direction_consistent") is True and isinstance(orthogonal.get("modalities"), int) and orthogonal["modalities"] >= 2:
        score += WEIGHTS["orthogonal_evidence"]
        reasons.append("At least two orthogonal evidence modalities agree in direction.")
    else:
        reasons.append("No qualifying multi-modal/orthogonal corroboration.")

    literature = card.get("curated_literature_evidence", {})
    if literature.get("supports_claim") is True and isinstance(literature.get("independent_sources"), int) and literature["independent_sources"] >= 2:
        score += WEIGHTS["curated_literature_evidence"]
        reasons.append("At least two independently curated sources support the constrained claim.")
    else:
        reasons.append("Literature support is missing, uncurated, or insufficiently independent.")

    confounding = card.get("confounding_robustness", {})
    confounding_controlled = (
        confounding.get("batch_controlled") is True
        and confounding.get("composition_controlled") is True
    )
    if confounding_controlled:
        score += WEIGHTS["confounding_robustness"]
        reasons.append("Batch and cell-composition confounding were both assessed.")
    else:
        hard_stops.append("Batch and/or cell-composition confounding has not been controlled.")

    experiment_complete = _complete_experiment(card.get("discriminating_experiment", {}))
    if experiment_complete:
        score += WEIGHTS["discriminating_experiment"]
        reasons.append("A pre-specified experiment can discriminate the competing hypotheses.")
    else:
        hard_stops.append("No complete discriminating experiment with comparator and opposing predictions.")

    score = round(score, 2)
    level = "HIGH" if score >= 0.80 else "MODERATE" if score >= 0.55 else "LOW"
    if not replicated or not confounding_controlled:
        level = "LOW"

    return Assessment(
        candidate_id=candidate_id,
        priority_score=score,
        level=level,
        ready_for_validation=(level == "HIGH" and experiment_complete),
        causal_language_permitted=perturbation_supported,
        reasons=reasons,
        hard_stops=hard_stops,
    )
