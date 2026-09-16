#!/usr/bin/env python3
"""Fetch the frozen list of public, processed GEO files with checksums.

This intentionally excludes raw FASTQ/BAM files and any controlled-access data.
Existing files are never overwritten; reruns instead recompute their checksum.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


APP_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = APP_ROOT / "data" / "raw"
MANIFEST = RAW_DIR / "public_processed_manifest.json"

FILES = {
    "GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/"
        "GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz"
    ),
    "GSE120575_patient_ID_single_cells.txt.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/"
        "GSE120575_patient_ID_single_cells.txt.gz"
    ),
    "GSE115978_tpm.csv.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115978/suppl/GSE115978_tpm.csv.gz"
    ),
    "GSE115978_cell.annotations.csv.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115978/suppl/"
        "GSE115978_cell.annotations.csv.gz"
    ),
    "GSE91061_BMS038109Sample.hg19KnownGene.rld.csv.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE91nnn/GSE91061/suppl/"
        "GSE91061_BMS038109Sample.hg19KnownGene.rld.csv.gz"
    ),
    "GSE91061_family.soft.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE91nnn/GSE91061/soft/GSE91061_family.soft.gz"
    ),
    "GSE78220_PatientFPKM.xlsx": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE78nnn/GSE78220/suppl/"
        "GSE78220_PatientFPKM.xlsx"
    ),
    "GSE78220_family.soft.gz": (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE78nnn/GSE78220/soft/GSE78220_family.soft.gz"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_with_resume(url: str, partial: Path) -> None:
    """Resume a partial HTTP download when the server honors byte ranges."""
    start = partial.stat().st_size if partial.exists() else 0
    request = Request(url, headers={"Range": f"bytes={start}-"} if start else {})
    with urlopen(request) as response:
        status = getattr(response, "status", 200)
        mode = "ab" if start and status == 206 else "wb"
        if mode == "wb" and start:
            print("Server did not honor Range; restarting this file.", flush=True)
        with partial.open(mode) as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for filename, url in FILES.items():
        target = RAW_DIR / filename
        if target.exists():
            action = "reused_existing"
        else:
            partial = target.with_suffix(target.suffix + ".partial")
            print(f"Downloading {filename}", flush=True)
            download_with_resume(url, partial)
            partial.replace(target)
            action = "downloaded"
        entries.append(
            {
                "filename": filename,
                "url": url,
                "action": action,
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
            }
        )
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Public processed GEO files only; no controlled-access raw reads.",
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
