"""
calcium_multidrug.py - DATA ONLY (no graphs): several drugs, one recording (CSV) per drug, SAME ROIs.

HOW TO USE
  1. Find the peak frames:   python calcium_multidrug.py --overview
  2. Run the analysis:       python calcium_multidrug.py
  The script ASKS every setting. A value in [brackets] is a suggestion - press ENTER to accept it,
  or type a new one. "(required)" = no suggestion, you must type it (drug names, peak windows ...).

Method (lab flowchart, done separately for every recording):
  X = cell - background, Bavg = mean X over the baseline frames, F = X - Bavg (= deltaF),
  SD = SD of F in the baseline, responder if mean F over the peak window > mean baseline + N*SD.
  deltaF/F0 = F / Bavg.

Optional quality control (QC): one recording with a control drug (e.g. KCl, ionomycin), any name.
  Only cells that respond to it are analysed; the others are listed as excluded.
  Responses are also given normalised to each cell's own QC peak: deltaF / deltaF(QC).
Optional cell size: ImageJ ROI Manager -> Measure (Area, Feret, ...) -> area and diameter per cell.

Output: one Excel file + the same tables as CSV files, ready for making any graph later.
Input: ImageJ Multi Measure CSV per recording (Mean gray value, one row per frame),
       background boxes = the LAST columns, same ROI set in every recording.
"""

# ========================= SETTINGS = SUGGESTIONS shown in [brackets]; None = must be typed =========================
N_DRUGS = 3
CSV_FILES = ["drug1.csv", "drug2.csv", "drug3.csv"]  # suggested file names (shown only if the file exists)
DRUG_NAMES = None        # None = must be typed every run
BASELINE = (1, 8)        # frames before the drug arrives (asked for every recording)
PEAKS = None             # None = must be typed every run (see --overview)
THRESHOLD_SD = 5         # lab rule: responder if mean peak > mean baseline + 5 SD
FRAME_INTERVAL = 1       # seconds between frames
WASH_TIME = None         # None = asked for EVERY gap between recordings (washes differ)
N_BACKGROUND_ROIS = 3
BACKGROUND_USE = None    # None = all boxes; or e.g. ["Mean98"]
QC_FILE = None           # None = must be typed ('none' if there is no quality-control recording)
QC_NAME = None           # None = must be typed (KCl, ionomycin, ...)
QC_PEAK = None           # None = must be typed
SIZE_FILE = "cell_size.csv"   # suggested only if the file exists; 'none' to skip
PIXEL_SIZE_UM = 0        # µm per pixel if the size file is in pixels; 0 = already in µm
CSV_STYLE = "en"         # "en" = comma-separated, decimal point | "de" = semicolon, decimal comma (German Excel)
OUTPUT_FOLDER = "multidrug_results"
# ====================================================================================================================

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ input
def read_imagej_csv(path):
    path = Path(path)
    first = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    if ";" in first:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    cols = [c for c in df.columns if str(c).strip().startswith("Mean")]
    if not cols:
        raise ValueError(f"{path.name}: no 'Mean' columns found - measure 'Mean gray value' in ImageJ.")
    data = df[cols].apply(pd.to_numeric, errors="coerce")
    data.columns = [str(c).strip() for c in cols]
    data.index = pd.RangeIndex(1, len(data) + 1, name="Frame")
    return data


def background_subtract(raw, n_bg, use=None):
    if n_bg > 0:
        bg_cols = list(use) if use else list(raw.columns[-n_bg:])
        bg = raw[bg_cols].mean(axis=1)
        cells = raw.iloc[:, :-n_bg]
    else:
        bg = pd.Series(0.0, index=raw.index)
        cells = raw
    return cells.sub(bg, axis=0), bg


