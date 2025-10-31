# pid_tuner_desktop/main.py
import sys
import time
import threading

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction, QPalette, QColor, QFont
from PySide6.QtWidgets import QStyle, QLabel, QDockWidget, QHeaderView
import pyqtgraph as pg


# ----------------------------- Theming ---------------------------------------
def apply_dark_fusion(app: QtWidgets.QApplication):
    """Modern dark Fusion palette + fonts."""
    app.setStyle("Fusion")
    p = QPalette()

    # base colors
    bg = QColor(22, 26, 34)      # window
    panel = QColor(28, 34, 46)   # panels
    alt = QColor(18, 22, 30)
    text = QColor(226, 230, 239)
    muted = QColor(160, 170, 186)
    accent = QColor(110, 166, 255)

    p.setColor(QPalette.Window, bg)
    p.setColor(QPalette.Base, alt)
    p.setColor(QPalette.AlternateBase, panel)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, panel)
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.ToolTipBase, panel)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Highlight, accent)
    p.setColor(QPalette.HighlightedText, QColor(12, 15, 22))
    p.setColor(QPalette.PlaceholderText, muted)
    p.setColor(QPalette.Disabled, QPalette.Text, muted)
    p.setColor(QPalette.Disabled, QPalette.ButtonText, muted)
    app.setPalette(p)

    # readable UI font
    app.setFont(QFont("Segoe UI", 10))


# --------------------------- Realtime mock engine -----------------------------
class RealtimeSim(QtCore.QObject):
    """
    Very small toy loop:
      Plant ~ FOPDT'ish: y' = (K*u - y)/tau
      Controller ~ P only (use Ti box as plant tau in the mock)
    Emits: tick(t, sp, pv, op)
    """
    tick = QtCore.Signal(float, float, float, float)

    def __init__(self, period_s: float = 1.0, parent=None):
        super().__init__(parent)
        self._period = period_s
        self._stop = threading.Event()
        self._thr: threading.Thread | None = None
        self._t = 0.0
        self._sp = 5.0
        self._pv = 0.0
        self._op = 0.0
        # "Controller" knobs the UI will read when ticking
        self.kp_provider = lambda: 0.3
        self.tau_provider = lambda: 20.0  # reusing "Ti" field as plant tau
        self.noise_provider = lambda: 0.0

    # public API
    def set_sp(self, value: float): self._sp = float(value)
    def get_sp(self) -> float: return self._sp

    def start(self):
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()

    # worker
    def _run(self):
        while not self._stop.is_set():
            kc = float(self.kp_provider())
            tau = max(0.1, float(self.tau_provider()))
            nstd = float(self.noise_provider())

            err = self._sp - self._pv
            self._op = max(0.0, min(100.0, kc * err * 100.0))  # %
            dy = ((self._op / 100.0) - self._pv) / tau         # K=1
            self._pv += dy * self._period + (nstd * (0.5 - time.time() % 1))
            self._t += self._period

            self.tick.emit(self._t, self._sp, self._pv, self._op)
            time.sleep(self._period)


