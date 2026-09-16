# Factorized synthetic safety benchmark: analysis protocol v1

## Scope

This protocol evaluates a deterministic TRACER implementation against frozen synthetic evidence packets. It does not test biomedical hypotheses, clinical utility, population safety, or the comparative intelligence of language models.

The 32 complete drafts exhaust every combination of five binary, registry-derived factors: transport compatibility, source independence, all-cohort FDR, perturbation support, and confounding control. The frozen eligibility rule assigns HIGH only when all five factors pass. A separate omission attack removes `literature-2` from every draft and therefore creates 32 additional, protocol-ineligible draft-integrity cases.

## Claim-to-test map

| Method claim | Endpoint | Comparator | Frozen evaluation unit | Reported quantity |
|---|---|---|---|---|
| Full TRACER follows the frozen eligibility protocol | Exact HIGH/LOW decision | Frozen reference standard | 32 complete factorial drafts | Exact decision matches |
| Transport compatibility prevents cross-measurement pseudo-replication | Unsafe HIGH | Full TRACER without transport gate | One transport-only failure plus all interaction cells | Unsafe HIGH count among 31 ineligible drafts |
| Source-independence auditing prevents label-count pseudo-replication | Unsafe HIGH | Full TRACER without source-independence gate | One same-source-only failure plus all interaction cells | Unsafe HIGH count among 31 ineligible drafts |
| All-cohort FDR control blocks selective significance escalation | Unsafe HIGH | Full TRACER without all-cohort-FDR gate | One FDR-only failure plus all interaction cells | Unsafe HIGH count among 31 ineligible drafts |
| Provenance coverage blocks selective citation omission | Unsafe HIGH | Full TRACER without provenance coverage | 32 source-omission drafts | Unsafe HIGH count among 32 ineligible omission drafts |
| Evidence-graph gating adds protection beyond simple counting | Unsafe HIGH | Naive counting baseline | 32 complete factorial drafts | Unsafe HIGH count among 31 ineligible drafts |

## Four critical cells and the full safety envelope

The protocol reports four named critical cells: one all-pass positive control, one cross-measurement-only failure, one same-source-only failure, and one all-cohort-FDR-only failure. These cells isolate the principal eligibility logic. The other 28 cells contain two or more failures and prevent a result that only works for clean single-failure examples.

This is stronger than describing the suite as four equal groups of eight: the full `2^5` enumeration makes every gate interaction visible, and the named critical cells preserve an intuitive audit trail.

## Comparator rules

Every comparator receives the same complete deterministic draft and the same frozen packet, except for the provenance-omission attack, where both methods receive the same deliberately incomplete draft. Each ablation disables exactly one module. The naive comparator disables provenance, transport, source-independence, and all-cohort-FDR checks while retaining the remaining perturbation and confounding requirements.

## Statistical policy

The suite is finite and exhaustively enumerated, so all results are reported as exact counts and exact finite-suite proportions. It is inappropriate to attach p-values or population confidence intervals to these deterministic cases. LLM prompt sampling, if later reported, must remain separate from this algorithm-verification table and must not treat correlated packets or model replies as independent biological observations.

## Leakage and interpretation boundaries

The frozen eligibility standard, packet manifest, comparator definitions, and primary endpoint are fixed before summary generation. No packet is selected after observing a model response. The language-model trace study remains a separate generator-robustness analysis; this protocol attributes deterministic failures to omitted evaluator modules only.
