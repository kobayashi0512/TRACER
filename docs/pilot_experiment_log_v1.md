# Pilot experiment log v1 — frozen snapshot

**Status:** implementation and synthetic safety-test pilot; **not** a biological result, model ranking, calibration study, or submission-ready efficacy result.

## Frozen inputs and execution

- Six fully synthetic evidence packets, with one complete positive control and five pre-specified evidence-failure structures: transport mismatch, contradictory evidence, absent perturbation, unresolved confounding, and single cohort.
- Four local, open-weight runtime tags: `qwen3:0.6b`, `llama3.2:1b`, `qwen2.5vl:3b`, and `qwen3-vl:30b-a3b-instruct-q4_K_M`.
- One Schema-constrained card generation per `model × packet` at seed `20260914`, temperature `0.0`, maximum 1,600 tokens: 24 raw traces.
- Evaluator-only eligibility labels were stripped before prompt rendering. All trace prompts, model metadata, and responses are retained under `results/synthetic_schema_runs_v1/`.

## Descriptive outcomes

| Runtime tag | Parseable JSON | Structurally admissible | Full-TRACER unsafe HIGH | Correct HIGH admission |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 0.6B | 6/6 | 3/6 | 0/6 | 0/6 |
| Llama 3.2 1B | 6/6 | 4/6 | 0/6 | 1/6 |
| Qwen2.5-VL 3B | 6/6 | 6/6 | 0/6 | 1/6 |
| Qwen3-VL 30B-A3B | 6/6 | 6/6 | 0/6 | 1/6 |

The conventional self-declared card score produced six observed unsafe `HIGH` escalations among cards for which that score could be evaluated. Invalid cards are not counted as safe; their self-declared score is deliberately treated as unavailable. Full TRACER had zero unsafe `HIGH` escalations in this finite synthetic replay, while admitting the complete positive control for three of four runtimes.

## Module ablations

The same 24 frozen raw traces were replayed without generating new text:

| Condition | Unsafe HIGH | Correct HIGH admission | Interpretation |
| --- | ---: | ---: | --- |
| Full TRACER | 0 | 3 | Intended workflow |
| No provenance coverage | 0 | 3 | No LLM trace omitted the conflict in this small run; no conclusion about the module follows from this null contrast |
| No transport-aware replication | 2 | 3 | Cross-assay pooling created unsafe upgrades in two already-frozen traces |

A separate deterministic synthetic selective-citation attack removes the pre-specified contradictory source. Full TRACER returns `LOW + REJECT_DRAFT`; disabling provenance coverage yields `HIGH + ADMIT_FOR_HUMAN_REVIEW`. This is an implementation property, not a model result.

## Permitted wording

It is accurate to say that this pilot demonstrates **feasibility**, preserves full generation provenance, and exhibits the intended safety behavior on a small synthetic stress suite.

It is not accurate to claim a model ranking, a statistically significant improvement, calibrated biomedical confidence, a melanoma mechanism, clinical utility, or a general reduction in hallucinations.

## Required next stage before a paper result

1. Freeze 48–80 independently audited real evidence packets before querying models.
2. Add at least one biomedical-tuned comparator only after its terms and exact runtime are documented.
3. Run paired free-form, conventional-card, and full-TRACER conditions at a pre-specified prompt budget.
4. Obtain blinded dual domain review and report agreement, then calculate packet-clustered confidence intervals and paired tests.
