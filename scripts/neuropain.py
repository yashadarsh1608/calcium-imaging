"""
calcium_gui.py - a window for the Python part of the pipeline (analysis + graphs).

Everything after ImageJ in one window, in the style of the Cellpose window:
  left   1 the data (open the folder, add the CSV files, or drag them into the window),
         2 the recordings (one CSV per drug, one of them the quality-control drug) with their
           baseline / peak windows, 3 measurement settings, 4 quality control, Run analysis, 5 graphs
  right  Overview (median trace of every recording with the baseline and peak windows drawn in),
         Summary (responders per drug), the five graphs, and the messages

HOW TO START (in the "cellpose" environment, which already has PyQt6):
    git pull                      # in the repository folder: get the newest version
    python scripts/calcium_gui.py

It uses the same code as the command line (calcium_multidrug.py and make_graphs.py), so the
results are identical. Results go to <experiment folder>/multidrug_results/.
"""

AUTO_UPDATE = True    # run "git pull" when the window starts (only if this folder is a git clone)

import contextlib
import io
import json
import re
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt
except ImportError:
    sys.exit("PyQt6 is missing. Run:  pip install PyQt6   (the 'cellpose' environment from "
             "environment.yml already has it)")

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

import calcium_multidrug as cm
import make_graphs as mg

SESSION_FILE = "calcium_gui_session.json"
EMPTY_SUMMARY = "<p style='color:#9aa0aa'>Run the analysis to see the results.</p>"
COLS = ["CSV file", "Name", "Role", "Baseline", "Peak", "SD", "Drug at", "Wash (s)"]
C_FILE, C_NAME, C_ROLE, C_BASE, C_PEAK, C_SD, C_ADD, C_WASH = range(8)
QC_HINT = re.compile(r"kcl|iono|qc", re.I)

TABLES = (".csv", ".xls", ".txt", ".tsv")       # what ImageJ saves a Results table as

C_BG, C_CARD, C_LINE, C_FIELD = "#16171a", "#1f2125", "#2d3036", "#131417"
C_TEXT, C_DIM, C_ACCENT, C_WARN = "#e8e8eb", "#9aa0aa", "#6cb6ff", "#f0a35e"

DARK = f"""
QWidget {{ background: {C_BG}; color: {C_TEXT}; font-size: 10pt; }}
QLabel {{ background: transparent; }}
QFrame#card {{ background: {C_CARD}; border: 1px solid {C_LINE}; border-radius: 10px; }}
QLabel#title {{ font-size: 15pt; font-weight: 600; }}
QLabel#subtitle {{ color: {C_DIM}; }}
QLabel#badge {{ background: {C_ACCENT}; color: #0d1117; border-radius: 11px; font-weight: 700; font-size: 9pt; }}
QLabel#step {{ font-weight: 600; font-size: 10.5pt; }}
QLabel#hint {{ color: {C_DIM}; font-size: 9pt; }}
QLabel#path {{ color: {C_TEXT}; font-weight: 600; }}
QLabel#qc {{ color: {C_TEXT}; padding: 7px 10px; background: {C_FIELD}; border: 1px solid {C_LINE}; border-radius: 6px; }}
QPushButton {{ background: #2a2d33; border: 1px solid #3b3f47; border-radius: 6px; padding: 6px 14px; }}
QPushButton:hover {{ background: #343841; border-color: #4a4f59; }}
QPushButton:pressed {{ background: #24272c; }}
QPushButton:disabled {{ color: #6b6f77; background: #22242a; border-color: {C_LINE}; }}
QPushButton#primary {{ background: #2f6fd0; border-color: #3d7fe3; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #3d7fe3; }}
QPushButton#run {{ background: #1f8f4e; border: 1px solid #27a85c; border-radius: 8px; color: white;
                  font-weight: 700; font-size: 11.5pt; padding: 11px; }}
QPushButton#run:hover {{ background: #27a85c; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {C_FIELD}; border: 1px solid #353941;
    border-radius: 5px; padding: 4px 7px; min-height: 20px; selection-background-color: #2f6fd0; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: 0; }}
QLabel#field {{ color: {C_DIM}; font-size: 9pt; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {C_ACCENT}; }}
QComboBox QAbstractItemView {{ background: {C_CARD}; border: 1px solid {C_LINE}; selection-background-color: #2f6fd0; }}
QTableWidget {{ background: {C_FIELD}; alternate-background-color: #181a1e; border: 1px solid {C_LINE};
    border-radius: 6px; gridline-color: #24272c; selection-background-color: #26456f; selection-color: {C_TEXT}; }}
QTableWidget QComboBox {{ border: 0; border-radius: 0; background: transparent; padding: 2px 5px; }}
QTableWidget QLineEdit {{ border: 1px solid {C_ACCENT}; border-radius: 0; padding: 0 3px; }}
QHeaderView::section {{ background: {C_FIELD}; color: {C_DIM}; border: 0; border-bottom: 1px solid {C_LINE};
    padding: 6px 4px; font-weight: 600; font-size: 9pt; }}
QTableCornerButton::section {{ background: {C_FIELD}; border: 0; border-bottom: 1px solid {C_LINE}; }}
QTabWidget::pane {{ border: 0; border-top: 1px solid {C_LINE}; }}
QTabBar::tab {{ background: transparent; color: {C_DIM}; padding: 9px 14px; border: 0;
    border-bottom: 2px solid transparent; font-weight: 600; }}
QTabBar::tab:hover {{ color: {C_TEXT}; }}
QTabBar::tab:selected {{ color: white; border-bottom: 2px solid {C_ACCENT}; }}
QPlainTextEdit, QTextBrowser {{ background: {C_FIELD}; border: 1px solid {C_LINE}; border-radius: 6px; padding: 6px; }}
QTextBrowser {{ background: {C_BG}; border: 0; }}
QMenuBar {{ background: {C_BG}; border-bottom: 1px solid {C_LINE}; }}
QMenu {{ background: {C_CARD}; border: 1px solid {C_LINE}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px; border-radius: 4px; }}
QMenu::item:selected, QMenuBar::item:selected {{ background: #2f6fd0; color: white; }}
QStatusBar {{ color: {C_DIM}; border-top: 1px solid {C_LINE}; }}
QScrollArea {{ border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3a3e46; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #4a4f59; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #3a3e46; border-radius: 4px; min-width: 30px; }}
QSplitter::handle {{ background: {C_BG}; }}
QToolTip {{ background: {C_CARD}; color: {C_TEXT}; border: 1px solid #4a4f59; padding: 5px; }}
QMessageBox, QFileDialog {{ background: {C_CARD}; }}
"""

