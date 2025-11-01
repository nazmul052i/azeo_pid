from __future__ import annotations
from PySide6 import QtCore, QtWidgets
from viewmodels.tuning_vm import TuningVM
from viewmodels.process_vm import ProcessVM
from viewmodels.controller_vm import ControllerVM
from widgets.bounds_table import BoundsTable
from widgets.case_table import CaseTable


class TuningPanel(QtWidgets.QWidget):
    """
    Tuning UI:
      - Rule dropdown (SIMC, Lambda, ZN)
      - Parameter for SIMC (τ_c) or Lambda rule (λ)
      - Bounds editor (Gain/Ti/Td)
      - Optimize checkboxes via CaseTable
      - Compute + Apply buttons
      - Result display
    """

    def __init__(self, vm: TuningVM, proc_vm: ProcessVM, ctrl_vm: ControllerVM, parent=None):
        super().__init__(parent)
        self.vm = vm
        self.proc_vm = proc_vm
        self.ctrl_vm = ctrl_vm

        # --- rule chooser
        self.rule = QtWidgets.QComboBox()
        self.rule.addItems(["SIMC", "Lambda", "ZN"])

        # --- stacked parameter (τc vs λ)
        self.stack = QtWidgets.QStackedWidget()
        self.page_simc = self._param_row("Target τc (s):", default=self.vm.get_tauc(), setter=self.vm.set_tauc)
        self.page_lambda = self._param_row("λ (s):", default=self.vm.get_lambda(), setter=self.vm.set_lambda)
        self.page_zn = QtWidgets.QWidget()  # no parameter
        self.stack.addWidget(self.page_simc)
        self.stack.addWidget(self.page_lambda)
        self.stack.addWidget(self.page_zn)

        # --- bounds + optimize tables
        self.bounds = BoundsTable()
        self.bounds.set_parameters(["Gain", "Ti", "Td"], self.vm.bounds())
        self.bounds.boundsChanged.connect(self.vm.set_bounds)

        self.case = CaseTable()
        # seed with a typical case row set
        rows = [
            ("Gain", True, *self.vm.bounds()["Gain"], 1.0, 0.3, 0.3),
            ("Ti",   True, *self.vm.bounds()["Ti"],   0.0, 20.0, 20.0),
            ("Td",   True, *self.vm.bounds()["Td"],   0.0, 0.0,  0.0),
        ]
        self.case.set_rows(rows)
        self.case.tableChanged.connect(self._on_case_changed)

        # --- buttons + results
        self.btn_compute = QtWidgets.QPushButton("Compute")
        self.btn_apply = QtWidgets.QPushButton("Apply to Controller")
        self.lbl_result = QtWidgets.QLabel("Kp=—, Ti=—, Td=—")

        # --- layout
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Rule"))
        top.addWidget(self.rule, 0)
        top.addSpacing(12)
        top.addWidget(self.stack, 1)
        top.addStretch(1)

        tables = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        tables.addWidget(self.bounds)
        tables.addWidget(self.case)
        tables.setSizes([300, 500])

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.btn_compute)
        btns.addWidget(self.btn_apply)
        btns.addStretch(1)
        btns.addWidget(self.lbl_result)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(top)
        v.addWidget(tables, 1)
        v.addSpacing(8)
        v.addLayout(btns)

        # init & wire
        self._apply_rule_ui()
        self._wire()

    def _sync_optimize_from_vm(self):
        """
        Refresh any optimize/tuning UI controls from the current VM state.
        This is intentionally simple; expand if you expose more controls.
        """
        # Example: refresh bounds table from VM
        names = ["Gain", "Ti", "Td"]
        self.bounds.set_parameters(names, self.vm.bounds())

    # ---- helpers
    def _param_row(self, label: str, default: float, setter):
        w = QtWidgets.QWidget()
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(1e-6, 1e9)
        spin.setDecimals(6)
        spin.setSingleStep(0.1)
        spin.setValue(float(default))
        spin.setMaximumWidth(220)
        spin.valueChanged.connect(setter)
        lay = QtWidgets.QHBoxLayout(w)
        lay.addWidget(QtWidgets.QLabel(label))
        lay.addWidget(spin)
        lay.addStretch(1)
        # store for access
        w._spin = spin  # type: ignore[attr-defined]
        return w

    def _wire(self):
        # UI -> VM
        self.rule.currentTextChanged.connect(self._on_rule_changed)
        self.btn_compute.clicked.connect(self._compute)
        self.btn_apply.clicked.connect(self._apply)

        # VM -> UI
        self.vm.resultChanged.connect(self._display_result)
        self.vm.boundsChanged.connect(lambda b: self.bounds.set_parameters(["Gain", "Ti", "Td"], b))
        self.vm.optimizeMapChanged.connect(lambda m: self._sync_optimize_from_vm())

    def _on_rule_changed(self, name: str):
        self.vm.set_rule(name)
        self._apply_rule_ui()

    def _apply_rule_ui(self):
        idx = {"SIMC": 0, "Lambda": 1, "ZN": 2}[self.vm.rule()]
        self.stack.setCurrentIndex(idx)

    def _display_result(self, Kp: float, Ti: float, Td: float):
        self.lbl_result.setText(f"Kp={Kp:.6g}, Ti={Ti:.6g}, Td={Td:.6g}")
        # also reflect in CaseTable "Final"
        rows = self.case.get_rows()
        if "Gain" in rows:
            rows["Gain"]["final"] = Kp
        if "Ti" in rows:
            rows["Ti"]["final"] = Ti
        if "Td" in rows:
            rows["Td"]["final"] = Td
        # reapply (preserve optimize/others)
        new_rows = [
            ("Gain", rows["Gain"]["optimize"], rows["Gain"]["lower"], rows["Gain"]["upper"],
             rows["Gain"]["existing"], rows["Gain"]["initial"], rows["Gain"]["final"]),
            ("Ti", rows["Ti"]["optimize"], rows["Ti"]["lower"], rows["Ti"]["upper"],
             rows["Ti"]["existing"], rows["Ti"]["initial"], rows["Ti"]["final"]),
            ("Td", rows["Td"]["optimize"], rows["Td"]["lower"], rows["Td"]["upper"],
             rows["Td"]["existing"], rows["Td"]["initial"], rows["Td"]["final"]),
        ]
        self.case.set_rows(new_rows)

    def _on_case_changed(self, rows: dict):
        # push optimize flags and bounds back to VM
        opt = {k: bool(v["optimize"]) for k, v in rows.items() if k in ("Gain", "Ti", "Td")}
        bnd = {k: (float(v["lower"]), float(v["upper"])) for k, v in rows.items() if k in ("Gain", "Ti", "Td")}
        self.vm.set_optimize_map(opt)
        self.vm.set_bounds(bnd)

    def _compute(self):
        res = self.vm.compute(self.proc_vm)
        self._display_result(res.Kp, res.Ti, res.Td)

    def _apply(self):
        res = self.vm.apply_to_controller(self.ctrl_vm, self.proc_vm)
        self._display_result(res.Kp, res.Ti, res.Td)
