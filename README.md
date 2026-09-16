# TRACER

**TRACER: Evidence-Graph Gates for Pseudo-Replication Control in LLM-Assisted Biomedical Hypothesis Generation**

TRACER (Transport-aware, Registry-audited, Abstention-first Causal Evidence Reconciliation) is a methods-pilot implementation for LLM-assisted biomedical hypothesis generation. A language model may draft a hypothesis and a next experiment, but it cannot create score-bearing evidence or assign research priority. The deterministic evaluator reconstructs the decision from a frozen registry and returns `LOW/ABSTAIN` whenever a required evidence gate fails.

This repository supports the accompanying manuscript. It documents algorithmic behavior on a frozen factorized safety suite and a dependent, real cross-measurement hard negative. It does **not** report a new biological mechanism, clinical utility, treatment recommendation, patient-level conclusion, or LLM leaderboard.

## Repository contents

- `src/` - evidence packet, candidate-card, graph-evaluation, confidence, and trace-validation modules.
- `config/` - frozen cohort registries, evaluation contracts, model protocols, and benchmark definitions.
- `data/` - synthetic and real control packets, derived metadata, source-file manifest, and public GEO source files. See `data/README.md` for deterministic recovery of the two files exceeding GitHub's file-size limit.
- `results/` - machine-readable deterministic and small-model trace results used by the methods pilot.
- `scripts/` - data auditing, packet construction, evaluation, aggregation, and manuscript-support scripts.
- `tests/` - regression tests for the evaluator and frozen data contracts.
- `docs/` - protocol, limitation, audit, and analysis documentation.
- `figures/` - final rendered figures and editable PowerPoint versions.
- `manuscript/` - repository-linked manuscript source.

## Quick verification

The core evaluator uses the Python standard library. Python 3.10 or later is recommended.

```bash
python -m unittest discover -s tests -v
python scripts/28_run_factorized_synthetic_suite_v2.py
python scripts/29_summarize_factorized_safety_benchmark_v2.py
```

`python-docx` is needed only to rebuild or edit the Word manuscript:

```bash
python -m pip install python-docx
```

To regenerate the vector safety-ablation figure, install the optional plotting dependencies:

```bash
python -m pip install -r requirements-figure.txt
```

## Data availability and scope

The real hard-negative panel is assembled from de-identified public GEO processed files. The frozen manifest in `data/raw/public_processed_manifest.json` records source URLs and SHA-256 checksums. Smaller source files are included under `data/raw/`. The two public files exceeding GitHub's 100 MB per-file limit are recovered directly from their authoritative GEO URLs by `python scripts/02_fetch_public_processed_data.py`; the script checks every resulting SHA-256 digest. Reuse remains subject to each source repository's terms.

The final paper's real hard-negative analysis uses GSE120575, GSE91061, and GSE78220. GSE115978 is retained in the frozen registry as mechanistic context and is not a clinical-response replication cohort.

## Interpretation boundary

The reported counts are deterministic implementation outcomes under a frozen protocol. They must not be interpreted as estimates of clinical risk, biomedical prevalence, biological truth, or comparative model quality.
