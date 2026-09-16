# TRACER backbone v1

**TRACER** = **T**ransport-aware, **R**egistry-audited, **A**bstention-first **C**ausal **E**vidence **R**econciliation.

TRACER is the main algorithmic contribution of this project. It is not a new language model and it does not fine-tune a general LLM. Instead, it changes the inference backbone between an LLM draft and a biomedical priority claim.

## Core design change

Earlier candidate-card scoring accepted fields such as `independent_cohorts`, `same_measurement_level`, and `tested` from a structured card. Even with schema validation, those values were still authored by the LLM. TRACER treats them as **untrusted declarations**.

It builds a provenance graph whose nodes are frozen evidence items and registered cohorts. It then derives every score-bearing variable from that graph:

\[
\tilde R = f_R(\text{cohort registry}, \text{packet evidence}),\quad
\tilde P = f_P(\text{perturbation-tagged evidence}),\quad
\tilde C = f_C(\text{confounding annotations}).
\]

The priority grader receives \((\tilde R,\tilde P,\tilde C)\), not the LLM's reported \((R,P,C)\).

## Modules

1. **Provenance-coverage module.** Every source cited by a draft must match a frozen evidence-item ID and identifier. Every evidence item supplied to the model must be represented; omitting contradictory evidence creates a hard stop.
2. **Transport-aware replication module.** A replication edge is eligible only when at least two *auditedly independent source groups* share an audited baseline response endpoint, biological compartment, and measurement level. A bulk-to-single-cell comparison receives no same-measurement replication credit. Registry v2 also requires every participating replication cohort's FDR to pass; a third cohort cannot be ignored by a two-slot legacy card schema.
3. **Direction and perturbation module.** Direction consistency, FDR availability, perturbation support, orthogonal modalities, and literature-source count are derived from typed packet items, not claimed by the model.
4. **Causal-language gate.** Causal verbs in hypotheses are detected. Without graph-derived direction-consistent perturbation support, they produce an explicit hard stop.
5. **Discriminating-experiment module.** The existing card contract still requires a comparator, readout, and opposing predictions. Thus abstention does not mean an unhelpful response: the system can still recommend the experiment that would resolve the uncertainty.

Each module has an explicit Boolean ablation switch in `src/evidence_graph.py`. Disabling `provenance_coverage` keeps source-ID integrity but allows a draft to omit packet items; disabling `transport_aware_replication` uses a deliberately transport-blind comparator that pools eligible baseline cohorts despite modality/compartment mismatch. These switches are only for the pre-specified ablation; they must never be used in the deployable workflow.

## Transport rule

For candidate replication across cohorts \(i,j\), the graph grants replication eligibility only if

\[
T_{ij}=I(B_i=B_j=1)\,I(G_i\ne G_j)\,I(M_i=M_j)\,I(K_i=K_j)\,I(E_i=E_j=1)=1,
\]

where \(B\) is audited baseline-response eligibility, \(G\) an audited source-independence group, \(M\) measurement level, \(K\) biological compartment, and \(E\) same-measurement replication eligibility. Direction/FDR are assessed only after this transport gate is passed; all participating cohort FDR values must meet the frozen threshold.

## Confirmatory ablation plan

The benchmark must compare the following conditions using the same frozen packets and model outputs:

| Condition | What it tests |
| --- | --- |
| Free-form LLM | Unconstrained baseline |
| JSON candidate card only | Effect of formatting alone |
| Card + conventional self-declared score | Whether schema alone is sufficient |
| TRACER without provenance coverage | Value of preventing selective citation |
| TRACER without transport gate | Value of blocking cross-modality pseudo-replication |
| Full TRACER | Combined algorithm |

Primary outcome: unsafe escalation rate. Secondary outcomes: false same-measurement replication, provenance error, appropriate abstention, valid-card rate, and discriminating-experiment adequacy. The evidence packet—not model generation—is the paired statistical unit.

## Current demonstration

In the frozen ICI packet, the model may see GSE120575 single-cell and GSE91061 bulk evidence. TRACER derives two cohorts, two measurement levels, two compartments, mixed directionality, absent perturbation evidence, and unresolved confounding. Therefore it returns `LOW`, regardless of any contradictory values written in the model draft.

This is a demonstration of evidence governance, not proof that a melanoma mechanism is false or absent.
