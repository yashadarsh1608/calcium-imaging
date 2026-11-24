"""
make_graphs.py - graphs from the result tables of calcium_multidrug.py (multidrug_results.xlsx).

HOW TO USE (in the experiment folder, after the analysis has run):
    python make_graphs.py
It asks a few questions ([brackets] = suggestion, ENTER accepts) and saves the graphs in
multidrug_results/graphs/. The analysis is NOT repeated: everything comes from the Excel file.
The same graphs are shown in the window of calcium_gui.py.

Every graph uses only the cells kept after the quality-control drug (e.g. KCl):
  1_traces_cells            F - F0 over time of every recording incl. the QC drug, every cell
                            one line (no mean), // = washing (not imaged)
  2_drug_and_QC             one row per drug, only the cells that RESPONDED to that drug: their
                            response to the drug on the left and the response of the SAME cells
                            to the QC drug on the right; every cell in grey, the mean in black
  3_pies_and_venn           black and grey: one pie per drug (responders vs non-responders) +
                            2-3 drugs: Venn diagram with circle sizes proportional to the number
                            of responders. 4 or more drugs: bar chart of every combination
  4_area_scatter            cell area per drug, every cell one dot (black = responder,
                            grey = non-responder), inside a bar outline
  5_area_responders_box     box-and-whisker of the cell area of the responders only
Graphs 4 and 5 need the cell size (cell_size.csv in the analysis).
"""

# ========================= SETTINGS = suggestions shown in [brackets] =========================
RESULTS_FILE = "multidrug_results/multidrug_results.xlsx"
UNIT = "dF"            # graphs 1 + 2: dF (= F - F0, gray value) | dF_F0 (= ΔF / F0)
FORMAT = "png"         # png | pdf | svg
STEP = 0.5             # graphs 4 + 5: distance between two drugs
VENN_MAX_DRUGS = 3     # graph 3: Venn diagram up to this many drugs, bar chart of the combinations above
                       # (4 or 5 would draw a Venn diagram of ellipses, which is hard to read)
# ==============================================================================================

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, Rectangle

INK = "#52514e"           # axis text
RULE = "#c9c8c2"          # axis lines, zero line
CELL_GREY = "#8f8e88"     # single cells
NONRESP = "#c9c8c2"       # graph 3: non-responder slice
DOT_NONRESP = "#bdbdbd"   # graph 4: non-responder dots
VENN_LINES = ["-", "--", ":", "-.", (0, (7, 1.5, 1, 1.5, 1, 1.5))]   # graph 3: one line style per drug
TRACE_COLS = ("Frame", "Recording", "Time in recording (s)", "Experiment time (s)")
UNIT_SHEET = {"dF": "Cell_traces_dF", "dF_F0": "Cell_traces_dF_F0"}
UNIT_LABEL = {"dF": "F − F0  (ΔF, gray value)", "dF_F0": "ΔF/F0"}
TRACE_COLS = ("Frame", "Recording", "Time in recording (s)", "Experiment time (s)")
UNIT_SHEET = {"dF": "Cell_traces_dF", "dF_F0": "Cell_traces_dF_F0"}
TRACE_COLS = ("Frame", "Recording", "Time in recording (s)", "Experiment time (s)")
UNIT_SHEET = {"dF": "Cell_traces_dF", "dF_F0": "Cell_traces_dF_F0"}
UNIT_LABEL = {"dF": "F − F0  (ΔF, gray value)", "dF_F0": "ΔF/F0"}
# Graph 2, y axis (the height of the traces):
#   "panel" = every panel has its own range (default: small responses are visible)
#   "row"   = the drug and the KCl panel of one row share a range (they can be compared)
#   "all"   = one fixed range for every panel
GRAPH2_Y = "panel"
RESPONDER_CSV_DIR = "responders"     # folder for the CSV files of the responders



