"""
make_graphs.py - graphs from the result tables of calcium_multidrug.py (multidrug_results.xlsx).

HOW TO USE (in the experiment folder, after calcium_multidrug.py has run):
    python make_graphs.py
It asks a few questions ([brackets] = suggestion, ENTER accepts) and saves the graphs in
multidrug_results/graphs/. The analysis is NOT repeated: everything comes from the Excel file.

Graphs:
  1_percent_responders.png           responders vs non-responders per drug (% of analysed cells)
  2_traces_responders_vs_non.png     mean trace ± error of responders and non-responders, per drug
  3_QC_<drug>_kept_vs_excluded.png   quality-control drug (e.g. KCl): kept vs excluded cells
  4_venn_drug_overlap.png            which cells respond to which drugs (Venn for 2-3 drugs,
                                     bar chart of every combination for 4 or more)
  5_area_responders_vs_non.png       cell area of responders vs non-responders, per drug
  6_percent_responders_by_area.png   % responders in small / medium / large cells, per drug
"""

RESULTS_FILE = "multidrug_results/multidrug_results.xlsx"
UNIT = "dF"           # dF | dF_F0 | norm   (norm = ΔF / ΔF(QC drug), only with quality control)
ERROR = "SEM"         # SEM | SD
FORMAT = "png"        # png | pdf | svg
N_SIZE_GROUPS = 3     # small / medium / large = equal numbers of cells per group

import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

RESP = "#2a78d6"      # responders
NONRESP = "#9a9890"   # non-responders
EXCL = "#eb6834"      # excluded by quality control
INK = "#52514e"
RULE = "#c9c8c2"
DRUG_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8f6bd6", "#6b8e23"]


def style(ax, xlabel="", ylabel="", title=""):
    ax.set_xlabel(xlabel, color=INK)
    ax.set_ylabel(ylabel, color=INK)
    if title:
        ax.set_title(title, loc="left", fontsize=11, color="#0b0b0b")
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
def load(xlsx):
    x = pd.ExcelFile(xlsx)
    summary = pd.read_excel(x, "Summary")
    resp = pd.read_excel(x, "Responders", index_col=0)
    traces = pd.read_excel(x, "Mean_traces")
    per_cell = pd.read_excel(x, "Per_cell", index_col=0)
    drugs = list(summary["Drug"].astype(str))
    qc_col = next((c for c in resp.columns if str(c).endswith("(quality control)")), None)
    qc = qc_col.replace(" (quality control)", "") if qc_col else None
    analysed = resp.index[resp[drugs[0]].astype(str).isin(["yes", "no"])]
    return dict(summary=summary, resp=resp, traces=traces, per_cell=per_cell, drugs=drugs,
                qc=qc, qc_col=qc_col, analysed=analysed)


def unit_cols(unit, qc):
    if unit == "dF_F0":
        return "ΔF/F0", "ΔF/F0"
    if unit == "norm":
        return f"ΔF/ΔF({qc})", f"ΔF / ΔF({qc} peak)"
    return "ΔF", "ΔF = X − Bavg (gray value)"


# ------------------------------------------------------------------ 1 % responders per drug
def g_percent(D, out, fmt):
    s = D["summary"]
    drugs = D["drugs"]
    n = int(s["Cells analysed"].iloc[0])
    r = s["Responders"].astype(int).values
    fig, ax = plt.subplots(figsize=(8, 0.75 * len(drugs) + 1.6))
    y = np.arange(len(drugs))[::-1]
    ax.barh(y, 100 * r / n, color=RESP, height=.6, label="responders")
    ax.barh(y, 100 * (n - r) / n, left=100 * r / n, color=NONRESP, height=.6, label="non-responders")
    for yy, k in zip(y, r):
        p = 100 * k / n
        if p >= 8:
            ax.text(p / 2, yy, f"{p:.0f}% ({k})", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        else:
            ax.text(p + 1, yy, f"{p:.0f}% ({k})", ha="left", va="center", color="white" if p > 0 else INK, fontsize=9)
    ax.set_yticks(y, drugs)
    ax.set_xlim(0, 100)
    style(ax, "% of analysed cells", "",
          f"Responders per drug  (n = {n} cells" + (f", {D['qc']}-positive only)" if D["qc"] else ")"))
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(.5, -0.22), fontsize=9)
    save(fig, out, "1_percent_responders", fmt)


