#!/usr/bin/env python3
"""Regenerate the figures the paper includes, in its own house style.

`make_paper_figures.py` renders every figure into `outputs/paper_figures` in a
plain matplotlib style. The paper includes `paper/media` instead, so these four
are rebuilt here from the same frozen outputs with the house palette and layout:
image3 (access sweep), image4 (index components), image12 (claim composition by
era), image9 (pipeline) and image7 (case-mix slopegraph). The remaining four
media figures carry no value that has changed since they were drawn.

Run after `make reproduce`; `make figures` invokes it.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import Counter

from matplotlib.colors import Normalize
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "media"

NAVY, TEAL, GOLD = "#1f3a5f", "#219288", "#c9a227"
PURPLE, RED, GREY = "#7b4f9d", "#c0392b", "#5a6672"
BLUE = "#2c7fb8"
FILL = {NAVY: "#dde3ea", TEAL: "#dcefec", GOLD: "#fbf1d9",
        PURPLE: "#ece2f2", RED: "#f7e3e0", GREY: "#e9ecee"}


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote paper/media/{name}")


def schelling():
    """Access sweep. The x label names e as a parameter, not a probability:
    denial is g(1-e), so e is monotone in access but is not the realized
    admission rate."""
    df = pd.DataFrame(json.load((ROOT / "outputs/schelling_scenarios.json")
                                .open())["phase_sweep"])
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    colors = {0.20: BLUE, 0.30: PURPLE, 0.45: RED}
    for tol, g in df.groupby("tolerance"):
        g = g.sort_values("access")
        c = colors[round(float(tol), 2)]
        ax.fill_between(g.access, g.segregation_mean - g.segregation_sd,
                        g.segregation_mean + g.segregation_sd, color=c, alpha=.13, lw=0)
        ax.plot(g.access, g.segregation_mean, marker="o", ms=5, lw=2.1, color=c)
        # Label each curve at its right end rather than in a legend box.
        ax.annotate(rf"$\tau$ = {tol:.2f}", xy=(g.access.iloc[-1], g.segregation_mean.iloc[-1]),
                    xytext=(8, 0), textcoords="offset points", va="center",
                    color=c, fontsize=10, weight="bold")
    ax.set_xticks(sorted(df.access.unique()))
    ax.set_xlabel("Access parameter $e$  (higher means fewer gatekeeping denials)", fontsize=10)
    ax.set_ylabel("Mean same-type neighbor share  (segregation)", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.set_xlim(df.access.min() - .03, df.access.max() + .10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="0.9", lw=.7)
    ax.set_axisbelow(True)
    save(fig, "image3.png")


def feii_components():
    """Circuit x component heatmap. The paper's point beside this figure is that
    a circuit high on one component need not be high on another, which the
    composite view cannot show."""
    df = pd.read_csv(ROOT / "data/processed/feii_panel.csv")
    df = df[df.unit_type == "circuit"]
    cols = ["z_opinion_volume", "z_outcome_cue_rate", "z_remedy_cue_intensity"]
    t = df.groupby("unit")[cols + ["FEII"]].mean().sort_values("FEII")
    m = t[cols].to_numpy()
    lim = float(np.nanmax(np.abs(m)))
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    im = ax.imshow(m, aspect="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > .62 * lim else "0.15")
    ax.set_xticks(range(3), ["Opinion\nvolume (z)", "Outcome-cue\nrate (z)",
                             "Remedy-cue\nintensity (z)"], fontsize=9)
    ax.set_yticks(range(len(t.index)), [f"C{int(u)}" for u in t.index], fontsize=9)
    ax.set_ylabel("Circuit (ordered by mean FEII)", fontsize=9.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=.046, pad=.03)
    cb.set_label("z-score vs. corpus mean", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    save(fig, "image4.png")


def eras():
    """Claim composition by era, drawn straight from era_stability.csv so the
    plotted values and the appendix text cannot drift apart."""
    df = pd.read_csv(ROOT / "outputs/validation/era_stability.csv")
    series = [("disparate_treatment", "Disparate treatment", NAVY),
              ("reasonable_accommodation", "Reasonable accommodation", TEAL),
              ("disparate_impact", "Disparate impact", RED),
              ("refusal_rent_sell", "Refusal / steering", GOLD),
              ("zoning_exclusionary", "Exclusionary zoning", "#8aa4b8")]
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    x = np.arange(len(df))
    for col, label, c in series:
        ax.plot(x, df[col], marker="o", ms=5, lw=2.1, color=c)
        ax.annotate(label, xy=(x[-1], df[col].iloc[-1]), xytext=(9, 0),
                    textcoords="offset points", va="center", color=c,
                    fontsize=9, weight="bold")
    ax.set_xticks(x, df.era, fontsize=9)
    ax.set_xlim(-.12, len(df) - 1 + .95)
    ax.set_ylim(0, .62)
    ax.set_ylabel("Share of opinions asserting claim", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="0.9", lw=.7)
    ax.set_axisbelow(True)
    save(fig, "image12.png")


def pipeline():
    """Nine-stage forward pass. The old version closed on a two-way-FE block;
    the merge yields eight one-year cells and no panel model is fitted, so the
    terminal block is the estimability stop."""
    fig, ax = plt.subplots(figsize=(10.0, 10.2))
    ax.set_xlim(0, 118); ax.set_ylim(-5, 102); ax.axis("off")

    def box(x, y, w, h, title, sub, color):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                    boxstyle="square,pad=0", fc=FILL[color],
                                    ec=color, lw=1.6, zorder=2))
        ax.text(x, y + h * .17, title, ha="center", va="center", fontsize=10.5,
                weight="bold", color=color, zorder=3)
        ax.text(x, y - h * .22, sub, ha="center", va="center", fontsize=9,
                color="0.15", zorder=3)

    def arrow(x1, y1, x2, y2, color):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=1,
                    arrowprops=dict(arrowstyle="-|>", lw=1.7, color=color,
                                    shrinkA=0, shrinkB=0))

    def edge(x, y, text, color):
        ax.text(x, y, text, ha="left", va="center", fontsize=8.4, style="italic", color=color)

    # Four lanes, left to right: the gold set, the main column, the edge labels,
    # and the housing branch. The container is sized around the boxes it holds
    # rather than the other way round, so the purple box cannot spill out of it.
    GX, GW = 11, 21            # blind gold set   -> spans  0.5..21.5
    CX, CW = 48, 44            # main column      -> spans   26..70
    LX     = 73                # edge-label lane
    HX, HW = 96, 35            # housing branch   -> spans 78.5..113.5
    BOXTOP, BOXBOT = 94, 84    # input row
    CONT_L, CONT_R = 23, 116   # container must enclose CX and HX boxes

    ax.add_patch(FancyBboxPatch((CONT_L, 82.5), CONT_R - CONT_L, 16.5,
                                boxstyle="square,pad=0", fc="#f4f5f7", ec=GREY,
                                lw=1.3, ls="--", zorder=0))
    ax.text(CONT_L + 2.5, 96.5, "Input", fontsize=10, style="italic", color=GREY, va="center")
    box(CX, 89, CW, 10, "Federal court opinions", "CourtListener bulk dumps", NAVY)
    box(HX, 89, HW, 10, "Housing & lending data", "ACS tracts  (+ HMDA)", PURPLE)

    box(CX, 69, CW, 11, "FHA opinion corpus",
        "NOS-443: 757 clusters\n751 full text $\\rightarrow$ 417 substantive", NAVY)
    arrow(CX, BOXBOT, CX, 74.8, NAVY)
    edge(LX, 78.0, "ingest $\\rightarrow$ PostgreSQL;\ncircuit crosswalk;\nfull-text recovery   §3", NAVY)

    box(CX, 50, CW, 11, "Structured doctrinal record",
        "claims · framework · strictness", TEAL)
    arrow(CX, 63.5, CX, 55.8, TEAL)
    edge(LX, 59.5, "weak supervision:\nlexicons + rules   §4.1", TEAL)
    box(GX, 50, GW, 12, "Blind gold set", "n = 93\nvalidation §4.4", GREY)
    arrow(GX + GW / 2, 50, CX - CW / 2 - 0.6, 50, GREY)

    box(CX, 31, CW, 11, "FEII", "circuit × year enforcement index", GOLD)
    arrow(CX, 44.5, CX, 36.8, GOLD)
    edge(LX, 40.5, "aggregate; EB shrinkage;\nz-scored comp.   §4.2", GOLD)

    box(CX, 16, CW, 11, "Circuit–vintage merge", "8 cells, 2022 only", GOLD)
    arrow(CX, 25.5, CX, 22.3, GOLD)
    edge(LX, 22, "county $\\rightarrow$ circuit\nweights   §4.3", PURPLE)
    arrow(HX, BOXBOT, HX, 16, PURPLE)
    arrow(HX, 16, CX + CW / 2 + 0.6, 16, PURPLE)

    # Terminal block is an estimability check, not an estimate.
    ax.add_patch(FancyBboxPatch((CONT_L, -4), CONT_R - CONT_L, 10,
                                boxstyle="square,pad=0", fc="#fbf0ee", ec=RED,
                                lw=1.4, ls="--", zorder=0))
    ax.text(CONT_L + 2.5, 3.6, "Feasibility stop", fontsize=9.5, style="italic",
            color=RED, va="center")
    ax.text((CONT_L + CONT_R) / 2, -1.2,
            "no within-unit variation  ·  no panel model fitted   §4.3",
            ha="center", va="center", fontsize=9.5, color=RED, zorder=3)
    arrow(CX, 10.5, CX, 6.4, RED)
    save(fig, "image9.png")


def casemix():
    """Circuit ranks before and after case-mix adjustment.

    Ranks are integers, so circuits sharing a rank would print their labels on
    top of one another; tied circuits are fanned symmetrically about the shared
    rank so every label stays legible.
    """
    slope_navy, slope_red = "#12395f", "#8b1a24"
    df = (pd.read_csv(ROOT / "outputs/validation/circuit_casemix.csv")
          .rename(columns={"Unnamed: 0": "circuit"}))

    def offsets(column):
        seen, used, out = Counter(df[column]), Counter(), {}
        for i, value in df[column].items():
            n = seen[value]
            out[i] = 0 if n == 1 else (used[value] - (n - 1) / 2) * 0.52
            used[value] += 1
        return out

    left, right = offsets("raw_rank"), offsets("adj_rank")
    fig, ax = plt.subplots(figsize=(4.4, 5.0))
    for i, row in df.iterrows():
        ends = ([0, 1], [row.raw_rank, row.adj_rank])
        ax.plot(*ends, color=slope_red, linewidth=1.8, alpha=.9, zorder=2)
        ax.plot(*ends, linestyle="none", marker="o", markersize=5,
                markerfacecolor=slope_navy, markeredgecolor="white",
                markeredgewidth=.8, zorder=3)
        # int() belongs here, not on the column: iterrows coerces each row to a
        # single dtype, so row.circuit arrives as a float and prints as "C7.0".
        label = f"C{int(row.circuit)}"
        ax.text(-.06, row.raw_rank + left[i], label,
                ha="right", va="center", color=slope_navy)
        ax.text(1.06, row.adj_rank + right[i], label,
                ha="left", va="center", color=slope_navy)
    ax.set_xticks([0, 1], ["Raw rank", "Case-mix-adjusted rank"])
    ax.set_yticks([1, 3, 5, 7, 9, 11])
    ax.set(ylabel="Circuit rank", xlim=(-.34, 1.34), ylim=(11.9, .3))
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    save(fig, "image7.png")


CLAIMS = ["disparate_treatment", "disparate_impact", "refusal_rent_sell",
          "reasonable_accommodation", "zoning_exclusionary"]


def _routes():
    """Precision and recall for the three extraction routes on the overlap."""
    val = ROOT / "data" / "validation"
    gold = {str(x["case_id"]): x["claims"]
            for x in json.load((val / "gold_human_codings.json").open())["primary"]}
    frozen = json.load((val / "llm_majority_votes.json").open())["goldVote"]
    rule = {r["cluster_id"]: {k: int(r["claim_" + k]) for k in CLAIMS}
            for _, r in pd.read_csv(
                ROOT / "outputs/validation/gold_machine_labels.csv",
                dtype={"cluster_id": str}).iterrows()}
    votes = {}
    for name in ("qwen32b_labels_full.jsonl", "qwen32b_labels_remainder.jsonl"):
        for line in (val / name).open():
            r = json.loads(line)
            if r.get("ok"):
                votes.setdefault(str(r["cluster_id"]), []).append(r)
    qwen = {c: {k: int(sum(r[k] for r in rs) * 2 > len(rs)) for k in CLAIMS}
            for c, rs in votes.items()}

    ids = sorted(set(gold) & set(frozen) & set(rule) & set(qwen))

    def pr(pred, keys):
        tp = fp = fn = 0
        for c in ids:
            for k in keys:
                p, g = int(pred[c][k]), int(gold[c].get(k, 0))
                tp += p & g; fp += p & (1 - g); fn += (1 - p) & g
        return tp / (tp + fp), tp / (tp + fn)

    def counts(pred, keys):
        tp = fp = fn = 0
        for c in ids:
            for k in keys:
                p, g = int(pred[c][k]), int(gold[c].get(k, 0))
                tp += p & g; fp += p & (1 - g); fn += (1 - p) & g
        return tp, fp, fn

    routes = [(name, counts(pred, CLAIMS), counts(pred, ["disparate_impact"]))
              for name, pred in (("Rule detector", rule),
                                 ("qwen3:32b (open, 4-bit)", qwen),
                                 ("Opus 4.8 (frozen)", frozen))]
    return routes, pr, len(ids)


def _sans():
    """Arial where the host has it, matplotlib's own sans otherwise."""
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Arial", "Helvetica", "DejaVu Sans"):
        if name in have:
            return {"family": "sans-serif", "fontname": name}
    return {"family": "sans-serif"}


