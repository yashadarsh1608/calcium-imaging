"""
compare_rois.py - do two segmentations give the same cells?

Use it to check that Cellpose in Google Colab and Cellpose on your own computer (terminal script
or Cellpose window) give the same outlines for the same image, or to compare an edited ROI set
with the original.

HOW TO USE:
    python compare_rois.py
It asks for the two ROI zip files (ImageJ / Cellpose "_rois.zip").

How it compares: every outline is turned into a filled area. Each cell in A is paired with the
cell in B that overlaps it most. Overlap = IoU (intersection over union): 1.0 = identical,
0 = no overlap. Pairs with IoU >= 0.5 count as "the same cell".

Output: a summary in the terminal + <A>_vs_<B>.csv with one row per cell pair
(areas there are approximate outline areas in pixels, for comparing A with B only).
Needs: numpy, pandas, matplotlib, roifile  (pip install roifile).
"""

MATCH_IOU = 0.5

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def read_rois(path):
    try:
        from roifile import roiread
    except ImportError:
        sys.exit("roifile is missing: pip install roifile")
    rois = roiread(str(path))
    if not isinstance(rois, list):
        rois = [rois]
    out = []
    for i, r in enumerate(rois, 1):
        xy = np.asarray(r.coordinates(), dtype=float)
        if xy.ndim != 2 or len(xy) < 3:
            continue
        out.append((r.name or str(i), xy))
    return out


def _box(xy):
    return np.floor(xy.min(axis=0)), np.ceil(xy.max(axis=0))


def _iou(xy1, xy2):
    """Overlap of two outlines, computed on their joint bounding box (outlines may overlap others)."""
    lo = np.minimum(xy1.min(axis=0), xy2.min(axis=0)).astype(int) - 1
    hi = np.maximum(xy1.max(axis=0), xy2.max(axis=0)).astype(int) + 2
    shape = (hi[1] - lo[1], hi[0] - lo[0])
    m1 = _fill_local(xy1 - lo, shape)
    m2 = _fill_local(xy2 - lo, shape)
    union = (m1 | m2).sum()
    return ((m1 & m2).sum() / union if union else 0.0), int(m1.sum()), int(m2.sum())


def _fill_local(xy, shape):
    from matplotlib.path import Path as MPath
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    pts = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
    return MPath(xy).contains_points(pts, radius=0.5).reshape(shape)


def compare(a_path, b_path, match_iou=MATCH_IOU):
    A, B = read_rois(a_path), read_rois(b_path)
    boxes_b = [_box(xy) for _, xy in B]
    cands = []
    for ia, (na_, xa) in enumerate(A):
        lo_a, hi_a = _box(xa)
        for ib, (lo_b, hi_b) in enumerate(boxes_b):
            if (lo_a > hi_b).any() or (lo_b > hi_a).any():
                continue                              # bounding boxes do not touch
            iou, sa, sb = _iou(xa, B[ib][1])
            if iou > 0:
                cands.append((iou, ia, ib, sa, sb))
    cands.sort(reverse=True)
    used_a, used_b, rows = set(), set(), []
    for iou, ia, ib, sa, sb in cands:               # best pairs first, each cell used once
        if ia in used_a or ib in used_b or iou < match_iou:
            continue
        used_a.add(ia); used_b.add(ib)
        rows.append(dict(cell_A=A[ia][0], cell_B=B[ib][0], IoU=round(iou, 3), area_A_px=sa, area_B_px=sb,
                         _a=ia, _b=ib))
    areas = lambda xy: int(_fill_local(xy - xy.min(axis=0).astype(int) + 1,
                                       tuple((np.ceil(xy.max(axis=0) - xy.min(axis=0)).astype(int) + 3)[::-1])).sum())
    for ia, (n, xy) in enumerate(A):
        if ia not in used_a:
            rows.append(dict(cell_A=n, cell_B="(no match)", IoU=0.0, area_A_px=areas(xy), area_B_px=0, _a=ia, _b=-1))
    for ib, (n, xy) in enumerate(B):
        if ib not in used_b:
            rows.append(dict(cell_A="(no match)", cell_B=n, IoU=0.0, area_A_px=0, area_B_px=areas(xy), _a=10**9, _b=ib))
    df = pd.DataFrame(rows).sort_values(["_a", "_b"])
    m = df[(df._a < 10**9) & (df._b >= 0)]
    same_order = bool(len(m) == len(A) == len(B) and (m._a.values == m._b.values).all())
    df = df.drop(columns=["_a", "_b"]).reset_index(drop=True)
    return df, dict(cells_A=len(A), cells_B=len(B), matched=len(m),
                    only_A=len(A) - len(m), only_B=len(B) - len(m),
                    mean_IoU=float(m.IoU.mean()) if len(m) else 0.0,
                    identical=int((m.IoU >= 0.99).sum()), same_order=same_order)


def _ask(prompt):
    while True:
        try:
            s = input(f"{prompt}: ").strip().strip('"').strip("'")
        except EOFError:
            raise SystemExit("\nno answer")
        p = Path(s)
        if p.exists():
            return p
        print(f"  file not found: {p} - try again")


def main():
    print("\nCompare two ROI zip files (e.g. Colab result vs terminal result).\n")
    a = _ask("ROI zip A (e.g. from Colab)")
    b = _ask("ROI zip B (e.g. from your computer)")
    df, s = compare(a, b)
    out = a.parent / f"{a.stem}_vs_{b.stem}.csv"
    df.to_csv(out, index=False)
    print(f"\n  cells in A: {s['cells_A']}    cells in B: {s['cells_B']}")
    print(f"  same cell found in both (IoU >= {MATCH_IOU}): {s['matched']}")
    print(f"  only in A: {s['only_A']}    only in B: {s['only_B']}")
    print(f"  mean overlap (IoU) of matched cells: {s['mean_IoU']:.3f}   identical outlines: {s['identical']}")
    print(f"  same cell numbering in A and B: {'yes' if s['same_order'] else 'no'}")
    if s["matched"] == s["cells_A"] == s["cells_B"] and s["mean_IoU"] > 0.98:
        print("\n  -> the same segmentation (differences only at single edge pixels).")
    elif s["matched"] >= 0.95 * max(s["cells_A"], s["cells_B"]):
        print("\n  -> nearly the same: a few cells differ. Check the 'no match' rows in the CSV.")
    else:
        print("\n  -> clearly different: check that both used the same image, settings and Cellpose version.")
    print(f"  details per cell: {out}")


if __name__ == "__main__":
    main()
