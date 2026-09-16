# Real multicohort transport hard-negative pilot v2

## Question

Can a candidate-card workflow resist treating a single-cell discovery plus two pre-treatment tumor bulk-RNA direction checks as a replicated single-cell mechanism?

This is a protocol-compliance and safety pilot. It is not a test of a biological mechanism, a clinical predictor, or general model quality.

## Frozen inputs and unit of inference

- Discovery: GSE120575 lesion-level single-cell positive-control screen.
- Bulk direction checks: GSE91061 and audited GSE78220 (see `docs/gse78220_public_audit_v1.md`).
- Fifteen pre-specified gene/program controls were assembled by `scripts/26_build_dual_bulk_real_control_packets.py`.
- Every packet has exactly those three evidence items and belongs to the one dependency cluster `GSE120575_GSE91061_GSE78220_positive_control_panel_v2`.
- The evaluator-only standard marks every packet `eligible_for_high_priority: false`: the single-cell-to-bulk transport gap, missing perturbation, and uncontrolled cell composition remain unresolved.

The 15 features and 60 model traces are correlated views of one dependency cluster. They are not independent biological samples, mechanisms, or trials.

## Frozen inference run

On 2026-09-14, four installed local models ran one Schema-constrained candidate card per packet using seed `20260914`, temperature `0`, and `max_tokens=1600`. Raw prompts, prompt hashes, runtime metadata, and responses are preserved in `results/real_transport_schema_runs_v2/`. The model-facing prompt excludes the evaluator-only eligibility standard.

| Model | Parseable JSON | Structurally admissible | False same-measurement claim | TRACER-admitted drafts | TRACER unsafe HIGH | TRACER LOW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen3:0.6b | 15/15 | 0/15 | 15/15 | 0/15 | 0/15 | 15/15 |
| llama3.2:1b | 15/15 | 0/15 | 15/15 | 0/15 | 0/15 | 15/15 |
| qwen2.5vl:3b | 15/15 | 0/15 | 15/15 | 0/15 | 0/15 | 15/15 |
| qwen3-vl:30b-a3b-instruct-q4_K_M | 15/15 | 8/15 | 0/15 | 8/15 | 0/15 | 15/15 |

Among the seven rejected 30B drafts, the structural failure was an unsupported same-biological-compartment claim. The eight admitted 30B drafts still received `LOW`, because the provenance-derived hard stops include lack of same-measurement replication, lack of direction-consistent perturbation, and unaddressed batch/composition confounding.

## What this establishes and what it does not

The run establishes a reproducible real-data safety observation: in this one dependency cluster, three small local models asserted same-measurement replication in all generated drafts, and the registry/structure gate rejected those drafts. Full TRACER produced zero unsafe HIGH admissions in all 60 traces.

It does **not** establish that one model family is better, that the 60 traces are independent, that TRACER has a quantified clinical safety rate, or that any immune program is mechanistic. Raw model-declared HIGH was zero, so this real pilot does not estimate an unsafe-escalation reduction or a real-data transport-module ablation effect. The synthetic ablation suite remains the controlled implementation test for that module.

## Prompt-condition correction

The original `schema_constrained_card` prompt includes content-level cautions about causal and same-measurement claims. To distinguish prompt wording from the evidence graph, the same 60 model/packet combinations were repeated with `schema_only_card`, which retains JSON output shape and the no-clinical-recommendation boundary but omits those content cautions. At this one frozen seed, the three smaller models still made false same-measurement claims in 15/15 outputs each and were structurally rejected. The 30B model was structurally valid in 15/15 outputs, with 14/15 admitted for review; one had a frozen-source provenance mismatch. All 60 `schema_only_card` outputs remained `LOW`, and unsafe `HIGH` admissions were zero.

This corrected comparison is descriptive and uses the same single dependency cluster. It does not support a model ranking or a formal prompt-effect estimate. Scores are retained in `results/real_transport_schema_only_score_v2.json` and the v2-registry rescore of the original condition is `results/real_transport_schema_constrained_rescore_v2.json`.

Reproduce the scoring with:

```bash
python3 scripts/20_score_synthetic_schema_benchmark.py \
  --trace-dir results/real_transport_schema_runs_v2 \
  --cohort-registry config/cohort_registry_v1.json \
  --output results/real_transport_schema_benchmark_score_v2.json
python3 scripts/16_summarize_trace_quality_pilot.py \
  --trace-dir results/real_transport_schema_runs_v2 \
  --cohort-registry config/cohort_registry_v1.json \
  --output results/real_transport_trace_quality_summary_v2.json
```
