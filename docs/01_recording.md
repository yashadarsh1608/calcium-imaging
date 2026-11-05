# 1 · Record

The analysis assumes: **one field of view, one movie per drug, a clean baseline at the start of every
movie, and the quality-control drug last.**

## Rules

- **Same field and same settings** for every movie: objective, exposure, binning, light. Do not move
  the stage between recordings.
- **Brightfield image** of the same field before the first drug. Cellpose segments this image; it shows
  every cell, also cells that stay dark in fluorescence.
- **Baseline:** at least **8 frames** before the drug reaches the cells. Add the drug after frame
  8–10, never at frame 1.
- **One movie per drug** (e.g. 50 frames at 1 s). Washes between drugs need not be imaged.
- **Quality-control drug last**, as its own movie: **KCl** for excitable cells (neurons; opens
  voltage-gated calcium channels), **ionomycin** for non-excitable cells (e.g. HEK cells barely respond
  to KCl).
- **Triggered illumination** on: the light is on only while the camera takes a frame, which reduces
  bleaching and phototoxicity.
- **Add solutions gently**, away from the imaged field, and do not touch the plate or the stage. This
  is the main cause of frame shifts ([02_check_recordings.md](02_check_recordings.md)).

## Write down for every experiment

The analysis script asks for these, and they belong in the lab notebook.

| Item | Example |
|---|---|
| Drug order, names, concentrations | capsaicin 1 µM → TSLP 100 nM → histamine 100 µM → KCl 50 mM |
| Frame at which each drug was added | 10, 10, 10, 10 |
| Frames per movie, frame interval | 50 frames, 1 s |
| Washing time between movies | 60 s, 120 s, 90 s |
| Objective, camera, binning | 20×, camera model, 1×1 |
| Pixel size (µm per pixel) | from Micro-Manager: Devices → Pixel Size Calibration |

**Pixel size:** camera pixel size ÷ objective magnification × binning (e.g. 6.5 µm / 20 × 1 =
0.325 µm per pixel). The value stored in the image file can be wrong, so check it.

## File names

Keep one folder per experiment and simple names, e.g.

```
2026-10-27_mDRG_exp1/
├── brightfield.tif
├── drug1.tif      (or capsaicin.tif)
├── drug2.tif
├── drug3.tif
└── kcl.tif
```

Never overwrite the raw movies.
