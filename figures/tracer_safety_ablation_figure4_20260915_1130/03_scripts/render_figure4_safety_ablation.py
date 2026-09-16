#!/usr/bin/env python3
"""Render Figure 4 from the frozen TRACER factorial-suite summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


FIGURE_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = FIGURE_ROOT.parents[1]

COLORS = {
    "ink": "#17213D",
    "slate": "#5E687D",
    "grid": "#D7DFEC",
    "teal": "#0A807A",
    "teal_pale": "#E8F7F4",
    "amber": "#D7902F",
    "amber_pale": "#FFF2D9",
    "red": "#C93E40",
    "red_pale": "#FFF0F0",
    "block": "#E7ECF3",
    "blue": "#235EAF",
}


def _row_by_method(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    matches = [row for row in rows if row["method"] == method]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one summary row for {method!r}, found {len(matches)}.")
    return matches[0]


def collect_plot_data(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate every number shown in the figure."""
    complete = summary["complete_draft_comparison"]
    provenance = summary["provenance_omission_comparison"]
    expected_complete = {
        "Full TRACER": 0,
        "TRACER without transport gate": 1,
        "TRACER without source-independence gate": 1,
        "TRACER without all-cohort FDR gate": 1,
        "Naive counting baseline": 7,
    }
    observed_complete = {
        method: _row_by_method(complete, method)["unsafe_high_n"]
        for method in expected_complete
    }
    if observed_complete != expected_complete:
        raise ValueError(f"Unexpected complete-draft unsafe-HIGH counts: {observed_complete}")
    if any(_row_by_method(complete, method)["n_expected_low"] != 31 for method in expected_complete):
        raise ValueError("Complete-draft panel must use the frozen denominator of 31 ineligible cases.")
    expected_provenance = {
        "Full TRACER": 0,
        "TRACER without provenance coverage": 1,
    }
    observed_provenance = {
        method: _row_by_method(provenance, method)["unsafe_high_n"]
        for method in expected_provenance
    }
    if observed_provenance != expected_provenance:
        raise ValueError(f"Unexpected provenance-attack unsafe-HIGH counts: {observed_provenance}")
    if any(_row_by_method(provenance, method)["n_expected_low"] != 32 for method in expected_provenance):
        raise ValueError("Provenance panel must use the frozen denominator of 32 omission drafts.")
    critical = summary["critical_cell_packet_ids"]
    required_critical = {
        "eligible_positive_control",
        "cross_measurement_only_failure",
        "same_source_only_failure",
        "all_cohort_fdr_only_failure",
    }
    if set(critical) != required_critical:
        raise ValueError(f"Unexpected critical-cell map: {critical}")
    return {
        "complete_labels": ["Full\nTRACER", "– Transport", "– Source", "– FDR", "Naive\ncounting"],
        "complete_values": [0, 1, 1, 1, 7],
        "complete_annotations": ["0/31", "1/31", "1/31", "1/31", "7/31"],
        "provenance_labels": ["Full\nTRACER", "– Provenance"],
        "provenance_values": [0, 1],
        "provenance_annotations": ["0/32", "1/32"],
        "critical_packet_ids": critical,
        "critical_matrix": np.array(
            [
                [1, 1, 1, 1, 1],
                [0, 1, 0, 0, 1],
                [0, 0, 1, 0, 1],
                [0, 0, 0, 1, 1],
            ],
            dtype=int,
        ),
        "critical_row_labels": [
            "Eligible\n(all pass)",
            "Cross-measurement\nfailure",
            "Same-source\nfailure",
            "All-cohort FDR\nfailure",
        ],
        "critical_column_labels": ["Full", "– T", "– S", "– FDR", "Naive"],
    }


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.15,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=15,
        fontweight="bold",
        color="white",
        ha="center",
        va="center",
        bbox={"boxstyle": "circle,pad=0.25", "facecolor": COLORS["blue"], "edgecolor": "none"},
    )


