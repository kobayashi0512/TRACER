# Current limitations and remediation register

This is an internal methods audit based only on the frozen repository inputs, code, and recorded model traces. It distinguishes defects that can be fixed by protocol/code from limitations that cannot honestly be coded away.

## Fixed in the current revision

| Issue | Why it mattered | Remediation | Verification |
| --- | --- | --- | --- |
| Only the first two cohort FDR values reached the priority grader | A third same-measurement cohort with failed FDR could be ignored | TRACER now derives `fdr_by_cohort` and requires every cited replication cohort to pass | New regression test fails a three-cohort card when the third FDR is 0.30 |
| Different accessions were assumed to be independent by name alone | Multiple views of one source study could inflate replication credit | Registry v2 adds `source_independence_group`; canonical replication count is the number of audited groups, and missing group metadata fails closed | New graph regression test makes two same-level cohorts in one group remain `LOW` |
| The existing Schema prompt already warned against unsafe content | Its apparent benefit could be confused with the algorithmic gate | Added `schema_only_card`: schema-shaped output without content-level causal or transport guidance. The prior condition remains available as `schema_constrained_card` | Prompt construction test covers both conditions and retains evaluator-only label isolation |
| Trace scoring recorded only headline error types | A total rejection count cannot show which protection fired | The scorer now writes per-model structural-error and TRACER-hard-stop counts | Both real prompt conditions were rescored from immutable traces |

These corrections are method-level safeguards. They do not create new biological evidence.

## Solvable next without new external data

| Issue | Why current result is insufficient | Concrete next action |
| --- | --- | --- |
| The real multicohort run has only one seed | Two prompt conditions now exist, but one deterministic generation cannot quantify sampling variability | Repeat both frozen prompt conditions at at least two additional pre-specified seeds, treating generations as nested within packet/model condition. |
| Real pilot has no model-declared `HIGH` | Zero unsafe TRACER `HIGH` admissions is reassuring, but cannot estimate a reduction in the primary unsafe-escalation endpoint | Completed a 32-packet factorial synthetic suite across transport, source dependence, all-cohort FDR, perturbation, and confounding; it includes a pre-specified provenance-omission counterfactual for each packet. Report it only as implementation safety, not biology or model performance. |
| Trace scoring records only headline error types | Reviewers need to see which gate caused a rejection | The factorial output now records independently re-derived factor states for transport, source independence, all-cohort FDR, perturbation, confounding, and provenance omission. Add the same compact attribution table to future real-trace summaries. |
| The positive-control panel is one dependency cluster | Fifteen genes/programs are not 15 independent mechanism tests | Preserve cluster-level aggregation, use block/bootstrap resampling by evidence packet only for benchmark uncertainty, and never use gene rows as biological sample size. |

### First corrected prompt comparison

The same 15 real transport packets were run once per model under both conditions at seed `20260914`. In `schema_only_card`, each of the three smaller models still made an invalid same-measurement and same-compartment claim in 15/15 cards; full TRACER admitted none. The 30B model produced 15/15 structurally valid cards, 14/15 of which were admissible for review; all remained `LOW` and none became unsafe `HIGH`. The one non-admitted 30B card had a frozen-evidence provenance mismatch.

In the earlier content-guided `schema_constrained_card` condition, the same three small models showed the same 15/15 invalid transport claims, while the 30B model had 8/15 structurally valid cards. This single-seed, one-cluster comparison is descriptive only: it shows that content guidance is not sufficient to remove the observed small-model transport error and that TRACER remains the final gate. It is not a model ranking or a statistical effect estimate.

## Cannot be solved by code alone

| Limitation | Why it cannot be bypassed | Correct response |
| --- | --- | --- |
| No audited, independent treatment-response cohort at the same single-cell measurement level | Bulk RNA cannot establish a cell-state replication edge | Keep all current biological cards at `LOW`; obtain and audit a true same-measurement cohort before allowing any real `HIGH` card. |
| GSE120575 discovery subset is 12 lesions (4 response, 8 non-response) | Small lesion-level discovery data cannot yield a general mechanism or clinical predictor | Use it only for workflow sanity checks and frozen positive controls, never for training or mechanistic discovery claims. |
| GSE78220 has unresolved participant dependence for labels such as Pt27A/Pt27B | Sample columns are not automatically independent patients | Retain it as a direction check only and do not use its columns as a patient-level denominator until source-level provenance resolves the relationship. |
| No direction-consistent perturbation evidence in the real packets | Observational expression cannot establish causal language | Require a real perturbation record and a discriminating experiment before any causal wording becomes permitted. |
| No blinded dual expert review yet | Automated validation cannot assess whether a proposed experiment is biologically discriminating | Run two independent blinded reviews, adjudicate with a third reviewer, and report agreement before claiming experimental usefulness. |
| Biomedical and remote comparator slots are pending | An installed generic model set is not the whole target population | Do not claim coverage of biomedical LLMs or Kimi until exact versions, access terms, and frozen runtime traces are available. |
| Registry source groups are curator assertions, not automatic proof of participant disjointness | Code can enforce a declared group but cannot discover latent cohort overlap | Retain an audit trail for each group; merge groups or mark the audit incomplete whenever overlap cannot be ruled out. |

## Findings that are not bugs

- Small local models repeatedly claiming same-measurement replication in the real transport packets is the intended failure mode being measured, not a reason to loosen the validator.
- A `LOW` result after an otherwise well-formed candidate card is an intended abstention when the graph lacks transportable replication, perturbation, or confounding control.
- The all-zero unsafe `HIGH` count in the current real pilot is not proof of safety and not a negative biological result; it only limits what can be claimed from that pilot.
