# Data inventory

## Included in Git

- Frozen synthetic packets and real control packets used by the evaluator.
- Derived metadata tables and machine-readable data manifests.
- Smaller GEO processed files and metadata needed by the published control checks.

## GitHub Release assets

The following public GEO processed files exceed GitHub's 100 MB Git-file limit and are attached to the repository release `v0.1.0-data`:

- `GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz`
- `GSE115978_tpm.csv.gz`

Their source URLs, byte sizes, and SHA-256 checksums are frozen in `raw/public_processed_manifest.json`. Download release assets into `data/raw/` before rerunning scripts that consume them.

The current manuscript's dependent real hard-negative panel uses GSE120575, GSE91061, and GSE78220. GSE115978 is retained as contextual registry material only. No controlled-access, patient-identifying, or newly collected data are included.
