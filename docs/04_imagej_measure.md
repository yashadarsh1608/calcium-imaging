# 4–5 · ROIs, background boxes and measuring (Fiji)

Here the Cellpose outlines become the measurement: one CSV file per movie with the mean gray value of
every cell (and 3 empty background boxes) in every frame. Optional: one file with the size of every cell.

**Never save the movies in Fiji.** Display changes (contrast) are not needed in the data. If Fiji asks
*"Apply LUT?"* click **Cancel**; if it asks *"Save changes?"* click **No**.

## 4a · Load the outlines

1. Open the first movie (`drug1.tif`).
2. **Analyze → Tools → ROI Manager.** If it lists old ROIs: select all → **Delete**.
3. ROI Manager → **More » → Open…** → `brightfield_rois.zip`. The count must equal the Cellpose count.
4. Make the cells visible: **Image → Adjust → Brightness/Contrast… → Auto** (2–3 times). Do **not**
   click *Apply*.
5. Tick **Show All**, untick **Labels** if the numbers hide the cells, zoom with **+** (move with the
   space bar + drag).
6. Check corners and middle, in frame 1 and the last frame: every outline should sit on one cell.

## 4b · Correct outlines (if needed)

Do this **before** adding the background boxes.

| Problem | In the ROI Manager |
|---|---|
| outline on debris / empty spot / cut cell | click it (or its number) → **Delete**; several: Ctrl + click, then Delete |
| cell missed | Freehand (or Oval / Wand) tool → draw just inside the cell edge → press **T** |
| two cells in one outline | Delete it, draw each cell, press T for each |
| one cell in two outlines | Ctrl + click both → **More » → OR (Combine)** → **Add** → delete the two old ones |
| shape a little off | click it, adjust, **Update** |

Then **More » → Save…** as `brightfield_rois_edited.zip` (keep the original). Cell numbers after a
deleted cell move up by one; that is fine as long as every movie is measured with the same zip. Note the
number of deleted and added cells in the lab notebook.

## 4c · Three background boxes

The background (camera offset, stray light) is subtracted from every cell, so the boxes must be
**empty, dark and flat** in every movie.

1. **Rectangle** tool → draw a small box in an area with **no cell, no debris, not touching an outline**
   → press **T**. Do this 3 times in different parts of the image (e.g. top left, middle, bottom right).
2. The 3 boxes must be the **last 3 ROIs** in the list.
3. Click each box → **Image → Stacks → Plot Z-axis Profile**: the line must be **flat**.
4. Open every other movie (including the quality-control movie), click on it, untick and tick **Show
   All**: the same ROIs appear. Check the outlines and the 3 box profiles there too. The strongest
   response (often KCl) is where a box next to a cell shows up.
5. A box that rises: delete it, draw a new one elsewhere, press **T**, check it again in all movies.
6. **Deselect** → **More » → Save…** → `ROIs_with_bg.zip`.

Boxes already added and you need to change the cells? Ctrl + click the 3 boxes → More » → Save… as
`bg_boxes.zip` (saves only the selected) → delete the boxes → edit cells → More » → Open… `bg_boxes.zip`
(they are added at the end again).

## 5a · Measure every movie (Multi Measure)

1. **Analyze → Set Measurements…** → tick **Mean gray value**, Decimal places **3** → OK.
   (Other ticked boxes do not hurt: the script reads only the *Mean* columns.)
2. Click the movie window (so it is the active one).
3. ROI Manager → **Deselect** → **More » → Multi Measure** → tick **Measure all slices** and **One row
   per slice** → OK.
4. The Results table: **one row per frame**, one *Mean* column per ROI (e.g. `Mean(1)` … `Mean(100)`).
   Check there are no empty cells.
5. Results window → **File → Save As…** → `drug1.csv` (the drug's name is fine too, e.g. `capsaicin.csv`).
6. Close the Results window. Repeat 2–6 for every movie: `drug2.csv`, `drug3.csv`, `kcl.csv`.

Always click the right movie before Multi Measure; otherwise Fiji measures the wrong one.

## 5b · Cell size (optional, once)

Gives area and diameter of every cell. The movies share the ROIs, so one measurement is enough.

1. Open one movie (or the brightfield image) with the same `ROIs_with_bg.zip` loaded.
2. **Image → Properties…**: look at *Pixel width* and *Unit*. If it says pixel, or a strange value
   (e.g. `0.0000023 µm`), remove the scale: **Analyze → Set Scale… → Click to Remove Scale → OK**. The
   script converts with the real pixel size you type.
3. **Analyze → Set Measurements…** → tick **Area**, **Perimeter**, **Shape descriptors**, **Feret's
   diameter** → OK.
4. ROI Manager → **Deselect** → **Measure** (the **Measure** button, not Multi Measure). One row per ROI.
5. Results → **File → Save As…** → `cell_size.csv`, in the same folder as the other CSV files.

## The folder for the analysis

```
2026-10-27_mDRG_exp1/
├── drug1.csv  drug2.csv  drug3.csv  kcl.csv
├── cell_size.csv            (optional)
└── ROIs_with_bg.zip         (keep it with the data)
```

Next: [05_python_analysis.md](05_python_analysis.md).
