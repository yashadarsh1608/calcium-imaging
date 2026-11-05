# 3b · Cellpose on your own computer

Two ways, both with the same Cellpose-SAM model as Colab. Install first: [00_installation.md](00_installation.md)
(Option A), then `conda activate cellpose`.

## Option 1 — the terminal script (same result as Colab)

`scripts/segment_cells.py` contains **the same code** as the Colab notebook (the notebook is built from
it), so with the same image, settings and Cellpose version it gives the same ROIs.

```bash
conda activate cellpose
cd /path/to/your/experiment          # the folder with brightfield.tif
python /path/to/calcium-imaging-pipeline/scripts/segment_cells.py
```

It asks (ENTER accepts the value in brackets):

```
Image to segment (e.g. brightfield.tif) (required): brightfield.tif
Cell diameter in pixels (0 = no resizing) [0.0]:
Cellprob threshold [0.0]:
Flow threshold [0.4]:
Flatten uneven illumination? y/n [n]:
```

Output next to the image: `brightfield_rois.zip`, `brightfield_outlines.png` (open it to check),
`brightfield_masks.tif`, `brightfield_segmentation.json`. The settings work as in
[03a_cellpose_colab.md](03a_cellpose_colab.md#settings).

On the CPU a 3200 × 2200 image takes a few minutes; the first run also downloads the model (~1 GB).

## Option 2 — the Cellpose window (GUI)

Good for looking at the result and trying settings by eye.

```bash
conda activate cellpose
python -m cellpose
```

1. **File → Load image** (or drag `brightfield.tif` into the window).
2. On the right: leave *diameter* at its default first; set *cellprob threshold* and *flow threshold*
   as in the table in 03a. Click **run** (the model is Cellpose-SAM, `cpsam`).
3. Check the outlines. You can delete a wrong cell (Ctrl + click) or draw a missing one (right-click,
   draw, right-click again).
4. **File → Save outlines as .zip archive of ROI files for ImageJ** (Ctrl + R) → `brightfield_rois.zip`
   next to the image.

The window uses the same Cellpose-SAM model, but it prepares the image itself (e.g. how an RGB or
multi-frame image is converted) and some of its defaults can differ from the script, so small
differences to Colab are possible. Use `compare_rois.py` to see how big they are. For results that
must match Colab exactly, use Option 1.

## Do Colab and my computer give the same ROIs?

Run both on **the same image with the same settings**, then compare the two zips (example output below):

```bash
python /path/to/calcium-imaging-pipeline/scripts/compare_rois.py
```

```
ROI zip A (e.g. from Colab): colab/brightfield_rois.zip
ROI zip B (e.g. from your computer): brightfield_rois.zip

  cells in A: 97    cells in B: 97
  same cell found in both (IoU >= 0.5): 97
  only in A: 0    only in B: 0
  mean overlap (IoU) of matched cells: 0.998   identical outlines: 95
  same cell numbering in A and B: yes

  -> the same segmentation (differences only at single edge pixels).
```

IoU = overlap of two outlines (1.0 = identical). A GPU (Colab) and a CPU can differ in the last digits of
the calculation, which can move single edge pixels; that does not change the measured intensities in a
meaningful way. If cells are missing or the numbering differs, check that both used the same image,
settings and Cellpose version (the `_segmentation.json` files list all three). The CSV
`A_vs_B.csv` lists every cell pair.

**Important:** whichever way you segment, use **one** ROI zip for all movies of an experiment.