def check_background(raw, n_bg, label, n_base=8):
    """Warn about background boxes that are not really empty (in this recording)."""
    if not n_bg:
        return []
    cells = raw.iloc[:, :-n_bg]
    cell_base = cells.iloc[:n_base].median(axis=1).mean()
    cell_rise = (cells.median(axis=1) - cell_base).abs().max()
    warn = []
    for c in raw.columns[-n_bg:]:
        b = raw[c]
        base = b.iloc[:n_base].mean()
        change = (b - base).abs().max()
        reasons = []
        if base >= cell_base:
            reasons.append(f"brighter at baseline ({base:.1f}) than the cells ({cell_base:.1f})")
        if change > max(1.0, 0.5 * cell_rise):
            reasons.append(f"changes by {change:.1f} gray values")
        if reasons:
            warn.append(c)
            print(f"  WARNING {label}, background {c}: " + " and ".join(reasons) +
                  " -> probably not an empty area")
    return warn


def baseline_check(X, baseline, label):
    """Warn if the cells already rise inside the baseline (drug arrived too early)."""
    b0, b1 = baseline
    if b1 - b0 < 4:
        return
    med = X.median(axis=1)
    early, late = med.loc[b0:b1 - 2], med.loc[b1 - 1:b1]
    if late.mean() > early.mean() + 4 * max(early.std(ddof=1), 1e-9) and late.mean() - early.mean() > 0.2:
        print(f"  WARNING {label}: the cells already rise in frames {b1 - 1}-{b1} of the baseline "
              f"-> end the baseline earlier (e.g. {b0}-{b1 - 2})")


def read_size_file(path, cells, px_um=0):
    """ImageJ ROI Manager -> Measure: one row per ROI in ROI order. The first len(cells) rows are the
    cells; extra rows (background boxes) are ignored."""
    path = Path(path)
    first = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    if ";" in first:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    elif "\t" in first:
        df = pd.read_csv(path, sep="\t", encoding="utf-8-sig")
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    if "Area" not in df.columns:
        raise ValueError(f"{path.name}: no 'Area' column. Columns found: {', '.join(map(str, df.columns[:8]))} "
                         f"- tick Area in Set Measurements, then ROI Manager > Measure (not Multi Measure)")
    if len(df) < len(cells):
        raise ValueError(f"{path.name} has {len(df)} rows but there are {len(cells)} cells - "
                         f"measure ALL ROIs (Deselect, then Measure)")
    df = df.iloc[:len(cells)].reset_index(drop=True)
    lin = px_um if px_um else 1.0
    size = pd.DataFrame(index=pd.Index(cells, name="Cell"))
    size["Area (µm²)"] = pd.to_numeric(df["Area"], errors="coerce").values * lin ** 2
    size["Equivalent diameter (µm)"] = 2 * np.sqrt(size["Area (µm²)"] / np.pi)
    for col, label in (("Feret", "Feret diameter max (µm)"), ("MinFeret", "Feret diameter min (µm)"),
                       ("Perim.", "Perimeter (µm)")):
        if col in df.columns:
            size[label] = pd.to_numeric(df[col], errors="coerce").values * lin
    for col, label in (("Circ.", "Circularity"), ("Round", "Roundness"), ("AR", "Aspect ratio"),
                       ("Solidity", "Solidity")):
        if col in df.columns:
            size[label] = pd.to_numeric(df[col], errors="coerce").values
    return size


# ------------------------------------------------------------------ analysis
def analyse_recording(csv, name, baseline, peak, n_sd, n_bg, use):
    raw = read_imagej_csv(csv)
    X, bg = background_subtract(raw, n_bg, use)
    b0, b1 = baseline
    p0, p1 = peak
    Bavg = X.loc[b0:b1].mean()
    F = X - Bavg
    mean_base = F.loc[b0:b1].mean()
    sd_base = F.loc[b0:b1].std(ddof=1)
    thr = mean_base + n_sd * sd_base
    peak_F = F.loc[p0:p1].mean()
    resp = peak_F > thr
    F0 = Bavg.where(Bavg > 0)                 # deltaF/F0 only for cells brighter than background
    return dict(name=name, csv=Path(csv), raw=raw, bg=bg, X=X, Bavg=Bavg, F=F, dFF0=F / F0,
                mean_base=mean_base, sd_base=sd_base, thr=thr, peak_F=peak_F, peak_dFF0=peak_F / F0,
                max_F=F.loc[p0:p1].max(), resp=resp, baseline=baseline, peak=peak, n_sd=n_sd)