# ------------------------------------------------------------------ 2 traces responders vs non-responders
def g_traces(D, out, fmt, unit, err):
    tr = D["traces"]
    lab, ylab = unit_cols(unit, D["qc"])
    drugs = D["drugs"]
    ncol = min(3, len(drugs))
    nrow = int(np.ceil(len(drugs) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 3.6 * nrow), squeeze=False, sharey=True)
    for ax in axs.flat[len(drugs):]:
        ax.axis("off")
    for ax, drug in zip(axs.flat, drugs):
        for grp, col, name in (("responders", RESP, "responders"), ("non-responders", NONRESP, "non-responders")):
            g = tr[(tr["Recording"] == drug) & (tr["Group"] == grp)]
            if g.empty or f"Mean {lab}" not in g:
                continue
            t, m, e = g["Time in recording (s)"], g[f"Mean {lab}"], g[f"{err} {lab}"].fillna(0)
            ax.fill_between(t, m - e, m + e, color=col, alpha=.22, lw=0)
            ax.plot(t, m, color=col, lw=2, label=f"{name} (n = {int(g['n cells'].iloc[0])})")
        ax.axhline(0, color=RULE, lw=1)
        style(ax, "Time (s)", ylab if ax in axs[:, 0] else "", drug)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle(f"Responders vs non-responders, mean ± {err}", x=.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, out, "2_traces_responders_vs_non", fmt)


# ------------------------------------------------------------------ 3 quality control
def g_qc(D, out, fmt, unit, err):
    qc = D["qc"]
    if not qc:
        print("  (no quality-control drug in this analysis - graph 3 skipped)")
        return
    tr = D["traces"]
    lab, ylab = unit_cols("dF" if unit == "norm" else unit, qc)      # normalised QC = 1 by definition
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for grp, col, name in (("all analysed cells", RESP, f"{qc}-positive (kept)"),
                           (f"excluded", EXCL, f"{qc}-negative (excluded)")):
        g = tr[(tr["Recording"] == qc) & (tr["Group"].astype(str).str.startswith(grp))]
        if g.empty or f"Mean {lab}" not in g or g[f"Mean {lab}"].isna().all():
            continue
        t, m, e = g["Time in recording (s)"], g[f"Mean {lab}"], g[f"{err} {lab}"].fillna(0)
        ax.fill_between(t, m - e, m + e, color=col, alpha=.22, lw=0)
        ax.plot(t, m, color=col, lw=2, label=f"{name}: n = {int(g['n cells'].iloc[0])}")
    ax.axhline(0, color=RULE, lw=1)
    n_all = len(D["resp"])
    n_k = len(D["analysed"])
    style(ax, f"Time after start of the {qc} recording (s)", ylab,
          f"Cells after {qc} addition: {n_k} of {n_all} kept ({100 * n_k / n_all:.0f}%), mean ± {err}")
    ax.legend(frameon=False, fontsize=9)
    save(fig, out, f"3_QC_{re.sub(r'[^A-Za-z0-9]+', '_', qc)}_kept_vs_excluded", fmt)


