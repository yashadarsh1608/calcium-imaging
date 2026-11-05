# 2 · Check the recordings and frame shift (Fiji)

Check every movie **before** segmentation: how many frames, when the response rises and peaks, and
whether the image shifted. A shift moves cells out of their ROIs and creates false rises or dips.

## 2a · Frames and timing

1. Open a movie (drag it onto Fiji). The window title shows e.g. `1/50; 3200x2200 pixels`.
2. Draw a large rectangle over many cells → **Image → Stacks → Plot Z-axis Profile**.
3. Note the frame where the signal **starts to rise** and the frames where it is **highest**.
   These give the **peak window** the analysis asks for (e.g. rise at 12, peak 17–20 → window 15–21).
4. Repeat for every movie. A drug with no visible rise is fine: choose its window from when you added
   the drug (see [05_python_analysis.md](05_python_analysis.md)).

## 2b · Frame shift inside one movie

Cells that do not move can still shift in the image: the stage or plate moves slightly when solutions
are added, slow thermal drift, or focus drift.

1. Go to frame 1 → **Image → Duplicate…**, untick *Duplicate stack*, name it `first`.
2. Go to the last frame → duplicate it the same way as `last`.
3. **Image → Color → Merge Channels…**: C1 (red) = `first`, C2 (green) = `last` → OK.
4. Zoom in on cell edges. **Yellow = same position.** Red on one side and green on the other = shift.

## 2c · Frame shift between movies

Do the same merge with the **last frame of drug 1** and the **first frame of drug 2**, and so on, and
with the **brightfield image** against the first frame of drug 1 (the cell outlines must match).

## 2d · Decide

| What you see | Do |
|---|---|
| no shift, or under 1–2 pixels | continue |
| small but clear (a few pixels, under ~1/10 of a cell diameter) | continue, note it; look at edge cells later |
| larger, or a sudden jump at one frame | correct it (2e) before segmentation |
| cells get blurry (focus drift) | cannot be corrected; note it, consider dropping that movie |

## 2e · Correct a shift (translation only)

1. **Image → Stacks → Tools → Concatenate…**: all movies in order → one stack.
2. **Plugins → Registration → Correct 3D Drift** (or StackReg with *Translation*).
3. Split it back: **Image → Stacks → Tools → Make Substack…** (frames 1-50, 51-100, …) and save as
   `drug1_reg.tif`, … Use the `_reg` files from now on.
4. If the brightfield no longer matches, segment an **Average Intensity** projection of the corrected
   stack instead (**Image → Stacks → Z Project… → Average Intensity**).

**Signs of a shift later in the data:** all cells jump at the same frame, a background box suddenly
changes, cells at the edge of their ROI show opposite changes.
