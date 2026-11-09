"""
make_graphs.py - graphs from the result tables of calcium_multidrug.py (multidrug_results.xlsx).

HOW TO USE (in the experiment folder, after calcium_multidrug.py has run):
    python make_graphs.py
It asks a few questions ([brackets] = suggestion, ENTER accepts) and saves the graphs in
multidrug_results/graphs/. The analysis is NOT repeated: everything comes from the Excel file.

Graphs (all cells = the cells kept after the quality-control drug, e.g. KCl):
  1_traces_all_recordings   ΔF (F - F0) over time of every recording incl. the QC drug:
                            every cell in grey, their mean in black, // = washing (not imaged)
  2_pies_and_venn           one pie per drug (responders vs non-responders) + Venn diagram
                            of the overlap (2-3 drugs; 4 or more: bar chart of every combination)
  3_area_scatter            cell area per drug, every cell one dot (black = responder,
                            grey = non-responder), inside a bar outline
  4_area_responders_box     box-and-whisker of the cell area of the responders only
Graphs 3 and 4 need the cell size (cell_size.csv in the analysis).
"""

# ========================= SETTINGS = suggestions shown in [brackets] =========================
RESULTS_FILE = "multidrug_results/multidrug_results.xlsx"
UNIT = "dF"          # graph 1: dF (= F - F0, gray value) | dF_F0 (= ΔF / F0)
FORMAT = "png"       # png | pdf | svg
STEP = 0.5           # graphs 3 + 4: distance between two drugs
# ==============================================================================================

import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

INK = "#52514e"           # axis text
RULE = "#c9c8c2"          # axis lines, zero line
CELL_GREY = "#b9b8b2"     # graph 1: single cells
NONRESP = "#c9c8c2"       # graph 2: non-responder slice
DOT_NONRESP = "#bdbdbd"   # graph 3: non-responder dots
DRUG_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8f6bd6", "#6b8e23"]
TRACE_COLS = ("Frame", "Recording", "Time in recording (s)", "Experiment time (s)")


