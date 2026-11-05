# 0 · Installation

You need three programs. Install them once.

| Program | For | Where |
|---|---|---|
| **Fiji** (ImageJ) | checking movies, ROIs, measuring | <https://fiji.sc> → Download for your system, unzip, start the Fiji program inside the folder |
| **Miniforge** (conda) | Python + Cellpose on your computer | <https://github.com/conda-forge/miniforge> → installer for your system |
| **A Google account** | only if you segment in Google Colab | <https://colab.research.google.com> |

You do **not** need Cellpose on your computer if you segment in Google Colab
([03a_cellpose_colab.md](03a_cellpose_colab.md)); then the analysis needs only the small
`requirements.txt` (Option B).

## Option A — one environment for everything (recommended)

Linux / macOS: open a terminal. Windows: open **Miniforge Prompt** from the Start menu.

```bash
git clone https://github.com/<your-user-name>/calcium-imaging-pipeline.git
cd calcium-imaging-pipeline
conda env create -f environment.yml        # 5-15 min, downloads Cellpose and PyTorch
conda activate cellpose
```

No `git`? On the GitHub page click **Code → Download ZIP**, unzip it, and `cd` into the folder.

Check that it works:

```bash
python -c "import cellpose, pandas, matplotlib, openpyxl, roifile; print('all good')"
```

Every time you open a new terminal, activate the environment first:

```bash
conda activate cellpose
```

## Option B — analysis and graphs only (Cellpose in Colab)

```bash
conda create -n calcium python=3.11 -y
conda activate calcium
pip install -r requirements.txt
```

## Option C — you already have a `cellpose` environment

```bash
conda activate cellpose
pip install -r requirements.txt
pip install "cellpose[gui]==4.2.1.1"       # same version as the Colab notebook
```

The Cellpose version matters: Colab and your computer give the same ROIs only with the same version.
Check with `python -c "from importlib.metadata import version; print(version('cellpose'))"`.

## GPU (optional)

Cellpose runs on the CPU, only slower (a few minutes for one large image). With an NVIDIA graphics
card it uses the GPU automatically. Check with:

```bash
python -c "import torch; print('GPU' if torch.cuda.is_available() else 'CPU only')"
```

The first Cellpose run downloads the Cellpose-SAM model (about 1 GB) from the internet; later runs
use the saved copy.