# ------------------------------ Main Window -----------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PID Tuner & Loop Analyzer (Desktop)")
        self.resize(1280, 820)

        # --------- Data buffers (used by slots) ----------
        self.ts, self.sps, self.pvs, self.ops = [], [], [], []

        # --------- Simulation engine (must exist before toolbar) ----------
        self.sim = RealtimeSim(period_s=1.0)
        self.sim.tick.connect(self.on_tick)

        # --------- Project Browser (tree) ----------
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self._populate_tree()

        # --------- Tabs (controller/process/sim/tuning) ----------
        self.tabs = QtWidgets.QTabWidget()
        self.controllerTab = self._build_controller_tab()
        self.processTab = self._build_process_tab()
        self.simTab = self._build_sim_tab()
        self.tuneTab = self._build_tune_tab()
        self.tabs.addTab(self.controllerTab, "Controller")
        self.tabs.addTab(self.processTab, "Process")
        self.tabs.addTab(self.simTab, "Simulation")
        self.tabs.addTab(self.tuneTab, "Tuning")

        # --------- Live plot ----------
        self._build_plot()

        # --------- Output console ----------
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("QPlainTextEdit { padding:6px; }")

        # --------- Dock layout (resizable) ----------
        self._setup_docks_and_central()

        # --------- Status bar ----------
        self._setup_statusbar()
        self.set_connected(False)

        # --------- Toolbar (after sim exists) ----------
        self.addToolBar(self._build_toolbar())

        # --------- Allow resizable/tabbed docks ----------
        self.setDockOptions(
            QtWidgets.QMainWindow.AllowNestedDocks
            | QtWidgets.QMainWindow.AllowTabbedDocks
            | QtWidgets.QMainWindow.AnimatedDocks
        )

        # wire sim parameter providers to UI fields
        self.sim.kp_provider = lambda: self.kp.value()
        self.sim.tau_provider = lambda: max(0.1, self.ti.value())
        self.sim.noise_provider = lambda: self.noise.value()

    # ----------------------------- UI builders --------------------------------
    def _populate_tree(self):
        root = QtWidgets.QTreeWidgetItem(["AptiTuneDemo"])
        signals = QtWidgets.QTreeWidgetItem(["Signals"])
        for name in ["TCAF", "PCAF", "TCBE", "TCCF", "TCCD"]:
            signals.addChild(QtWidgets.QTreeWidgetItem([name]))
        cases = QtWidgets.QTreeWidgetItem(["Loop Tuning Cases"])
        cases.addChild(QtWidgets.QTreeWidgetItem(["tuning case"]))
        root.addChild(signals)
        root.addChild(cases)
        self.tree.addTopLevelItem(root)
        self.tree.expandAll()
        self.tree.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def _build_plot(self):
        self.plot = pg.PlotWidget()
        self.plot.setBackground(QColor(12, 17, 26))
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "PV / SP")
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=0.25)
        self.plot.getAxis("bottom").setPen(QColor(90, 100, 120))
        self.plot.getAxis("left").setPen(QColor(90, 100, 120))
        self.plot.showAxis("right")
        self.plot.getAxis("right").setPen(QColor(90, 100, 120))
        self.plot.getAxis("right").setLabel("OP (%)")
        self.plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # primary curves
        self.cur_sp = self.plot.plot([], [], pen=pg.mkPen(color=(110, 166, 255), style=QtCore.Qt.DashLine, width=2))
        self.cur_pv = self.plot.plot([], [], pen=pg.mkPen(color=(63, 185, 80), width=2))

        # right-axis viewbox for OP
        self.ax2 = pg.ViewBox()
        self.plot.scene().addItem(self.ax2)
        self.plot.getAxis("right").linkToView(self.ax2)
        self.ax2.setXLink(self.plot)
        self.cur_op = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 189, 46), width=2))
        self.ax2.addItem(self.cur_op)

        # keep right view aligned
        def _sync_views():
            self.ax2.setGeometry(self.plot.getViewBox().sceneBoundingRect())
            self.ax2.linkedViewChanged(self.plot.getViewBox(), self.ax2.XAxis)
        self.plot.getViewBox().sigResized.connect(_sync_views)
        _sync_views()

    def _setup_docks_and_central(self):
        # Left dock: Project Browser
        dock_tree = QDockWidget("Project Browser", self)
        dock_tree.setObjectName("dockProject")
        dock_tree.setWidget(self.tree)
        dock_tree.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_tree)

        # Bottom dock: Output console
        dock_console = QDockWidget("Output", self)
        dock_console.setObjectName("dockConsole")
        dock_console.setWidget(self.output)
        dock_console.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock_console.setMinimumHeight(120)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_console)

        # Central widget: tabs + plot vertically
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)
        v.addWidget(self.tabs)
        v.addWidget(self.plot, 1)
        v.setStretch(0, 0)  # tabs
        v.setStretch(1, 1)  # plot grows
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        sb = QtWidgets.QStatusBar(self)
        self.setStatusBar(sb)
        self.statusLight = QLabel("●")
        self.statusLight.setStyleSheet("QLabel { color:#666; font-size:14px; }")
        self.statusLabel = QLabel("Disconnected")
        sb.addWidget(self.statusLight)
        sb.addWidget(self.statusLabel)
        self.fpsLabel = QLabel("FPS: 1")
        sb.addPermanentWidget(self.fpsLabel)

    def _build_toolbar(self):
        tb = QtWidgets.QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QtCore.QSize(18, 18))

        def add(text, icon, slot, tip=None, shortcut=None):
            act = QAction(self.style().standardIcon(icon), text, self)
            if shortcut:
                act.setShortcut(shortcut)
            if tip:
                act.setStatusTip(tip)
                act.setToolTip(tip)
            act.triggered.connect(slot)
            tb.addAction(act)
            return act

        add("New Case", QStyle.SP_FileIcon, lambda: self.log("New case created"),
            "Create a new tuning case", "Ctrl+N")
        add("Step Test", QStyle.SP_BrowserReload, lambda: self.log("Step Test started"),
            "Detect steps from data", "Ctrl+T")
        add("Identify", QStyle.SP_DirOpenIcon, lambda: self.log("Identification started"),
            "Fit FOPDT/SOPDT/INT model", "Ctrl+I")
        add("Tune", QStyle.SP_CommandLink, lambda: self.log("Tuning (SIMC)…"),
            "Compute PID from model", "Ctrl+U")

        tb.addSeparator()
        add("Run", QStyle.SP_MediaPlay, self._cmd_run, "Run realtime simulation", "Ctrl+R")
        add("Stop", QStyle.SP_MediaStop, self._cmd_stop, "Stop simulation", "Ctrl+S")

        tb.addSeparator()
        add("Save Initial", QStyle.SP_DialogSaveButton, lambda: self.log("Saved Initial"),
            "Save initial guess")
        add("Save Current", QStyle.SP_DialogApplyButton, lambda: self.log("Saved Current"),
            "Save current parameters")

        tb.addSeparator()
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self.modeBadge = QLabel(" Initial guess ")
        self.modeBadge.setStyleSheet(
            "QLabel { border:1px solid #3b4660; border-radius:5px; padding:2px 6px; color:#aab3c4; }"
        )
        tb.addWidget(self.modeBadge)
        return tb

    # ------------------------------ Tabs --------------------------------------
    @staticmethod
    def _grow_spin(decimals=2, minimum=0.0, maximum=1e9, step=0.1, value=0.0, suffix=""):
        s = QtWidgets.QDoubleSpinBox()
        s.setDecimals(decimals)
        s.setRange(minimum, maximum)
        s.setSingleStep(step)
        s.setValue(value)
        if suffix:
            s.setSuffix(" " + suffix)
        s.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        s.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return s

    @staticmethod
    def _grow_edit(text=""):
        e = QtWidgets.QLineEdit(text)
        e.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return e

    def _build_controller_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.kp = self._grow_spin(3, 1e-4, 1e3, 0.01, 0.30)
        self.ti = self._grow_spin(2, 0.01, 1e6, 0.1, 20.0, "s")
        self.td = self._grow_spin(2, 0.00, 1e6, 0.1, 0.0, "s")
        self.beta = self._grow_spin(2, 0.00, 1.0, 0.01, 1.00)
        self.alpha = self._grow_spin(3, 0.010, 1.0, 0.005, 0.125)

        action = QtWidgets.QComboBox()
        action.addItems(["Reverse", "Direct"])
        action.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        vendor = QtWidgets.QComboBox()
        vendor.addItems(["DeltaV Standard PIDe", "Ideal PID", "Series (ISA)"])
        vendor.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        form.addRow("Vendor form", vendor)
        form.addRow("Action", action)
        form.addRow("Gain Kp", self.kp)
        form.addRow("Ti", self.ti)
        form.addRow("Td", self.td)
        form.addRow("β (setpoint weight)", self.beta)
        form.addRow("α (deriv. filter)", self.alpha)
        return w

    def _build_process_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.tag_pv = self._grow_edit("TCAF")
        self.tag_op = self._grow_edit("PCAF")
        self.tag_sp = self._grow_edit("TCAF.SP")
        self.model_gain = self._grow_spin(3, -1e6, 1e6, 0.01, 1.0)
        self.model_tau = self._grow_spin(2, 0.01, 1e9, 0.1, 120.0, "s")
        self.model_theta = self._grow_spin(2, 0.0, 1e9, 0.1, 5.0, "s")

        form.addRow("PV tag", self.tag_pv)
        form.addRow("OP tag", self.tag_op)
        form.addRow("SP tag", self.tag_sp)
        form.addRow("Model Gain K", self.model_gain)
        form.addRow("Model Tau", self.model_tau)
        form.addRow("Deadtime θ", self.model_theta)
        return w

    def _build_sim_tab(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.spstep = self._grow_spin(2, -1e6, 1e6, 0.1, 5.0)
        self.noise = self._grow_spin(3, 0.0, 10.0, 0.01, 0.10)
        self.speed = QtWidgets.QComboBox()
        self.speed.addItems(["1×", "2×", "5×"])
        self.speed.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.clicked.connect(self._cmd_apply_sp)

        # place apply button on same row (add a small container)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.spstep, 1)
        row.addWidget(apply_btn, 0)

        form.addRow("SP step", self._wrap(row))
        form.addRow("Noise σ", self.noise)
        form.addRow("Speed", self.speed)
        return w

    def _build_tune_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        top = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(top)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.rule = QtWidgets.QComboBox()
        self.rule.addItems(["SIMC", "Lambda/IMC", "Ziegler–Nichols"])
        self.target = self._grow_spin(2, 0.0, 1e6, 1.0, 60.0)
        btn = QtWidgets.QPushButton("Compute")
        btn.clicked.connect(lambda: self.log(f"Compute tuning ({self.rule.currentText()})…"))

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.rule, 1)
        row.addWidget(btn, 0)

        form.addRow("Rule", self._wrap(row))
        form.addRow("Target λ / τc", self.target)
        layout.addWidget(top)

        # Results table (placeholder data)
        self.tbl = QtWidgets.QTableWidget(4, 4)
        self.tbl.setHorizontalHeaderLabels(["Param", "Existing", "Initial", "Final"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        hdr = self.tbl.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        rows = [
            ("Kp", "1", "0.0122", "0.0146"),
            ("Ti", "—", "119.1", "290.3"),
            ("Td", "—", "119.0", "9.65"),
            ("α", "0.125", "0.312", "0.503"),
        ]
        for r, (p, a, b, c) in enumerate(rows):
            for cidx, val in enumerate((p, a, b, c)):
                self.tbl.setItem(r, cidx, QtWidgets.QTableWidgetItem(val))
        layout.addWidget(self.tbl, 1)
        return w

    # helpers
    @staticmethod
    def _wrap(hbox: QtWidgets.QHBoxLayout):
        w = QtWidgets.QWidget()
        w.setLayout(hbox)
        w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return w

    # ------------------------------ Commands -----------------------------------
    def _cmd_apply_sp(self):
        self.sim.set_sp(self.spstep.value())
        self.log(f"Applied SP = {self.sim.get_sp():.2f}")

    def _cmd_run(self):
        self.sim.start()
        self.set_connected(True)
        self.log("Simulation started")

    def _cmd_stop(self):
        self.sim.stop()
        self.set_connected(False)
        self.log("Simulation stopped")

    # ------------------------------ Slots --------------------------------------
    @QtCore.Slot(float, float, float, float)
    def on_tick(self, t, sp, pv, op):
        self.ts.append(t)
        self.sps.append(sp)
        self.pvs.append(pv)
        self.ops.append(op)

        # keep last N seconds for a simple scrolling effect
        N = 150
        self.ts = self.ts[-N:]
        self.sps = self.sps[-N:]
        self.pvs = self.pvs[-N:]
        self.ops = self.ops[-N:]

        self.cur_sp.setData(self.ts, self.sps)
        self.cur_pv.setData(self.ts, self.pvs)
        self.cur_op.setData(self.ts, self.ops)

    # ------------------------------ Utils --------------------------------------
    def log(self, msg: str):
        self.output.appendPlainText(msg)

    def set_connected(self, on: bool):
        self.statusLight.setStyleSheet(
            f"QLabel {{ color:{'#27c93f' if on else '#666'}; font-size:14px; }}"
        )
        self.statusLabel.setText("Connected (sim)" if on else "Disconnected")


# ---------------------------------- Main --------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_fusion(app)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
