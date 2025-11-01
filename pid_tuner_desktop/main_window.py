from __future__ import annotations
import os
import time
from typing import Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

# Views
from views.project_browser import ProjectBrowser
from views.plot_panel import PlotPanel
from views.console_panel import ConsolePanel
from views.controller_panel import ControllerPanel
from views.process_panel import ProcessPanel
from views.simulation_panel import SimulationPanel
from views.tuning_panel import TuningPanel

# ViewModels
from viewmodels.app_state import AppState
from viewmodels.controller_vm import ControllerVM
from viewmodels.process_vm import ProcessVM
from viewmodels.simulation_vm import SimulationVM
from viewmodels.tuning_vm import TuningVM

# Services
from services.simulation_service import ProcessSpec, PIDSpec
from services.tuning_service import simc, lambda_imc, zn_reaction_curve, TuningResult
from services.identification_service import detect_steps, fit_fopdt, fit_sopdt_from_fopdt, fit_integrating
from services.storage_service import StorageService, Sample
from services.opc_ua_service import OpcUaService
from services.opc_da_service import OpcDaService

# Adapters
from adapters.core_models import ui_to_core_process, is_valid_process
from adapters.core_tuning import GenericPID, to_vendor_form


def _icon(name: str) -> QtGui.QIcon:
    # Try :/icons/name first then filesystem fallback
    res = QtGui.QIcon(f":/icons/{name}")
    if not res.isNull():
        return res
    fs = os.path.join(os.path.dirname(__file__), "qrc", "icons", name)
    return QtGui.QIcon(fs) if os.path.exists(fs) else QtGui.QIcon()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PID Tuner & Loop Analyzer (Desktop)")
        self.resize(1400, 900)

        # ---------- State / Services ----------
        self.state = AppState()

        # storage (create runtime dirs)
        runtime_dir = os.path.join(os.path.dirname(__file__), "runtime")
        os.makedirs(os.path.join(runtime_dir, "sessions"), exist_ok=True)
        db_path = os.path.join(runtime_dir, "sessions", "pid_tuner.sqlite")
        self.storage = StorageService(db_path)

        # opc bridges
        self.ua = OpcUaService()
        self.da = OpcDaService()

        # ---------- ViewModels ----------
        self.ctrl_vm = ControllerVM()
        self.proc_vm = ProcessVM()
        self.sim_vm = SimulationVM(period_s=1.0)
        self.tune_vm = TuningVM()
        self.tune_vm.resultChanged.connect(
            lambda Kp, Ti, Td: self.console.log(f"Tuned → Kp={Kp:.6g}, Ti={Ti:.6g}, Td={Td:.6g}")
        )

        # Apply controller VM to the running realtime simulator when changed
        self.ctrl_vm.paramChanged.connect(self._apply_vm_to_sim)

        # ---------- UI Layout ----------
        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        # Connect VM ticks to plot
        self.sim_vm.tick.connect(self._on_tick_from_vm)

        # Connect ProjectBrowser actions
        self.browser.request_opc_ua_discover.connect(self._on_ua_discover)
        self.browser.request_opc_ua_connect_browse.connect(self._on_ua_connect_browse)
        self.browser.request_opc_da_browse.connect(self._on_da_browse)
        self.browser.subscribe_live_requested.connect(self._on_subscribe_live_tag)

        # Start simulator idle
        self.console.log("Application ready.")

    # ================= UI Construction =================

    def _build_menus(self):
        mb = self.menuBar()

        # File
        m_file = mb.addMenu("&File")
        act_new = QtGui.QAction("New Session", self, triggered=self._on_new_session)
        act_open = QtGui.QAction("Open DB Folder", self, triggered=self._on_open_db_folder)
        act_export = QtGui.QAction("Export Current Controller (DeltaV PIDe JSON)", self, triggered=self._on_export_vendor)
        act_quit = QtGui.QAction("Quit", self, triggered=self.close)
        m_file.addActions([act_new, act_open, act_export])
        m_file.addSeparator()
        m_file.addAction(act_quit)

        # View
        m_view = mb.addMenu("&View")
        self._act_view_left = QtGui.QAction("Show Project Browser", self, checkable=True, checked=True)
        self._act_view_bottom = QtGui.QAction("Show Console", self, checkable=True, checked=True)
        self._act_view_left.triggered.connect(lambda on: self.dock_left.setVisible(on))
        self._act_view_bottom.triggered.connect(lambda on: self.dock_bottom.setVisible(on))
        m_view.addActions([self._act_view_left, self._act_view_bottom])

        # Tools
        m_tools = mb.addMenu("&Tools")
        m_tools.addAction(QtGui.QAction("Detect Steps (current plot)", self, triggered=self._on_detect_steps))
        m_tools.addAction(QtGui.QAction("Identify FOPDT", self, triggered=self._on_identify_fopdt))
        m_tools.addAction(QtGui.QAction("Tune (current rule)", self, triggered=self._on_tune))

        # Help
        m_help = mb.addMenu("&Help")
        m_help.addAction(QtGui.QAction("About", self, triggered=self._on_about))

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setIconSize(QtCore.QSize(18, 18))
        tb.setMovable(False)

        self._act_run = QtGui.QAction(_icon("play.svg"), "Run", self, triggered=self._on_run)
        self._act_stop = QtGui.QAction(_icon("stop.svg"), "Stop", self, triggered=self._on_stop)
        self._act_tune = QtGui.QAction(_icon("tune.svg"), "Tune", self, triggered=self._on_tune)
        self._act_db = QtGui.QAction(_icon("database.svg"), "Start Session", self, triggered=self._on_new_session)

        tb.addAction(self._act_run)
        tb.addAction(self._act_stop)
        tb.addSeparator()
        tb.addAction(self._act_tune)
        tb.addSeparator()
        tb.addAction(self._act_db)

    def _build_central(self):
        # Left dock: project browser
        self.browser = ProjectBrowser(self.state)
        self.dock_left = QtWidgets.QDockWidget("Project", self)
        self.dock_left.setWidget(self.browser)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock_left)
        self.dock_left.setMinimumWidth(260)

        # Bottom dock: console
        self.console = ConsolePanel()
        self.dock_bottom = QtWidgets.QDockWidget("Console", self)
        self.dock_bottom.setWidget(self.console)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock_bottom)
        self.dock_bottom.setMinimumHeight(140)

        # Center: tabs (Controller, Process, Simulation, Tuning) above Plot
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(ControllerPanel(self.ctrl_vm), "Controller")
        self.tabs.addTab(ProcessPanel(self.proc_vm, self.state), "Process")
        self.tabs.addTab(SimulationPanel(self.sim_vm), "Simulation")
        self.tabs.addTab(TuningPanel(self.tune_vm, self.proc_vm, self.ctrl_vm), "Tuning")

        self.plot = PlotPanel()

        center_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        center_split.addWidget(self.tabs)
        center_split.addWidget(self.plot)
        center_split.setSizes([350, 550])

        self.setCentralWidget(center_split)

        # Wire SimulationVM updates to PlotPanel
        self.sim_vm.historyCleared.connect(self.plot.clear)

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.showMessage("Ready")
        self._lbl_state = QtWidgets.QLabel("Sim: Stopped")
        self._lbl_tags = QtWidgets.QLabel("SP/PV/OP: (none)")
        sb.addPermanentWidget(self._lbl_state)
        sb.addPermanentWidget(self._lbl_tags)

        # track running state
        self.sim_vm.runningChanged.connect(lambda r: self._lbl_state.setText("Sim: Running" if r else "Sim: Stopped"))
        # track tag map
        self.state.tagMapChanged.connect(lambda m: self._lbl_tags.setText(f"SP/PV/OP: {m.get('SP','-')}/{m.get('PV','-')}/{m.get('OP','-')}"))

    # ================= Toolbar/Menu Handlers =================

    def _on_run(self):
        self.sim_vm.start()
        self.console.log("Realtime simulation started.")

    def _on_stop(self):
        self.sim_vm.stop()
        self.console.log("Realtime simulation stopped.")

    def _on_tune(self):
        # Compute per rule and apply back to controller and simulator
        res = self.tune_vm.apply_to_controller(self.ctrl_vm, self.proc_vm)
        self._apply_vm_to_sim()
        self.console.log(f"Applied tuned params to controller: Kp={res.Kp:.6g}, Ti={res.Ti:.6g}, Td={res.Td:.6g}")

    def _on_new_session(self):
        t0 = time.time()
        sid = self.storage.start_session(t0, notes="GUI session")
        self._current_session_id = sid
        self.statusBar().showMessage(f"Session {sid} started at {t0:.0f}")
        self.console.log(f"Session started (id={sid}).")

    def _on_open_db_folder(self):
        path = os.path.join(os.path.dirname(__file__), "runtime", "sessions")
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def _on_export_vendor(self):
        pid = GenericPID(
            Kp=self.ctrl_vm.Kp(), Ti=self.ctrl_vm.Ti(), Td=self.ctrl_vm.Td(),
            beta=self.ctrl_vm.beta(), alpha=self.ctrl_vm.alpha(),
            mode=self.ctrl_vm.mode(), d_on=self.ctrl_vm.derivative_on()
        )
        data = to_vendor_form("Emerson DeltaV PIDe", pid)
        text = "{\n" + ",\n".join([f'  "{k}": {float(v):g}' for k, v in data.items()]) + "\n}"
        cb = QtWidgets.QApplication.clipboard()
        cb.setText(text)
        self.console.log("Copied DeltaV PIDe JSON to clipboard.")

    def _on_detect_steps(self):
        ts, sps, pvs, ops = self.sim_vm.history()
        if not ts:
            self.console.log("No data available to detect steps.")
            return
        steps = detect_steps(ts, ops, min_du=1.0, min_dt=5.0)
        if not steps:
            self.console.log("No steps detected.")
            return
        self.console.log(f"Detected {len(steps)} step(s). First at t={steps[0].t0:.1f}s, ΔOP={steps[0].du:.3g}.")

    def _on_identify_fopdt(self):
        ts, sps, pvs, ops = self.sim_vm.history()
        if not ts:
            self.console.log("No data to identify.")
            return
        steps = detect_steps(ts, ops, min_du=1.0, min_dt=5.0)
        if not steps:
            self.console.log("No steps detected for identification.")
            return
        fr = fit_fopdt(ts, pvs, ops, steps[0])
        self.console.log(f"FOPDT fit: K={fr.params['K']:.6g}, tau={fr.params['tau']:.6g}, theta={fr.params['theta']:.6g}, r2={fr.stats['r2']:.3f}")
        # Push into ProcessVM
        self.proc_vm.set_fopdt(fr.params["K"], fr.params["tau"], fr.params["theta"])

    def _on_about(self):
        QtWidgets.QMessageBox.information(
            self, "About PID Tuner",
            "PID Tuner & Loop Analyzer (Desktop)\n\n"
            "Realtime loop simulation, identification, and tuning.\n"
            "© PIDLab"
        )

    # ================= OPC UA/DA Integration =================

    def _on_ua_discover(self):
        eps = self.ua.discover_local()
        if not eps:
            self.console.log("No OPC UA servers discovered.")
            return
        self.console.log("OPC UA discovered:\n  " + "\n  ".join(eps))

    def _on_ua_connect_browse(self, endpoint: str):
        names = self.ua.browse_root(endpoint)
        if not names:
            self.console.log(f"Browse failed: {endpoint}")
        else:
            self.console.log(f"OPC UA [{endpoint}] root children:\n  " + "\n  ".join(map(str, names)))

    def _on_da_browse(self, host: str):
        servers = self.da.list_servers(host)
        self.console.log(f"OPC DA servers on '{host or '(local)'}':\n  " + "\n  ".join(servers))

    def _on_subscribe_live_tag(self, tag: str):
        # Try UA sim tags first; fallback to DA sim items
        if tag.startswith("ns="):
            self.ua.subscribe(
                "opc.tcp://localhost:4840",
                [tag],
                callback=lambda nid, val, ts: self._on_live_sample(tag=nid, value=val, ts=ts),
                period_s=1.0,
            )
            self.console.log(f"Subscribed UA: {tag}")
        else:
            self.da.subscribe(
                "(local)",
                "Matrikon.OPC.Simulation.1",
                [tag],
                callback=lambda nid, val, ts: self._on_live_sample(tag=nid, value=val, ts=ts),
                period_s=1.0,
            )
            self.console.log(f"Subscribed DA: {tag}")

    def _on_live_sample(self, tag: str, value: float, ts: float):
        # For demonstration: if the tag matches known roles, update AppState and Plot
        m = self.state.tags()
        if tag == m.get("SP"):
            # Only update SP value shown in plot; NOT forcing simulator SP
            t = self._elapsed_sim_time()
            self.plot.append(t, float(value), float(value), 0.0)  # mirror to visualize quickly
        elif tag == m.get("PV"):
            t = self._elapsed_sim_time()
            self.plot.append(t, 0.0, float(value), 0.0)
        elif tag == m.get("OP"):
            t = self._elapsed_sim_time()
            self.plot.append(t, 0.0, 0.0, float(value))
        else:
            # Unknown tag; just log
            self.console.log(f"{tag} = {float(value):.6g}")

        # Store in DB if session active
        sid = getattr(self, "_current_session_id", None)
        if sid is not None:
            try:
                self.storage.insert_samples(sid, [Sample(ts=ts, tag=tag, value=float(value))])
            except Exception:
                pass

    def _elapsed_sim_time(self) -> float:
        # derive from sim history to keep a monotonic time base for plotting
        ts, *_ = self.sim_vm.history()
        return ts[-1] if ts else 0.0

    # ================= VM / SIM Wiring =================

    def _apply_vm_to_sim(self, *args):
        # Push ControllerVM → underlying simulator PIDSpec (accessing internal _sim attribute)
        try:
            sim = self.sim_vm._sim  # type: ignore[attr-defined]
            sim.pid = PIDSpec(
                Kp=self.ctrl_vm.Kp(),
                Ti=self.ctrl_vm.Ti(),
                Td=self.ctrl_vm.Td(),
                beta=self.ctrl_vm.beta(),
                alpha=self.ctrl_vm.alpha(),
                mode=self.ctrl_vm.mode(),
                d_on=self.ctrl_vm.derivative_on(),
                u_min=0.0, u_max=100.0, bias=0.0
            )
        except Exception:
            pass

        # Push ProcessVM → simulator ProcessSpec
        try:
            p = self.proc_vm.get_params()
            m = self.proc_vm.model()
            payload = ui_to_core_process(m, p)
            if is_valid_process(payload):
                sim = self.sim_vm._sim  # type: ignore[attr-defined]
                if payload["type"] == "FOPDT":
                    sim.proc = ProcessSpec(type="FOPDT", K=payload["K"], tau=payload["tau"], theta=payload["theta"])
                elif payload["type"] == "SOPDT":
                    sim.proc = ProcessSpec(type="SOPDT", K=payload["K"], tau1=payload["tau1"], tau2=payload["tau2"], theta=payload["theta"])
                else:
                    sim.proc = ProcessSpec(type="Integrating", Ki=payload["Ki"], theta=payload["theta"])
        except Exception:
            pass

    @QtCore.Slot(float, float, float, float)
    def _on_tick_from_vm(self, t: float, sp: float, pv: float, op: float):
        self.plot.append(t, sp, pv, op)
        # Log every 10s
        if int(t) % 10 == 0:
            self.console.log(f"t={t:6.1f}  SP={sp:8.3f}  PV={pv:8.3f}  OP={op:8.3f}%")
        # Store quickly if session running
        sid = getattr(self, "_current_session_id", None)
        if sid is not None and (int(t) % 1 == 0):
            try:
                self.storage.insert_samples(sid, [
                    Sample(ts=t, tag=self.state.tags().get("SP", "SP"), value=float(sp)),
                    Sample(ts=t, tag=self.state.tags().get("PV", "PV"), value=float(pv)),
                    Sample(ts=t, tag=self.state.tags().get("OP", "OP"), value=float(op)),
                ])
            except Exception:
                pass
