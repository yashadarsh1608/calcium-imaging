# 6 · Python analysis — `calcium_multidrug.py`

Reads the CSV files from Fiji and writes, for every cell, whether it responded to each drug, plus all
numbers behind it. **Tables only** (Excel + CSV); graphs come from [06_graphs.md](06_graphs.md).

## Run it

```bash
conda activate cellpose                     # or the environment from 00_installation.md
cd /path/to/your/experiment                 # the folder with drug1.csv ... kcl.csv
python /path/to/calcium-imaging-pipeline/scripts/calcium_multidrug.py --overview
python /path/to/calcium-imaging-pipeline/scripts/calcium_multidrug.py
```

You can also copy `calcium_multidrug.py` into the experiment folder and run `python calcium_multidrug.py`.

- `--overview` asks only for the files and background boxes, then prints per movie where the median cell
  rises and peaks, and suggests a peak window. Use it with the Z-axis profiles from Fiji (step 2a).
- Without `--overview` the full analysis runs.

## What it asks

A value in `[brackets]` is a suggestion: **ENTER** accepts it. `(required)` = no suggestion, you must type
it. Wrong input (e.g. a missing file, `1 10` instead of `1-10`) is explained and asked again.

| Question | Example answer | Notes |
|---|---|---|
| Number of drugs (NOT counting the quality-control recording) | `3` | 1–10 drugs |
| Drug 1: CSV file | `drug1.csv` | suggested only if the file is in the folder |
| Drug 1: name | `Capsaicin` | required; used in every table |
| … the same for every drug, in the order they were given | | |
| Quality-control recording CSV (e.g. KCl or ionomycin), or 'none' | `kcl.csv` | `none` = no quality control |
| Quality-control drug name | `KCl` | any name |
| Number of background ROIs (last columns) | `3` | the boxes must be the last ROIs |
| Background boxes to use ('all' or e.g. Mean98) | `all` | the script warns about a box that is not empty and suggests the clean ones; `98`, `Mean98`, `Mean(98)` all work |
| Seconds between frames | `1` | |
| Washing time between Capsaicin and TSLP (s) | `60` | asked for **every** gap; only used for the experiment time column |
| Capsaicin: baseline frames (first-last) | `1-8` | frames before the drug arrives |
| Capsaicin: peak frames (first-last) | `15-25` | required; must start after the baseline |
| Capsaicin: threshold (number of SD) | `5` | lab rule: mean baseline + 5 SD |
| … baseline, peak, threshold for every movie, also the QC drug | | |
| Cell size file (ImageJ Measure of the ROIs), or 'none' | `cell_size.csv` | optional |
| Pixel size in µm if that file is in pixels (0 = already in µm) | `0.325` | 0 if Fiji measured in µm |
| CSV style: en = 1.5 with commas, de = 1,5 with semicolons | `de` | `de` for German Excel; the .xlsx works either way |

Everything you answered is saved in `multidrug_results/settings.json` and the *Settings* sheet.

**Choosing the peak window:** around the frames where the response is highest (step 2a). For a drug that
shows **no response**, choose the window from **when you added it** (e.g. added at frame 10 → `12-25`),
or copy the window of a drug that worked. Nothing breaks: the cells stay below the threshold and are
counted as non-responders — that is the correct result. Decide the window before you look at the results.

## The method (per cell, per movie)

1. X = cell − mean of the background boxes (each frame)
2. Bavg = mean X over the baseline frames
3. ΔF = X − Bavg
4. SD = standard deviation of ΔF over the baseline (sample SD, like Excel STDEV.S)
5. **Responder** if mean ΔF in the peak window > mean baseline + 5 × SD
6. ΔF/F0 = ΔF / Bavg
7. With a quality-control drug: only cells that respond to it are analysed (**kept**); the others are
   **excluded** and listed with the reason. ΔF/ΔF(QC) = ΔF / the cell's own mean ΔF in the QC peak window.

Details: [method.md](method.md).

## Warnings it can print

| Message | Meaning |
|---|---|
| `WARNING …, background Mean(99): changes by …` | that box is not empty; use the boxes it suggests or redraw them |
| `WARNING …: the cells already rise in frames 9-10 of the baseline` | the drug arrived during the baseline: end the baseline earlier |
| `note …: 3 cell(s) not brighter than background at rest` | those cells have no ΔF/F0 (ΔF is still used); many such cells → check the background boxes and those ROIs |
| `WARNING: … cell(s) have EMPTY values in a CSV` | an ROI has no data in a movie (outside the image, other ROI set): marked *excluded (missing data)* |
| `note: diameters look like PIXELS` | give the pixel size in µm |

## Output: `multidrug_results/`

`multidrug_results.xlsx` and the same tables as CSV files in `multidrug_results/csv/`:

| Sheet | Content |
|---|---|
| **Summary** | per drug: cells analysed, responders, % responders, mean peak ΔF, ΔF/F0, ΔF/ΔF(QC) ± SEM and SD |
| **Responders** | one row per cell: kept/excluded (with reason), **yes/no per drug**, "responds to" (e.g. *Capsaicin + Histamine*), number of drugs |
| Combinations | number of cells for every combination of drugs |
| QC, Excluded_cells | kept / excluded counts and the excluded cells with all their numbers |
| Per_cell | every number per cell: size, resting intensity, Bavg, SD, threshold, mean and max peak, ΔF/F0, normalised peak, responder 1/0 |
| Cell_size | area (µm²), equivalent diameter, Feret max/min, perimeter, circularity, … |
| Mean_traces | mean, SD, SEM per frame for all cells, responders, non-responders; *time in recording* and *experiment time* (washes included) |
| Cell_traces_dF / _dF_F0 / _norm | every kept cell, every frame, on the experiment time |
| QC_…_dF_all_cells | the QC trace of **every** cell, including excluded ones (with threshold and mean peak) |
| Settings, Raw_… | your answers; the raw values and the background of every movie |

## Try it without typing

```bash
cd examples/data
python ../../scripts/calcium_multidrug.py < ../answers_example.txt
```

`answers_example.txt` holds one answer per line in the order of the questions above; you can make one
for your own experiments too.