# ------------------------------------------------------------------ 4 Venn / combinations
def _venn(ax, drugs, sets, n_total):
    cols = DRUG_COLORS
    if len(drugs) == 2:
        centers = [(-0.55, 0), (0.55, 0)]
        name_pos = [(-1.15, 1.12), (1.15, 1.12)]
        regions = {(1, 0): (-0.95, 0), (0, 1): (0.95, 0), (1, 1): (0, 0)}
    else:
        centers = [(-0.6, 0.35), (0.6, 0.35), (0, -0.62)]
        name_pos = [(-1.3, 1.45), (1.3, 1.45), (0, -1.85)]
        regions = {(1, 0, 0): (-1.05, 0.6), (0, 1, 0): (1.05, 0.6), (0, 0, 1): (0, -1.15),
                   (1, 1, 0): (0, 0.82), (1, 0, 1): (-0.68, -0.35), (0, 1, 1): (0.68, -0.35),
                   (1, 1, 1): (0, 0.05)}
    for (cx, cy), col in zip(centers, cols):
        ax.add_patch(Circle((cx, cy), 1.0, facecolor=col, alpha=.18, edgecolor=col, lw=2))
    for (x, y), d, col in zip(name_pos, drugs, cols):
        k = len(sets[d])
        ax.text(x, y, f"{d}\n{k} responders", ha="center", va="center", fontsize=10, color=INK, fontweight="bold")
    all_cells = set().union(*sets.values()) if sets else set()
    for key, (x, y) in regions.items():
        inside = [d for d, b in zip(drugs, key) if b]
        outside = [d for d, b in zip(drugs, key) if not b]
        cells = set.intersection(*[sets[d] for d in inside]) - set().union(*[sets[d] for d in outside]) \
            if outside else set.intersection(*[sets[d] for d in inside])
        k = len(cells)
        ax.text(x, y, f"{k}\n{100 * k / n_total:.0f}%", ha="center", va="center", fontsize=10, color="#0b0b0b")
    none = n_total - len(all_cells)
    ax.text(1.75, -1.75 if len(drugs) == 3 else -1.25, f"no drug: {none} ({100 * none / n_total:.0f}%)",
            ha="right", va="center", fontsize=9, color=INK)
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-2.1 if len(drugs) == 3 else -1.5, 1.75 if len(drugs) == 3 else 1.45)
    ax.set_aspect("equal")
    ax.axis("off")


def g_venn(D, out, fmt):
    drugs = D["drugs"]
    resp = D["resp"].loc[D["analysed"]]
    n = len(resp)
    sets = {d: set(resp.index[resp[d].astype(str) == "yes"]) for d in drugs}
    title = f"Overlap of responders between drugs  (n = {n} analysed cells" + \
        (f", {D['qc']}-positive only)" if D["qc"] else ")")
    if 2 <= len(drugs) <= 3:
        fig, ax = plt.subplots(figsize=(7, 7))
        _venn(ax, drugs, sets, n)
        ax.set_title(title, loc="left", fontsize=11, color="#0b0b0b")
        save(fig, out, "4_venn_drug_overlap", fmt)
        return
    # 1 drug or 4+: every combination as bars (an UpSet-style plot)
    combo = resp["Responds to"].astype(str).value_counts()
    order = sorted(combo.index, key=lambda s: (s == "none", -s.count("+"), -combo[s]))
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(order) + 1.5))
    y = np.arange(len(order))[::-1]
    ax.barh(y, combo[order].values, color=[NONRESP if o == "none" else RESP for o in order], height=.6)
    for yy, v in zip(y, combo[order].values):
        ax.text(v + .3, yy, f"{v} ({100 * v / n:.0f}%)", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, order, fontsize=9)
    style(ax, "Number of cells", "", title)
    save(fig, out, "4_venn_drug_overlap", fmt)


