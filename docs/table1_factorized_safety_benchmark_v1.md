# Table 1. Factorized synthetic safety benchmark

This is a finite deterministic gate-verification suite, not an LLM leaderboard or biomedical validation. `Unsafe HIGH` counts an ineligible frozen packet that a comparator elevated to HIGH. `Eligible retention` is defined only for the one frozen all-pass control.

| Evaluation set | Method | Unsafe HIGH | Eligible retention | Exact priority decision |
|---|---|---:|---:|---:|
| complete frozen draft | Full TRACER | 0/31 (0.0%) | 1/1 (100.0%) | 32/32 (100.0%) |
| complete frozen draft | TRACER without transport gate | 1/31 (3.2%) | 1/1 (100.0%) | 31/32 (96.9%) |
| complete frozen draft | TRACER without source-independence gate | 1/31 (3.2%) | 1/1 (100.0%) | 31/32 (96.9%) |
| complete frozen draft | TRACER without all-cohort FDR gate | 1/31 (3.2%) | 1/1 (100.0%) | 31/32 (96.9%) |
| complete frozen draft | Naive counting baseline | 7/31 (22.6%) | 1/1 (100.0%) | 25/32 (78.1%) |
| provenance-omission attack | Full TRACER | 0/32 (0.0%) | not applicable: every omission draft is ineligible by protocol | 32/32 (100.0%) |
| provenance-omission attack | TRACER without provenance coverage | 1/32 (3.1%) | not applicable: every omission draft is ineligible by protocol | 31/32 (96.9%) |

## Predeclared critical cells

- Eligible positive control: `SYNTH-FCT-T1-I1-F1-P1-C1`
- Cross-measurement-only failure: `SYNTH-FCT-T0-I1-F1-P1-C1`
- Same-source-only failure: `SYNTH-FCT-T1-I0-F1-P1-C1`
- All-cohort-FDR-only failure: `SYNTH-FCT-T1-I1-F0-P1-C1`

The remaining 28 cells contain two or more factor failures and test compositional safety stress. All 32 provenance-omission cards are separate draft-integrity attacks; their expected label is LOW.