def clean(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(RULE)
    ax.tick_params(colors=INK)


# ------------------------------------------------------------------ read the result tables
def load(xlsx):
    """Everything the graphs need, from multidrug_results.xlsx."""
    x = pd.ExcelFile(xlsx)
    summary = pd.read_excel(x, "Summary")
    resp = pd.read_excel(x, "Responders", index_col=0)
    per_cell = pd.read_excel(x, "Per_cell", index_col=0)
    traces = {u: pd.read_excel(x, s) for u, s in UNIT_SHEET.items() if s in x.sheet_names}
    combos = pd.read_excel(x, "Combinations") if "Combinations" in x.sheet_names else None
    drugs = list(summary["Drug"].astype(str))
    qc_col = next((c for c in resp.columns if str(c).endswith("(quality control)")), None)
    qc = qc_col.replace(" (quality control)", "") if qc_col else None
    kept = resp.index[resp[drugs[0]].astype(str).isin(["yes", "no"])]
    status_col = qc_col or ("Cell status" if "Cell status" in resp.columns else None)
    excluded = resp.loc[~resp.index.isin(kept), status_col].astype(str).value_counts() if status_col else pd.Series(dtype=int)
    acol = next((c for c in per_cell.columns if str(c).startswith("Area")), None)
    area = pd.to_numeric(per_cell.loc[kept, acol], errors="coerce") if acol else None
    if area is not None and area.isna().all():
        area = None
    return dict(xlsx=Path(xlsx), summary=summary, combos=combos, resp_all=resp, resp=resp.loc[kept],
                per_cell=per_cell, traces=traces, drugs=drugs, qc=qc, n_all=len(resp), excluded=excluded,
                area=area, area_label=("Cell a" + acol[1:]) if acol else "Cell area")


def _cells(tr):
    return [c for c in tr.columns if c not in TRACE_COLS]


def _responders(D, drug):
    r = D["resp"]
    return list(r.index[r[drug].astype(str) == "yes"])


# ------------------------------------------------------------------ 1 every cell, every recording
def fig_cells(D, unit="dF"):
    tr = D["traces"][unit]
    recs = list(dict.fromkeys(tr["Recording"]))          # experiment order
    cells = _cells(tr)
    widths = [tr.loc[tr.Recording == r, "Time in recording (s)"].max() + 1 for r in recs]
    fig = Figure(figsize=(3.3 * len(recs) + 1, 4.6))
    axs = fig.subplots(1, len(recs), sharey=True, squeeze=False,
                       gridspec_kw=dict(width_ratios=widths, wspace=0.12))[0]
    for k, (ax, r) in enumerate(zip(axs, recs)):
        d = tr[tr.Recording == r]
        t = d["Experiment time (s)"].values
        ax.plot(t, d[cells].values, color=CELL_GREY, lw=0.6, alpha=0.7)
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
    axs[0].set_ylabel(UNIT_LABEL[unit], color=INK)
    fig.supxlabel("Experiment time (s)", color=INK, fontsize=10, y=-0.1)
    return fig


# ------------------------------------------------------------------ 2 each drug next to the QC drug
def fig_drug_qc(D, unit="dF"):
    """Row per drug, only the cells that responded to that drug (all of them passed the quality
    control): their response to the drug (left) and of the same cells to the QC drug (right).
    Every cell grey, the mean black."""
    tr = D["traces"][unit]
    drugs, qc = D["drugs"], D["qc"]
    all_cells = _cells(tr)
    ncol = 2 if qc else 1
    dur = lambda r: tr.loc[tr.Recording == r, "Time in recording (s)"].max() + 1
    widths = [max(dur(d) for d in drugs)] + ([dur(qc)] if qc else [])
    fig = Figure(figsize=(4.4 * ncol + 1.2, 2.7 * len(drugs) + 0.7))
    share = {"all": True, "row": "row", "panel": False}[GRAPH2_Y]
    axs = fig.subplots(len(drugs), ncol, sharey=share, sharex="col", squeeze=False,
                       gridspec_kw=dict(width_ratios=widths, wspace=0.22, hspace=0.42))
    for i, drug in enumerate(drugs):
        cells = [c for c in _responders(D, drug) if c in all_cells]
        for j, rec in enumerate([drug] + ([qc] if qc else [])):
            ax = axs[i, j]
            d = tr[tr.Recording == rec]
            t = d["Time in recording (s)"].values
            if cells:
                ax.plot(t, d[cells].values, color=CELL_GREY, lw=0.6, alpha=0.7, zorder=1)
                ax.plot(t, d[cells].mean(axis=1).values, color="black", lw=2.2, zorder=3)
            else:
                ax.text(0.5, 0.5, "no responders", transform=ax.transAxes, ha="center", va="center",
                        fontsize=9, color=INK)
            ax.axhline(0, color=RULE, lw=0.8, zorder=0)
            ax.set_xlim(t[0], t[-1])
            title = f"{drug}  ({len(cells)} of {len(D['resp'])} cells responded)" if j == 0 else f"{qc}"
            ax.set_title(title, fontsize=10.5, color="#0b0b0b", loc="left")
            clean(ax)
            if j == 0:
                ax.set_ylabel(UNIT_LABEL[unit], color=INK, fontsize=9)
            if i == len(drugs) - 1:
                ax.set_xlabel("Time in recording (s)", color=INK)
    return fig


# ------------------------------------------------------------------ 3 pies + proportional Venn
def _lens(r1, r2, d):
    """Overlap area of two circles with radii r1, r2 and centre distance d."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return np.pi * min(r1, r2) ** 2
    a1 = np.arccos(np.clip((d * d + r1 * r1 - r2 * r2) / (2 * d * r1), -1, 1))
    a2 = np.arccos(np.clip((d * d + r2 * r2 - r1 * r1) / (2 * d * r2), -1, 1))
    return r1 * r1 * (a1 - np.sin(2 * a1) / 2) + r2 * r2 * (a2 - np.sin(2 * a2) / 2)


def _distance(r1, r2, target):
    """Centre distance at which two circles overlap by the area `target`."""
    if target <= 0:
        return (r1 + r2) * 1.04                           # apart, with a small gap
    if target >= np.pi * min(r1, r2) ** 2 * 0.999:
        return abs(r1 - r2) * 0.98                        # one inside the other
    lo, hi = abs(r1 - r2), r1 + r2
    for _ in range(60):
        mid = (lo + hi) / 2
        if _lens(r1, r2, mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def venn_layout(sizes, pair_sizes):
    """Circles whose AREA is proportional to the set size and whose pairwise overlaps are
    proportional to the pairwise intersections. sizes = [nA, nB(, nC)],
    pair_sizes = {(i, j): n}. Returns [(x, y, r) or None for an empty set]."""
    nmax = max(sizes) if max(sizes) > 0 else 1
    r = [np.sqrt(n / nmax) for n in sizes]
    live = [i for i, n in enumerate(sizes) if n > 0]
    dist = lambda i, j: _distance(r[i], r[j], np.pi * pair_sizes.get((min(i, j), max(i, j)), 0) / nmax)
    pos = {}
    if live:
        pos[live[0]] = (0.0, 0.0)
    if len(live) >= 2:
        pos[live[1]] = (dist(live[0], live[1]), 0.0)
    if len(live) == 3:
        a, b, c = live
        dab, dac, dbc = pos[b][0], dist(a, c), dist(b, c)
        if dab < 1e-9:
            pos[c] = (dac, 0.0)
        else:
            x = (dac ** 2 - dbc ** 2 + dab ** 2) / (2 * dab)
            pos[c] = (x, -np.sqrt(max(dac ** 2 - x ** 2, 0.0)))
    return [(pos[i][0], pos[i][1], r[i]) if i in pos else None for i in range(len(sizes))]


# Venn diagrams of 4 and 5 sets need ellipses (x, y, width, height, angle); these two layouts
# contain every possible overlap. They cannot be drawn to scale.
ELLIPSES = {
    4: [(0.350, 0.400, 0.72, 0.45, 140), (0.450, 0.500, 0.72, 0.45, 140),
        (0.544, 0.500, 0.72, 0.45, 40), (0.644, 0.400, 0.72, 0.45, 40)],
    5: [(0.428, 0.449, 0.87, 0.50, 155), (0.469, 0.543, 0.87, 0.50, 82), (0.558, 0.523, 0.87, 0.50, 10),
        (0.578, 0.432, 0.87, 0.50, 118), (0.489, 0.383, 0.87, 0.50, 46)],
}
ELLIPSE_SCALE = 3.4        # so that numbers and lines have the same size as in the circle diagram


def _outline(shape, k=200):
    x, y, w, h, a = shape
    t, p = np.radians(a), np.linspace(0, 2 * np.pi, k, endpoint=False)
    u, v = w / 2 * np.cos(p), h / 2 * np.sin(p)
    return x + u * np.cos(t) - v * np.sin(t), y + u * np.sin(t) + v * np.cos(t)


def _inside(shape, gx, gy):
    x, y, w, h, a = shape
    t = np.radians(a)
    u = (gx - x) * np.cos(t) + (gy - y) * np.sin(t)
    v = -(gx - x) * np.sin(t) + (gy - y) * np.cos(t)
    return (2 * u / w) ** 2 + (2 * v / h) ** 2 < 1


def _edge_distance(shape, gx, gy):
    """Distance of every grid point to the outline of the shape."""
    x, y, w, h, a = shape
    if abs(w - h) < 1e-12:                                # circle: exact
        return np.abs(np.hypot(gx - x, gy - y) - w / 2)
    ox, oy = _outline(shape)
    best = np.full(gx.shape, np.inf)
    for k in range(0, len(ox), 20):
        d = np.hypot(gx[..., None] - ox[k:k + 20], gy[..., None] - oy[k:k + 20]).min(axis=-1)
        best = np.minimum(best, d)
    return best


def _venn(ax, sets, n):
    """Venn diagram of 2-5 sets. 2-3: circles to scale. 4-5: equal ellipses (not to scale)."""
    names = list(sets)
    k = len(names)
    sizes = [len(sets[s]) for s in names]
    to_scale = k <= 3
    if to_scale:
        pairs = {(i, j): len(sets[names[i]] & sets[names[j]]) for i in range(k) for j in range(i + 1, k)}
        shapes = [None if c is None else (c[0], c[1], 2 * c[2], 2 * c[2], 0) for c in venn_layout(sizes, pairs)]
    else:
        f = ELLIPSE_SCALE
        shapes = [(x * f, y * f, w * f, h * f, a) for x, y, w, h, a in ELLIPSES[k]]
    drawn = [(i, sh) for i, sh in enumerate(shapes) if sh is not None]
    for i, (x, y, w, h, a) in drawn:                 # grey fills (overlaps get darker), black outlines
        ax.add_patch(Ellipse((x, y), w, h, angle=a, facecolor="black", alpha=.10 if to_scale else .06,
                             edgecolor="none"))
        ax.add_patch(Ellipse((x, y), w, h, angle=a, facecolor="none", edgecolor="black", lw=1.6,
                             ls=VENN_LINES[i % len(VENN_LINES)]))

    # the number of cells in every region, written at the roomiest point of that region
    region = {}
    for cell in set().union(*sets.values()) if sets else ():
        key = tuple(cell in sets[s] for s in names)
        region[key] = region.get(key, 0) + 1
    hidden = []
    if drawn:
        outl = [_outline(sh) for _, sh in drawn]
        x0 = min(o[0].min() for o in outl); x1 = max(o[0].max() for o in outl)
        y0 = min(o[1].min() for o in outl); y1 = max(o[1].max() for o in outl)
        res = 420 if to_scale else 300
        gx, gy = np.meshgrid(np.linspace(x0, x1, res), np.linspace(y0, y1, res))
        inside, edge = {}, np.full(gx.shape, np.inf)
        for i, sh in drawn:
            inside[i] = _inside(sh, gx, gy)
            edge = np.minimum(edge, _edge_distance(sh, gx, gy))
        nothing = np.zeros(gx.shape, bool)
        for key, count in sorted(region.items(), key=lambda kv: -kv[1]):
            m = np.ones(gx.shape, bool)
            for i in range(k):
                m &= inside.get(i, nothing) if key[i] else ~inside.get(i, nothing)
            who = " + ".join(s for s, b in zip(names, key) if b)
            if not m.any():
                hidden.append(f"{who}: {count}")             # this overlap cannot be drawn with circles
                continue
            room = np.where(m, edge, -1)
            iy, ix = np.unravel_index(np.argmax(room), room.shape)
            small = room[iy, ix] < (0.11 if to_scale else 0.16)
            ax.text(gx[iy, ix], gy[iy, ix], f"{count}" if small else f"{count}\n{100 * count / n:.0f}%",
                    ha="center", va="center", fontsize=8 if small else 10, color="#0b0b0b")
        if not to_scale:                                 # drug name at the outer end of its ellipse
            cx = np.mean([sh[0] for _, sh in drawn]); cy = np.mean([sh[1] for _, sh in drawn])
            for (i, sh), (ox, oy) in zip(drawn, outl):
                far = np.argmax(np.hypot(ox - cx, oy - cy))
                dx, dy = ox[far] - cx, oy[far] - cy
                L = np.hypot(dx, dy)
                ax.text(ox[far] + 0.07 * dx / L, oy[far] + 0.07 * dy / L, names[i], fontsize=10.5,
                        fontweight="bold", color="#0b0b0b", ha="left" if dx > 0.25 * L else "right" if dx < -0.25 * L
                        else "center", va="bottom" if dy > 0.25 * L else "top" if dy < -0.25 * L else "center")
        pad = 0.12 if to_scale else 0.3
        ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad)
    none = n - len(set().union(*sets.values())) if sets else n
    handles = [Line2D([], [], color="black", lw=1.6, ls=VENN_LINES[i % len(VENN_LINES)],
                      label=f"{s}: {sizes[i]} responders ({100 * sizes[i] / n:.0f}%)") for i, s in enumerate(names)]
    handles.append(Line2D([], [], color="none", label=f"no drug: {none} ({100 * none / n:.0f}%)"))
    ax.legend(handles=handles, frameon=False, fontsize=9.5, loc="center left", bbox_to_anchor=(1.02, 0.5),
              handlelength=3.6)
    if hidden:
        ax.text(0.5, -0.04, "overlap too small to draw:  " + ";  ".join(hidden), transform=ax.transAxes,
                ha="center", va="top", fontsize=8.5, color=INK)
    ax.set_aspect("equal"); ax.axis("off")


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


def fig_pies_venn(D):
    r, drugs = D["resp"], D["drugs"]
    n = len(r)
    ncol = len(drugs) if len(drugs) <= 5 else 4
    nrow = int(np.ceil(len(drugs) / ncol))
    overlap = len(drugs) >= 2
    venn = len(drugs) <= min(VENN_MAX_DRUGS, 5)          # more drugs: bars of every combination
    wide = 3.6 if ncol <= 3 else 3.0
    low = (5.2 if len(drugs) <= 3 else 7.0) if venn else 5.2
    fig = Figure(figsize=(wide * ncol + 1.2, 3.3 * nrow + (low if overlap else 0)))
    gs = fig.add_gridspec(nrow + (1 if overlap else 0), ncol, hspace=0.15,
                          height_ratios=[1] * nrow + ([low / 3.3] if overlap else []))
    for j, d in enumerate(drugs):
        ax = fig.add_subplot(gs[j // ncol, j % ncol])
        k = int((r[d].astype(str) == "yes").sum())
        texts = [f"responders\n{k} ({100 * k / n:.0f}%)", f"non-responders\n{n - k} ({100 * (n - k) / n:.0f}%)"]
        wedges = ax.pie([k, n - k], colors=["black", NONRESP], startangle=90, counterclock=False,
                        wedgeprops=dict(edgecolor="white", linewidth=2),
                        labels=texts if ncol <= 3 else None, textprops=dict(fontsize=9, color=INK))[0]
        if ncol > 3:                                     # many pies: the numbers go under the pie
            ax.legend(wedges, [t.replace("\n", "  ") for t in texts], frameon=False, fontsize=9, labelcolor=INK,
                      loc="upper center", bbox_to_anchor=(0.5, 0.06), handlelength=1, handleheight=1)
        ax.set_title(d, fontsize=12, fontweight="bold", color="#0b0b0b")
    if overlap:
        ax = fig.add_subplot(gs[nrow, :])
        if venn:
            _venn(ax, {d: set(_responders(D, d)) for d in drugs}, n)
        else:
            _combinations(ax, r, n)
    return fig


# ------------------------------------------------------------------ 4 + 5 cell area
def fig_area_scatter(D):
    r, drugs, area = D["resp"], D["drugs"], D["area"]
    rng = np.random.default_rng(0)
    jit = rng.uniform(-0.12, 0.12, len(area))
    fig = Figure(figsize=(0.75 * len(drugs) + 2.6, 5.2))
    ax = fig.subplots()
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
        ax.add_patch(Rectangle((j * STEP - 0.17, 0), 0.34, top, fill=False, edgecolor="black", lw=1.0, zorder=1))
    ax.set_xticks([j * STEP for j in range(len(drugs))], labels)
    ax.set_xlim(-0.35, (len(drugs) - 1) * STEP + 0.35)
    ax.set_ylim(0, top * 1.03)
    ax.set_ylabel(D["area_label"], color=INK)
    clean(ax)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1, 1))
    return fig


def fig_area_box(D):
    r, drugs, area = D["resp"], D["drugs"], D["area"]
    rng = np.random.default_rng(1)
    fig = Figure(figsize=(0.75 * len(drugs) + 2.0, 5.2))
    ax = fig.subplots()
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
    return fig


# ------------------------------------------------------------------ all graphs
GRAPHS = [  # (file name, tab title, needs cell size)
    ("1_traces_cells", "1 · Cells", False),
    ("2_drug_and_QC", "2 · Drug and QC", False),
    ("3_pies_and_venn", "3 · Responders", False),
    ("4_area_scatter", "4 · Area", True),
    ("5_area_responders_box", "5 · Area of responders", True),
]


def make_figure(D, name, unit="dF"):
    """The figure of one graph, or None if it cannot be made (no cell size in the results)."""
    if name == "1_traces_cells":
        return fig_cells(D, unit)
    if name == "2_drug_and_QC":
        return fig_drug_qc(D, unit)
    if name == "3_pies_and_venn":
        return fig_pies_venn(D)
    if D["area"] is None:
        return None
    return fig_area_scatter(D) if name == "4_area_scatter" else fig_area_box(D)


def save_all(D, out, fmt="png", unit="dF"):
    """Save every graph into the folder `out`; returns the saved paths."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("[1-6]_*.*"):                   # graphs of an earlier run would be out of date
        if old.suffix.lower() in (".png", ".pdf", ".svg"):
            old.unlink()
    saved = []
    for name, _, _ in GRAPHS:
        fig = make_figure(D, name, unit)
        if fig is None:
            continue
        path = out / f"{name}.{fmt}"
        fig.savefig(path, dpi=300 if fmt == "png" else None, bbox_inches="tight", facecolor="white")
        saved.append(path)
#save_responder_csv(D, out, unit)
    return saved

# ------------------------------------------------------------------ command line
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
            raise ValueError(f"not found: {p} (run the analysis first, or give the full path)")
        return p
    xlsx = _ask("Results file", RESULTS_FILE, f_xlsx)

    def f_unit(s):
        s = s.lower()
        if s not in ("df", "df_f0"):
            raise ValueError("type dF or dF_F0")
        return "dF" if s == "df" else "dF_F0"
    unit = _ask("Graphs 1 + 2 in dF (= F - F0) or dF_F0", UNIT, f_unit)

    def f_fmt(s):
        s = s.lower().lstrip(".")
        if s not in ("png", "pdf", "svg"):
            raise ValueError("type png, pdf or svg")
        return s
    fmt = _ask("File format png, pdf or svg", FORMAT, f_fmt)

    D = load(xlsx)
    print(f"  drugs: {', '.join(D['drugs'])}" + (f" | quality control: {D['qc']}" if D["qc"] else "")
          + f" | cells: {len(D['resp'])}\n")
    out = Path(xlsx).parent / "graphs"
    for p in save_all(D, out, fmt, unit):
        print(f"  saved {p.name}")
    if D["area"] is None:
        print("  (no cell size in the results - graphs 4 and 5 skipped; run the analysis with cell_size.csv)")
    print(f"\nGraphs in: {out}")


if __name__ == "__main__":
    main()