# Real-data hard-negative pilot log v1

**Status:** descriptive, single-dependency-cluster feasibility result. It is not a melanoma mechanism finding, a model ranking, or an inferential comparison.

## Evidence provenance and dependence

The 15 packets are generated without LLM editing from frozen rows in:

- GSE120575 lesion-level CD45+ single-cell pseudo-bulk positive-control screen: 12 baseline anti-PD-1 monotherapy lesions.
- GSE91061 pre-treatment nivolumab bulk-RNA direction check: 49 samples.

Every feature packet contains the same two source cohorts and the same pre-specified immune-state panel. Therefore all 15 packets belong to one locked dependency cluster: `GSE120575_GSE91061_positive_control_panel_v1`. The valid statistical unit here is the cluster, **not** individual genes, programs, packets, or generated responses.

The frozen eligibility label for every packet is `false`: a bulk-RNA check is not same-measurement or same-compartment replication of a single-cell state; there is no direction-consistent perturbation evidence; and composition confounding is unresolved.

## Frozen execution

- Four local runtime tags: `qwen3:0.6b`, `llama3.2:1b`, `qwen2.5vl:3b`, `qwen3-vl:30b-a3b-instruct-q4_K_M`.
- Schema-constrained candidate card; seed `20260914`; temperature `0.0`; maximum 1,600 tokens.
- 60 raw traces = 4 runtimes × 15 related packets.
- Prompt rendering omitted the evaluator-only labels. Full response, prompt hash, model metadata, and registry are retained.

## Descriptive cluster outcome

| Runtime tag | Parseable JSON | Structurally admissible | False same-measurement claim | Full TRACER unsafe HIGH |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 0.6B | 15/15 | 0/15 | 15/15 | 0/15 |
| Llama 3.2 1B | 15/15 | 0/15 | 15/15 | 0/15 |
| Qwen2.5-VL 3B | 15/15 | 0/15 | 15/15 | 0/15 |
| Qwen3-VL 30B-A3B | 15/15 | 8/15 | 0/15 | 0/15 |

The 30B runtime's eight admissible cards explicitly stayed `LOW` in both the conventional card score and TRACER. The remaining seven 30B cards were rejected for other contract errors. Across the one dependence cluster, full TRACER produced zero `HIGH` priorities, as required by the frozen evidence rule.

## What may and may not be claimed

Permitted: the system demonstrably rejects or downgrades this **specific real cross-modality hard-negative cluster** under frozen prompts and registry rules.

Prohibited: claims of 60 independent observations, significance tests, general model superiority/inferiority, melanoma biology, external clinical validation, calibration, or clinical utility.

## Next real-data requirement

An evaluable paper benchmark still needs multiple **independent** source clusters, including both eligible and ineligible examples. A second ICI-treated tumor single-cell or spatial cohort must have audited baseline timing, treatment, patient-level response mapping, biological compartment, and access terms before it can create a same-measurement replication edge.
