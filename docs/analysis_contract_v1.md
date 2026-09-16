# ICB-Disambiguate analysis contract, v1

## What the system is allowed to do

An LLM may turn fixed analytical outputs and retrieved, versioned evidence into a *candidate card*. It may formulate two competing explanations and propose a discriminating experiment. Its output is a draft for expert review, not a biological result.

The deterministic validator rejects any card that lacks a disease/treatment/unit scope, two falsifiable alternatives, traceable evidence entries, or opposite predicted outcomes for the proposed experiment. The deterministic evidence grader then gives a research-priority level.

## What the system is forbidden to conclude

- That a lesion-level or bulk-RNA association is a cell-intrinsic effect.
- That a cross-modality result is independent same-compartment replication.
- That a mechanism is causal without direction-consistent perturbation evidence.
- Any patient-level treatment recommendation.

## Current evidence gate

The frozen GSE120575 discovery set has only 12 pre-treatment anti-PD-1 monotherapy lesions. It may generate low-priority hypotheses after fixed analysis, but cannot independently train a model or establish a new mechanism.

The GSE91061 bulk-RNA cohort is an independent clinical direction check, not a single-cell replication cohort. Its disagreement with the exhausted-program control is retained as a negative transport result. A future high-priority card requires a second ICI-treated single-cell or spatial cohort with audited response labels, plus perturbation evidence.
