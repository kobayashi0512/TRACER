# Positive-control cross-cohort interpretation, v1

## What was tested

The pre-specified GSE120575 immune-state positive-control panel was screened at lesion level in the frozen discovery cohort (12 pre-treatment anti-PD-1 monotherapy lesions; 4 responders and 8 non-responders). The same gene/program panel was then direction-checked in GSE91061 (49 pre-treatment nivolumab bulk-RNA samples; 10 responders and 39 non-responders).

The source results are `positive_control_screen_v1.tsv` and `gse91061_positive_control_direction_check_v1.tsv`. These files must be read together.

## Result

All 15 features had the expected direction in the GSE120575 lesion-mean screen. This is a sanity check, not a discovery: the input contains all CD45+ cells, so its lesion means are composition-sensitive.

In GSE91061 bulk RNA, only 8/15 features retained their expected direction. The memory-like T-cell program retained the responder direction, but did not reach the pre-specified panel-level FDR threshold. The dysfunctional/exhausted program reversed direction (responder higher) and also did not reach the panel-level FDR threshold. The two cohorts' numeric expression scales and assay units are not pooled.

## Decision

GSE91061 **does not count as independent replication** of a single-cell immune-state or cell-intrinsic mechanism. It remains useful as an explicitly recorded cross-modality transport test and as a warning against treating bulk expression as cell-state confirmation.

The confidence rubric now requires same biological compartment and same measurement level before a second cohort can earn the cross-cohort-replication component. A bulk-RNA result can only be documented as orthogonal/contextual evidence after its biological interpretation is manually reviewed.

## Required next evidence

Before any novel candidate can obtain a high research-priority level, it needs a second ICI-treated single-cell or spatial cohort with patient/lesion-level response metadata, plus a direction-consistent perturbation or functional dataset. The present data cannot support a causal or clinical claim.
