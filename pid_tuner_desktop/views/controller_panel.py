from __future__ import annotations
from PySide6 import QtCore, QtWidgets
from viewmodels.controller_vm import ControllerVM


class ControllerPanel(QtWidgets.QWidget):
    """
    Editor for PID controller parameters:
      - Mode (P/PI/PID)
      - Derivative on (PV/Error)
      - Kp, Ti, Td, β, α
    Binds bidirectionally with ControllerVM.
    """

    def __init__(self, vm: ControllerVM, parent=None):
        super().__init__(parent)
        self.vm = vm

        # Controls
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["P", "PI", "PID"])
        self.d_on = QtWidgets.QComboBox()
        self.d_on.addItems(["PV", "Error"])

        self.kp = self._spin(0, 1e6, 0.001, 0.3)
        self.ti = self._spin(0, 1e6, 0.001, 20.0)
        self.td = self._spin(0, 1e6, 0.001, 0.0)
        self.beta = self._spin(0, 2.0, 0.01, 1.0)
        self.alpha = self._spin(1e-6, 1.0, 0.001, 0.125)

        form = QtWidgets.QFormLayout()
        form.addRow("Mode", self.mode)
        form.addRow("Derivative on", self.d_on)
        form.addRow("Kp (gain)", self.kp)
        form.addRow("Ti (s)", self.ti)
        form.addRow("Td (s)", self.td)
        form.addRow("β (setpoint weight)", self.beta)
        form.addRow("α (D filter)", self.alpha)

        self.setLayout(form)
        self._vm_to_ui()
        self._wire()

    # ---- helpers
    def _spin(self, lo: float, hi: float, step: float, val: float) -> QtWidgets.QDoubleSpinBox:
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(6)
        s.setSingleStep(step)
        s.setValue(val)
        s.setKeyboardTracking(False)
        s.setMaximumWidth(220)
        return s

    def _vm_to_ui(self):
        self.mode.setCurrentText(self.vm.mode())
        self.d_on.setCurrentText(self.vm.derivative_on())
        self.kp.setValue(self.vm.Kp())
        self.ti.setValue(self.vm.Ti())
        self.td.setValue(self.vm.Td())
        self.beta.setValue(self.vm.beta())
        self.alpha.setValue(self.vm.alpha())
        self._apply_mode_visibility()

    def _apply_mode_visibility(self):
        m = self.mode.currentText()
        self.ti.setEnabled(m in ("PI", "PID"))
        self.td.setEnabled(m == "PID")
        self.d_on.setEnabled(m == "PID")

    def _wire(self):
        # UI -> VM
        self.mode.currentTextChanged.connect(lambda t: (self.vm.set_mode(t), self._apply_mode_visibility()))
        self.d_on.currentTextChanged.connect(self.vm.set_derivative_on)
        self.kp.valueChanged.connect(self.vm.set_Kp)
        self.ti.valueChanged.connect(self.vm.set_Ti)
        self.td.valueChanged.connect(self.vm.set_Td)
        self.beta.valueChanged.connect(self.vm.set_beta)
        self.alpha.valueChanged.connect(self.vm.set_alpha)

        # VM -> UI
        self.vm.paramChanged.connect(lambda *_: self._vm_to_ui())