def _style_axis(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(COLORS["ink"])
    ax.spines[["left", "bottom"]].set_linewidth(1.25)
    ax.tick_params(axis="both", colors=COLORS["ink"], labelsize=9)
    ax.yaxis.grid(True, color=COLORS["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def render_figure(summary_path: Path, output_dir: Path) -> list[Path]:
    source_bytes = summary_path.read_bytes()
    summary = json.loads(source_bytes.decode("utf-8"))
    data = collect_plot_data(summary)
    output_dir.mkdir(parents=True, exist_ok=True)
    for generated_directory in ("01_data", "02_specs", "05_qa"):
        (FIGURE_ROOT / generated_directory).mkdir(exist_ok=True)
    shutil.copy2(summary_path, FIGURE_ROOT / "01_data" / "factorized_safety_benchmark_summary_v1.json")

    plt.rcParams.update(
        {
            "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"],
            "font.size": 10,
            "svg.fonttype": "none",
            "axes.titleweight": "bold",
        }
    )
    fig = plt.figure(figsize=(14.2, 5.45), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=[1.33, 0.92, 1.42], wspace=0.48)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[0, 2])

    # A. Complete-draft gate ablation.
    x_a = np.arange(len(data["complete_values"]))
    bars_a = ax_a.bar(
        x_a,
        data["complete_values"],
        color=[COLORS["teal"], COLORS["amber"], COLORS["amber"], COLORS["amber"], COLORS["red"]],
        edgecolor=COLORS["ink"],
        linewidth=0.9,
        width=0.68,
    )
    for bar, annotation in zip(bars_a, data["complete_annotations"]):
        ax_a.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height(), 0) + 0.19,
            annotation,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=COLORS["ink"],
        )
    ax_a.set_ylim(0, 8.25)
    ax_a.set_yticks([0, 2, 4, 6, 8])
    ax_a.set_ylabel("Unsafe HIGH count", fontsize=10, color=COLORS["ink"])
    ax_a.set_xticks(x_a, data["complete_labels"])
    ax_a.set_title("Complete drafts\n31 ineligible packets", fontsize=11, color=COLORS["ink"], pad=10)
    _style_axis(ax_a)
    _panel_label(ax_a, "A")

    # B. Provenance omission attack remains a separate denominator.
    x_b = np.arange(len(data["provenance_values"]))
    bars_b = ax_b.bar(
        x_b,
        data["provenance_values"],
        color=[COLORS["teal"], COLORS["amber"]],
        edgecolor=COLORS["ink"],
        linewidth=0.9,
        width=0.6,
    )
    for bar, annotation in zip(bars_b, data["provenance_annotations"]):
        ax_b.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height(), 0) + 0.07,
            annotation,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=COLORS["ink"],
        )
    ax_b.set_ylim(0, 1.35)
    ax_b.set_yticks([0, 1])
    ax_b.set_ylabel("Unsafe HIGH count", fontsize=10, color=COLORS["ink"])
    ax_b.set_xticks(x_b, data["provenance_labels"])
    ax_b.set_title("Provenance-omission attack\n32 incomplete drafts", fontsize=11, color=COLORS["ink"], pad=10)
    _style_axis(ax_b)
    _panel_label(ax_b, "B")

    # C. Named single-failure cells make the module attribution inspectable.
    cmap = ListedColormap([COLORS["block"], COLORS["teal"]])
    ax_c.imshow(data["critical_matrix"], cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax_c.set_xticks(np.arange(5), data["critical_column_labels"], fontsize=9)
    ax_c.set_yticks(np.arange(4), data["critical_row_labels"], fontsize=9)
    for row in range(4):
        for col in range(5):
            decision = "HIGH" if data["critical_matrix"][row, col] else "BLOCK"
            ax_c.text(
                col,
                row,
                decision,
                ha="center",
                va="center",
                fontsize=8.5,
                fontweight="bold",
                color="white" if decision == "HIGH" else COLORS["slate"],
            )
    ax_c.set_title("Predeclared critical cells\n1 = HIGH is permitted", fontsize=11, color=COLORS["ink"], pad=10)
    ax_c.set_xticks(np.arange(-0.5, 5, 1), minor=True)
    ax_c.set_yticks(np.arange(-0.5, 4, 1), minor=True)
    ax_c.grid(which="minor", color="white", linewidth=1.7)
    ax_c.tick_params(which="minor", bottom=False, left=False)
    ax_c.spines[:].set_visible(False)
    ax_c.tick_params(axis="both", length=0, colors=COLORS["ink"])
    ax_c.legend(
        handles=[
            Patch(facecolor=COLORS["teal"], edgecolor="none", label="HIGH permitted"),
            Patch(facecolor=COLORS["block"], edgecolor="none", label="BLOCK / ABSTAIN"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
        frameon=False,
        fontsize=8.8,
    )
    _panel_label(ax_c, "C")

    fig.suptitle(
        "Each evidence-graph gate blocks a distinct pre-specified unsafe escalation",
        x=0.5,
        y=0.99,
        fontsize=16,
        fontweight="bold",
        color=COLORS["ink"],
    )
    fig.text(
        0.5,
        0.018,
        "Frozen 2⁵ deterministic enumeration. Exact finite-suite counts only; no p values or confidence intervals.",
        ha="center",
        fontsize=9.2,
        color=COLORS["slate"],
    )
    fig.subplots_adjust(left=0.06, right=0.985, top=0.79, bottom=0.23)

    base = output_dir / "tracer_figure4_safety_ablation"
    outputs = []
    for suffix, dpi in (("png", 320), ("pdf", 320), ("svg", 320)):
        destination = base.with_suffix(f".{suffix}")
        fig.savefig(destination, dpi=dpi, facecolor="white")
        outputs.append(destination)
    plt.close(fig)

    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    (FIGURE_ROOT / "02_specs" / "figure4_plot_data_v1.json").write_text(
        json.dumps(
            {
                "source_summary": str(summary_path),
                "source_summary_sha256": source_sha256,
                "values": {
                    "complete_draft_unsafe_high_counts": data["complete_values"],
                    "provenance_omission_unsafe_high_counts": data["provenance_values"],
                    "critical_matrix": data["critical_matrix"].tolist(),
                },
                "critical_packet_ids": data["critical_packet_ids"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (FIGURE_ROOT / "05_qa" / "figure_caption.md").write_text(
        "Figure 4. Safety ablation on the frozen factorized suite. (A) Across 31 ineligible complete drafts, "
        "Full TRACER produced no unsafe HIGH decisions; removing transport, source-independence, or all-cohort-FDR "
        "gating each admitted one predeclared unsafe cell, whereas the naive counting comparator admitted seven. "
        "(B) Across 32 deliberately incomplete provenance-omission drafts, Full TRACER produced no unsafe HIGH decision, "
        "whereas removing provenance coverage admitted one. (C) The all-pass control and three named single-failure cells "
        "show which exact gate removal permits each escalation. This is a finite deterministic implementation verification, "
        "not an LLM benchmark, biomedical finding, clinical-utility analysis, or population safety estimate.\n",
        encoding="utf-8",
    )
    (FIGURE_ROOT / "05_qa" / "QA_notes.md").write_text(
        "Verification\n\n"
        f"- Source: {summary_path}\n"
        f"- Source SHA-256: {source_sha256}\n"
        "- Panel A denominator: 31 ineligible complete drafts.\n"
        "- Panel B denominator: 32 ineligible omission drafts.\n"
        "- Panel C values are binary decision states for four predeclared critical cells.\n"
        "- PNG, PDF, and SVG were rendered from the same exact source values.\n"
        "- SVG uses editable vector text and plot primitives; it contains no generated image assets.\n",
        encoding="utf-8",
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=APP_ROOT / "results" / "factorized_safety_benchmark_summary_v1.json",
    )
    parser.add_argument("--output-dir", type=Path, default=FIGURE_ROOT / "04_output")
    args = parser.parse_args()
    for path in render_figure(args.summary, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