# ------------------------------------------------------------------ 5 + 6 size
def g_size(D, out, fmt, n_groups):
    pc = D["per_cell"]
    acol = next((c for c in pc.columns if str(c).startswith("Area")), None)
    if acol is None:
        print("  (no cell size in the results - graphs 5 and 6 skipped; run calcium_multidrug.py with cell_size.csv)")
        return
    drugs = D["drugs"]
    resp = D["resp"].loc[D["analysed"]]
    area = pd.to_numeric(pc.loc[resp.index, acol], errors="coerce")
    unit = acol[acol.find("("):] if "(" in acol else ""
    rng = np.random.default_rng(0)

    # 5: area of responders vs non-responders
    fig, ax = plt.subplots(figsize=(2.2 * len(drugs) + 2, 4.8))
    xt, xl = [], []
    for j, d in enumerate(drugs):
        for k, (val, col, name) in enumerate((("no", NONRESP, "non-resp."), ("yes", RESP, "resp."))):
            v = area[resp[d].astype(str) == val].dropna()
            x = 3 * j + k
            ax.scatter(x + rng.uniform(-.22, .22, len(v)), v, s=12, color=col, alpha=.75, lw=0)
            if len(v):
                ax.plot([x - .3, x + .3], [v.median()] * 2, color="#0b0b0b", lw=2)
            xt.append(x); xl.append(f"{name}\nn = {len(v)}")
        ax.text(3 * j + .5, 1.02, d, transform=ax.get_xaxis_transform(), ha="center", fontsize=10,
                color=INK, fontweight="bold")
    ax.set_xticks(xt, xl, fontsize=8)
    style(ax, "", f"Cell area {unit}", "")
    ax.set_title("Cell area of responders vs non-responders (black line = median)", loc="left",
                 fontsize=11, color="#0b0b0b", pad=24)
    save(fig, out, "5_area_responders_vs_non", fmt)

    # 6: % responders in size groups (equal numbers of cells per group)
    names = {2: ["small", "large"], 3: ["small", "medium", "large"], 4: ["Q1 small", "Q2", "Q3", "Q4 large"]}.get(
        n_groups, [f"G{i + 1}" for i in range(n_groups)])
    groups = pd.qcut(area, n_groups, labels=names)
    edges = area.groupby(groups, observed=False).agg(["min", "max", "count"])
    fig, ax = plt.subplots(figsize=(2.0 * len(drugs) + 3, 4.6))
    w = 0.8 / n_groups
    shades = [plt.matplotlib.colors.to_rgba(RESP, a) for a in np.linspace(.35, 1, n_groups)]
    for gi, gname in enumerate(names):
        cells = groups.index[groups == gname]
        pct = [100 * (resp.loc[cells, d].astype(str) == "yes").mean() if len(cells) else 0 for d in drugs]
        xs = np.arange(len(drugs)) + (gi - (n_groups - 1) / 2) * w
        lo, hi, cnt = edges.loc[gname]
        ax.bar(xs, pct, width=w * .92, color=shades[gi], label=f"{gname}: {lo:.0f}–{hi:.0f} {unit.strip('()')} (n = {int(cnt)})")
        for x, p in zip(xs, pct):
            ax.text(x, p + 1, f"{p:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(np.arange(len(drugs)), drugs)
    ax.set_ylim(0, 105)
    style(ax, "", "% responders in the size group", "% responders by cell area")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1, 1))
    save(fig, out, "6_percent_responders_by_area", fmt)


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
    D = load(xlsx)
    print(f"  drugs: {', '.join(D['drugs'])}" + (f" | quality control: {D['qc']}" if D["qc"] else ""))

    def f_unit(s):
        s = s.lower()
        if s not in ("df", "df_f0", "norm"):
            raise ValueError("type dF, dF_F0 or norm")
        if s == "norm" and not D["qc"]:
            raise ValueError("norm needs a quality-control drug")
        return {"df": "dF", "df_f0": "dF_F0", "norm": "norm"}[s]
    unit = _ask("Traces in dF, dF_F0 or norm (= ΔF/ΔF(QC))", UNIT, f_unit)

    def f_err(s):
        s = s.upper()
        if s not in ("SEM", "SD"):
            raise ValueError("type SEM or SD")
        return s
    err = _ask("Error band SEM or SD", ERROR, f_err)

    def f_fmt(s):
        s = s.lower().lstrip(".")
        if s not in ("png", "pdf", "svg"):
            raise ValueError("type png, pdf or svg")
        return s
    fmt = _ask("File format png, pdf or svg", FORMAT, f_fmt)

    def f_groups(s):
        v = int(s)
        if not 2 <= v <= 5:
            raise ValueError("between 2 and 5")
        return v
    n_groups = _ask("Number of size groups (equal numbers of cells)", N_SIZE_GROUPS, f_groups)

    out = Path(xlsx).parent / "graphs"
    out.mkdir(exist_ok=True)
    for old in out.glob("[1-6]_*.*"):          # graphs of an earlier run would be out of date
        if old.suffix.lower() in (".png", ".pdf", ".svg"):
            old.unlink()
    print()
    g_percent(D, out, fmt)
    g_traces(D, out, fmt, unit, err)
    g_qc(D, out, fmt, unit, err)
    g_venn(D, out, fmt)
    g_size(D, out, fmt, n_groups)
    print(f"\nGraphs in: {out}")


if __name__ == "__main__":
    main()
