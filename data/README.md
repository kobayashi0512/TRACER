# Data inventory

## Included in Git

- Frozen synthetic packets and real control packets used by the evaluator.
- Derived metadata tables and machine-readable data manifests.
- Smaller GEO processed files and metadata needed by the published control checks.

## Deterministic recovery of large public inputs

The following public GEO processed files exceed GitHub's 100 MB per-file limit and are therefore not mirrored in this Git repository:

- `GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz`
- `GSE115978_tpm.csv.gz`

Their authoritative GEO URLs, byte sizes, and SHA-256 checksums are frozen in `raw/public_processed_manifest.json`. Recover every missing public processed input and verify its digest with:

```bash
python scripts/02_fetch_public_processed_data.py
python scripts/03_audit_public_inputs.py
```

The downloader resumes partial transfers when the GEO server supports byte ranges, never overwrites an existing complete file, and records the retrieval state locally. No controlled-access, patient-identifying, or newly collected data are included.

The current manuscript's dependent real hard-negative panel uses GSE120575, GSE91061, and GSE78220. GSE115978 is retained as contextual registry material only. No controlled-access, patient-identifying, or newly collected data are included.
