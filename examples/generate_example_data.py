"""
generate_example_data.py - makes SYNTHETIC (made-up) example data to try the pipeline.

It writes ImageJ-style CSV files into examples/data/: three drug recordings, one KCl
quality-control recording (97 cells + 3 background boxes, 50 frames each) and a cell size file
in pixels. No real experiment data is included in this repository.

    python examples/generate_example_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "data"
N_CELLS, N_BG, N_FRAMES = 97, 3, 50

rng = np.random.default_rng(3)
frames = np.arange(1, N_FRAMES + 1)
rest = rng.uniform(102.5, 108, N_CELLS)                    # resting raw gray value per cell
names = [f"Mean({i + 1})" for i in range(N_CELLS + N_BG)]  # ImageJ column names


def recording(fraction, rise, peak, amp, decay, path):
    responds = rng.random(N_CELLS) < fraction
    cols = {}
    for i in range(N_CELLS):
        y = rest[i] + rng.normal(0, 0.08, N_FRAMES) - 0.002 * frames      # noise + slight bleaching
        if responds[i]:
            a = amp * rng.uniform(.5, 1.5)
            shape = np.clip((frames - rise) / (peak - rise), 0, 1)
            fall = np.where(frames > peak, np.exp(-(frames - peak) / decay) * .6 + .4, 1)
            y = y + a * shape * fall
        cols[names[i]] = y
    for k in range(N_BG):
        cols[names[N_CELLS + k]] = 100 + rng.normal(0, 0.05, N_FRAMES)   # empty background boxes
    pd.DataFrame(cols, index=frames).round(3).to_csv(path, index_label=" ")


def main():
    OUT.mkdir(exist_ok=True)
    recording(.45, 12, 20, 1.5, 8, OUT / "drug1.csv")     # e.g. capsaicin
    recording(.25, 14, 24, 0.8, 10, OUT / "drug2.csv")    # e.g. TSLP
    recording(.35, 12, 18, 1.2, 6, OUT / "drug3.csv")     # e.g. histamine
    recording(.88, 11, 17, 3.0, 10, OUT / "kcl.csv")      # quality control
    area = np.r_[rng.lognormal(np.log(1800), .35, N_CELLS), [1600] * N_BG]   # pixels
    pd.DataFrame({"Area": area.round(0), "Mean": rng.uniform(100, 110, N_CELLS + N_BG).round(3),
                  "Perim.": (2 * np.sqrt(np.pi * area) * 1.1).round(3),
                  "Circ.": rng.uniform(.7, .95, N_CELLS + N_BG).round(3),
                  "Feret": (2 * np.sqrt(area / np.pi) * 1.15).round(3),
                  "MinFeret": (2 * np.sqrt(area / np.pi) * .85).round(3)},
                 index=range(1, N_CELLS + N_BG + 1)).to_csv(OUT / "cell_size.csv", index_label=" ")
    print(f"example data written to {OUT}")


if __name__ == "__main__":
    main()
