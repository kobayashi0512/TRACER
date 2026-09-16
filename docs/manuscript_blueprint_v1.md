# Manuscript blueprint v1: evidence-grounded abstention for biomedical LLMs

## The narrow, defensible paper

**Working title:** *Evidence-Grounded Abstention for LLM-Generated Immunotherapy Mechanism Hypotheses: A Reproducible ICI Case Study*

This is a biomedical-informatics **methods/evaluation** paper, not a claim to have discovered a new melanoma resistance mechanism. Its central question is:

> Can a frozen evidence registry and deterministic, falsifiable candidate-card protocol prevent an LLM from upgrading weak observational ICI signals into high-confidence or causal mechanism claims?

The contribution is deliberately small: the LLM proposes a structured draft; it never decides whether the evidence is strong enough. A deterministic validator checks provenance, cohort eligibility, competing alternatives, and an experiment with opposing predictions. A deterministic grader then returns a research-priority level or abstains/downgrades.

## Why this is more than “LLM finds papers”

Existing biomedical agents can retrieve literature, analyze omics data, and propose experiments. The specific failure mode tested here is different: an apparently plausible mechanistic narrative can wrongly treat cell-level observations as patient-level evidence, bulk RNA as cell-state replication, or association as perturbation support. The method creates checkable failure conditions for these three errors.

The present implementation already contains a real negative transport example: pre-specified memory/exhaustion controls have 15/15 expected directions in the GSE120575 discovery analysis but only 8/15 direction matches in independent GSE91061 bulk RNA; the exhausted program is opposite in direction. This does **not** adjudicate either biology. It demonstrates why cross-modal agreement cannot be assumed and why the system must not label this as replication.

## Pre-registered research questions

| Question | Comparison | Primary outcome |
| --- | --- | --- |
| RQ1: Does the protocol reduce unsupported escalation? | Free-form LLM answer vs. structured candidate card + registry gate, on identical evidence packets | Unsafe high-confidence/causal-claim rate |
| RQ2: Does it abstain on known invalid evidence patterns? | Evidence packets with one cohort, cross-modality evidence, missing perturbation, or unresolved composition confounding | Appropriate-abstention rate |
| RQ3: Is the confidence score calibrated to evidence eligibility rather than model rhetoric? | LLM self-reported 0–100 confidence vs. deterministic priority level | Brier score and expected calibration error for the binary label “meets the frozen eligibility rule” |
| RQ4: Are the suggested next experiments genuinely discriminating? | Free-form experimental suggestion vs. card-required opposing predictions | Blinded expert rating of whether one pre-specified readout could distinguish the two stated hypotheses |

The target label in RQ3 is **evidence eligibility under the frozen protocol**, not “biological truth.” This distinction avoids pretending that a small observational cohort can supply a causal ground truth.

## Minimal benchmark design

### Evidence packets

Construct 48–80 versioned packets before querying any LLM. Each packet contains only: disease/treatment scope, pseudo-bulk result, cohort metadata, modality and compartment labels, pre-curated perturbation entries if any, and stable source identifiers. Do not give the model hidden outcome labels.

Stratify packets across four pre-specified categories:

1. eligible same-measurement replication + perturbation support;
2. observational association only;
3. cross-modality or cross-compartment apparent “replication”;
4. evidence with a known confounding gap.

Use the ICI data in this repository as a transparent case study and add independent published packets from other tumour/therapy settings only after their raw source, sample-level endpoint, and access terms are audited. The final benchmark must not re-use an evidence packet as both prompt-development material and held-out evaluation.

### Systems compared

For each frozen packet, query at least three model families/versions, with version, date, temperature, system prompt, retrieval corpus version, and complete output retained. Each model produces:

- a free-form mechanism answer and a 0–100 self-confidence score;
- a candidate card constrained by the JSON contract;
- an abstention when fields cannot be filled from the packet.

The actual model names should be chosen and frozen immediately before data collection; API model aliases must never be reported without the exact version/date. A biomedical-tuned model can be included, but it is a comparator rather than the paper's claimed contribution.

### Human reference standard

Two domain reviewers independently judge each output against the frozen evidence packet, blind to model identity and study condition. They label:

- provenance correct / incorrect / unverifiable;
- causal wording permitted / not permitted;
- same-measurement replication claim permitted / not permitted;
- abstention appropriate / inappropriate;
- discriminating experiment adequate / inadequate.

Adjudicate disagreements using a third reviewer; report raw agreement and Cohen's kappa with confidence intervals. Reviewers judge protocol compliance, not whether a proposed mechanism is clinically actionable.

## Metrics and analysis plan

The primary endpoint is the proportion of outputs that either use prohibited causal wording or assign high priority when the packet does not meet the frozen eligibility rule. Analyse the paired free-form and gated outputs with McNemar's test and report the paired risk difference with a 95% confidence interval.

Secondary endpoints are: (1) provenance error rate; (2) false same-measurement replication rate; (3) appropriate abstention; (4) valid-card completion; (5) expert-rated discriminating-experiment adequacy; and (6) calibration of self-reported confidence to the **protocol eligibility** label. Bootstrap confidence intervals by evidence packet, not by generated sentence. If multiple generations are used, treat them as nested within the packet/model condition rather than independent biomedical samples.

Pre-specify a language normalization rule: causal verbs include *causes, drives, mediates, proves, determines,* and their Chinese equivalents when unsupported by a direction-consistent perturbation entry. Use a blinded manual audit rather than keyword counting alone.

## What the present data can and cannot support

| Asset | Permitted use | Prohibited use |
| --- | --- | --- |
| GSE120575, 12 frozen baseline anti-PD-1 lesions | Discovery packet and workflow sanity check | Training an outcome model; cell-as-patient inference; new mechanism claim |
| GSE91061, 49 audited baseline bulk samples | Independent clinical direction check; deliberate cross-modality hard-negative | Single-cell replication; cell-intrinsic inference |
| GSE115978 | Mechanistic context / functional-study provenance | Audited clinical response replication until a patient-level endpoint is recovered and checked |
| HRA005837 | Future candidate only | Any analysis until access and endpoint metadata are approved and audited |

## Required evidence before submission

1. Freeze the complete benchmark and adjudication guide before model querying.
2. Obtain ethics/terms confirmation for every evidence packet; use only public or explicitly authorized data.
3. Run all baseline and gated conditions with the same source packet and a documented prompt budget.
4. Perform blinded dual review and quantify inter-rater agreement.
5. Release card schema, cohort registry, prompts, model outputs where license permits, reviewer rubric, and analysis code.
6. State that the system ranks research hypotheses; it is not a diagnostic, clinical-decision, or treatment-recommendation system.

## Success criterion and honest stopping rule

This direction is publishable only if the gated workflow substantially reduces the primary unsafe-escalation endpoint while retaining useful, expert-rated discriminating experiments. If it merely produces more polished text or rejects everything, it is not enough. If there is no independent expert review or versioned evidence registry, the work should be presented only as a software prototype, not as a calibration study.