def clean(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(RULE)
    ax.tick_params(colors=INK)


def save(fig, out, name, fmt):
    path = out / f"{name}.{fmt}"
    fig.savefig(path, dpi=300 if fmt == "png" else None, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path.name}")


# ------------------------------------------------------------------ read the result tables
def load(xlsx, unit):
    x = pd.ExcelFile(xlsx)
    summary = pd.read_excel(x, "Summary")
    resp = pd.read_excel(x, "Responders", index_col=0)
    per_cell = pd.read_excel(x, "Per_cell", index_col=0)
    sheet = "Cell_traces_dF_F0" if unit == "dF_F0" else "Cell_traces_dF"
    traces = pd.read_excel(x, sheet)
    drugs = list(summary["Drug"].astype(str))
    qc_col = next((c for c in resp.columns if str(c).endswith("(quality control)")), None)
    qc = qc_col.replace(" (quality control)", "") if qc_col else None
    kept = resp.index[resp[drugs[0]].astype(str).isin(["yes", "no"])]
    acol = next((c for c in per_cell.columns if str(c).startswith("Area")), None)
    return dict(resp=resp.loc[kept], per_cell=per_cell, traces=traces, drugs=drugs, qc=qc,
                area=pd.to_numeric(per_cell.loc[kept, acol], errors="coerce") if acol else None,
                area_label=acol or "Cell area")


# ------------------------------------------------------------------ 1 traces of every recording
def g_traces(D, out, fmt, unit):
    tr = D["traces"]
    recs = list(dict.fromkeys(tr["Recording"]))          # experiment order, QC drug last
    cells = [c for c in tr.columns if c not in TRACE_COLS]
    widths = [tr.loc[tr.Recording == r, "Time in recording (s)"].max() + 1 for r in recs]
    fig, axs = plt.subplots(1, len(recs), figsize=(3.3 * len(recs) + 1, 4.6), sharey=True, squeeze=False,
                            gridspec_kw=dict(width_ratios=widths, wspace=0.12))
    axs = axs[0]
    for k, (ax, r) in enumerate(zip(axs, recs)):
        d = tr[tr.Recording == r]
        t = d["Experiment time (s)"].values
        ax.plot(t, d[cells].values, color=CELL_GREY, lw=0.5, alpha=0.6, zorder=1)
        ax.plot(t, d[cells].mean(axis=1).values, color="black", lw=2.2, zorder=3)
        ax.axhline(0, color=RULE, lw=0.8, zorder=0)
        ax.set_xlim(t[0], t[-1])
        ax.set_title(r + (" (QC)" if r == D["qc"] else ""), fontsize=11, color="#0b0b0b")
        clean(ax)
        if k > 0:
            ax.spines["left"].set_visible(False)
            ax.tick_params(left=False)
        if k < len(recs) - 1:                            # // break marks + washing time
            ax.spines["right"].set_visible(False)
            nxt = tr.loc[tr.Recording == recs[k + 1], "Experiment time (s)"].min()
            dt = t[1] - t[0] if len(t) > 1 else 1
            gap = nxt - t[-1] - dt
            kw = dict(transform=ax.transAxes, color=INK, clip_on=False, lw=1.2)
            for dx in (0.985, 1.025):
                ax.plot([dx - 0.015, dx + 0.015], [-0.03, 0.03], **kw)
            ax.text(1.005, -0.15, f"wash {gap:g} s", transform=ax.transAxes, ha="center", va="top",
                    fontsize=8, color=INK)
    axs[0].set_ylabel("ΔF/F0" if unit == "dF_F0" else "F − F0  (ΔF, gray value)", color=INK)
    fig.supxlabel("Experiment time (s)", color=INK, fontsize=10, y=-0.1)
    save(fig, out, "1_traces_all_recordings", fmt)


# ------------------------------------------------------------------ 2 pies + Venn
def _venn(ax, sets, n):
    names = list(sets)
    if len(names) == 2:
        centers, name_pos = [(-0.55, 0), (0.55, 0)], [(-1.15, 1.2), (1.15, 1.2)]
        regions = {(1, 0): (-0.95, 0), (0, 1): (0.95, 0), (1, 1): (0, 0)}
        lim_y, none_y = (-1.4, 1.55), -1.3
    else:
        centers, name_pos = [(-0.6, 0.35), (0.6, 0.35), (0, -0.62)], [(-1.3, 1.5), (1.3, 1.5), (0, -1.9)]
        regions = {(1, 0, 0): (-1.05, 0.6), (0, 1, 0): (1.05, 0.6), (0, 0, 1): (0, -1.15),
                   (1, 1, 0): (0, 0.82), (1, 0, 1): (-0.68, -0.35), (0, 1, 1): (0.68, -0.35),
                   (1, 1, 1): (0, 0.05)}
        lim_y, none_y = (-2.2, 1.85), -1.9
    for (cx, cy), col in zip(centers, DRUG_COLORS):
        ax.add_patch(Circle((cx, cy), 1.0, facecolor=col, alpha=.18, edgecolor=col, lw=2))
    for (px, py), nm in zip(name_pos, names):
        ax.text(px, py, f"{nm}\n{len(sets[nm])} responders", ha="center", va="center", fontsize=10,
                fontweight="bold", color=INK)
    for key, (px, py) in regions.items():
        ins = [s for s, b in zip(names, key) if b]
        outs = [s for s, b in zip(names, key) if not b]
        c = set.intersection(*[sets[s] for s in ins])
        if outs:
            c = c - set().union(*[sets[s] for s in outs])
        ax.text(px, py, f"{len(c)}\n{100 * len(c) / n:.0f}%", ha="center", va="center", fontsize=10)
    none = n - len(set().union(*sets.values()))
    ax.text(1.9, none_y, f"no drug: {none} ({100 * none / n:.0f}%)", ha="right", fontsize=9, color=INK)
    ax.set_xlim(-2, 2); ax.set_ylim(*lim_y); ax.set_aspect("equal"); ax.axis("off")


def _combinations(ax, r, n):
    combo = r["Responds to"].astype(str).value_counts()
    order = sorted(combo.index, key=lambda s: (s == "none", -s.count("+"), -combo[s]))
    y = np.arange(len(order))[::-1]
    ax.barh(y, combo[order].values, color=["#bdbdbd" if o == "none" else "black" for o in order], height=.6)
    for yy, v in zip(y, combo[order].values):
        ax.text(v + .3, yy, f"{v} ({100 * v / n:.0f}%)", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, order, fontsize=9)
    ax.set_xlabel("Number of cells", color=INK)
    clean(ax)


def g_pies_venn(D, out, fmt):
    r, drugs = D["resp"], D["drugs"]
    n = len(r)
    ncol = min(len(drugs), 4)
    nrow = int(np.ceil(len(drugs) / ncol))
    has_overlap = len(drugs) >= 2
    fig = plt.figure(figsize=(3.6 * ncol + 1.2, 3.3 * nrow + (5.8 if has_overlap else 0)))
    gs = fig.add_gridspec(nrow + (1 if has_overlap else 0), ncol,
                          height_ratios=[1] * nrow + ([1.6 * nrow if len(drugs) <= 3 else 1.2] if has_overlap else []),
                          hspace=0.15)
    for j, d in enumerate(drugs):
        ax = fig.add_subplot(gs[j // ncol, j % ncol])
        k = int((r[d].astype(str) == "yes").sum())
        ax.pie([k, n - k], colors=[DRUG_COLORS[j % len(DRUG_COLORS)], NONRESP], startangle=90,
               counterclock=False, wedgeprops=dict(edgecolor="white", linewidth=2),
               labels=[f"responders\n{k} ({100 * k / n:.0f}%)", f"non-responders\n{n - k} ({100 * (n - k) / n:.0f}%)"],
               textprops=dict(fontsize=9, color=INK))
        ax.set_title(d, fontsize=12, fontweight="bold", color="#0b0b0b")
    if has_overlap:
        ax = fig.add_subplot(gs[nrow, :])
        if len(drugs) <= 3:
            _venn(ax, {d: set(r.index[r[d].astype(str) == "yes"]) for d in drugs}, n)
        else:                                            # 4+ drugs: a Venn diagram is unreadable
            _combinations(ax, r, n)
    save(fig, out, "2_pies_and_venn", fmt)


# ------------------------------------------------------------------ 3 + 4 cell area
def g_area_scatter(D, out, fmt):
    r, drugs, area = D["resp"], D["drugs"], D["area"]
    rng = np.random.default_rng(0)
    jit = rng.uniform(-0.12, 0.12, len(area))
    fig, ax = plt.subplots(figsize=(0.75 * len(drugs) + 2.6, 5.2))
    labels = []
    for j, d in enumerate(drugs):
        yes = (r[d].astype(str) == "yes").values
        ax.scatter(j * STEP + jit[~yes], area[~yes], s=13, color=DOT_NONRESP, lw=0, zorder=2,
                   label="non-responder" if j == 0 else None)
        ax.scatter(j * STEP + jit[yes], area[yes], s=15, color="black", lw=0, zorder=3,
                   label="responder" if j == 0 else None)
        labels.append(f"{d}\n{int(yes.sum())} of {len(yes)}")
    top = np.nanmax(area.values) * 1.05                  # every dot sits inside its bar outline
    for j in range(len(drugs)):
        ax.add_patch(plt.Rectangle((j * STEP - 0.17, 0), 0.34, top, fill=False, edgecolor="black",
                                   lw=1.0, zorder=1))
    ax.set_xticks([j * STEP for j in range(len(drugs))], labels)
    ax.set_xlim(-0.35, (len(drugs) - 1) * STEP + 0.35)
    ax.set_ylim(0, top * 1.03)
    ax.set_ylabel(D["area_label"], color=INK)
    clean(ax)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1, 1))
    save(fig, out, "3_area_scatter", fmt)


def g_area_box(D, out, fmt):
    r, drugs, area = D["resp"], D["drugs"], D["area"]
    rng = np.random.default_rng(1)
    fig, ax = plt.subplots(figsize=(0.75 * len(drugs) + 2.0, 5.2))
    labels = []
    for j, d in enumerate(drugs):
        v = area[(r[d].astype(str) == "yes").values].dropna()
        if len(v):
            ax.boxplot([v], positions=[j * STEP], widths=0.25, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="white", edgecolor="black", lw=1.0),
                       medianprops=dict(color="black", lw=1.6), whiskerprops=dict(color="black", lw=1.0),
                       capprops=dict(color="black", lw=1.0), zorder=1)
            ax.scatter(j * STEP + rng.uniform(-0.07, 0.07, len(v)), v, s=12, color="#555555", lw=0, zorder=3)
        labels.append(f"{d}\nn = {len(v)}")
    ax.set_xticks([j * STEP for j in range(len(drugs))], labels)
    ax.set_xlim(-0.35, (len(drugs) - 1) * STEP + 0.35)
    unit = D["area_label"][D["area_label"].find("("):] if "(" in D["area_label"] else ""
    ax.set_ylabel(f"Cell area of responders {unit}".strip(), color=INK)
    clean(ax)
    save(fig, out, "4_area_responders_box", fmt)


