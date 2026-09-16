# GSE78220 public processed-data audit v1

Scope: a read-only eligibility and header-linkage audit. This document does not report a differential-expression result, a cell-state result, a mechanism, or a clinical predictor.

## Frozen source

- GEO series: [GSE78220](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE78220).
- Processed matrix: `GSE78220_PatientFPKM.xlsx`, SHA-256 `ae3b044f23a0a4cd2859da36726a220856c35216a169c17f93dfc3bd20b04de6`.
- GEO sample metadata: `GSE78220_family.soft.gz`, SHA-256 `ed47c48810839ede910542b73002bff1506e70d5adeea5bd16367ecc9fe64c6d`.
- Audit output: `results/gse78220_eligibility_audit_v1.json`.

The workbook has one `FPKM` sheet spanning `A1:AC25269`: a gene column plus 28 expression columns. All 28 headers match a GEO SOFT `!Sample_title`. Twenty-seven headers labelled `.baseline` are also labelled `biopsy time: pre-treatment` in SOFT; the sole `.OnTx` column is excluded.

## Frozen response grouping

For the 27 verified pre-treatment columns, all treatment labels are `Pembrolizumab`. SOFT response categories are 5 complete responses, 10 partial responses, and 12 progressive diseases. The pre-specified analysis mapping is CR/PR to `Responder` and PD to `Non-responder`, yielding 15 versus 12 sample columns.

This grouping is adequate for a bulk baseline expression-direction check only. It must not be used as a same-measurement replication of a single-cell state, nor as evidence of a causal mechanism. In particular, the public labels do not establish whether similarly named columns such as `Pt27A` and `Pt27B` are independent participants; matrix columns are therefore not a patient-level denominator.

## Consequence for TRACER

The cohort registry records `baseline_ici_response_association_eligible: true` and `same_measurement_replication_eligible: false`. A GSE78220 edge may support a transport-limited external bulk direction check, but cannot contribute a same-compartment/same-measurement replication edge or remove the cell-composition and perturbation gates.

`scripts/25_validate_positive_controls_gse78220.py` tests only the previously frozen 15-feature panel after the checksum and eligibility gates pass. Its `10/15` direction agreement is a reproducibility stress observation, not a biological discovery or an independent count of mechanisms.