COLUMN_HELP = {
    C_FILE: "The table saved from ImageJ (ROI Manager → More → Multi Measure) for this recording.",
    C_NAME: "Name of the drug, as it should appear in the tables and graphs.",
    C_ROLE: "Drug, or QC = the quality-control drug (e.g. KCl, ionomycin).\n"
            "Only cells that respond to the QC drug are analysed.",
    C_BASE: "Frames before the drug arrives, first-last, e.g. 1-8.",
    C_PEAK: "Frames of the response, first-last, e.g. 15-25. Read them off the Overview.\n"
            "A drug without any response: use the frames after the drug was added.",
    C_SD: "Threshold. A cell responds if its mean in the peak window is above\n"
          "mean baseline + this number × standard deviation of the baseline.",
    C_ADD: "Frame at which the drug was added (empty = last frame of the baseline).",
    C_WASH: "Seconds of washing after this recording, before the next one (not imaged).",
}


def classify(path):
    """What a table saved from ImageJ is: ("recording" | "size" | None, its column names).
    recording = Multi Measure (columns Mean1, Mean2 ...), size = Measure of the ROIs (column Area)."""
    try:
        first = Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return None, []
    cols = [c.strip().strip('"') for c in re.split(r"[;,\t]", first)]
    if "Area" in cols:
        return "size", cols
    if sum(c.startswith("Mean") for c in cols) >= 2:
        return "recording", cols
    return None, cols


def scan_folder(folder):
    """The ImageJ tables of the folder: (recordings, size files), as file names."""
    recs, sizes = [], []
    for p in sorted(Path(folder).iterdir(), key=lambda q: q.name.lower()):
        if not p.is_file() or p.suffix.lower() not in TABLES:
            continue
        kind, _ = classify(p)
        if kind == "size":
            sizes.append(p.name)
        elif kind == "recording":
            recs.append(p.name)
    return recs, sizes