def _err(v, kind):
    v = v.dropna()
    if len(v) < 2:
        return np.nan
    sd = v.std(ddof=1)
    return sd / np.sqrt(len(v)) if kind == "SEM" else sd


def safe_sheet(name, used):
    s = re.sub(r"[\[\]\:\*\?\/\\]", "_", name)[:28] or "sheet"
    base, k = s, 2
    while s in used:
        s = f"{base[:25]}_{k}"; k += 1
    used.add(s)
    return s


def safe_file(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "table"


def run(csvs, names, baselines, peaks, n_sds, n_bg, use, interval, washes, out,
        qc_index=None, size_csv=None, px_um=0, csv_style="en"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.csv")) + list(out.glob("*.xlsx")):
        old.unlink()

    recs = []
    for csv, nm, bl, pk, sd in zip(csvs, names, baselines, peaks, n_sds):
        d = analyse_recording(csv, nm, bl, pk, sd, n_bg, use)
        baseline_check(d["X"], bl, nm)
        recs.append(d)

    ref = list(recs[0]["F"].columns)
    for d in recs[1:]:
        if list(d["F"].columns) != ref:
            raise ValueError(f"{d['csv'].name} has different ROI columns than {recs[0]['csv'].name} "
                             f"- measure every recording with the SAME ROI zip.")
    n_all = len(ref)
    for d in recs:
        bad = d["Bavg"][d["Bavg"] <= 0].index.tolist()
        if bad:
            print(f"  note {d['name']}: {len(bad)} cell(s) not brighter than background at rest "
                  f"({', '.join(bad[:6])}{'...' if len(bad) > 6 else ''}) -> no ΔF/F0 for them (ΔF still used)")

    qc = recs[qc_index] if qc_index is not None else None
    drugs = [d for i, d in enumerate(recs) if i != qc_index]
    qn = qc["name"] if qc else None
    kept = qc["resp"].copy() if qc else pd.Series(True, index=pd.Index(ref))
    kept.index.name = "Cell"
    missing = [c for c in ref if any(d["raw"][c].isna().any() for d in recs)]
    if missing:
        print(f"  WARNING: {len(missing)} cell(s) have EMPTY values in a CSV: {', '.join(missing[:10])}"
              f"{'...' if len(missing) > 10 else ''} -> marked 'excluded (missing data)'; check these ROIs in ImageJ")
    kept[missing] = False
    status = pd.Series(np.where(kept, "kept", f"excluded (no {qn} response)" if qc else "excluded"),
                       index=kept.index)
    status[missing] = "excluded (missing data)"
    n_kept = int(kept.sum())
    if qc and n_kept == 0:
        raise ValueError(f"no cell passed the {qn} quality control - check the {qn} peak window")
    cells_k = kept.index[kept]

    if qc:
        qc_peak = qc["peak_F"].where(kept)            # > threshold > 0 for every kept cell
        for d in recs:
            d["norm"] = d["F"] / qc_peak
            d["peak_norm"] = d["peak_F"] / qc_peak

    # experiment time: recordings in order, washes as gaps
    start, starts = 0.0, []
    for i, d in enumerate(recs):
        starts.append(start)
        start += len(d["F"]) * interval + (washes[i] if i < len(washes) else 0)

    # ---------------- 1) Responders: one row per cell, yes/no per drug
    resp_tab = pd.DataFrame(index=pd.Index(ref, name="Cell"))
    if qc:
        resp_tab[f"{qn} (quality control)"] = status.values
    for d in drugs:
        yes = np.where(d["resp"], "yes", "no")
        resp_tab[d["name"]] = np.where(kept, yes, "excluded")
    rt = pd.DataFrame({d["name"]: d["resp"] & kept for d in drugs})
    combo = rt.apply(lambda r: " + ".join([n for n in rt.columns if r[n]]) or "none", axis=1)
    resp_tab["Responds to"] = np.where(kept, combo, status.values)
    resp_tab["Number of drugs"] = rt.sum(axis=1).where(kept)

    # ---------------- 2) Per cell: every number
    per_cell = pd.DataFrame(index=pd.Index(ref, name="Cell"))
    if qc:
        per_cell[f"{qn} QC"] = status.values
    size = None
    if size_csv:
        size = read_size_file(size_csv, ref, px_um)
        for c in size.columns:
            per_cell[c] = size[c]
        med = size["Equivalent diameter (µm)"].median()
        print(f"  cell size: median equivalent diameter {med:.1f} µm, median area {size['Area (µm²)'].median():.1f} µm²")
        if not px_um and med > 60:
            print("  note: diameters look like PIXELS - give the pixel size in µm when asked, "
                  "or set the scale in ImageJ (Analyze > Set Scale) before measuring")
    per_cell["Resting raw intensity, first recording (frames of its baseline)"] = \
        recs[0]["raw"][ref].loc[recs[0]["baseline"][0]:recs[0]["baseline"][1]].mean()
    for d in recs:
        n = d["name"]
        per_cell[f"{n} | Bavg (resting X)"] = d["Bavg"]
        per_cell[f"{n} | SD baseline"] = d["sd_base"]
        per_cell[f"{n} | threshold (mean + {d['n_sd']:g} SD)"] = d["thr"]
        per_cell[f"{n} | mean peak ΔF"] = d["peak_F"]
        per_cell[f"{n} | max ΔF in peak window"] = d["max_F"]
        per_cell[f"{n} | mean peak ΔF/F0"] = d["peak_dFF0"]
        if qc and d is not qc:
            per_cell[f"{n} | mean peak ΔF/ΔF({qn})"] = d["peak_norm"]
        per_cell[f"{n} | responder (1/0)"] = d["resp"].astype(int)

    # ---------------- 3) Summary per drug (analysed = kept cells)
    rows = []
    for d in drugs:
        r = (d["resp"] & kept)
        sel = r[r].index
        row = {"Drug": d["name"], "File": d["csv"].name, "Frames": len(d["F"]),
               "Baseline frames": f"{d['baseline'][0]}-{d['baseline'][1]}",
               "Peak frames": f"{d['peak'][0]}-{d['peak'][1]}", "Threshold": f"mean + {d['n_sd']:g} SD",
               "Cells analysed": n_kept, "Responders": int(r.sum()),
               "% responders": round(100 * r.sum() / n_kept, 1),
               "Mean peak ΔF (responders)": d["peak_F"][sel].mean(),
               "SEM peak ΔF": _err(d["peak_F"][sel], "SEM"), "SD peak ΔF": _err(d["peak_F"][sel], "SD"),
               "Mean peak ΔF/F0 (responders)": d["peak_dFF0"][sel].mean(),
               "SEM peak ΔF/F0": _err(d["peak_dFF0"][sel], "SEM"), "SD peak ΔF/F0": _err(d["peak_dFF0"][sel], "SD")}
        if qc:
            row[f"Mean peak ΔF/ΔF({qn}) (responders)"] = d["peak_norm"][sel].mean()
            row[f"SEM peak ΔF/ΔF({qn})"] = _err(d["peak_norm"][sel], "SEM")
            row[f"SD peak ΔF/ΔF({qn})"] = _err(d["peak_norm"][sel], "SD")
        rows.append(row)
    summary = pd.DataFrame(rows)

    counts = combo[kept].value_counts()
    order = sorted(counts.index, key=lambda s: (s == "none", -s.count("+"), s))
    combos = pd.DataFrame({"Responds to": order, "Cells": counts.reindex(order).values,
                           "% of analysed cells": (100 * counts.reindex(order).values / n_kept).round(1)})

    # ---------------- 4) Traces: mean per frame (long table) and every cell (wide, on the experiment time)
    long_rows, wide = [], {"dF": [], "dF_F0": [], "dF_norm": []}
    for i, d in enumerate(recs):
        fr = d["F"].index.values
        t_rec = (fr - 1) * interval
        t_exp = starts[i] + t_rec
        groups = [("all analysed cells", cells_k)]
        if d is not qc:
            r = d["resp"] & kept
            groups += [("responders", r[r].index), ("non-responders", r[(~r) & kept].index)]
        else:
            groups += [(f"excluded ({qn}-negative)", kept.index[~kept])]
        for gname, cells in groups:
            base = {"Recording": d["name"], "Group": gname, "n cells": len(cells), "Frame": fr,
                    "Time in recording (s)": t_rec, "Experiment time (s)": t_exp}
            blk = pd.DataFrame(base)
            for key, lab in (("F", "ΔF"), ("dFF0", "ΔF/F0"), ("norm", f"ΔF/ΔF({qn})")):
                if key not in d or len(cells) == 0:
                    continue
                v = d[key][cells]
                n = v.notna().sum(axis=1)
                blk[f"Mean {lab}"] = v.mean(axis=1).values
                blk[f"SD {lab}"] = v.std(axis=1, ddof=1).values
                blk[f"SEM {lab}"] = (v.std(axis=1, ddof=1) / np.sqrt(n)).values
            long_rows.append(blk)
        for key, tag in (("F", "dF"), ("dFF0", "dF_F0"), ("norm", "dF_norm")):
            if key in d:
                w = d[key][cells_k].copy()
                w.insert(0, "Experiment time (s)", t_exp)
                w.insert(0, "Time in recording (s)", t_rec)
                w.insert(0, "Recording", d["name"])
                wide[tag].append(w.reset_index())
    mean_traces = pd.concat(long_rows, ignore_index=True)
    wide = {k: pd.concat(v, ignore_index=True) for k, v in wide.items() if v}

    # ---------------- 5) Settings
    set_rows = [("Recordings (in order)", " | ".join(f"{d['name']} = {d['csv'].name}" for d in recs)),
                ("Frame interval (s)", interval),
                ("Washing between recordings (s)", " | ".join(f"{recs[i]['name']} -> {recs[i + 1]['name']}: {w:g}"
                                                              for i, w in enumerate(washes)) or "-"),
                ("Background ROIs", ", ".join(use) if use else ", ".join(recs[0]["raw"].columns[-n_bg:]) if n_bg else "none"),
                ("Responder rule", "mean ΔF in peak window > mean baseline + N SD (per recording, per cell)"),
                ("Units", "ΔF = X - Bavg (gray value), ΔF/F0 = ΔF / Bavg")]
    for d in recs:
        set_rows.append((f"{d['name']}", f"baseline {d['baseline'][0]}-{d['baseline'][1]}, peak "
                                          f"{d['peak'][0]}-{d['peak'][1]}, mean + {d['n_sd']:g} SD"))
    if qc:
        set_rows += [("Quality control", f"{qn}: only cells responding to {qn} are analysed"),
                     ("Cells kept / total", f"{n_kept} / {n_all}"),
                     ("Normalisation", f"ΔF / mean ΔF in the {qn} peak window of the same cell")]
    if size is not None:
        set_rows += [("Size file", Path(size_csv).name), ("Pixel size (µm)", px_um or "file already in µm")]
    settings = pd.DataFrame(set_rows, columns=["Setting", "Value"])

    # ---------------- write: Excel + CSV
    tables = [("Summary", summary, False), ("Responders", resp_tab, True), ("Combinations", combos, False)]
    if qc:
        qcs = pd.DataFrame({"": ["Total cells", f"{qn}-positive (kept)", f"{qn}-negative (excluded)"],
                            "Cells": [n_all, n_kept, n_all - n_kept],
                            "%": [100.0, round(100 * n_kept / n_all, 1), round(100 * (n_all - n_kept) / n_all, 1)]})
        tables += [("QC", qcs, False), ("Excluded_cells", per_cell[~kept.values], True)]
    tables += [("Per_cell", per_cell, True)]
    if size is not None:
        tables += [("Cell_size", size, True)]
    tables += [("Mean_traces", mean_traces, False), ("Cell_traces_dF", wide["dF"], False),
               ("Cell_traces_dF_F0", wide["dF_F0"], False)]
    if qc:
        qall = qc["F"].copy()
        qall.insert(0, "Time in recording (s)", (qall.index.values - 1) * interval)
        status = pd.DataFrame([["", ""] + list(status.values),
                               ["", "threshold"] + list(qc["thr"].values),
                               ["", "mean peak"] + list(qc["peak_F"].values)],
                              columns=["Frame", "Time in recording (s)"] + list(qc["F"].columns))
        qall = pd.concat([status, qall.reset_index()], ignore_index=True)
        tables += [(f"QC_{safe_file(qn)}_dF_all_cells", qall, False)]
    if "dF_norm" in wide:
        tables += [(f"Cell_traces_norm_{safe_file(qn)}", wide["dF_norm"], False)]
    tables += [("Settings", settings, False)]
    for i, d in enumerate(recs, 1):
        r = d["raw"].copy(); r["Background used"] = d["bg"]
        tables.append((f"Raw_{i}_{d['name']}", r, True))

    sep, dec = (";", ",") if csv_style == "de" else (",", ".")
    xlsx = out / "multidrug_results.xlsx"
    used = set()
    with pd.ExcelWriter(xlsx) as w:
        for name, df, idx in tables:
            df.to_excel(w, sheet_name=safe_sheet(name, used), index=idx)
    csv_dir = out / "csv"
    csv_dir.mkdir(exist_ok=True)
    for old in csv_dir.glob("*.csv"):
        old.unlink()
    for k, (name, df, idx) in enumerate(tables, 1):
        df.to_csv(csv_dir / f"{k:02d}_{safe_file(name)}.csv", sep=sep, decimal=dec, index=idx,
                  encoding="utf-8-sig")

    zpath = out.parent / f"{out.name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, arcname=f"{out.name}/{f.relative_to(out)}")

    print(f"\n{n_all} cells (same ROIs in all recordings)")
    if qc:
        print(f"  quality control {qn}: {n_kept} kept ({100 * n_kept / n_all:.1f}%), "
              f"{n_all - n_kept} excluded -> everything below is of the {n_kept} kept cells")
    for row in rows:
        print(f"  {row['Drug']:<15s} responders {row['Responders']:4d} ({row['% responders']:5.1f}%)   "
              f"baseline {row['Baseline frames']}, peak {row['Peak frames']}")
    print("  responded to:")
    for _, r in combos.iterrows():
        print(f"    {r['Responds to']:<35s} {r['Cells']:4d} ({r['% of analysed cells']:5.1f}%)")
    print(f"  results: {xlsx}\n           {csv_dir}/ ({len(tables)} CSV files)  (zip: {zpath.name})")
    return dict(per_cell=per_cell, responders=resp_tab, summary=summary, mean_traces=mean_traces)


def overview(csvs, names, n_bg, use, out_dir):
    """No graph: prints where each recording rises and peaks, and saves the median trace per frame."""
    rows = {}
    for csv, nm in zip(csvs, names):
        raw = read_imagej_csv(csv)
        X, bg = background_subtract(raw, n_bg, use)
        med = X.median(axis=1)
        rest = med.iloc[:8]
        lim = rest.mean() + 5 * max(rest.std(ddof=1), 1e-9)
        above = med[med > lim]
        top = int(med.idxmax())
        rise = int(above.index[0]) if len(above) else None
        if rise:
            print(f"  {nm:<15s} {len(raw)} frames | median cell rises above rest at frame {rise} | "
                  f"highest median at frame {top} -> e.g. peak window {max(1, top - 3)}-{min(len(raw), top + 3)}")
        else:
            print(f"  {nm:<15s} {len(raw)} frames | no clear rise in the median cell -> choose the peak "
                  f"window from when the drug was added (few cells may still respond)")
        rows[f"{nm} median ΔX"] = med - rest.mean()
    path = Path(out_dir) / "overview_median_per_frame.csv"
    pd.DataFrame(rows).to_csv(path)
    print(f"Overview table saved: {path}")
    print("  (a weak or slow response may not show in the median - also check the Z-axis profile in ImageJ)")


# ====================================================================== interactive
def _ask(prompt, default, cast=str):
    """default None = no suggestion: the user MUST type an answer."""
    while True:
        if default is None:
            shown = ""
        else:
            shown = f"{default[0]}-{default[1]}" if isinstance(default, tuple) else \
                ",".join(default) if isinstance(default, list) else default
        try:
            s = input(f"{prompt}{f' [{shown}]' if shown != '' else ' (required)'}: ").strip()
        except EOFError:
            raise SystemExit(f"\nno answer for: {prompt}")
        if s == "" and default is None:
            print("  this one has no default - please type it")
            continue
        try:
            return cast(default) if s == "" else cast(s)
        except ValueError as e:
            print(f"  {e if cast not in (int, float) else 'please enter a number'} - try again")


def _range(s, n_frames=None):
    nums = [int(v) for v in re.findall(r"\d+", str(s))]
    if len(nums) != 2:
        raise ValueError("type two frame numbers, first and last, e.g. 1-10")
    a, b = sorted(nums)
    if a < 1 or (n_frames and b > n_frames):
        raise ValueError(f"frames must be between 1 and {n_frames}")
    return a, b


def _find(name):
    p = Path(str(name).strip().strip('"').strip("'"))
    if not p.exists() and not p.is_absolute():
        alt = Path(__file__).resolve().parent / p
        if alt.exists():
            return alt
    if not p.exists():
        raise ValueError(f"file not found: {p} (put it in this folder or give the full path)")
    return p


def _exists(name):
    return bool(name) and (Path(name).exists() or (Path(__file__).resolve().parent / name).exists())


def _file_or_none(v):
    v = str(v).strip()
    if v.lower() in ("none", "no", "n", "0", ""):
        return None
    return _find(v)


def main():
    import argparse, json
    ap = argparse.ArgumentParser(description="Several drugs, one ImageJ CSV per drug, same ROIs. Data only.")
    ap.add_argument("--overview", action="store_true", help="only print where each recording rises and peaks")
    a = ap.parse_args()

    print("\nPress ENTER to accept the value in [brackets], or type a new one.\n")

    def ndrugs(v):
        v = int(v)
        if not 1 <= v <= 10:
            raise ValueError("between 1 and 10")
        return v
    n = _ask("Number of drugs (NOT counting the quality-control recording)", N_DRUGS, ndrugs)

    csvs, names, raws = [], [], []

    def add(csv, nm):
        raw = read_imagej_csv(csv)
        print(f"  {csv.name}: {len(raw)} frames, columns {raw.columns[0]} ... {raw.columns[-1]}")
        if raws and list(raw.columns) != list(raws[0].columns):
            print("  WARNING: the columns differ from the first file - were all recordings measured "
                  "with the SAME ROI zip?")
        csvs.append(csv); names.append(nm); raws.append(raw)

    for i in range(n):
        dflt_csv = CSV_FILES[i] if i < len(CSV_FILES) else f"drug{i + 1}.csv"
        csv = _ask(f"Drug {i + 1}: CSV file", dflt_csv if _exists(dflt_csv) else None, _find)
        nm = _ask(f"Drug {i + 1}: name", DRUG_NAMES[i] if DRUG_NAMES and i < len(DRUG_NAMES) else None)
        add(csv, nm)

    qc_csv = _ask("Quality-control recording CSV (e.g. KCl or ionomycin), or 'none'",
                  QC_FILE if _exists(QC_FILE) else None, _file_or_none)
    qc_index = None
    if qc_csv:
        nm = _ask("Quality-control drug name (e.g. KCl, ionomycin)", QC_NAME)
        add(qc_csv, nm)
        qc_index = len(csvs) - 1
        print(f"  -> only cells that respond to {nm} are analysed; the others are listed as excluded")

    n_cols = raws[0].shape[1]

    def nbg(v):
        v = int(v)
        if not 0 <= v < n_cols:
            raise ValueError(f"must be between 0 and {n_cols - 1}")
        return v
    n_bg = _ask("Number of background ROIs (last columns)", N_BACKGROUND_ROIS, nbg)
    bg_cols = list(raws[0].columns[-n_bg:]) if n_bg else []
    use = None
    if n_bg:
        print(f"  background boxes: {', '.join(bg_cols)}")
        warned = set()
        for raw, nm in zip(raws, names):
            warned |= set(check_background(raw, n_bg, nm))
        if warned:
            good = [c for c in bg_cols if c not in warned]
            print(f"  -> suggestion: use only {', '.join(good)}" if good else
                  "  -> redraw the background boxes in ImageJ on truly empty, dark areas")
        else:
            print("  all background boxes look empty and flat in every recording")

        def pick(v):
            v = ",".join(v) if isinstance(v, list) else str(v).strip()
            if v.lower() in ("all", "none", ""):
                return None
            by_num = {re.findall(r"\d+", c)[-1]: c for c in bg_cols if re.findall(r"\d+", c)}
            nums = re.findall(r"\d+", v)
            if not nums or any(k not in by_num for k in nums):
                raise ValueError(f"choose from {', '.join(bg_cols)} or 'all'")
            return [by_num[k] for k in nums]
        dflt = [c for c in (BACKGROUND_USE or []) if c in bg_cols] or "all"   # e.g. ["Mean98"] or ["Mean(98)"]
        use = _ask("Background boxes to use ('all' or e.g. Mean98)", dflt, pick)

    if a.overview:
        overview(csvs, names, n_bg, use, Path(csvs[0]).parent)
        return

    interval = _ask("Seconds between frames", FRAME_INTERVAL, float)
    washes = []
    for i in range(len(names) - 1):
        washes.append(_ask(f"Washing time between {names[i]} and {names[i + 1]} (s)", WASH_TIME, float))

    baselines, peaks, n_sds = [], [], []
    for i, (nm, raw) in enumerate(zip(names, raws)):
        nf = len(raw)
        rng = lambda v, nf=nf: _range(v, nf)
        is_qc = i == qc_index
        print(f"\n  {nm} ({nf} frames){'  - quality control' if is_qc else ''}")
        bl = _ask(f"  {nm}: baseline frames (first-last)", BASELINE, rng)
        pk_d = QC_PEAK if is_qc else (PEAKS[i] if PEAKS and i < len(PEAKS) else None)
        while True:
            pk = _ask(f"  {nm}: peak frames (first-last)",
                      pk_d if pk_d and pk_d[1] <= nf and pk_d[0] > bl[1] else None, rng)
            if pk[0] > bl[1]:
                break
            print("  the peak window must start after the baseline ends - try again")
        sd = _ask(f"  {nm}: threshold (number of SD)", float(THRESHOLD_SD), float)
        baselines.append(bl); peaks.append(pk); n_sds.append(sd)

    size_csv = _ask("Cell size file (ImageJ Measure of the ROIs), or 'none'",
                    SIZE_FILE if _exists(SIZE_FILE) else "none", _file_or_none)
    px_um = 0.0
    if size_csv:
        px_um = _ask("Pixel size in µm if that file is in pixels (0 = already in µm)", float(PIXEL_SIZE_UM), float)

    def style(v):
        v = str(v).strip().lower()
        if v not in ("en", "de"):
            raise ValueError("type en (comma, decimal point) or de (semicolon, decimal comma)")
        return v
    csv_style = _ask("CSV style: en = 1.5 with commas, de = 1,5 with semicolons (German Excel)", CSV_STYLE, style)

    out = Path(csvs[0]).parent / OUTPUT_FOLDER
    print()
    run(csvs, names, baselines, peaks, n_sds, n_bg, use, interval, washes, out,
        qc_index=qc_index, size_csv=size_csv, px_um=px_um, csv_style=csv_style)

    settings = dict(csvs=[c.name for c in csvs], names=names, baselines=baselines, peaks=peaks,
                    n_sd=n_sds, n_bg=n_bg, bg_use=use, interval=interval, washes=washes,
                    qc=names[qc_index] if qc_index is not None else None,
                    size_file=size_csv.name if size_csv else None, pixel_size_um=px_um, csv_style=csv_style)
    (out / "settings.json").write_text(json.dumps(settings, indent=2))


if __name__ == "__main__":
    main()
