# 3a · Cellpose in Google Colab

Colab gives you a free GPU in the browser: nothing to install. The notebook draws one outline per cell
on the brightfield image and saves them as an ImageJ ROI zip.

**Segment once per experiment** and use the same ROI zip for every movie.

## Steps

1. **Prepare the image.** If `brightfield.tif` has several frames, make one image in Fiji first:
   **Image → Stacks → Z Project… → Average Intensity** → File → Save As → Tiff.
2. **Upload it to Google Drive**, e.g. into a folder `cellpose` (My Drive → New → Folder).
3. **Open the notebook**: go to <https://colab.research.google.com> → *GitHub* tab → paste the
   repository URL → open `notebooks/cellpose_colab.ipynb`
   (or File → Upload notebook → choose `notebooks/cellpose_colab.ipynb` from the downloaded repository).
4. **Runtime → Change runtime type → T4 GPU → Save.**
5. **Cell 1** (connect Drive): run it, allow access to your Google Drive.
6. **Cell 2** (install): wait 1–2 minutes. It installs **Cellpose 4.2.1.1**, the same version as on your
   computer.
7. **Cell 3** (segment): set `IMAGE_PATH`, e.g.
   `"/content/drive/MyDrive/cellpose/brightfield.tif"`, and run. It prints:
   - `Image used: 3200 x 2200 pixels` — must be the same size as your movies (Fiji window title)
   - `Cells found: 97` and `Median diameter: … px`
   - a picture with the outlines in yellow
8. **Check the outlines** and change the settings if needed (table below), then run Cell 3 again.
9. **Cell 4** (save): downloads `brightfield_rois.zip`. The zip, `brightfield_outlines.png`,
   `brightfield_masks.tif` and `brightfield_segmentation.json` (settings + cell count) are also saved
   next to the image on your Drive.

## Settings

| Setting | Default | Change when |
|---|---|---|
| `DIAMETER` | `0` = no resizing (Cellpose-SAM works at most cell sizes) | cells are split into pieces or merged: enter the cell diameter in pixels (e.g. the printed median) |
| `CELLPROB_THRESHOLD` | `0` | cells missed → `-1`; debris or background outlined → `1` |
| `FLOW_THRESHOLD` | `0.4` | irregular cells missed → `0.6` |
| `FLATTEN_ILLUMINATION` | `False` | one side of the image is darker → `True` |

Write the settings and the number of cells in the lab notebook (they are also in the `_segmentation.json`).

Next: a few outlines wrong? Fix them in Fiji ([04_imagej_measure.md](04_imagej_measure.md), *Correct
outlines*). Many wrong? Change the settings and run Cell 3 again.