# ------------------------------------------------------------------ interactive
def _ask(prompt, default, check=None):
    while True:
        try:
            s = input(f"{prompt} [{default}]: ").strip() or str(default)
        except EOFError:
            s = str(default)
        try:
            return check(s) if check else s
        except ValueError as e:
            print(f"  {e} - try again")


def main():
    print("\nPress ENTER to accept the value in [brackets], or type a new one.\n")

    def f_xlsx(s):
        p = Path(s.strip().strip('"').strip("'"))
        if p.is_dir():
            p = p / "multidrug_results.xlsx"
        if not p.exists():
            raise ValueError(f"not found: {p} (run calcium_multidrug.py first, or give the full path)")
        return p
    xlsx = _ask("Results file", RESULTS_FILE, f_xlsx)

    def f_unit(s):
        s = s.lower()
        if s not in ("df", "df_f0"):
            raise ValueError("type dF or dF_F0")
        return "dF" if s == "df" else "dF_F0"
    unit = _ask("Graph 1 in dF (= F - F0) or dF_F0", UNIT, f_unit)

    def f_fmt(s):
        s = s.lower().lstrip(".")
        if s not in ("png", "pdf", "svg"):
            raise ValueError("type png, pdf or svg")
        return s
    fmt = _ask("File format png, pdf or svg", FORMAT, f_fmt)

    D = load(xlsx, unit)
    print(f"  drugs: {', '.join(D['drugs'])}" + (f" | quality control: {D['qc']}" if D["qc"] else "")
          + f" | cells: {len(D['resp'])}")
    out = Path(xlsx).parent / "graphs"
    out.mkdir(exist_ok=True)
    for old in out.glob("[1-6]_*.*"):                   # graphs of an earlier run would be out of date
        if old.suffix.lower() in (".png", ".pdf", ".svg"):
            old.unlink()
    print()
    g_traces(D, out, fmt, unit)
    g_pies_venn(D, out, fmt)
    if D["area"] is None or D["area"].isna().all():
        print("  (no cell size in the results - graphs 3 and 4 skipped; run calcium_multidrug.py with cell_size.csv)")
    else:
        g_area_scatter(D, out, fmt)
        g_area_box(D, out, fmt)
    print(f"\nGraphs in: {out}")


if __name__ == "__main__":
    main()
