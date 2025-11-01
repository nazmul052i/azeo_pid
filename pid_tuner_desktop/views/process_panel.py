from __future__ import annotations
from PySide6 import QtCore, QtWidgets
from viewmodels.process_vm import ProcessVM
from viewmodels.app_state import AppState
from widgets.tag_picker import TagPicker


class ProcessPanel(QtWidgets.QWidget):
    """
    Process model editor + SP/PV/OP tag assignment.
    Supports FOPDT / SOPDT / Integrating.
    """

    def __init__(self, vm: ProcessVM, app_state: AppState, parent=None):
        super().__init__(parent)
        self.vm = vm
        self.app_state = app_state

        # --- top: model selector
        self.model = QtWidgets.QComboBox()
        self.model.addItems(["FOPDT", "SOPDT", "Integrating"])

        # --- stacked parameter editors
        self.stack = QtWidgets.QStackedWidget()
        self.page_fopdt = self._make_fopdt_page()
        self.page_sopdt = self._make_sopdt_page()
        self.page_int = self._make_integrator_page()
        self.stack.addWidget(self.page_fopdt)
        self.stack.addWidget(self.page_sopdt)
        self.stack.addWidget(self.page_int)

        # --- tag row
        self.sp_tag = QtWidgets.QLineEdit(self.app_state.tags().get("SP", ""))
        self.pv_tag = QtWidgets.QLineEdit(self.app_state.tags().get("PV", ""))
        self.op_tag = QtWidgets.QLineEdit(self.app_state.tags().get("OP", ""))
        self.btn_pick = QtWidgets.QPushButton("Pick Tags…")

        tags_grid = QtWidgets.QGridLayout()
        tags_grid.addWidget(QtWidgets.QLabel("SP tag"), 0, 0)
        tags_grid.addWidget(self.sp_tag, 0, 1)
        tags_grid.addWidget(QtWidgets.QLabel("PV tag"), 1, 0)
        tags_grid.addWidget(self.pv_tag, 1, 1)
        tags_grid.addWidget(QtWidgets.QLabel("OP tag"), 2, 0)
        tags_grid.addWidget(self.op_tag, 2, 1)
        tags_grid.addWidget(self.btn_pick, 0, 2, 3, 1)

        # --- layout
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Model"))
        top.addWidget(self.model)
        top.addStretch(1)

        main = QtWidgets.QVBoxLayout(self)
        main.addLayout(top)
        main.addWidget(self.stack)
        main.addSpacing(8)
        main.addLayout(tags_grid)
        main.addStretch(1)

        self._vm_to_ui()
        self._wire()

    # ----- pages
    def _dbl(self, v: float, lo: float = -1e9, hi: float = 1e9, step: float = 0.001) -> QtWidgets.QDoubleSpinBox:
        s = QtWidgets.QDoubleSpinBox()
        s.setDecimals(6)
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setValue(v)
        s.setMaximumWidth(220)
        s.setKeyboardTracking(False)
        return s

    def _make_fopdt_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        self.f_k = self._dbl(1.0)
        self.f_tau = self._dbl(20.0, 1e-9, 1e9)
        self.f_theta = self._dbl(1.0, 0.0, 1e9)
        form = QtWidgets.QFormLayout(w)
        form.addRow("K (gain)", self.f_k)
        form.addRow("τ (time constant, s)", self.f_tau)
        form.addRow("θ (deadtime, s)", self.f_theta)
        return w

    def _make_sopdt_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        self.s_k = self._dbl(1.0)
        self.s_tau1 = self._dbl(20.0, 1e-9, 1e9)
        self.s_tau2 = self._dbl(5.0, 1e-9, 1e9)
        self.s_theta = self._dbl(1.0, 0.0, 1e9)
        self.s_zeta = self._dbl(1.0, 0.1, 10.0, 0.01)
        form = QtWidgets.QFormLayout(w)
        form.addRow("K (gain)", self.s_k)
        form.addRow("τ1 (s)", self.s_tau1)
        form.addRow("τ2 (s)", self.s_tau2)
        form.addRow("θ (s)", self.s_theta)
        form.addRow("ζ (damping)", self.s_zeta)
        return w

    def _make_integrator_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        self.i_ki = self._dbl(0.1, -1e9, 1e9)
        self.i_theta = self._dbl(1.0, 0.0, 1e9)
        form = QtWidgets.QFormLayout(w)
        form.addRow("Ki (integrator gain)", self.i_ki)
        form.addRow("θ (deadtime, s)", self.i_theta)
        return w

    # ----- bindings
    def _vm_to_ui(self):
        m = self.vm.model()
        self.model.setCurrentText(m)
        self.stack.setCurrentIndex({"FOPDT": 0, "SOPDT": 1, "Integrating": 2}[m])
        p = self.vm.get_params()
        if m == "FOPDT":
            self.f_k.setValue(p["K"]); self.f_tau.setValue(p["tau"]); self.f_theta.setValue(p["theta"])
        elif m == "SOPDT":
            self.s_k.setValue(p["K"]); self.s_tau1.setValue(p["tau1"]); self.s_tau2.setValue(p["tau2"])
            self.s_theta.setValue(p["theta"]); self.s_zeta.setValue(p["zeta"])
        else:
            self.i_ki.setValue(p["Ki"]); self.i_theta.setValue(p["theta"])

    def _wire(self):
        # UI -> VM
        self.model.currentTextChanged.connect(self._on_model_changed)
        self.f_k.valueChanged.connect(lambda v: self.vm.set_fopdt(v, self.f_tau.value(), self.f_theta.value()))
        self.f_tau.valueChanged.connect(lambda v: self.vm.set_fopdt(self.f_k.value(), v, self.f_theta.value()))
        self.f_theta.valueChanged.connect(lambda v: self.vm.set_fopdt(self.f_k.value(), self.f_tau.value(), v))

        self.s_k.valueChanged.connect(lambda v: self.vm.set_sopdt(v, self.s_tau1.value(), self.s_tau2.value(), self.s_theta.value(), self.s_zeta.value()))
        self.s_tau1.valueChanged.connect(lambda v: self.vm.set_sopdt(self.s_k.value(), v, self.s_tau2.value(), self.s_theta.value(), self.s_zeta.value()))
        self.s_tau2.valueChanged.connect(lambda v: self.vm.set_sopdt(self.s_k.value(), self.s_tau1.value(), v, self.s_theta.value(), self.s_zeta.value()))
        self.s_theta.valueChanged.connect(lambda v: self.vm.set_sopdt(self.s_k.value(), self.s_tau1.value(), self.s_tau2.value(), v, self.s_zeta.value()))
        self.s_zeta.valueChanged.connect(lambda v: self.vm.set_sopdt(self.s_k.value(), self.s_tau1.value(), self.s_tau2.value(), self.s_theta.value(), v))

        self.i_ki.valueChanged.connect(lambda v: self.vm.set_integrator(v, self.i_theta.value()))
        self.i_theta.valueChanged.connect(lambda v: self.vm.set_integrator(self.i_ki.value(), v))

        # VM -> UI
        self.vm.modelChanged.connect(lambda *_: self._vm_to_ui())
        self.vm.paramsChanged.connect(lambda *_: self._vm_to_ui())

        # tag widgets
        self.sp_tag.editingFinished.connect(lambda: self.app_state.set_tag("SP", self.sp_tag.text()))
        self.pv_tag.editingFinished.connect(lambda: self.app_state.set_tag("PV", self.pv_tag.text()))
        self.op_tag.editingFinished.connect(lambda: self.app_state.set_tag("OP", self.op_tag.text()))
        self.btn_pick.clicked.connect(self._pick_tags)
        self.app_state.tagMapChanged.connect(self._on_tags_changed)

    # ---- handlers
    @QtCore.Slot(str)
    def _on_model_changed(self, txt: str):
        self.vm.set_model(txt)
        self.stack.setCurrentIndex({"FOPDT": 0, "SOPDT": 1, "Integrating": 2}[self.vm.model()])

    def _pick_tags(self):
        dlg = TagPicker(self)
        # pre-populate sources; real app will query OPC/db
        src = {
            "Signals": ["TCAF", "PCAF", "TCBE", "TCCF", "TCCD", "TCAF.SP"],
            "OPC UA": ["ns=2;s=Sim.PV", "ns=2;s=Sim.OP", "ns=2;s=Sim.SP"],
            "Database": ["db:TCAF", "db:PCAF", "db:TCAF.SP"]
        }
        dlg.set_sources(src)
        role_before = "PV"
        dlg.set_role_choices(["SP", "PV", "OP"])
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.app_state.set_tag(dlg.selected_role(), dlg.selected_tag())

    def _on_tags_changed(self, mapping: dict):
        self.sp_tag.setText(mapping.get("SP", ""))
        self.pv_tag.setText(mapping.get("PV", ""))
        self.op_tag.setText(mapping.get("OP", ""))