def open_baseline():
    """Extraction diagnostics by route, shaded so the pattern reads as a picture.

    The values are the ones a reviewer would check, so they stay printed; the
    shading is there to make one cell obvious -- the rule detector's impact
    precision, the only value on the board in the low band. Every string is set
    in the same unbolded sans as the tick labels on the other figures, so the
    matrix does not announce itself against them.
    """
    routes, pr, n = _routes()
    ramp = plt.get_cmap("RdYlGn")
    norm = Normalize(vmin=.35, vmax=1.0)
    face = _sans()
    scopes = [(1, "All five constructs"), (2, "Disparate impact alone")]

    fig, ax = plt.subplots(figsize=(7.2, 2.35))
    gutter = .80
    for col, (idx, _) in enumerate(scopes):
        for m, metric in enumerate(("P", "R", "F1")):
            x = col * (3 + gutter) + m
            for row, (name, *scores) in enumerate(routes):
                tp, fp, fn = scores[idx - 1]
                prec = tp / (tp + fp) if tp + fp else 0.0
                rec = tp / (tp + fn) if tp + fn else 0.0
                value = {"P": prec, "R": rec,
                         "F1": 2 * prec * rec / (prec + rec)}[metric]
                rgba = ramp(norm(value))
                # Contiguous cells ruled in black, the ordinary heatmap grid;
                # detached tiles read as a pictogram instead of a matrix.
                ax.add_patch(Rectangle((x, -row - 1), 1, 1, fc=rgba,
                                       ec="black", lw=.8))
                # Relative luminance decides the ink: both ends of this ramp are
                # dark, so a fixed threshold on the value would misfire at 1.00.
                lum = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
                ax.text(x + .5, -row - .5, f"{value:.2f}".lstrip("0"),
                        ha="center", va="center", fontsize=9.5,
                        color="white" if lum < .5 else "#1a1a1a", **face)
            ax.text(x + .5, -3.14, metric, ha="center", va="top", fontsize=9,
                    color="0.4", **face)
        ax.text(col * (3 + gutter) + 1.5, .22, scopes[col][1], ha="center",
                va="bottom", fontsize=9.5, color="0.2", **face)
    for row, (name, *_) in enumerate(routes):
        ax.text(-.28, -row - .5, name, ha="right", va="center", fontsize=9.5,
                **face)
    # Each scope carries its own frame; the gap between them does the dividing.
    for col in range(2):
        ax.add_patch(Rectangle((col * (3 + gutter), -3), 3, 3, fc="none",
                               ec="black", lw=1.4, zorder=5))
    ax.set_xlim(-3.5, 2 * 3 + gutter + .15)
    ax.set_ylim(-3.62, .62)
    ax.axis("off")
    ax.set_aspect("equal")
    save(fig, "image19.png")
    print(f"    (scored on {n} clusters)")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    schelling()
    feii_components()
    eras()
    pipeline()
    casemix()
    open_baseline()
