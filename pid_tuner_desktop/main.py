# pid_tuner_desktop/main.py
import sys, time, threading, math
from typing import Optional

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction, QPalette, QColor, QFont
from PySide6.QtWidgets import QStyle, QLabel, QDockWidget, QHeaderView
import pyqtgraph as pg


# ----------------------------- Theming ---------------------------------------
def apply_dark_fusion(app: QtWidgets.QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    bg = QColor(22, 26, 34)
    panel = QColor(28, 34, 46)
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
    app.setFont(QFont("Segoe UI", 10))


# --------------------------- Realtime mock engine -----------------------------
class RealtimeSim(QtCore.QObject):
    """
    Toy loop (wire to real pid_tuner later):
      Plant ~ FOPDT'ish: y' = (K*u + d - y)/tau  with optional deadtime approx (ignored here)
      Controller ~ P only in this mock (we still display Kp, Ti, Td in UI)
    Emits: tick(t, sp, pv, op)
    """
    tick = QtCore.Signal(float, float, float, float)

    def __init__(self, period_s: float = 1.0, parent=None):
        super().__init__(parent)
        self._period = period_s
        self._stop = threading.Event()
        self._thr: Optional[threading.Thread] = None
        self._t = 0.0
        self._sp = 5.0
        self._pv = 0.0
        self._op = 0.0

        # providers (bound to UI from MainWindow)
        self.kp_provider = lambda: 0.3
        self.ti_provider = lambda: 20.0   # used as plant tau in mock
        self.noise_provider = lambda: 0.0
        self.model_gain_provider = lambda: 1.0
        self.dist_time_provider = lambda: 9999.0
        self.dist_mag_provider = lambda: 0.0

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

    def _run(self):
        while not self._stop.is_set():
            Kc = float(self.kp_provider())
            tau = max(0.1, float(self.ti_provider()))  # mock: use Ti as tau
            nstd = float(self.noise_provider())
            Kp_model = float(self.model_gain_provider())
            t_dist = float(self.dist_time_provider())
            d_mag = float(self.dist_mag_provider())

            err = self._sp - self._pv
            # controller P on error (mock)
            self._op = max(0.0, min(100.0, Kc * err * 100.0))  # %

            # disturbance as additive bias on plant input after t_dist
            d = d_mag if self._t >= t_dist else 0.0
            # plant: y' = (K*u + d - y) / tau
            u = (self._op / 100.0)
            dy = (Kp_model * u + d - self._pv) / tau

            # integrate + noise
            self._pv += dy * self._period + (nstd * (0.5 - (time.time() % 1)))
            self._t += self._period

            self.tick.emit(self._t, self._sp, self._pv, self._op)
            time.sleep(self._period)


# ------------------------------ Main Window -----------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PID Tuner & Loop Analyzer (Desktop)")
        self.resize(1320, 860)

        # ---- data buffers
        self.ts, self.sps, self.pvs, self.ops = [], [], [], []

        # ---- simulation engine
        self.sim = RealtimeSim(period_s=1.0)
        self.sim.tick.connect(self.on_tick)

        # ---- project browser
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self._populate_tree()

        # ---- tabs
        self.tabs = QtWidgets.QTabWidget()
        self.controllerTab = self._build_controller_tab()
        self.processTab = self._build_process_tab()
        self.simTab = self._build_sim_tab()
        self.tuneTab = self._build_tune_tab()
        self.workflowTab = self._build_workflow_tab()  # NEW
        self.tabs.addTab(self.controllerTab, "Controller")
        self.tabs.addTab(self.processTab, "Process")
        self.tabs.addTab(self.simTab, "Simulation")
        self.tabs.addTab(self.tuneTab, "Tuning")
        self.tabs.addTab(self.workflowTab, "Workflow  (ID → Tune → Sim)")  # NEW

        # ---- plot
        self._build_plot()

        # ---- output console
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("QPlainTextEdit { padding:6px; }")

        # ---- docks + central
        self._setup_docks_and_central()

        # ---- status bar
        self._setup_statusbar()
        self.set_connected(False)

        # ---- toolbar
        self.addToolBar(self._build_toolbar())

        # ---- dock behavior
        self.setDockOptions(
            QtWidgets.QMainWindow.AllowNestedDocks
            | QtWidgets.QMainWindow.AllowTabbedDocks
            | QtWidgets.QMainWindow.AnimatedDocks
        )

        # bind providers
        self.sim.kp_provider = lambda: self.kp.value()
        self.sim.ti_provider = lambda: max(0.1, self.ti.value())
        self.sim.noise_provider = lambda: self.noise.value()
        self.sim.model_gain_provider = lambda: self.model_gain.value()
        self.sim.dist_time_provider = lambda: self.wf_dist_time.value()
        self.sim.dist_mag_provider = lambda: self.wf_dist_mag.value()

    # ----------------------------- UI builders --------------------------------
    def _populate_tree(self):
        root = QtWidgets.QTreeWidgetItem(["AptiTuneDemo"])
        signals = QtWidgets.QTreeWidgetItem(["Signals"])
        for name in ["TCAF", "PCAF", "TCBE", "TCCF", "TCCD"]:
            signals.addChild(QtWidgets.QTreeWidgetItem([name]))
        cases = QtWidgets.QTreeWidgetItem(["Loop Tuning Cases"])
        cases.addChild(QtWidgets.QTreeWidgetItem(["tuning case"]))
        root.addChild(signals); root.addChild(cases)
        self.tree.addTopLevelItem(root); self.tree.expandAll()
        self.tree.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def _build_plot(self):
        self.plot = pg.PlotWidget()
        self.plot.setBackground(QColor(12, 17, 26))
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "PV / SP")
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=0.25)
        for ax in ("bottom", "left"):
            self.plot.getAxis(ax).setPen(QColor(90, 100, 120))
        self.plot.showAxis("right")
        self.plot.getAxis("right").setPen(QColor(90, 100, 120))
        self.plot.getAxis("right").setLabel("OP (%)")
        self.plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.cur_sp = self.plot.plot([], [], pen=pg.mkPen(color=(110, 166, 255), style=QtCore.Qt.DashLine, width=2))
        self.cur_pv = self.plot.plot([], [], pen=pg.mkPen(color=(63, 185, 80), width=2))

        self.ax2 = pg.ViewBox()
        self.plot.scene().addItem(self.ax2)
        self.plot.getAxis("right").linkToView(self.ax2)
        self.ax2.setXLink(self.plot)
        self.cur_op = pg.PlotCurveItem(pen=pg.mkPen(color=(255, 189, 46), width=2))
        self.ax2.addItem(self.cur_op)

        def _sync_views():
            self.ax2.setGeometry(self.plot.getViewBox().sceneBoundingRect())
            self.ax2.linkedViewChanged(self.plot.getViewBox(), self.ax2.XAxis)
        self.plot.getViewBox().sigResized.connect(_sync_views)
        _sync_views()

    def _setup_docks_and_central(self):
        dock_tree = QDockWidget("Project Browser", self)
        dock_tree.setObjectName("dockProject")
        dock_tree.setWidget(self.tree)
        dock_tree.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_tree)

        dock_console = QDockWidget("Output", self)
        dock_console.setObjectName("dockConsole")
        dock_console.setWidget(self.output)
        dock_console.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock_console.setMinimumHeight(120)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_console)

        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)
        v.addWidget(self.tabs)
        v.addWidget(self.plot, 1)
        v.setStretch(0, 0)
        v.setStretch(1, 1)
        self.setCentralWidget(central)

    def _setup_statusbar(self):
        sb = QtWidgets.QStatusBar(self)
        self.setStatusBar(sb)
        self.statusLight = QLabel("●")
        self.statusLight.setStyleSheet("QLabel { color:#666; font-size:14px; }")
        self.statusLabel = QLabel("Disconnected")
        sb.addWidget(self.statusLight); sb.addWidget(self.statusLabel)
        self.fpsLabel = QLabel("FPS: 1")
        sb.addPermanentWidget(self.fpsLabel)

    def _build_toolbar(self):
        tb = QtWidgets.QToolBar("Main"); tb.setMovable(False); tb.setIconSize(QtCore.QSize(18, 18))

        def add(text, icon, slot, tip=None, shortcut=None):
            act = QAction(self.style().standardIcon(icon), text, self)
            if shortcut: act.setShortcut(shortcut)
            if tip: act.setStatusTip(tip); act.setToolTip(tip)
            act.triggered.connect(slot); tb.addAction(act); return act

        add("New Case", QStyle.SP_FileIcon, lambda: self.log("New case created"), "Create a new tuning case", "Ctrl+N")
        add("Step Test", QStyle.SP_BrowserReload, lambda: self.log("Step Test started"), "Detect steps", "Ctrl+T")
        add("Identify", QStyle.SP_DirOpenIcon, lambda: self.log("Identification started"), "Fit model", "Ctrl+I")
        add("Tune", QStyle.SP_CommandLink, lambda: self.log("Tuning (SIMC)…"), "Compute PID", "Ctrl+U")
        tb.addSeparator()
        add("Run", QStyle.SP_MediaPlay, self._cmd_run, "Run realtime simulation", "Ctrl+R")
        add("Stop", QStyle.SP_MediaStop, self._cmd_stop, "Stop simulation", "Ctrl+S")
        tb.addSeparator()
        add("Save Initial", QStyle.SP_DialogSaveButton, lambda: self.log("Saved Initial"), "Save initial")
        add("Save Current", QStyle.SP_DialogApplyButton, lambda: self.log("Saved Current"), "Save current")
        tb.addSeparator()
        spacer = QtWidgets.QWidget(); spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self.modeBadge = QLabel(" Initial guess ")
        self.modeBadge.setStyleSheet("QLabel { border:1px solid #3b4660; border-radius:5px; padding:2px 6px; color:#aab3c4; }")
        tb.addWidget(self.modeBadge)
        return tb

    # ------------------------------ Tabs --------------------------------------
    @staticmethod
    def _grow_spin(decimals=2, minimum=0.0, maximum=1e9, step=0.1, value=0.0, suffix=""):
        s = QtWidgets.QDoubleSpinBox()
        s.setDecimals(decimals); s.setRange(minimum, maximum); s.setSingleStep(step); s.setValue(value)
        if suffix: s.setSuffix(" " + suffix)
        s.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        s.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return s

    @staticmethod
    def _grow_edit(text=""):
        e = QtWidgets.QLineEdit(text)
        e.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return e

    @staticmethod
    def _wrap(hbox: QtWidgets.QHBoxLayout):
        w = QtWidgets.QWidget(); w.setLayout(hbox)
        w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred); return w

    def _build_controller_tab(self):
        w = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(w)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.kp = self._grow_spin(3, 1e-4, 1e3, 0.01, 0.30)
        self.ti = self._grow_spin(2, 0.01, 1e6, 0.1, 20.0, "s")
        self.td = self._grow_spin(2, 0.00, 1e6, 0.1, 0.0, "s")
        self.beta = self._grow_spin(2, 0.00, 1.0, 0.01, 1.00)
        self.alpha = self._grow_spin(3, 0.010, 1.0, 0.005, 0.125)

        action = QtWidgets.QComboBox(); action.addItems(["Reverse", "Direct"])
        vendor = QtWidgets.QComboBox(); vendor.addItems(["DeltaV Standard PIDe", "Ideal PID", "Series (ISA)"])
        for c in (action, vendor): c.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        form.addRow("Vendor form", vendor)
        form.addRow("Action", action)
        form.addRow("Gain Kp", self.kp)
        form.addRow("Ti", self.ti)
        form.addRow("Td", self.td)
        form.addRow("β (setpoint weight)", self.beta)
        form.addRow("α (deriv. filter)", self.alpha)
        return w

    def _build_process_tab(self):
        w = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(w)
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
        form.addRow("Model Tau τ", self.model_tau)
        form.addRow("Deadtime θ", self.model_theta)
        return w

    def _build_sim_tab(self):
        w = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(w)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.spstep = self._grow_spin(2, -1e6, 1e6, 0.1, 5.0)
        self.noise = self._grow_spin(3, 0.0, 10.0, 0.01, 0.10)
        self.speed = QtWidgets.QComboBox(); self.speed.addItems(["1×", "2×", "5×"])
        self.speed.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        apply_btn = QtWidgets.QPushButton("Apply"); apply_btn.clicked.connect(self._cmd_apply_sp)

        row = QtWidgets.QHBoxLayout(); row.addWidget(self.spstep, 1); row.addWidget(apply_btn, 0)
        form.addRow("SP step", self._wrap(row))
        form.addRow("Noise σ", self.noise)
        form.addRow("Speed", self.speed)
        return w

    def _build_tune_tab(self):
        w = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(w); layout.setContentsMargins(0,0,0,0)
        top = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(top)
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.rule = QtWidgets.QComboBox(); self.rule.addItems(["SIMC", "Lambda/IMC", "Ziegler–Nichols"])
        self.target = self._grow_spin(2, 0.0, 1e6, 1.0, 60.0)  # λ or τc
        btn = QtWidgets.QPushButton("Compute")
        btn.clicked.connect(self._cmd_compute_tuning)

        row = QtWidgets.QHBoxLayout(); row.addWidget(self.rule, 1); row.addWidget(btn, 0)
        form.addRow("Rule", self._wrap(row))
        form.addRow("Target λ / τc", self.target)
        layout.addWidget(top)

        self.tbl = QtWidgets.QTableWidget(4, 4)
        self.tbl.setHorizontalHeaderLabels(["Param", "Existing", "Initial", "Final"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        hdr = self.tbl.horizontalHeader(); hdr.setStretchLastSection(True); hdr.setSectionResizeMode(QHeaderView.Stretch)

        for r, vals in enumerate([("Kp", "", "", ""), ("Ti", "", "", ""), ("Td", "", "", ""), ("α", "", "", "")]):
            for c, val in enumerate(vals): self.tbl.setItem(r, c, QtWidgets.QTableWidgetItem(val))
        layout.addWidget(self.tbl, 1)
        return w

    # -------------- NEW: Workflow (Identify → Tune → Simulate) -----------------
    def _build_workflow_tab(self):
        w = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(w); outer.setContentsMargins(0,0,0,0)

        # Identify
        grp_id = QtWidgets.QGroupBox("1) Identify Process")
        f1 = QtWidgets.QFormLayout(grp_id)
        self.wf_model = QtWidgets.QComboBox(); self.wf_model.addItems(["FOPDT", "SOPDT (coming soon)", "Integrator (coming soon)"])
        self.wf_K = self._grow_spin(3, -1e6, 1e6, 0.01, 1.0)
        self.wf_tau = self._grow_spin(2, 0.01, 1e9, 0.1, 80.0, "s")
        self.wf_theta = self._grow_spin(2, 0.0, 1e9, 0.1, 5.0, "s")
        btn_id = QtWidgets.QPushButton("Identify")
        btn_id.clicked.connect(self._cmd_identify_mock)
        row = QtWidgets.QHBoxLayout(); row.addWidget(self.wf_model, 1); row.addWidget(btn_id, 0)
        f1.addRow("Model", self._wrap(row))
        f1.addRow("Gain K", self.wf_K)
        f1.addRow("Tau τ", self.wf_tau)
        f1.addRow("Deadtime θ", self.wf_theta)

        # Tune
        grp_tune = QtWidgets.QGroupBox("2) Compute PID Tuning")
        f2 = QtWidgets.QFormLayout(grp_tune)
        self.wf_rule = QtWidgets.QComboBox(); self.wf_rule.addItems(["SIMC", "Lambda/IMC", "Ziegler–Nichols (reaction curve, mock)"])
        self.wf_target = self._grow_spin(2, 0.0, 1e6, 1.0, 60.0)
        self.wf_out_kp = self._grow_spin(4, 0, 1e6, 0.001, 0.3); self.wf_out_kp.setReadOnly(True)
        self.wf_out_ti = self._grow_spin(3, 0, 1e9, 0.1, 20.0, "s"); self.wf_out_ti.setReadOnly(True)
        self.wf_out_td = self._grow_spin(3, 0, 1e9, 0.1, 0.0, "s"); self.wf_out_td.setReadOnly(True)
        btn_tune = QtWidgets.QPushButton("Compute Tuning")
        btn_apply = QtWidgets.QPushButton("Apply to Controller")
        btn_tune.clicked.connect(self._cmd_workflow_compute)
        btn_apply.clicked.connect(self._cmd_workflow_apply)
        row2 = QtWidgets.QHBoxLayout(); row2.addWidget(self.wf_rule, 1); row2.addWidget(btn_tune, 0); row2.addWidget(btn_apply, 0)
        f2.addRow("Rule", self._wrap(row2))
        f2.addRow("Target λ / τc", self.wf_target)
        f2.addRow("Kp", self.wf_out_kp)
        f2.addRow("Ti", self.wf_out_ti)
        f2.addRow("Td", self.wf_out_td)

        # Sim
        grp_sim = QtWidgets.QGroupBox("3) Simulate with Options")
        f3 = QtWidgets.QFormLayout(grp_sim)
        self.wf_sp = self._grow_spin(2, -1e6, 1e6, 0.1, 5.0)
        self.wf_noise = self._grow_spin(3, 0.0, 10.0, 0.01, 0.10)
        self.wf_dist_time = self._grow_spin(2, 0.0, 1e9, 1.0, 9999.0, "s")
        self.wf_dist_mag = self._grow_spin(3, -10.0, 10.0, 0.1, 0.0)
        btn_run = QtWidgets.QPushButton("Run Scenario")
        btn_run.clicked.connect(self._cmd_workflow_run)
        f3.addRow("SP step", self.wf_sp)
        f3.addRow("Noise σ", self.wf_noise)
        f3.addRow("Disturbance time", self.wf_dist_time)
        f3.addRow("Disturbance magnitude", self.wf_dist_mag)
        f3.addRow("", btn_run)

        # stack
        outer.addWidget(grp_id)
        outer.addWidget(grp_tune)
        outer.addWidget(grp_sim)
        outer.addStretch(1)
        return w

    # ------------------------------ Commands -----------------------------------
    def _cmd_apply_sp(self):
        self.sim.set_sp(self.spstep.value())
        self.log(f"Applied SP = {self.sim.get_sp():.2f}")

    def _cmd_run(self):
        self.sim.start(); self.set_connected(True); self.log("Simulation started")

    def _cmd_stop(self):
        self.sim.stop(); self.set_connected(False); self.log("Simulation stopped")

    # Tuning tab compute
    def _cmd_compute_tuning(self):
        K = self.model_gain.value(); tau = self.model_tau.value(); theta = self.model_theta.value()
        rule = self.rule.currentText(); target = max(0.01, self.target.value())
        kp, ti, td = self._compute_pid_from_model(rule, K, tau, theta, target)
        self._write_tuning_table(kp, ti, td)
        self.log(f"Tuning ({rule}) → Kp={kp:.4g}, Ti={ti:.4g}s, Td={td:.4g}s")

    # Workflow: Identify → Tune
    def _cmd_identify_mock(self):
        # In the real app, call step detection + model fit then set wf_K/τ/θ from results
        self.log("Identify (mock): using entered K, τ, θ as identified values.")
        # push identified to Process tab too (nice UX)
        self.model_gain.setValue(self.wf_K.value())
        self.model_tau.setValue(self.wf_tau.value())
        self.model_theta.setValue(self.wf_theta.value())

    def _cmd_workflow_compute(self):
        K = self.wf_K.value(); tau = self.wf_tau.value(); theta = self.wf_theta.value()
        rule = self.wf_rule.currentText(); target = max(0.01, self.wf_target.value())
        kp, ti, td = self._compute_pid_from_model(rule, K, tau, theta, target)
        self.wf_out_kp.setValue(kp); self.wf_out_ti.setValue(ti); self.wf_out_td.setValue(td)
        self.log(f"Workflow tuning ({rule}) → Kp={kp:.4g}, Ti={ti:.4g}s, Td={td:.4g}s")

    def _cmd_workflow_apply(self):
        self.kp.setValue(self.wf_out_kp.value())
        self.ti.setValue(self.wf_out_ti.value())
        self.td.setValue(self.wf_out_td.value())
        self.log("Applied workflow PID parameters to Controller tab.")

    def _cmd_workflow_run(self):
        # apply scenario knobs to the main sim providers
        self.sim.set_sp(self.wf_sp.value())
        self.noise.setValue(self.wf_noise.value())
        # disturbance settings are already read via providers
        self._cmd_run()

    # --------------------------- Math helpers ----------------------------------
    def _compute_pid_from_model(self, rule: str, K: float, tau: float, theta: float, target: float):
        """
        Simple closed-form mock of common rules (FOPDT):
          SIMC (as per your notes): Kp = τ / (K (τc + θ)), Ti = min(τ, 4(τc + θ)), Td ~ θ/ (for PI set 0)
          Lambda/IMC (PI): Kp = τ / (K (λ + θ)), Ti = τ
          ZN (reaction-curve, rough): Kp = 1.2 * τ / (K θ), Ti = 2 θ, Td = 0.5 θ
        """
        tau = max(1e-6, tau); K = K if abs(K) > 1e-9 else 1e-9
        if "SIMC" in rule:
            tau_c = target
            kp = tau / (K * (tau_c + theta))
            ti = min(tau, 4.0 * (tau_c + theta))
            td = max(0.0, theta / 2.0)  # mild D for demo
        elif "Lambda" in rule or "IMC" in rule:
            lam = target
            kp = tau / (K * (lam + theta))
            ti = tau
            td = 0.0
        else:  # ZN reaction-curve approx
            kp = 1.2 * tau / (K * max(1e-6, theta))
            ti = 2.0 * max(1e-6, theta)
            td = 0.5 * max(0.0, theta)
        return float(kp), float(ti), float(td)

    def _write_tuning_table(self, kp: float, ti: float, td: float):
        rows = [("Kp", f"{self.kp.value():.4g}", "", f"{kp:.4g}"),
                ("Ti", "", "", f"{ti:.4g}"),
                ("Td", "", "", f"{td:.4g}"),
                ("α", f"{self.alpha.value():.4g}", "", f"{self.alpha.value():.4g}")]
        self.tbl.setRowCount(len(rows))
        for r, (p, a, b, c) in enumerate(rows):
            for cidx, val in enumerate((p, a, b, c)):
                self.tbl.setItem(r, cidx, QtWidgets.QTableWidgetItem(val))

    # ------------------------------ Slots --------------------------------------
    @QtCore.Slot(float, float, float, float)
    def on_tick(self, t, sp, pv, op):
        self.ts.append(t); self.sps.append(sp); self.pvs.append(pv); self.ops.append(op)
        N = 150
        self.ts, self.sps, self.pvs, self.ops = self.ts[-N:], self.sps[-N:], self.pvs[-N:], self.ops[-N:]
        self.cur_sp.setData(self.ts, self.sps)
        self.cur_pv.setData(self.ts, self.pvs)
        self.cur_op.setData(self.ts, self.ops)

    # ------------------------------ Utils --------------------------------------
    def log(self, msg: str): self.output.appendPlainText(msg)
    def set_connected(self, on: bool):
        self.statusLight.setStyleSheet(f"QLabel {{ color:{'#27c93f' if on else '#666'}; font-size:14px; }}")
        self.statusLabel.setText("Connected (sim)" if on else "Disconnected")


# ---------------------------------- Main --------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_fusion(app)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
