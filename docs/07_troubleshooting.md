# Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `conda: command not found` | Miniforge not installed or terminal not restarted | install Miniforge; on Windows use *Miniforge Prompt* |
| `ModuleNotFoundError: No module named 'pandas'` (or cellpose, openpyxl, roifile) | wrong environment active | `conda activate cellpose`, or `pip install -r requirements.txt` |
| `KeyboardInterrupt` | Ctrl+C was pressed while the script waited for an answer | run again; it waits for you to type or press ENTER |
| `IsADirectoryError` in make_graphs | a folder was typed instead of the .xlsx | press ENTER at the question (or update the script) |
| Cellpose: `URLError` on the first run | the model (~1 GB) cannot be downloaded | check the internet connection / proxy; or use Colab |
| Cellpose very slow | running on the CPU | normal (minutes); or use Colab with a T4 GPU |
| `Image used: … pixels` differs from the movie size | brightfield taken with another binning / crop | take the brightfield with the same settings, or segment an average of the movie |
| Outlines shifted on one movie | frame shift between movies | [02_check_recordings.md](02_check_recordings.md) 2c–2e |
| All cells jump up or down at one frame | stage bump / frame shift | correct the drift (2e) |
| Dip in all cells right after a drug | a background box catches signal | use the boxes the script suggests, or redraw them |
| `the cells already rise in frames … of the baseline` | drug arrived during the baseline | end the baseline earlier (e.g. `1-6`) |
| `different ROI columns than …` | a movie was measured with another ROI set | Multi Measure every movie with the same `ROIs_with_bg.zip` |
| Cell `excluded (missing data)` | empty values in a CSV: ROI outside the image or deleted before measuring | check that ROI in Fiji, Multi Measure again |
| Many cells `excluded (no KCl response)` | wrong QC peak window, or the cells do not respond to KCl | check the `QC_…_dF_all_cells` sheet; non-excitable cells → use ionomycin |
| Many `not brighter than background at rest` | a background box is bright, or ROIs on debris | check the boxes in the `Raw_…` sheets and those ROIs |
| `no 'Area' column` | Area not ticked, or the file came from Multi Measure | Set Measurements → Area; ROI Manager → **Measure** → save |
| Diameters ~100 or more | size file in pixels | type the real µm per pixel when asked |
| Excel shows wrong numbers in a CSV | German decimal comma | answer `de` to the CSV style, or open the .xlsx |
| Graphs 5/6 skipped | analysis ran without the cell size file | run the analysis again with `cell_size.csv` |
| A drug shows no peak | the drug did not act | fine: choose the window from when you added it; all cells are non-responders |
