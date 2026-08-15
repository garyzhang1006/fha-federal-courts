#!/usr/bin/env python3
"""Generate every figure included by the FHA-443 paper from frozen outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fha.prevalence import mcnemar_power  # noqa: E402

OUT = ROOT / "outputs" / "paper_figures"
VAL = ROOT / "outputs" / "paper" / "validation"
BLUE, RED, PURPLE, GOLD, TEAL = "#2166ac", "#b2182b", "#7b3294", "#d4a72c", "#218c83"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def volume():
    records = [json.loads(line) for line in (ROOT / "data/processed/paper_corpus.jsonl").open()
               if line.strip()]
    years = pd.Series([row.get("year") for row in records]).dropna().astype(int)
    counts = years.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.fill_between(counts.index, counts.values, color=BLUE, alpha=.18)
    ax.plot(counts.index, counts.values, color=BLUE, linewidth=2)
    ax.set(xlabel="Decision year", ylabel="Full-text opinion clusters")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "image5.png")


def power():
    summary = json.load((VAL / "prevalence_summary.json").open())
    p = summary["power"]
    sizes = np.arange(25, 651, 5)
    values = [mcnemar_power(p["n10"], p["n01"], summary["n_substantive"], int(n))
              for n in sizes]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(sizes, values, color=PURPLE, linewidth=2.5)
    ax.axhline(.8, color="0.45", linestyle="--", linewidth=1)
    ax.axvline(p["p80"]["n_substantive"], color=RED, linestyle="--", linewidth=1)
    ax.scatter([summary["n_substantive"]], [p["power_at_observed"]], color=BLUE, zorder=3)
    ax.text(summary["n_substantive"] + 10, p["power_at_observed"],
            f"n={summary['n_substantive']}, power={p['power_at_observed']:.3f}")
    ax.set(xlabel="Substantive cases", ylabel="Exact McNemar power", ylim=(0, 1.02))
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "image2.png")


def corrections():
    df = pd.read_csv(VAL / "prevalence_random.csv")
    labels = {
        "disparate_treatment": "Disparate treatment",
        "reasonable_accommodation": "Reasonable accommodation",
        "disparate_impact": "Disparate impact",
        "refusal_rent_sell": "Refusal / steering",
        "zoning_exclusionary": "Exclusionary zoning",
    }
    df["order"] = df.construct.map({name: i for i, name in enumerate(labels)})
    df = df.sort_values("order")
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9, 5.8))
    for offset, column, color, label in [
        (-.22, "regex_share_417", "#b9b9b9", "Raw regex (n=417)"),
        (0, "llm_share", BLUE, "LLM majority draw (n=76)"),
        (.22, "regex_share_417_corrected", RED, "Precision-recall correction"),
    ]:
        values = 100 * df[column]
        ax.barh(y + offset, values, height=.2, color=color, label=label)
        for yi, value in zip(y + offset, values):
            ax.text(value + .7, yi, f"{value:.0f}", va="center", color=color)
    ax.set_yticks(y, [labels[name] for name in df.construct])
    ax.invert_yaxis()
    ax.set(xlabel="Asserted-claim prevalence (%)", xlim=(0, 65))
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "image6.png")


def casemix():
    df = pd.read_csv(ROOT / "outputs/validation/circuit_casemix.csv") \
        .rename(columns={"Unnamed: 0": "circuit"})
    fig, ax = plt.subplots(figsize=(7, 6))
    for _, row in df.iterrows():
        ax.plot([0, 1], [row.raw_rank, row.adj_rank], color="0.72", linewidth=1.5)
        ax.text(-.03, row.raw_rank, str(row.circuit), ha="right", va="center")
        ax.text(1.03, row.adj_rank, str(row.circuit), ha="left", va="center")
    ax.set_xticks([0, 1], ["Raw rank", "Case-mix-adjusted rank"])
    ax.set(ylabel="Circuit rank", xlim=(-.18, 1.18), ylim=(11.6, .4))
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    save(fig, "image7.png")


def feii():
    df = pd.read_csv(ROOT / "data/processed/feii_panel.csv")
    table = df.pivot(index="unit", columns="year", values="FEII")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    limit = float(np.nanmax(np.abs(table.to_numpy())))
    image = ax.imshow(table, aspect="auto", cmap="RdBu_r", vmin=-limit, vmax=limit)
    ax.set_yticks(range(len(table.index)), table.index)
    years = list(table.columns)
    ticks = np.linspace(0, len(years) - 1, min(7, len(years)), dtype=int)
    ax.set_xticks(ticks, [years[i] for i in ticks], rotation=35, ha="right")
    ax.set(xlabel="Year", ylabel="Circuit")
    fig.colorbar(image, ax=ax, label="FEII (standardized)")
    save(fig, "image4.png")


def gates():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.axis("off")
    boxes = [
        (.18, .52, "Preference threshold\n(local tolerance)"),
        (.50, .52, "Cross-group access\nbarrier"),
        (.82, .52, "Move admitted"),
    ]
    for x, y, label in boxes:
        ax.text(x, y, label, ha="center", va="center", fontsize=12,
                bbox=dict(boxstyle="round,pad=.6", fc="#eef3f5", ec="#38566d", lw=1.5))
    for x1, x2 in ((.29, .39), (.61, .71)):
        ax.annotate("", xy=(x2, .55), xytext=(x1, .55),
                    arrowprops=dict(arrowstyle="->", lw=2, color="#38566d"))
    ax.text(.5, .82, "Access levels are illustrative and swept independently of measured FEII",
            ha="center", va="center", color="#38566d", fontsize=11)
    ax.text(.5, .18, "Sorting changes only when both gates permit a move",
            ha="center", va="center", color=RED, fontsize=12)
    save(fig, "image18.png")


def schelling():
    data = json.load((ROOT / "outputs/schelling_scenarios.json").open())
    df = pd.DataFrame(data["phase_sweep"])
    fig, ax = plt.subplots(figsize=(8.2, 5.7))
    colors = {0.2: BLUE, 0.3: PURPLE, 0.45: RED}
    for tolerance, group in df.groupby("tolerance"):
        group = group.sort_values("access")
        color = colors[tolerance]
        ax.plot(group.access, group.segregation_mean, marker="o", linewidth=2.5,
                color=color, label=rf"$\tau={tolerance:.2f}$")
        ax.fill_between(group.access, group.segregation_mean - group.segregation_sd,
                        group.segregation_mean + group.segregation_sd, color=color, alpha=.12)
    ax.set(xlabel=r"Access parameter $e$ (higher means fewer gatekeeping denials)",
           ylabel="Mean same-type neighbor share")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "image3.png")


def eras():
    df = pd.read_csv(ROOT / "outputs/validation/era_stability.csv")
    columns = ["disparate_treatment", "reasonable_accommodation", "disparate_impact",
               "refusal_rent_sell", "zoning_exclusionary"]
    labels = ["Treatment", "Accommodation", "Impact", "Refusal", "Zoning"]
    fig, ax = plt.subplots(figsize=(8.4, 5.3))
    for column, label in zip(columns, labels):
        ax.plot(df.era, 100 * df[column], marker="o", linewidth=2, label=label)
    ax.set(xlabel="Decision era", ylabel="Rule-positive share (%)", ylim=(0, 60))
    ax.legend(frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "image12.png")


def pipeline():
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.axis("off")
    nodes = [
        (.5, .9, "Frozen full-text snapshot\n751 clusters", "#e7edf3"),
        (.5, .73, "Deterministic substantive rule\n417 clusters", "#e4f2ef"),
        (.5, .56, "Extractor + frozen validation\nhuman gold and model labels", "#e4f2ef"),
        (.28, .36, "Circuit-year FEII\n115 cells", "#fff4d8"),
        (.72, .36, "Circuit doctrine split\n417 clusters", "#eee7f2"),
        (.28, .17, "Housing merge\n8 cells, 2022 only", "#fff4d8"),
        (.72, .17, "Seeded Schelling scope\nno causal estimate", "#f7e8e4"),
    ]
    for x, y, label, color in nodes:
        ax.text(x, y, label, ha="center", va="center", fontsize=11,
                bbox=dict(boxstyle="round,pad=.55", fc=color, ec="#38566d", lw=1.4))
    for start, end in [((.5, .85), (.5, .78)), ((.5, .68), (.5, .61)),
                       ((.46, .51), (.31, .41)), ((.54, .51), (.69, .41)),
                       ((.28, .31), (.28, .22))]:
        ax.annotate("", xy=end, xytext=start,
                    arrowprops=dict(arrowstyle="->", lw=1.8, color="#38566d"))
    ax.text(.28, .055, "Feasibility stop: one year, no TWFE", ha="center", color=RED,
            fontsize=11, weight="bold")
    save(fig, "image9.png")


def main():
    for build in (volume, power, corrections, casemix, feii, gates, schelling, eras, pipeline):
        build()
    expected = {f"image{n}.png" for n in (2, 3, 4, 5, 6, 7, 9, 12, 18)}
    created = {path.name for path in OUT.glob("*.png")}
    if created != expected:
        raise SystemExit(f"paper figure set mismatch: expected {sorted(expected)}, got {sorted(created)}")
    print(f"generated {len(created)} paper figures in {OUT}")


if __name__ == "__main__":
    main()
