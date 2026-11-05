"""
segment_cells.py - Cellpose-SAM segmentation on your own computer (terminal).

Does EXACTLY what the Google Colab notebook does (same code, same settings), so the two
should give the same ROIs for the same image and the same Cellpose version.
Check this on your own image with compare_rois.py.

HOW TO USE (in the folder with the image, in the "cellpose" conda environment):
    python segment_cells.py
It asks for the image and the settings ([brackets] = suggestion, ENTER accepts).

Output, next to the image:
    <name>_rois.zip          ImageJ ROIs, one per cell  -> load in Fiji's ROI Manager
    <name>_outlines.png      picture of the outlines, to check the segmentation
    <name>_masks.tif         label image (0 = background, 1..N = cell number)
    <name>_segmentation.json settings, Cellpose version, number of cells, median diameter
"""

# =========================== SETTINGS = SUGGESTIONS shown in [brackets] ===========================
DIAMETER = 0                  # 0 = no resizing (Cellpose-SAM default); else the cell diameter in pixels
CELLPROB_THRESHOLD = 0.0      # lower (e.g. -1) = more cells, higher (e.g. 1) = fewer
FLOW_THRESHOLD = 0.4          # higher (e.g. 0.6) = accepts less perfect shapes
FLATTEN_ILLUMINATION = False  # True if one side of the image is brighter than the other
# ===================================================================================================

import json
import sys
from pathlib import Path

import numpy as np


# ---------- the segmentation itself: IDENTICAL to the code in notebooks/cellpose_colab.ipynb ----------
def load_image(path):
    """Read the image as one 2D grey image (RGB -> grey, several frames -> average)."""
    from cellpose import io
    img = io.imread(str(path)).astype(np.float32)
    print("Image shape as loaded:", img.shape)
    if img.ndim == 3:
        if img.shape[-1] in (3, 4):          # RGB -> gray
            img = img[..., :3].mean(axis=-1)
        else:                                # several frames -> average
            img = img.mean(axis=0)
    print(f"Image used: {img.shape[1]} x {img.shape[0]} pixels (width x height) -> must match the movies")
    return img


def segment(img, diameter=0, cellprob_threshold=0.0, flow_threshold=0.4, flatten_illumination=False):
    """Run Cellpose-SAM. Returns the label image (0 = background, 1..N = cells)."""
    from cellpose import models
    from scipy.ndimage import gaussian_filter
    if flatten_illumination:
        img = img / (gaussian_filter(img, sigma=100) + 1e-6)
    model = models.CellposeModel(gpu=True)    # uses the GPU if there is one, otherwise the CPU
    masks, flows, styles = model.eval(
        img,
        diameter=None if diameter == 0 else diameter,
        cellprob_threshold=cellprob_threshold,
        flow_threshold=flow_threshold,
    )
    return masks
# --------------------------------------------------------------------------------------------------------


def save_outputs(img, masks, image_path, settings):
    from cellpose import io, utils
    import cellpose
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import tifffile

    stem = str(Path(image_path).with_suffix(""))
    n_cells = int(masks.max())
    diam = float(utils.diameters(masks)[0]) if n_cells else 0.0
    print(f"Cells found: {n_cells}")
    print(f"Median diameter: {diam:.1f} px")

    io.save_rois(masks, stem)                                   # -> <stem>_rois.zip
    tifffile.imwrite(stem + "_masks.tif", masks.astype(np.uint16 if n_cells < 65535 else np.uint32))

    lo, hi = np.percentile(img, (1, 99))
    fig, ax = plt.subplots(1, 2, figsize=(20, 9))
    ax[0].imshow(img, cmap="gray", vmin=lo, vmax=hi); ax[0].set_title("Image")
    ax[1].imshow(img, cmap="gray", vmin=lo, vmax=hi)
    for o in utils.outlines_list(masks):
        ax[1].plot(o[:, 0], o[:, 1], color="yellow", linewidth=0.8)
    ax[1].set_title(f"{n_cells} cells")
    for a in ax:
        a.axis("off")
    plt.tight_layout()
    fig.savefig(stem + "_outlines.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    info = dict(settings, image=Path(image_path).name, image_size_px=[int(img.shape[1]), int(img.shape[0])],
                cells=n_cells, median_diameter_px=round(diam, 2),
                cellpose_version=getattr(cellpose, "version", None) or _pkg_version("cellpose"))
    Path(stem + "_segmentation.json").write_text(json.dumps(info, indent=2))
    print(f"\nSaved: {Path(stem).name}_rois.zip, _outlines.png, _masks.tif, _segmentation.json")
    print("Open the _outlines.png: if cells are missed or debris is outlined, change the settings and run again.")


def _pkg_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "unknown"


def _ask(prompt, default, cast=str):
    while True:
        shown = "" if default is None else f" [{default}]"
        try:
            s = input(f"{prompt}{shown if shown else ' (required)'}: ").strip()
        except EOFError:
            raise SystemExit(f"\nno answer for: {prompt}")
        if s == "" and default is None:
            print("  please type it")
            continue
        try:
            return cast(default) if s == "" else cast(s)
        except ValueError as e:
            print(f"  {e} - try again")


def _image(v):
    p = Path(str(v).strip().strip('"').strip("'"))
    if not p.exists():
        raise ValueError(f"file not found: {p}")
    return p


def _yesno(v):
    v = str(v).strip().lower()
    if v in ("y", "yes", "true", "1"):
        return True
    if v in ("n", "no", "false", "0"):
        return False
    raise ValueError("type y or n")


def main():
    try:
        import cellpose  # noqa: F401
    except ImportError:
        sys.exit("Cellpose is not installed in this environment. Run:  conda activate cellpose  "
                 "(or see docs/03_cellpose_local.md)")
    print("\nPress ENTER to accept the value in [brackets], or type a new one.\n")
    image = _ask("Image to segment (e.g. brightfield.tif)", None, _image)
    diameter = _ask("Cell diameter in pixels (0 = no resizing)", float(DIAMETER), float)
    cellprob = _ask("Cellprob threshold", float(CELLPROB_THRESHOLD), float)
    flow = _ask("Flow threshold", float(FLOW_THRESHOLD), float)
    flatten = _ask("Flatten uneven illumination? y/n", "y" if FLATTEN_ILLUMINATION else "n", _yesno)
    settings = dict(diameter=diameter, cellprob_threshold=cellprob, flow_threshold=flow,
                    flatten_illumination=flatten)
    print()
    img = load_image(image)
    masks = segment(img, diameter, cellprob, flow, flatten)
    save_outputs(img, masks, image, settings)


if __name__ == "__main__":
    main()