def figure_pixmap(fig, dpi=170):
    """A matplotlib figure exactly as it is saved (tight box), as an image for the window."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    pix = QtGui.QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    return pix


class ImageView(QtWidgets.QScrollArea):
    """Shows a picture scaled to the free space (never larger than its real size)."""

    def __init__(self, message=""):
        super().__init__()
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QtWidgets.QLabel(message)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.setWidget(self.label)
        self.pix = None

    def set_message(self, text):
        self.pix = None
        self.label.setPixmap(QtGui.QPixmap())
        self.label.setText(text)

    def set_pixmap(self, pix):
        self.pix = pix
        self.label.setText("")
        self._fit()

    def _fit(self):
        if self.pix is None or self.pix.isNull():
            return
        room = self.viewport().size() - QtCore.QSize(12, 12)
        if self.pix.width() > room.width() or self.pix.height() > room.height():
            self.label.setPixmap(self.pix.scaled(room, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
        else:
            self.label.setPixmap(self.pix)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calcium imaging analysis")
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1560, screen.width() - 40), min(1010, screen.height() - 60))
        self.folder = None
        self.csv_files, self.size_files = [], []
        self.raw_cache = {}
        self.D = None                      # loaded results (make_graphs.load)
        self.building = False
        self.last_checks = ""
        self.setAcceptDrops(True)          # the folder or the CSV files can be dragged into the window
        self._build_ui()
        self.timer = QtCore.QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.refresh_overview)
        if AUTO_UPDATE:
            QtCore.QTimer.singleShot(200, lambda: self.git_pull(quiet=True))

    # ------------------------------------------------------------------ window
    def _card(self, number, title):
        """A numbered box of the left panel: (frame, its layout)."""
        W = QtWidgets
        box = W.QFrame()
        box.setObjectName("card")
        v = W.QVBoxLayout(box)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(10)
        h = W.QHBoxLayout()
        h.setSpacing(9)
        n = W.QLabel(str(number))
        n.setObjectName("badge")
        n.setFixedSize(22, 22)
        n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = W.QLabel(title)
        t.setObjectName("step")
        h.addWidget(n); h.addWidget(t); h.addStretch(1)
        v.addLayout(h)
        return box, v

    @staticmethod
    def _fields(parent_layout, fields, columns=2):
        """Fields in a grid, each with its label above it. fields = [(label, widget), ...]."""
        g = QtWidgets.QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(10)
        for k, (label, widget) in enumerate(fields):
            cell = QtWidgets.QVBoxLayout()
            cell.setSpacing(3)
            lab = QtWidgets.QLabel(label)
            lab.setObjectName("field")
            widget.setFixedHeight(32)
            cell.addWidget(lab)
            cell.addWidget(widget)
            cell.addStretch(1)
            g.addLayout(cell, k // columns, k % columns)
        for c in range(columns):
            g.setColumnStretch(c, 1)
        parent_layout.addLayout(g)

    @staticmethod
    def _hint(text):
        lab = QtWidgets.QLabel(text)
        lab.setObjectName("hint")
        lab.setWordWrap(True)
        return lab

    def _build_ui(self):
        W = QtWidgets
        split = W.QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(6)
        self.setCentralWidget(split)

        # ---------- left: controls
        left = W.QWidget()
        lay = W.QVBoxLayout(left)
        lay.setContentsMargins(14, 12, 10, 6)
        lay.setSpacing(12)

        title = W.QLabel("Calcium imaging analysis")
        title.setObjectName("title")
        sub = W.QLabel("From the ImageJ tables to the responders of every drug and the graphs")
        sub.setObjectName("subtitle")
        head = W.QVBoxLayout()
        head.setSpacing(1)
        head.addWidget(title); head.addWidget(sub)
        lay.addLayout(head)

        box, v = self._card(1, "Data from ImageJ")
        h = W.QHBoxLayout()
        b = W.QPushButton("Open folder…")
        b.setObjectName("primary")
        b.setToolTip("Choose the folder that contains the CSV files; every recording in it is listed.")
        b.clicked.connect(self.choose_folder)
        h.addWidget(b)
        b = W.QPushButton("Add CSV files…")
        b.setToolTip("Choose the CSV files themselves (one per recording, and the cell size file if you have one).")
        b.clicked.connect(self.add_files)
        h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.path_label = W.QLabel("No data opened yet")
        self.path_label.setObjectName("path")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(self.path_label)
        v.addWidget(self._hint("One CSV file per recording. You can also drag the folder or the files into this window."))
        lay.addWidget(box)

        box, v = self._card(2, "Recordings, in the order they were recorded")
        self.table = W.QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        for c, text in COLUMN_HELP.items():
            self.table.horizontalHeaderItem(c).setToolTip(text)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setFixedWidth(26)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(W.QHeaderView.ResizeMode.Interactive)
        hh.setHighlightSections(False)
        for c, w in zip(range(len(COLS)), (138, 96, 64, 68, 60, 36, 60, 60)):
            self.table.setColumnWidth(c, w)
        hh.setStretchLastSection(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setMinimumHeight(134)
        self.table.itemChanged.connect(self.changed)
        v.addWidget(self.table)
        h = W.QHBoxLayout()
        h.setSpacing(6)
        for text, tip, slot in (("+ Add row", "Add one more recording", self.add_row),
                                ("Remove", "Remove the selected recording", self.remove_row),
                                ("↑", "Move the selected recording up", lambda: self.move_row(-1)),
                                ("↓", "Move the selected recording down", lambda: self.move_row(1))):
            b = W.QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.qc_label = W.QLabel()
        self.qc_label.setObjectName("qc")
        self.qc_label.setWordWrap(True)
        v.addWidget(self.qc_label)
        v.addWidget(self._hint(
            "<b>Baseline</b> and <b>Peak</b> are frames, first-last (e.g. 1-8 and 15-25); read the peak off the "
            "Overview. Hold the mouse over a column title to see what it means."))
        lay.addWidget(box)

        def plain(spin):                                 # a number field (its arrows are hidden by the style sheet)
            spin.lineEdit().setTextMargins(7, 0, 0, 0)
            return spin
        box, v = self._card(3, "Measurement")
        self.n_bg = plain(W.QSpinBox()); self.n_bg.setRange(0, 50); self.n_bg.setValue(3)
        self.bg_use = W.QLineEdit("all")
        self.bg_use.setPlaceholderText("all, or e.g. 98, 99")
        self.interval = plain(W.QDoubleSpinBox()); self.interval.setRange(0.001, 3600); self.interval.setDecimals(3)
        self.interval.setValue(1.0); self.interval.setSuffix(" s")
        self.size_file = W.QComboBox()
        self.size_file.addItem("none")
        self.px_um = plain(W.QDoubleSpinBox()); self.px_um.setRange(0, 100); self.px_um.setDecimals(4)
        self.px_um.setValue(0); self.px_um.setSuffix(" µm")
        self.n_bg.setToolTip("How many of the LAST ROIs are the empty background boxes.")
        self.bg_use.setToolTip("'all', or the numbers of the boxes to use if one of them is not empty, e.g. 98, 99.")
        self.size_file.setToolTip("Optional. ImageJ: ROI Manager → Measure, saved as cell_size.csv.\n"
                                  "Needed for the two cell-area graphs.")
        self.px_um.setToolTip("Only if the cell size file is in pixels: the size of one pixel in µm.")
        self._fields(v, [("Background boxes (the last ROIs)", self.n_bg),
                         ("Background boxes to use", self.bg_use),
                         ("Time between two frames", self.interval),
                         ("Cell size file (optional)", self.size_file),
                         ("Pixel size (0 = size file already in µm)", self.px_um)], columns=3)
        self.n_bg.valueChanged.connect(self.changed)
        self.bg_use.editingFinished.connect(self.changed)
        self.interval.valueChanged.connect(self.changed)
        lay.addWidget(box)

        box, v = self._card(4, "Quality control: two more rules")
        self.late_s = plain(W.QDoubleSpinBox()); self.late_s.setRange(0, 100000); self.late_s.setDecimals(1)
        self.late_s.setValue(cm.LATE_RESPONSE_S); self.late_s.setSuffix(" s after the drug")
        self.min_dff0 = plain(W.QDoubleSpinBox()); self.min_dff0.setRange(0, 1000); self.min_dff0.setDecimals(5)
        self.min_dff0.setSingleStep(0.0001); self.min_dff0.setValue(cm.MIN_QC_DFF0)
        self.late_s.setToolTip("A cell is removed if, in a drug recording, its response starts later than this.\n"
                               "0 = this rule is switched off.")
        self.min_dff0.setToolTip("A cell is removed if its peak ΔF/F0 for the quality-control drug is below this.\n"
                                 "0 = this rule is switched off.")
        self._fields(v, [("Remove cells that respond later than  (0 = off)", self.late_s),
                         ("Remove cells with a QC response (ΔF/F0) below  (0 = off)", self.min_dff0)])
        self.late_s.valueChanged.connect(self.changed)
        lay.addWidget(box)

        self.run_btn = W.QPushButton("Run analysis")
        self.run_btn.setObjectName("run")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self.run_analysis)
        lay.addStretch(1)

        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel = W.QWidget()                              # the boxes scroll, the Run button stays in view
        pv = W.QVBoxLayout(panel)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)
        pv.addWidget(scroll, 1)
        foot = W.QVBoxLayout()
        foot.setContentsMargins(14, 8, 10, 10)
        foot.setSpacing(6)
        foot.addWidget(self.run_btn)
        foot.addWidget(self._hint("The tables (Excel + CSV) and the graphs are saved in the folder multidrug_results, "
                                  "next to the CSV files."))
        pv.addLayout(foot)
        panel.setMinimumWidth(680)
        split.addWidget(panel)

        # ---------- right: tabs + messages
        right = W.QSplitter(Qt.Orientation.Vertical)
        right.setHandleWidth(6)
        self.tabs = W.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.overview = ImageView("Open the folder with the CSV files from ImageJ, or add the CSV files.\n\n"
                                  "The median trace of every recording appears here, with the baseline and "
                                  "peak windows drawn in.")
        self.tabs.addTab(self.overview, "Overview")
        self.summary = W.QTextBrowser()
        self.summary.setOpenExternalLinks(True)
        self.summary.setHtml(EMPTY_SUMMARY)
        self.tabs.addTab(self.summary, "Summary")
        self.graph_views = {}
        for name, tab_title, _ in mg.GRAPHS:
            view = ImageView("Run the analysis (or File → Open results file…) to see this graph.")
            self.graph_views[name] = view
            self.tabs.addTab(view, tab_title)
        self.tabs.tabBar().setDrawBase(False)
        top = W.QWidget()
        tv = W.QVBoxLayout(top)
        tv.setContentsMargins(0, 6, 10, 0)
        tv.setSpacing(8)
        tv.addWidget(self.tabs, 1)
        bar = W.QHBoxLayout()
        bar.setSpacing(8)
        self.unit = W.QComboBox(); self.unit.addItems(["F − F0  (ΔF)", "ΔF / F0"])
        self.fmt = W.QComboBox(); self.fmt.addItems(["png", "pdf", "svg"])
        self.save_btn = W.QPushButton("Save graphs")
        self.save_btn.clicked.connect(self.save_graphs)
        self.open_btn = W.QPushButton("Open results folder")
        self.open_btn.clicked.connect(self.open_results_folder)
        for wdg in ("Graphs 1 and 2 show", self.unit, "  Save as", self.fmt, self.save_btn):
            if isinstance(wdg, str):
                wdg = self._hint(wdg)
                wdg.setWordWrap(False)
            bar.addWidget(wdg)
        bar.addStretch(1)
        bar.addWidget(self.open_btn)
        tv.addLayout(bar)
        self.unit.currentIndexChanged.connect(self.draw_graphs)
        right.addWidget(top)
        logwrap = W.QWidget()
        lv = W.QVBoxLayout(logwrap)
        lv.setContentsMargins(0, 8, 10, 6)
        lv.setSpacing(4)
        lv.addWidget(self._hint("MESSAGES"))
        self.logbox = W.QPlainTextEdit(readOnly=True)
        self.logbox.setPlaceholderText("Messages and warnings appear here.")
        f = QtGui.QFont("monospace"); f.setStyleHint(QtGui.QFont.StyleHint.Monospace); f.setPointSize(9)
        self.logbox.setFont(f)
        lv.addWidget(self.logbox)
        right.addWidget(logwrap)
        right.setSizes([720, 170])
        split.addWidget(right)
        split.setSizes([700, 860])

        # ---------- menu
        m = self.menuBar().addMenu("&File")
        for text, key, slot in (("Open folder…", "Ctrl+O", self.choose_folder),
                                ("Add CSV files…", "Ctrl+Shift+O", self.add_files),
                                ("Open results file… (graphs only)", "Ctrl+L", self.choose_results),
                                ("Run analysis", "Ctrl+R", self.run_analysis),
                                ("Save graphs", "Ctrl+S", self.save_graphs),
                                ("Quit", "Ctrl+Q", self.close)):
            a = QtGui.QAction(text, self); a.setShortcut(key); a.triggered.connect(slot); m.addAction(a)
        m = self.menuBar().addMenu("&Help")
        a = QtGui.QAction("Update now (git pull)", self); a.triggered.connect(lambda: self.git_pull(quiet=False)); m.addAction(a)
        a = QtGui.QAction("All steps (STEPS.md)", self); a.triggered.connect(self.open_steps); m.addAction(a)
        self.statusBar().showMessage("Open the folder with the CSV files from ImageJ to start.")
        self._enable_results(False)
        self.update_qc_label()

    def _enable_results(self, on):
        self.save_btn.setEnabled(on)

    def log(self, text):
        text = text.rstrip()
        if text:
            self.logbox.appendPlainText(text)
            self.logbox.verticalScrollBar().setValue(self.logbox.verticalScrollBar().maximum())

    # ------------------------------------------------------------------ update
    def git_pull(self, quiet=True):
        repo = next((p for p in [HERE, *HERE.parents] if (p / ".git").exists()), None)
        if repo is None:
            if not quiet:
                self.log("Update: this folder is not a git clone. Get the newest version with\n"
                         "  git clone https://github.com/yashadarsh1608/calcium-imaging.git")
            return
        proc = QtCore.QProcess(self)
        proc.setWorkingDirectory(str(repo))
        proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)

        def done(code, _status):
            out = bytes(proc.readAll()).decode(errors="replace").strip()
            if code != 0:
                self.log("Update (git pull): could not check for a newer version"
                         + (f" - {out.splitlines()[-1]}" if out else " (offline?)"))
            elif "Already up to date" in out or "Bereits aktuell" in out:
                self.log("Update (git pull): already the newest version.")
            else:
                self.log("Update (git pull): a newer version was downloaded.\n" + out +
                         "\n-> close this window and start it again to use it.")
        proc.finished.connect(done)
        proc.errorOccurred.connect(lambda _e: self.log("Update: git is not installed; skipped.") if not quiet else None)
        proc.start("git", ["pull", "--ff-only"])
        QtCore.QTimer.singleShot(20000, lambda: proc.kill() if proc.state() != QtCore.QProcess.ProcessState.NotRunning else None)

    def open_steps(self):
        local = HERE.parent / "STEPS.md"
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(local)) if local.exists() else
                                       QtCore.QUrl("https://github.com/yashadarsh1608/calcium-imaging/blob/main/STEPS.md"))

    # ------------------------------------------------------------------ recordings table
    def _combo(self, items, current):
        c = QtWidgets.QComboBox()
        c.addItems(items)
        if current in items:
            c.setCurrentText(current)
        return c

    def set_rows(self, rows):
        self.building = True
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            files = list(self.csv_files)
            if r.get("file") and r["file"] not in files:
                files.append(r["file"])
            fc = QtWidgets.QComboBox()                   # shows the file name, keeps the path if it is elsewhere
            for f in files:
                fc.addItem(Path(f).name, f)
            fc.setCurrentIndex(max(fc.findData(r.get("file", "")), 0))
            fc.setToolTip(str(self.folder / r["file"]) if self.folder and r.get("file") else "")
            fc.currentIndexChanged.connect(self.changed)
            self.table.setCellWidget(i, C_FILE, fc)
            rc = self._combo(["Drug", "QC"], r.get("role", "Drug"))
            rc.currentIndexChanged.connect(lambda _=0, combo=rc: self.role_changed(combo))
            self.table.setCellWidget(i, C_ROLE, rc)
            for c, key, default in ((C_NAME, "name", ""), (C_BASE, "baseline", "1-8"), (C_PEAK, "peak", ""),
                                    (C_SD, "sd", "5"), (C_ADD, "added", ""), (C_WASH, "wash", "60")):
                self.table.setItem(i, c, QtWidgets.QTableWidgetItem(str(r.get(key, default))))
        self.table.setFixedHeight(36 + 32 * max(3, self.table.rowCount()))   # as high as its rows
        self.building = False
        self.changed()

    def rows(self):
        out = []
        for i in range(self.table.rowCount()):
            text = lambda c: (self.table.item(i, c).text().strip() if self.table.item(i, c) else "")
            out.append(dict(file=self.table.cellWidget(i, C_FILE).currentData() or "",
                            role=self.table.cellWidget(i, C_ROLE).currentText(),
                            name=text(C_NAME), baseline=text(C_BASE), peak=text(C_PEAK),
                            sd=text(C_SD), added=text(C_ADD), wash=text(C_WASH)))
        return out

    def role_changed(self, combo):
        if self.building:
            return
        if combo.currentText() == "QC":                  # only one quality-control recording
            self.building = True
            for i in range(self.table.rowCount()):
                other = self.table.cellWidget(i, C_ROLE)
                if other is not combo and other.currentText() == "QC":
                    other.setCurrentText("Drug")
            self.building = False
        self.changed()

    def add_row(self):
        if self.folder is None or not self.csv_files:
            return self.add_files()
        rows = self.rows()
        used = {r["file"] for r in rows}
        free = next((f for f in self.csv_files if f not in used), self.csv_files[0] if self.csv_files else "")
        rows.append(dict(file=free, name=Path(free).stem if free else ""))
        self.set_rows(rows)

    def remove_row(self):
        i = self.table.currentRow()
        rows = self.rows()
        if 0 <= i < len(rows):
            del rows[i]
            self.set_rows(rows)

    def move_row(self, step):
        i = self.table.currentRow()
        rows = self.rows()
        j = i + step
        if 0 <= i < len(rows) and 0 <= j < len(rows):
            rows[i], rows[j] = rows[j], rows[i]
            self.set_rows(rows)
            self.table.setCurrentCell(j, C_NAME)

    def changed(self, *_):
        if not self.building:
            self.update_qc_label()
            self.timer.start()

    def update_qc_label(self):
        rows = self.rows()
        qc = next((r for r in rows if r["role"] == "QC"), None)
        if not rows:
            self.qc_label.setText("The quality-control drug (e.g. KCl) gets the <b>Role QC</b>: only cells that "
                                  "respond to it are analysed.")
        elif qc:
            name = qc["name"] or Path(qc["file"]).stem
            self.qc_label.setText(f"Quality-control drug: <b>{name}</b>. Only cells that respond to {name} "
                                  f"are analysed and shown in the graphs.")
        else:
            self.qc_label.setText(f"<span style='color:{C_WARN}'><b>No quality-control drug chosen.</b></span> "
                                  f"Every cell is analysed. To keep only cells that respond to e.g. KCl, set the "
                                  f"<b>Role</b> of that recording to <b>QC</b>.")

    # ------------------------------------------------------------------ folder / files / session
    def _start_dir(self):
        return str(self.folder or Path.home())

    def choose_folder(self):
        # Qt's own dialog instead of the system one: it also shows the files inside the folders,
        # so you can see that you are in the folder with the CSV files.
        dlg = QtWidgets.QFileDialog(self, "Choose the FOLDER that contains the CSV files from ImageJ", self._start_dir())
        dlg.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        dlg.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, False)
        dlg.setLabelText(QtWidgets.QFileDialog.DialogLabel.Accept, "Open this folder")
        places = [Path.home(), Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"]
        for vol in QtCore.QStorageInfo.mountedVolumes():      # USB sticks and other drives
            root = vol.rootPath()
            if vol.isValid() and vol.isReady() and re.match(r"(/media/|/run/media/|/mnt/|/Volumes/|[A-Za-z]:)", root):
                places.append(Path(root))
        dlg.setSidebarUrls([QtCore.QUrl.fromLocalFile(str(q)) for q in places if q.exists()])
        dlg.resize(900, 560)
        for sp in dlg.findChildren(QtWidgets.QSplitter):      # room for the names of the places on the left
            sp.setSizes([190, 710])
        if dlg.exec() and dlg.selectedFiles():
            self.open_folder(dlg.selectedFiles()[0])

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "CSV files from ImageJ: one per recording (and the cell size file)", self._start_dir(),
            "ImageJ tables (*.csv *.CSV *.xls *.txt *.tsv);;All files (*)")
        if files:
            self.take_files(files)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            e.acceptProposedAction()
            QtCore.QTimer.singleShot(0, lambda: self.take_files(paths))

    def _shown(self, path):
        """How a file is written in the table: its name if it is in the experiment folder, else the full path."""
        path = Path(path)
        return path.name if path.parent.resolve() == self.folder.resolve() else str(path)

    def take_files(self, paths):
        """Files chosen with 'Add CSV files…' or dropped on the window (a dropped folder is opened)."""
        paths = [Path(q) for q in paths]
        folders = [q for q in paths if q.is_dir()]
        if folders:
            return self.open_folder(folders[0])
        recs, sizes, unknown = [], [], []
        for q in paths:
            kind, cols = classify(q)
            if kind == "recording":
                recs.append(q)
            elif kind == "size":
                sizes.append(q)
            else:
                unknown.append(f"{q.name}: columns " + (", ".join(cols[:6]) if cols and len(cols) > 1 else "not readable"))
        if unknown:
            QtWidgets.QMessageBox.warning(
                self, "Not a table from ImageJ",
                "These files were not added, because they have no columns Mean1, Mean2 … (a recording) "
                "and no column Area (the cell sizes):\n\n" + "\n".join(unknown) +
                "\n\nIn ImageJ: Analyze → Set Measurements → tick 'Mean gray value', then ROI Manager → More → "
                "Multi Measure, and save the Results table as CSV.")
        if not recs and not sizes:
            return
        if self.folder is None:
            self._set_folder((recs or sizes)[0].parent)
            rows = []
        else:
            rows = self.rows()
        used = {r["file"] for r in rows}
        has_qc = any(r["role"] == "QC" for r in rows)
        for q in recs:
            shown = self._shown(q)
            if shown not in self.csv_files:
                self.csv_files.append(shown)
            if shown not in used:
                is_qc = not has_qc and bool(QC_HINT.search(q.stem))
                has_qc = has_qc or is_qc
                rows.append(dict(file=shown, name=q.stem, role="QC" if is_qc else "Drug"))
        for q in sizes:
            shown = self._shown(q)
            if shown not in self.size_files:
                self.size_files.append(shown)
                self.size_file.addItem(shown)
            self.size_file.setCurrentText(shown)
        self.set_rows(rows)
        self.log(f"Added {len(recs)} recording(s)" + (f" and the cell size file {sizes[-1].name}" if sizes else "")
                 + ". Check the order, names and roles, then type each peak window.")
        self.tabs.setCurrentWidget(self.overview)

    def _set_folder(self, folder):
        """Make `folder` the experiment folder (results go to its multidrug_results/); no recordings yet."""
        self.save_session()
        self.folder = Path(folder)
        self.raw_cache.clear()
        self.csv_files, self.size_files = scan_folder(self.folder)
        self.path_label.setText(str(self.folder))
        self.size_file.clear()
        self.size_file.addItems(["none"] + self.size_files)
        results = self.folder / cm.OUTPUT_FOLDER / "multidrug_results.xlsx"
        if results.exists():
            self.load_results(results, announce=False)
        else:
            self.clear_results()
        self.statusBar().showMessage(str(self.folder))

    def open_folder(self, folder):
        self._set_folder(folder)
        if not self.csv_files:
            self.set_rows([])
            self.overview.set_message("No recordings found in this folder.\n\nA recording is a table saved from ImageJ "
                                      "(ROI Manager → More → Multi Measure) with the columns Mean1, Mean2 …\n"
                                      "If the files are somewhere else, use 'Add CSV files…'.")
            self.log(f"{self.folder}: no recording CSV files found.")
            return
        session = self.folder / SESSION_FILE
        restored = False
        if session.exists():
            try:
                self.apply_session(json.loads(session.read_text()))
                restored = True
                self.log(f"Opened {self.folder} (settings of the last time restored).")
            except (ValueError, KeyError, TypeError):
                pass
        if not restored:
            drugs = [f for f in self.csv_files if not QC_HINT.search(Path(f).stem)]
            qcs = [f for f in self.csv_files if QC_HINT.search(Path(f).stem)]
            rows = [dict(file=f, name=Path(f).stem, role="Drug") for f in drugs + qcs[1:]]
            if qcs:
                rows.append(dict(file=qcs[0], name=Path(qcs[0]).stem, role="QC"))
            if self.size_files:
                self.size_file.setCurrentText(self.size_files[0])
            self.set_rows(rows)
            self.log(f"Opened {self.folder}: {len(self.csv_files)} recording(s)"
                     + (f", size file {self.size_files[0]}" if self.size_files else "")
                     + ". Check the order, names and roles, then type each peak window.")
        self.tabs.setCurrentWidget(self.overview)

    def session(self):
        return dict(rows=self.rows(), n_bg=self.n_bg.value(), bg_use=self.bg_use.text(),
                    interval=self.interval.value(), size_file=self.size_file.currentText(),
                    px_um=self.px_um.value(), late_s=self.late_s.value(), min_dff0=self.min_dff0.value(),
                    unit=self.unit.currentIndex(), fmt=self.fmt.currentText())

    def apply_session(self, s):
        self.building = True
        self.n_bg.setValue(int(s.get("n_bg", 3)))
        self.bg_use.setText(s.get("bg_use", "all"))
        self.interval.setValue(float(s.get("interval", 1)))
        for r in s["rows"]:                                # files that were added from another folder
            if r.get("file") and r["file"] not in self.csv_files and (self.folder / r["file"]).exists():
                self.csv_files.append(r["file"])
        size = s.get("size_file")
        if size and size not in ["none"] + self.size_files and (self.folder / size).exists():
            self.size_files.append(size)
            self.size_file.addItem(size)
        if size in ["none"] + self.size_files:
            self.size_file.setCurrentText(size)
        self.px_um.setValue(float(s.get("px_um", 0)))
        self.late_s.setValue(float(s.get("late_s", cm.LATE_RESPONSE_S)))
        self.min_dff0.setValue(float(s.get("min_dff0", cm.MIN_QC_DFF0)))
        self.unit.setCurrentIndex(int(s.get("unit", 0)))
        self.fmt.setCurrentText(s.get("fmt", "png"))
        self.building = False
        self.set_rows(s["rows"])

    def save_session(self):
        if self.folder and self.folder.exists() and self.table.rowCount():
            try:
                (self.folder / SESSION_FILE).write_text(json.dumps(self.session(), indent=2))
            except OSError:
                pass

    def closeEvent(self, e):
        self.save_session()
        super().closeEvent(e)

    # ------------------------------------------------------------------ reading the inputs
    def raw(self, name):
        path = self.folder / name
        key = (str(path), path.stat().st_mtime)
        if key not in self.raw_cache:
            self.raw_cache[key] = cm.read_imagej_csv(path)
        return self.raw_cache[key]

    def background(self, columns):
        n_bg = self.n_bg.value()
        if not 0 <= n_bg < len(columns):
            raise ValueError(f"Background boxes: must be between 0 and {len(columns) - 1}")
        boxes = list(columns[-n_bg:]) if n_bg else []
        text = self.bg_use.text().strip()
        if not n_bg or text.lower() in ("", "all", "none"):
            return n_bg, None
        by_num = {re.findall(r"\d+", c)[-1]: c for c in boxes if re.findall(r"\d+", c)}
        nums = re.findall(r"\d+", text)
        if not nums or any(k not in by_num for k in nums):
            raise ValueError(f"Background boxes to use: choose from {', '.join(boxes)} or 'all'")
        return n_bg, [by_num[k] for k in nums]

    def collect(self):
        """All inputs, checked. Raises ValueError with a message for the user."""
        if self.folder is None:
            raise ValueError("Open the folder with the CSV files first (Open folder… or Add CSV files…).")
        rows = self.rows()
        if not rows:
            raise ValueError("Add at least one recording (Add CSV files…).")
        a = dict(csvs=[], names=[], baselines=[], peaks=[], n_sds=[], washes=[], added=[], qc_index=None)
        for i, r in enumerate(rows):
            if not r["file"] or not (self.folder / r["file"]).exists():
                raise ValueError(f"Row {i + 1}: choose the CSV file.")
            name = r["name"] or Path(r["file"]).stem
            raw = self.raw(r["file"])
            nf = len(raw)
            try:
                bl = cm._range(r["baseline"], nf)
            except ValueError as e:
                raise ValueError(f"{name}, baseline: {e}")
            if not r["peak"]:
                raise ValueError(f"{name}: type the peak window (first-last frame, e.g. 15-25). "
                                 f"The Overview tab shows where the response is.")
            try:
                pk = cm._range(r["peak"], nf)
            except ValueError as e:
                raise ValueError(f"{name}, peak: {e}")
            if pk[0] <= bl[1]:
                raise ValueError(f"{name}: the peak window must start after the baseline ends.")
            try:
                sd = float(r["sd"].replace(",", "."))
                wash = float(r["wash"].replace(",", ".")) if i < len(rows) - 1 else 0.0
            except ValueError:
                raise ValueError(f"{name}: SD and Wash must be numbers.")
            if sd <= 0 or wash < 0:
                raise ValueError(f"{name}: SD must be above 0 and Wash cannot be negative.")
            try:
                added = int(float(r["added"])) if r["added"] else bl[1]
            except ValueError:
                raise ValueError(f"{name}: 'Drug at' must be a frame number (or empty = end of the baseline).")
            if not 1 <= added < nf:
                raise ValueError(f"{name}: 'Drug at' must be a frame between 1 and {nf - 1}.")
            if r["role"] == "QC":
                a["qc_index"] = i
            a["csvs"].append(self.folder / r["file"]); a["names"].append(name)
            a["baselines"].append(bl); a["peaks"].append(pk); a["n_sds"].append(sd); a["added"].append(added)
            if i < len(rows) - 1:
                a["washes"].append(wash)
        if len(set(a["names"])) != len(a["names"]):
            raise ValueError("Every recording needs its own name.")
        if len(a["names"]) - (a["qc_index"] is not None) < 1:
            raise ValueError("Add at least one drug recording besides the quality control.")
        a["n_bg"], a["use"] = self.background(self.raw(rows[0]["file"]).columns)
        a["interval"] = self.interval.value()
        a["size_csv"] = None if self.size_file.currentText() == "none" else self.folder / self.size_file.currentText()
        a["px_um"] = self.px_um.value()
        a["late_s"] = self.late_s.value()
        a["min_dff0"] = self.min_dff0.value() if a["qc_index"] is not None else 0.0
        return a

    # ------------------------------------------------------------------ overview
    def refresh_overview(self):
        if self.folder is None:
            return
        rows = [r for r in self.rows() if r["file"] and (self.folder / r["file"]).exists()]
        if not rows:
            return self.overview.set_message("Add the recordings: 'Add CSV files…' or '+ Add row'.")
        checks = io.StringIO()
        try:
            n_bg, use = self.background(self.raw(rows[0]["file"]).columns)
        except (ValueError, OSError) as e:
            return self.overview.set_message(str(e))
        ncol = 1 if len(rows) == 1 else 2 if len(rows) <= 6 else 3
        nrow = int(np.ceil(len(rows) / ncol))
        fig = Figure(figsize=(5.0 * ncol, 3.1 * nrow + 0.3))
        axs = np.atleast_1d(fig.subplots(nrow, ncol, squeeze=False)).ravel()
        for ax in axs[len(rows):]:
            ax.axis("off")
        for ax, r in zip(axs, rows):
            name = r["name"] or Path(r["file"]).stem
            try:
                raw = self.raw(r["file"])
                with contextlib.redirect_stdout(checks):
                    cm.check_background(raw, n_bg, name)
                X, _ = cm.background_subtract(raw, n_bg, use)
            except Exception as e:                      # unreadable file etc.
                ax.text(0.5, 0.5, str(e), ha="center", va="center", wrap=True, fontsize=8, transform=ax.transAxes)
                ax.axis("off")
                continue
            fr = X.index.values
            nf = len(fr)
            bl = pk = None
            with contextlib.suppress(ValueError):
                bl = cm._range(r["baseline"], nf)
            with contextlib.suppress(ValueError):
                pk = cm._range(r["peak"], nf) if r["peak"] else None
            zero = X.loc[bl[0]:bl[1]].mean() if bl else X.iloc[:8].mean()
            F = X - zero
            if bl:
                with contextlib.redirect_stdout(checks):
                    cm.baseline_check(X, bl, name)
            med = F.median(axis=1)
            ax.fill_between(fr, F.quantile(.25, axis=1), F.quantile(.75, axis=1), color="#2a78d6", alpha=.18, lw=0)
            ax.plot(fr, F.quantile(.9, axis=1), color="#2a78d6", lw=0.8, ls=":", label="top 10% of cells")
            ax.plot(fr, med, color="#14213d", lw=2, label="median cell")
            if bl:
                ax.axvspan(bl[0] - .5, bl[1] + .5, color="#9a9890", alpha=.25, lw=0)
                ax.text((bl[0] + bl[1]) / 2, 0.97, "baseline", transform=ax.get_xaxis_transform(), ha="center",
                        va="top", fontsize=8, color="#52514e")
            if pk:
                ax.axvspan(pk[0] - .5, pk[1] + .5, color="#eb6834", alpha=.22, lw=0)
                ax.text((pk[0] + pk[1]) / 2, 0.97, "peak", transform=ax.get_xaxis_transform(), ha="center",
                        va="top", fontsize=8, color="#b3421a")
            with contextlib.suppress(ValueError):
                added = int(float(r["added"])) if r["added"] else (bl[1] if bl else None)
                if added:
                    ax.axvline(added + .5, color="#14213d", lw=1, ls="--")
                    ax.text(added + .5, 0.86, " drug", transform=ax.get_xaxis_transform(), fontsize=8, color="#14213d")
                    limit = added + self.late_s.value() / max(self.interval.value(), 1e-9)
                    if r["role"] != "QC" and self.late_s.value() > 0 and limit < fr[-1]:
                        ax.axvspan(limit, fr[-1] + .5, color="#b3421a", alpha=.08, lw=0)
                        ax.text(limit, 0.86, f" later than {self.late_s.value():g} s", fontsize=8, color="#b3421a",
                                transform=ax.get_xaxis_transform())
            top = int(F.quantile(.9, axis=1).idxmax())
            ax.set_title(f"{name}{'  (QC)' if r['role'] == 'QC' else ''} · {nf} frames · highest at frame {top}"
                         + ("" if pk else " · peak window missing"), fontsize=9.5, loc="left",
                         color="#0b0b0b" if pk else "#b3421a")
            ax.axhline(0, color="#c9c8c2", lw=.8)
            ax.set_xlim(fr[0], fr[-1])
            ax.set_xlabel("Frame", fontsize=9, color="#52514e")
            ax.set_ylabel("cell − background − baseline", fontsize=8.5, color="#52514e")
            ax.xaxis.set_minor_locator(MultipleLocator(1))
            mg.clean(ax)
        axs[0].legend(frameon=False, fontsize=8, loc="center right")
        fig.tight_layout()
        self.overview.set_pixmap(figure_pixmap(fig, dpi=160))
        text = checks.getvalue().strip()
        if text != self.last_checks:
            self.last_checks = text
            self.log("Checks of the recordings:\n" + text if text else "Checks of the recordings: background boxes "
                     "and baselines look fine.")

    # ------------------------------------------------------------------ analysis
    def run_analysis(self):
        try:
            a = self.collect()
        except (ValueError, OSError) as e:
            QtWidgets.QMessageBox.warning(self, "Check the inputs", str(e))
            return
        if a["qc_index"] is None:
            yes = QtWidgets.QMessageBox.StandardButton.Yes
            if QtWidgets.QMessageBox.question(
                    self, "No quality-control drug",
                    "No recording has the Role QC, so every cell is analysed and shown in the graphs.\n\n"
                    "To keep only the cells that respond to the quality-control drug (e.g. KCl), choose "
                    "'No' and set the Role of that recording to QC.\n\nRun without quality control?") != yes:
                return
        out = self.folder / cm.OUTPUT_FOLDER
        buf = io.StringIO()
        self.statusBar().showMessage("Running the analysis …")
        QtWidgets.QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QtWidgets.QApplication.processEvents()
        error = None
        try:
            with contextlib.redirect_stdout(buf):
                cm.run(a["csvs"], a["names"], a["baselines"], a["peaks"], a["n_sds"], a["n_bg"], a["use"],
                       a["interval"], a["washes"], out, qc_index=a["qc_index"], size_csv=a["size_csv"],
                       px_um=a["px_um"], added=a["added"], late_s=a["late_s"],
                       min_qc_dff0=a["min_dff0"])
            settings = dict(csvs=[c.name for c in a["csvs"]], names=a["names"], baselines=a["baselines"],
                            peaks=a["peaks"], n_sd=a["n_sds"], n_bg=a["n_bg"], bg_use=a["use"],
                            interval=a["interval"], washes=a["washes"],
                            qc=a["names"][a["qc_index"]] if a["qc_index"] is not None else None,
                            size_file=a["size_csv"].name if a["size_csv"] else None,
                            pixel_size_um=a["px_um"], drug_added_at_frame=a["added"],
                            late_response_s=a["late_s"], min_qc_dff0=a["min_dff0"])
            (out / "settings.json").write_text(json.dumps(settings, indent=2))
        except ValueError as e:
            error = str(e)
        except Exception:
            error = traceback.format_exc()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self.log("\n── Analysis ──────────────────────────────\n" + buf.getvalue())
        if error:
            self.log("ERROR: " + error)
            self.statusBar().showMessage("The analysis stopped with an error.")
            QtWidgets.QMessageBox.critical(self, "The analysis stopped", error.strip().splitlines()[-1])
            return
        self.save_session()
        self.load_results(out / "multidrug_results.xlsx")
        self.save_graphs(quiet=True)
        self.tabs.setCurrentWidget(self.summary)
        self.statusBar().showMessage(f"Done. Results: {out}")

    # ------------------------------------------------------------------ results + graphs
    def choose_results(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "multidrug_results.xlsx", str(self.folder or Path.home()),
                                                     "Results (*.xlsx)")
        if f:
            self.load_results(Path(f))
            self.tabs.setCurrentWidget(self.summary)

    def clear_results(self):
        self.D = None
        self._enable_results(False)
        self.summary.setHtml(EMPTY_SUMMARY)
        for v in self.graph_views.values():
            v.set_message("Run the analysis (or File → Open results file…) to see this graph.")

    def load_results(self, xlsx, announce=True):
        try:
            self.D = mg.load(xlsx)
        except Exception as e:
            self.log(f"Could not read {xlsx}: {e}")
            QtWidgets.QMessageBox.warning(self, "Results file", f"Could not read the results file:\n{e}")
            return
        self._enable_results(True)
        self.summary.setHtml(self.summary_html())
        self.draw_graphs()
        if announce:
            self.log(f"Results loaded: {xlsx}")
        else:
            self.log(f"Earlier results found and shown: {xlsx}")

    def summary_html(self):
        D = self.D
        s, n = D["summary"], len(D["resp"])
        css = (f"<style>body{{color:{C_TEXT}}} table.t{{border-collapse:collapse;margin:4px 0 18px 0}} "
               f"table.t th,table.t td{{padding:6px 14px;border-bottom:1px solid {C_LINE};text-align:right}} "
               f"table.t th{{color:{C_DIM};font-weight:600}} "
               f"h3{{color:{C_TEXT};margin:18px 0 4px 0}} .dim{{color:{C_DIM}}}</style>")

        def tile(big, small):
            return (f"<td bgcolor='{C_CARD}' style='padding:12px 20px'><span style='font-size:20pt;font-weight:600'>"
                    f"{big}</span><br><span class='dim'>{small}</span></td><td width='10'></td>")
        html = [css, "<table cellspacing='0' cellpadding='0'><tr>"]
        html.append(tile(n, f"of {D['n_all']} cells analysed" + (f"<br>(passed the {D['qc']} quality control)"
                                                                if D["qc"] else "<br>(no quality-control drug)")))
        for _, r in s.iterrows():
            html.append(tile(f"{r['% responders']:.0f}%", f"{r['Drug']}<br>{int(r['Responders'])} of {n} responded"))
        html.append("</tr></table>")
        if len(D["excluded"]):
            html.append("<h3>Cells removed by the quality control</h3><table class='t'><tr><th align='left'>Reason</th>"
                        "<th>Cells</th></tr>")
            for reason, c in D["excluded"].items():
                html.append(f"<tr><td align='left'>{reason}</td><td>{int(c)}</td></tr>")
            html.append("</table>")
        html.append("<h3>Responders per drug</h3><table class='t'><tr><th align='left'>Drug</th><th>Responders</th>"
                    "<th>%</th><th>Baseline</th><th>Peak</th><th>Threshold</th><th>Mean peak ΔF ± SEM</th></tr>")
        for _, r in s.iterrows():
            sem = r.get("SEM peak ΔF")
            peak = "–" if np.isnan(r["Mean peak ΔF (responders)"]) else \
                f"{r['Mean peak ΔF (responders)']:.2f}" + ("" if sem is None or np.isnan(sem) else f" ± {sem:.2f}")
            html.append(f"<tr><td align='left'><b>{r['Drug']}</b></td><td>{int(r['Responders'])} of {n}</td>"
                        f"<td>{r['% responders']:.1f}</td><td>{r['Baseline frames']}</td><td>{r['Peak frames']}</td>"
                        f"<td>{r['Threshold']}</td><td>{peak}</td></tr>")
        html.append("</table>")
        if D["combos"] is not None:
            html.append("<h3>Which drugs the cells responded to</h3><table class='t'><tr><th align='left'>Responds to</th>"
                        "<th>Cells</th><th>%</th></tr>")
            for _, r in D["combos"].iterrows():
                html.append(f"<tr><td align='left'>{r['Responds to']}</td><td>{int(r['Cells'])}</td>"
                            f"<td>{r['% of analysed cells']:.1f}</td></tr>")
            html.append("</table>")
        if D["area"] is not None:
            html.append(f"<h3>Cell size (analysed cells)</h3><p>Median area {D['area'].median():.1f} µm², median "
                        f"equivalent diameter {2 * np.sqrt(D['area'].median() / np.pi):.1f} µm.</p>")
        html.append(f"<p class='dim'>All tables: {D['xlsx']}</p>")
        return "".join(html)

    def graph_unit(self):
        return "dF" if self.unit.currentIndex() == 0 else "dF_F0"

    def draw_graphs(self, *_):
        if self.D is None or self.building:
            return
        QtWidgets.QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for name, _, needs_size in mg.GRAPHS:
                view = self.graph_views[name]
                try:
                    fig = mg.make_figure(self.D, name, self.graph_unit())
                except Exception as e:
                    view.set_message(f"This graph could not be drawn:\n{e}")
                    self.log(f"Graph {name}: {traceback.format_exc()}")
                    continue
                if fig is None:
                    view.set_message("This graph needs the cell size.\n\nChoose the cell size file "
                                     "(ImageJ: ROI Manager → Measure, saved as cell_size.csv) under Measurement "
                                     "and run the analysis again.")
                else:
                    view.set_pixmap(figure_pixmap(fig))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def save_graphs(self, quiet=False):
        if self.D is None:
            return
        out = self.D["xlsx"].parent / "graphs"
        try:
            saved = mg.save_all(self.D, out, self.fmt.currentText(), self.graph_unit())
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Save graphs", str(e))
            return
        self.log(f"Graphs saved in {out}: " + ", ".join(p.name for p in saved))
        if not quiet:
            self.statusBar().showMessage(f"{len(saved)} graphs saved in {out}")

    def open_results_folder(self):
        target = self.D["xlsx"].parent if self.D else self.folder
        if target:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(target)))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK)
    win = Window()
    win.show()
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():      # python calcium_gui.py /path/to/experiment
        win.open_folder(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()