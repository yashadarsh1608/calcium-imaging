# Calcium imaging analysis: all steps

Every step from the microscope to the graphs, in order. Do them one after another; each step says what
you need, what to do and what you get.

| Step | Where | You get |
|---|---|---|
| [0 Installation](#step-0--installation) | computer | ImageJ, a `cellpose` Python environment |
| [1 Record](#step-1--record) | microscope | one movie per drug + QC drug, brightfield image |
| [2 Check the movies and frame shift](#step-2--check-the-movies-and-frame-shift-imagej) | ImageJ | frames, peak frames, drift yes/no |
| [3 Outline the cells](#step-3--outline-the-cells-cellpose) | Colab or computer | `brightfield_rois.zip` |
| [4 ROIs and background boxes](#step-4--rois-and-background-boxes-imagej) | ImageJ | `ROIs_with_bg.zip` |
| [5 Measure every movie](#step-5--measure-every-movie-imagej) | ImageJ | `drug1.csv` … `kcl.csv` |
| [6 Cell size](#step-6--cell-size-optional-imagej) | ImageJ | `cell_size.csv` |
| [7 Analysis](#step-7--analysis-python) | Python | `multidrug_results.xlsx` + CSV |
| [8 Graphs](#step-8--graphs-python) | Python | 5 graphs |
| [Flowcharts](#flowcharts) · [Script reference](#script-reference) · [Method](#method) · [Troubleshooting](#troubleshooting) | | |

---

## Flowcharts

### The whole pipeline

```mermaid
flowchart TD
    R["Step 1 · Record<br/>brightfield + one movie per drug<br/>+ QC drug (e.g. KCl) last"]:::img --> C["Step 2 · Check movies<br/>peak frames, frame shift"]:::img
    C --> S["Step 3 · Cellpose<br/>outlines on brightfield<br/>→ brightfield_rois.zip"]:::img
    S --> B["Step 4 · ImageJ<br/>check ROIs + 3 background boxes<br/>→ ROIs_with_bg.zip"]:::img
    B --> M["Step 5 · ImageJ Multi Measure<br/>every movie, same ROIs<br/>→ drug1.csv … kcl.csv"]:::img
    B --> Z["Step 6 · ImageJ Measure<br/>→ cell_size.csv"]:::img
    M --> A["Step 7 · analysis<br/>window (calcium_gui.py) or calcium_multidrug.py<br/>→ multidrug_results.xlsx + CSV"]:::py
    Z --> A
    A --> G["Step 8 · graphs<br/>window or make_graphs.py<br/>→ 5 graphs"]:::py
    classDef img fill:#f2f2f2,stroke:#555,color:#111
    classDef py fill:#e3f4e8,stroke:#1a7f3c,color:#111
```

### The analysis of every cell (`calcium_multidrug.py`)

Blue = every **drug** movie, red = the **quality-control** movie (e.g. KCl), green = combining them.
Each movie is processed with its own baseline.

```mermaid
flowchart TD
    D0["drug CSV<br/>(ImageJ Multi Measure)"]:::drug --> D1["X = cell − mean background<br/>(every frame)"]:::drug
    D1 --> D2["Bavg = mean X over baseline frames<br/>ΔF = X − Bavg"]:::drug
    D2 --> D3["SD of ΔF in baseline<br/>threshold = mean + 5 × SD<br/>mean peak = mean ΔF in peak window"]:::drug
    D3 --> D4{"mean peak<br/>> threshold?"}:::drug
    D4 -- yes --> DR["responder to this drug"]:::drug
    D4 -- no --> DN["non-responder"]:::drug

    Q0["QC CSV (e.g. KCl)"]:::qc --> Q1["X = cell − mean background"]:::qc
    Q1 --> Q2["Bavg, ΔF = X − Bavg"]:::qc
    Q2 --> Q3["threshold = mean + 5 × SD<br/>QC peak = mean ΔF in QC peak window"]:::qc
    Q3 --> Q4{"QC peak<br/>> threshold?"}:::qc
    Q4 -- no --> QE["excluded<br/>(listed with the reason)"]:::qc
    Q4 -- yes --> Q5{"QC peak ΔF/F0<br/>≥ 0.0001?"}:::qc
    Q5 -- no --> QE
    Q5 -- yes --> QK["passed the QC drug"]:::qc

    D3 --> L1{"response to a drug starts<br/>later than 40 s after<br/>the drug was added?"}:::drug
    L1 -- yes --> QE
    QK --> G1["kept cells:<br/>only these are counted"]:::comb
    L1 -- no --> G1
    DR --> G1
    DN --> G1
    G1 --> G2["% responders per drug<br/>combinations (Venn)<br/>ΔF/F0 = ΔF / Bavg<br/>ΔF / ΔF(QC peak)<br/>+ cell area / diameter"]:::comb
    G2 --> G3["multidrug_results.xlsx + csv/"]:::comb
    classDef drug fill:#dbe8fb,stroke:#2a78d6,color:#111
    classDef qc fill:#fde3da,stroke:#eb6834,color:#111
    classDef comb fill:#dff3e6,stroke:#1a7f3c,color:#111
```

Without a QC drug the red part is skipped. The two extra rules (minimum ΔF/F0 of the QC response, late
response) can each be switched off with 0.

---

## Step 0 — Installation

Once per computer.

1. **ImageJ:** <https://imagej.net/ij/download.html> → download for your system → unzip → start ImageJ.
   Only if you need drift correction (Step 2e): also install the **StackReg** and **TurboReg** plugins from
   <https://bigwww.epfl.ch/thevenaz/stackreg/> (copy them into ImageJ's `plugins` folder, restart ImageJ).
2. **Miniforge** (Python): <https://github.com/conda-forge/miniforge> → installer for your system.
   Windows: afterwards use **Miniforge Prompt** from the Start menu as the terminal.
3. **This repository:** on GitHub **Code → Download ZIP**, unzip; or `git clone https://github.com/yashadarsh1608/calcium-imaging.git`.
4. **Python environment** (5–15 min), in the terminal inside the repository folder:
   ```bash
   conda env create -f environment.yml
   conda activate cellpose
   python -c "import cellpose, pandas, matplotlib, openpyxl, roifile; print('all good')"
   ```
   Already have a `cellpose` environment? `conda activate cellpose`, then
   `pip install -r requirements.txt` and `pip install "cellpose[gui]==4.2.1.1"`.
   Segmenting only in Google Colab? `pip install -r requirements.txt` is enough.
5. **Every new terminal:** `conda activate cellpose` first.

Optional GPU check: `python -c "import torch; print('GPU' if torch.cuda.is_available() else 'CPU only')"`.
Cellpose also runs on the CPU (minutes per image). The first run downloads the model (~1 GB).

---

## Step 1 — Record

**Rules**

- **Same field and same settings** (objective, exposure, binning, light) for every movie; do not move the stage.
- **Brightfield image** of the same field before the first drug, same camera settings.
- **Baseline:** at least **8 frames** before the drug reaches the cells (add it after frame 8–10).
- **One movie per drug** (e.g. 50 frames at 1 s). Washes between drugs need not be imaged.
- **Quality-control (QC) drug last**, as its own movie: **KCl** for excitable cells (neurons), **ionomycin**
  for non-excitable cells (e.g. HEK cells barely respond to KCl).
- **Triggered illumination** on (light only while the camera takes a frame) to reduce bleaching.
- **Add solutions gently**, away from the field, and do not touch the plate or stage (frame shift, Step 2).

**Write down** (the analysis asks for it): drug order, names, concentrations; frame at which each drug was
added; frames per movie and frame interval; washing time between movies; objective, camera, binning; pixel
size in µm (Micro-Manager: Devices → Pixel Size Calibration, or camera pixel size ÷ objective × binning,
e.g. 6.5 µm / 20 = 0.325 µm). The pixel size stored in the file can be wrong.

**Files:** one folder per experiment, simple names, never overwrite the raw movies:

```
2026-10-27_exp1/
├── brightfield.tif
├── drug1.tif   drug2.tif   drug3.tif
└── kcl.tif
```

---

## Step 2 — Check the movies and frame shift (ImageJ)

**2a · Frames and peaks.** Open each movie: the title shows e.g. `1/50; 3200x2200 pixels`. Draw a large
rectangle over many cells → **Image → Stacks → Plot Z-axis Profile**. Note the frame where the signal
**rises** and where it is **highest** → the **peak window** for Step 7 (e.g. peak at 18 → `15-21`).
A drug with no rise is fine (see Step 7).

**2b · Frame shift inside a movie.** Cells that do not move can still shift in the image (stage or plate
moves when solutions are added, thermal drift, focus drift).
1. Frame 1 → **Image → Duplicate…** (untick *Duplicate stack*) → `first`; last frame → `last`.
2. **Image → Color → Merge Channels…**: C1 red = `first`, C2 green = `last` → OK.
3. Zoom on cell edges: **yellow = no shift**; red on one side and green on the other = shift.

**2c · Frame shift between movies.** The same merge with the last frame of one movie and the first frame of
the next, and with the brightfield image against frame 1 of the first movie.

**2d · Decide.**

| What you see | Do |
|---|---|
| no shift or under 1–2 pixels | continue |
| a few pixels (under ~1/10 of a cell) | continue, note it |
| larger, or a jump at one frame | correct it (2e) |
| cells get blurry (focus drift) | cannot be corrected; note it, consider dropping that movie |

**2e · Correct a shift.** **Image → Stacks → Tools → Concatenate** (all movies in order) → **Plugins →
StackReg** (transformation *Translation*) → split back with **Image → Stacks → Tools →
Make Substack…** → save as `drug1_reg.tif`, … and use these. If the brightfield no longer matches, segment an
Average Intensity projection of the corrected stack instead.

---

## Step 3 — Outline the cells (Cellpose)

Segment **once**; the same ROIs are used for every movie. If `brightfield.tif` has several frames, make one
image first: **Image → Stacks → Z Project… → Average Intensity** → save as TIFF.

### Option A — Google Colab (free GPU, nothing to install)

1. Upload `brightfield.tif` to Google Drive, e.g. folder `cellpose`.
2. <https://colab.research.google.com> → **File → Open notebook → GitHub** → `yashadarsh1608/calcium-imaging`
   → `notebooks/cellpose_colab.ipynb`.
3. **Runtime → Change runtime type → T4 GPU.**
4. **Cell 1** connect Drive · **Cell 2** install (1–2 min) · **Cell 3** set
   `IMAGE_PATH = "/content/drive/MyDrive/cellpose/brightfield.tif"` and run · **Cell 4** save and download.
5. Cell 3 prints `Image used: … pixels` (must equal the movie size), `Cells found`, `Median diameter`, and
   shows the outlines in yellow.

### Option B — your computer

```bash
conda activate cellpose
cd /path/to/experiment
python /path/to/calcium-imaging/scripts/segment_cells.py
```

It asks for the image and the settings below. Output next to the image: `brightfield_rois.zip`,
`brightfield_outlines.png` (open it to check), `brightfield_masks.tif`, `brightfield_segmentation.json`.
The Cellpose window (`python -m cellpose`) also works: load the image, run, then **File → Save outlines as
.zip archive of ROI files for ImageJ**; its defaults can differ slightly.

### Settings (Colab and computer)

| Setting | Default | Change when |
|---|---|---|
| `DIAMETER` | `0` = no resizing | cells split or merged → the cell diameter in pixels (e.g. the printed median) |
| `CELLPROB_THRESHOLD` | `0` | cells missed → `-1`; debris outlined → `1` |
| `FLOW_THRESHOLD` | `0.4` | irregular cells missed → `0.6` |
| `FLATTEN_ILLUMINATION` | `False` | one side of the image darker → `True` |

Note the settings and the cell count (also in `_segmentation.json`).

**Same ROIs from Colab and computer?** Segment the same image with the same settings both ways, then
`python scripts/compare_rois.py` with the two zips: it reports cells in each, matched cells, overlap (IoU,
1.0 = identical) and whether the numbering is the same.

---

## Step 4 — ROIs and background boxes (ImageJ)

**Never save the movies.** "Apply LUT?" → **Cancel**; "Save changes?" → **No**.

**4a · Load the outlines.** Open the first movie → **Analyze → Tools → ROI Manager** (delete old ROIs) →
**More » → Open…** `brightfield_rois.zip` (count = Cellpose count) → **Image → Adjust → Brightness/Contrast →
Auto** (not *Apply*) → tick **Show All** (untick *Labels* if needed) → zoom with **+**. Check corners and
middle in frame 1 and the last frame.

**4b · Correct outlines** (before adding the boxes).

| Problem | In the ROI Manager |
|---|---|
| outline on debris / empty spot / cut cell | select it → **Delete** (several: Ctrl + click, then Delete) |
| cell missed | Freehand / Oval / Wand tool → draw just inside the cell → **T** |
| two cells in one outline | Delete, draw each cell, **T** for each |
| one cell in two outlines | Ctrl + click both → **More » → OR (Combine)** → **Add** → delete the two old ones |
| shape slightly off | select, adjust, **Update** |

Save as `brightfield_rois_edited.zip` (keep the original). Numbers after a deleted cell move up by one;
that is fine as long as every movie uses the same zip. Note deleted/added cells in the notebook.

**4c · Three background boxes.**
1. **Rectangle** tool → small box in an area with **no cell, no debris, not touching an outline** → **T**.
   Three times, in different parts of the image. They must be the **last 3 ROIs**.
2. Each box → **Image → Stacks → Plot Z-axis Profile**: must be **flat**.
3. Open every other movie (also the QC movie), click it, toggle **Show All**: check the outlines and the
   3 box profiles there too. A box that rises → delete, redraw elsewhere, **T**, check again.
4. **Deselect** → **More » → Save…** → `ROIs_with_bg.zip`.

Boxes already added but cells need changes? Ctrl + click the 3 boxes → **More » → Save…** `bg_boxes.zip`
→ delete the boxes → edit cells → **More » → Open…** `bg_boxes.zip` (added at the end again).

---

## Step 5 — Measure every movie (ImageJ)

1. **Analyze → Set Measurements…** → **Mean gray value**, decimal places **3** → OK.
2. Click the movie window (it must be the active one).
3. ROI Manager → **Deselect** → **More » → Multi Measure** → tick **Measure all slices** and **One row per
   slice** → OK.
4. Results: **one row per frame**, one *Mean* column per ROI (`Mean(1)` …), no empty cells.
5. Results → **File → Save As…** → `drug1.csv`. Close the Results.
6. Repeat 2–5 for every movie: `drug2.csv`, `drug3.csv`, `kcl.csv`.

---

## Step 6 — Cell size (optional, ImageJ)

Once; all movies share the ROIs.

1. One movie (or the brightfield) open with `ROIs_with_bg.zip` loaded.
2. **Image → Properties…**: if the unit is *pixel* or the value looks wrong (e.g. `0.0000023 µm`) →
   **Analyze → Set Scale… → Click to Remove Scale** (the script converts with the real pixel size).
3. **Analyze → Set Measurements…** → **Area**, **Perimeter**, **Shape descriptors**, **Feret's diameter**.
4. ROI Manager → **Deselect** → **Measure** (not Multi Measure) → one row per ROI.
5. Results → **File → Save As…** → `cell_size.csv` (same folder as the other CSV files).

---

## Step 7 — Analysis (Python)

Two ways with the same result: **A · the window** (buttons, the traces are shown while you set the
windows) or **B · the command line** (questions in the terminal).

### A · The window (`calcium_gui.py`)

```bash
conda activate cellpose
cd /path/to/calcium-imaging
git pull                          # newest version (the window also checks when it starts)
python scripts/calcium_gui.py
```

1. **Get the CSV files into the window**, in one of three ways:
   - **Open folder…** (Ctrl+O): choose the *folder* with `drug1.csv` … `kcl.csv` (+ `cell_size.csv`).
     Every recording in it becomes a row of the table.
   - **Add CSV files…** (Ctrl+Shift+O): choose the *files* themselves (hold Ctrl to select several).
     Use this if the folder also contains other tables, or if the files are in different folders.
   - **Drag** the folder or the files from the file manager into the window.

   A file with `kcl`, `iono` or `qc` in its name gets the role **QC**; a table with an *Area* column is
   taken as the cell size file. A file that is not a table from ImageJ is not added, and a message says
   which columns it has. The results are saved next to the first files (`multidrug_results/`).
2. **The table** (double-click a cell to type):

   | Column | What to enter |
   |---|---|
   | CSV file | the file of that recording |
   | Name | the drug name (used in every table and graph) |
   | Role | **Drug** or **QC** (only one QC; none = every cell is analysed) |
   | Baseline | first-last frame before the drug arrives, e.g. `1-8` |
   | Peak | first-last frame of the response, e.g. `15-25`; **must be typed** |
   | SD | threshold, `5` = mean baseline + 5 × SD |
   | Drug at | frame at which the drug was added (empty = end of the baseline); used for the late-response rule |
   | Wash (s) | washing time after this recording, before the next one |

   **↑ / ↓** put the rows in the order of the experiment; **+ Add row / Remove** add or remove a row.
   Hold the mouse over a column title to read what it means. The line under the table says which drug is
   the quality control; it turns orange if none is chosen.
3. **Overview tab:** one panel per recording with the median cell (dark line), the middle 50 % of the
   cells (band) and the top 10 % (dotted, shows a response of few cells). The baseline is shaded grey and
   the peak window orange, and the title says at which frame the signal is highest. It redraws while you
   type, so set the windows by looking at it.
4. **Measurement:** number of background boxes (last ROIs), boxes to use (`all`, or e.g. `98, 99` if the
   messages warn about a box), time between frames, cell size file, pixel size in µm (0 = file already in µm).
   **Quality control:** the two extra rules: remove cells that respond later than 40 s after the drug, and
   remove cells whose QC ΔF/F0 is below 0.0001 (0 = rule off).
5. **Run analysis** (Ctrl+R). A wrong or missing entry is explained in a message. If no recording has the
   role QC, the window asks whether to run without quality control. Afterwards:
   - **Summary** tab: cells kept by the QC, responders per drug, combinations, cell size
   - graph tabs **1–5** (Step 8)
   - **Messages** at the bottom right: all warnings (table under *B* below)
   - files: `multidrug_results/` with the Excel file, `csv/`, `graphs/`, `settings.json`
6. **Under the graphs:** `F − F0` or `ΔF/F0` for graphs 1 and 2 (redrawn at once); **Save graphs** as
   png, pdf or svg; **Open results folder**.
7. Your entries are saved in the folder (`calcium_gui_session.json`) and come back when you open it again.
   **File → Open results file…** shows the graphs of an earlier analysis without running it again.

Missing PyQt6 (`No module named PyQt6`)? `pip install PyQt6`. The window does not open on Linux
(`xcb` error)? `sudo apt install libxcb-cursor0`.

### B · The command line (`calcium_multidrug.py`)

Folder with `drug1.csv` … `kcl.csv` (+ `cell_size.csv`), terminal in that folder:

```bash
conda activate cellpose
python /path/to/calcium-imaging/scripts/calcium_multidrug.py --overview
python /path/to/calcium-imaging/scripts/calcium_multidrug.py
```

(or copy the script into the folder and run `python calcium_multidrug.py`). `--overview` prints, per movie,
where the median cell rises and peaks.

**The questions.** `[value]` = suggestion, ENTER accepts; `(required)` = must be typed; wrong input is
explained and asked again.

| Question | Example |
|---|---|
| Number of drugs (NOT counting the quality-control recording) | `3` |
| Drug 1: CSV file · Drug 1: name (… every drug, in order) | `drug1.csv` · `Capsaicin` |
| Quality-control recording CSV (e.g. KCl or ionomycin), or 'none' | `kcl.csv` |
| Quality-control drug name | `KCl` |
| Number of background ROIs (last columns) | `3` |
| Background boxes to use ('all' or e.g. Mean98) | `all` (or the clean boxes it suggests) |
| Seconds between frames | `1` |
| Washing time between Capsaicin and TSLP (s) (every gap) | `60` |
| …: baseline frames (first-last) (every movie) | `1-8` |
| …: peak frames (first-last) (every movie, required) | `15-25` |
| …: threshold (number of SD) | `5` |
| …: frame at which the drug was added (every movie) | `10` (suggestion: end of the baseline) |
| Remove cells whose response starts later than this many seconds after the drug (0 = off) | `40` |
| Remove cells whose peak ΔF/F0 for KCl is below (0 = off) | `0.0001` |
| Cell size file (ImageJ Measure of the ROIs), or 'none' | `cell_size.csv` |
| Pixel size in µm if that file is in pixels (0 = already in µm) | `0.325` |

**Peak window for a drug with no response:** choose it from when the drug was added (e.g. added at frame
10 → `12-25`) or copy the window of a drug that worked. Its cells stay below the threshold and are counted
as non-responders — the correct result. Choose the window before looking at the results.

**Warnings it can print**

| Message | Meaning / do |
|---|---|
| `background Mean(99): changes by …` | box not empty → use the suggested boxes or redraw |
| `cells already rise in frames 9-10 of the baseline` | end the baseline earlier |
| `… cell(s) not brighter than background at rest` | no ΔF/F0 for them; many → check boxes and ROIs |
| `… cell(s) have EMPTY values in a CSV` | ROI without data → *excluded (missing data)*; check in ImageJ |
| `diameters look like PIXELS` | give the pixel size in µm |

**Output** `multidrug_results/multidrug_results.xlsx` (+ the same tables in `csv/`):

| Sheet | Content |
|---|---|
| Summary | per drug: cells analysed, responders, %, mean peak ΔF, ΔF/F0, ΔF/ΔF(QC) ± SEM/SD |
| Responders | per cell: kept/excluded (reason), yes/no per drug, "responds to", number of drugs |
| Combinations | cells per combination of drugs |
| QC, Excluded_cells | cells kept and cells removed by each rule; the excluded cells with all numbers |
| Per_cell | all numbers per cell (status, size, Bavg, SD, threshold, peaks, ΔF/F0, when the response starts, normalised, 1/0) |
| Cell_size | area (µm²), equivalent diameter, Feret max/min, perimeter, circularity |
| Mean_traces | mean/SD/SEM per frame (all, responders, non-responders), recording and experiment time |
| Cell_traces_dF / _dF_F0 / _norm | every kept cell, every frame |
| QC_…_dF_all_cells | QC trace of every cell incl. excluded |
| Settings, Raw_… | your answers; raw values and background of every movie |

---

## Step 8 — Graphs (Python)

**In the window** the graphs are the tabs 1–5; they are saved automatically after the analysis and again
with **Save graphs**. **On the command line**, in the folder that contains `multidrug_results/`:

```bash
python /path/to/calcium-imaging/scripts/make_graphs.py
```

Questions: results file (ENTER), `dF` or `dF_F0`, file format `png`/`pdf`/`svg`. Saved in
`multidrug_results/graphs/`.

**Every graph uses only the cells kept after the quality-control drug.**

| File | Shows |
|---|---|
| `1_traces_cells` | F − F0 over time of every recording incl. the QC drug: every cell one line (no mean), `//` + washing time |
| `2_drug_and_QC` | one row per drug, **only the cells that responded to that drug** (all of them passed the quality control). Left: their response to the drug. Right: the response of exactly the same cells to the QC drug. Example: 20 of 83 kept cells respond to drug 1 → both panels of row 1 show these 20 cells; 45 respond to drug 2 → row 2 shows these 45. Every cell grey, mean black |
| `3_pies_and_venn` | black and grey: one pie per drug (responders black, non-responders grey) + Venn diagram (one line style per drug). **2–3 drugs:** the area of each circle is proportional to its number of responders, the overlaps to the shared responders. **4 or more drugs:** a bar chart with one bar per combination of drugs (a Venn diagram of so many drugs is hard to read) |
| `4_area_scatter` | area of every kept cell per drug in a bar outline: black = responder, grey = non-responder |
| `5_area_responders_box` | box-and-whisker of the area of the responders only |

Graphs 4 and 5 need the cell size (Step 6). `STEP` at the top of `make_graphs.py` sets the distance between
drugs. With three circles not every overlap can be drawn exactly to scale; an overlap that cannot be drawn is
written under the diagram, and the numbers in the diagram are always the real counts.

---

## Script reference

Written in the style of a function documentation: what each script does, what it needs, what it gives.

### `calcium_multidrug.py` — the analysis

**Description:** takes one ImageJ CSV per drug movie (+ optionally a QC movie and a cell size file) and gives,
for every cell, responder yes/no per drug (threshold mean + N × SD), the QC decision, all values and traces
(flowchart above). Asks every setting interactively; `--overview` only prints where each movie rises and peaks.

| Function | What it does |
|---|---|
| `read_imagej_csv()` | reads an ImageJ Results table (CSV, or tab-separated `.xls`/`.txt`), keeps the *Mean* columns, frame 1 = row 1 |
| `background_subtract()` | X = cell − mean of the chosen background boxes, frame by frame |
| `check_background()` | warns about boxes that are brighter than the cells or change during the movie |
| `baseline_check()` | warns if the cells already rise at the end of the baseline |
| `analyse_recording()` | Bavg, ΔF, SD, threshold, mean peak, responder, ΔF/F0 for one movie |
| `response_start()` | the frame at which each cell's response starts (first of 3 frames in a row above its threshold) |
| `read_size_file()` | reads ImageJ *Measure* (Area, Feret, …), converts pixels to µm |
| `run()` | QC filter, normalisation to the QC peak, combinations, experiment time, writes Excel + CSV |
| `overview()` | the `--overview` mode |
| `main()` | asks the questions |

**Inputs:** `drug1.csv` … (rows = frames; columns = `Mean(1)` … one per ROI, background boxes last),
optional QC CSV, optional `cell_size.csv`. **Outputs:** `multidrug_results/` (Excel, `csv/`, `settings.json`, zip).

### `calcium_gui.py` — the window

**Description:** a PyQt6 window for Steps 7 and 8. It only collects the inputs and shows the results; the
calculation is done by `calcium_multidrug.run()` and the graphs by `make_graphs`, so window and command line
give identical tables.

| Part | What it does |
|---|---|
| `classify()`, `scan_folder()` | recognise a recording (several *Mean* columns) and the size file (*Area* column) |
| `Window.choose_folder()`, `add_files()`, `take_files()` | open a folder, add single files, files dragged into the window |
| `Window.collect()` | reads and checks the table and the settings; explains what is wrong |
| `Window.refresh_overview()` | draws the Overview and runs the background-box and baseline checks |
| `Window.run_analysis()` | runs the analysis, writes `settings.json`, loads the results, saves the graphs |
| `Window.draw_graphs()` / `save_graphs()` | shows / saves the five graphs |
| `Window.git_pull()` | `git pull` when the window starts (Help → Update now) |

### `make_graphs.py` — the graphs

**Description:** reads `multidrug_results.xlsx` and draws the five graphs of Step 8; nothing is recalculated.

| Function | Graph |
|---|---|
| `load()` | reads Summary, Responders, Combinations, Per_cell and the cell traces |
| `fig_cells()` | `1_traces_cells`: every kept cell, every recording, // = washing |
| `fig_drug_qc()` | `2_drug_and_QC`: the responders of each drug, next to the same cells in the QC recording; cells grey, mean black |
| `venn_layout()`, `fig_pies_venn()` | `3_pies_and_venn`: pie per drug + Venn to scale (2–3 drugs) or combination bars (4 or more drugs) |
| `fig_area_scatter()` | `4_area_scatter`: area of every cell, black = responder, grey = non-responder |
| `fig_area_box()` | `5_area_responders_box`: box-and-whisker of the responders' area |
| `save_all()` | saves all graphs (used by the window and the command line) |

### `segment_cells.py` and `notebooks/cellpose_colab.ipynb` — the outlines

**Description:** the same Cellpose-SAM code (version 4.2.1.1) in the terminal and in Colab.

| Function | What it does |
|---|---|
| `load_image()` | reads the image; RGB → grey, several frames → average |
| `segment()` | runs Cellpose-SAM with diameter, cellprob and flow threshold (optional illumination flattening) |
| `save_outputs()` | writes `_rois.zip`, `_outlines.png`, `_masks.tif`, `_segmentation.json` |

### `compare_rois.py` — same outlines?

**Description:** compares two ROI zips (e.g. Colab vs computer): pairs every cell with the most overlapping
cell of the other set (IoU ≥ 0.5 = same cell) and reports matched cells, cells only in one set, mean IoU and
whether the numbering is the same; writes `A_vs_B.csv`.

---
## Method

The method follows `Normalization_ionomycin.R` from
[Calcium-Imaging-Analysis-with-R](https://github.com/amapruns/Calcium-Imaging-Analysis-with-R/blob/master/Normalization_ionomycin.R),
reimplemented and extended in Python.

Per cell, per movie (each movie has its own baseline):

1. **X** = mean gray value of the cell − mean of the background boxes (each frame)
2. **Bavg** = mean X over the baseline frames
3. **ΔF = F − F0** = X − Bavg
4. **SD** = standard deviation of ΔF over the baseline (sample SD, like Excel STDEV.S)
5. **Responder** if mean ΔF in the peak window > mean baseline ΔF + 5 × SD
6. **ΔF/F0** = ΔF / Bavg (only cells brighter than background at rest)
7. **Quality control:** a cell is **kept** only if it passes every rule; otherwise it is **excluded** with the
   reason, and nothing of it is counted.
   - **QC drug:** the cell responds to the quality-control drug (e.g. KCl), by the rule of point 5.
   - **Minimum QC response:** its mean peak ΔF/F0 for the QC drug is at least 0.0001. This also removes cells
     that are not brighter than the background at rest (ΔF/F0 cannot be calculated or is negative).
   - **Late response:** in no drug recording does its response start later than 40 s after the drug was
     added. The response *starts* at the first frame after the drug from which ΔF stays above the cell's
     threshold for 3 frames in a row (single noisy frames do not count). A response that starts in time and
     lasts longer than 40 s is fine. A recording that ends sooner than 40 s after the drug cannot have a
     late response.

   Both numbers can be changed, and 0 switches a rule off.
   **ΔF/ΔF(QC)** = ΔF / the cell's own mean ΔF in the QC peak window (KCl is not a true maximum; values > 1
   are possible).
8. **Averages:** over cells; SEM = SD / √n. Percentages are of the kept cells.
9. **Cell size:** area; equivalent diameter = 2·√(area/π); Feret = longest/shortest width.
10. **Experiment time:** each movie starts after the earlier movies plus the washing times in between.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `conda: command not found` | install Miniforge; Windows: use *Miniforge Prompt* |
| `No module named 'pandas'` (or cellpose, openpyxl, roifile) | `conda activate cellpose` or `pip install -r requirements.txt` |
| window: `No module named PyQt6` | `pip install PyQt6` (in the `cellpose` environment) |
| window does not open, `Could not load the Qt platform plugin "xcb"` | `sudo apt install libxcb-cursor0`; on Wayland start with `QT_QPA_PLATFORM=xcb python scripts/calcium_gui.py` |
| window: a recording is missing in the table | its CSV needs several *Mean* columns (ImageJ Multi Measure); **+ Add** adds a row |
| window: "Update (git pull): could not check" | no internet, or the folder was downloaded as ZIP; the window works anyway |
| `KeyboardInterrupt` | Ctrl+C was pressed while the script waited; run again and press ENTER |
| Cellpose `URLError` on the first run | no internet for the model download; or use Colab |
| `Image used` size differs from the movies | brightfield with other binning/crop; retake or segment an average of the movie |
| outlines shifted / all cells jump at one frame | frame shift → Step 2 |
| dip in all cells after a drug | a background box catches signal → use clean boxes |
| `different ROI columns than …` | measure every movie with the same `ROIs_with_bg.zip` |
| many `excluded (late response …)` | check *Drug at* (frame of the addition); slow drift upwards or spontaneous activity also counts as a late start; 0 switches the rule off |
| many `excluded (no KCl response)` | check the QC peak window and the `QC_…` sheet; non-excitable cells → ionomycin |
| `no 'Area' column` | Set Measurements → Area; ROI Manager → **Measure** |
| diameters ~100 or more | give the real µm per pixel |
| Excel shows wrong numbers in a CSV | open `multidrug_results.xlsx` instead (same tables); a German Excel reads `1.5` in a CSV wrongly |
| the window shows no CSV files / "No recordings found" | use **Add CSV files…** and choose the files, or drag them into the window; a recording must be the Multi Measure table with columns `Mean1`, `Mean2` … |
| graph 3 shows bars instead of a Venn diagram | this is the rule for 4 or more drugs. If you have only 3 drugs, the QC drug is listed as a drug: set its **Role** to **QC** |
| a drug shows no peak | choose its window from when it was added; all its cells are non-responders |