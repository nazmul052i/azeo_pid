from __future__ import annotations
from PySide6 import QtCore, QtWidgets
from viewmodels.simulation_vm import SimulationVM


class SimulationPanel(QtWidgets.QWidget):
    """
    Simulation controls:
      - SP step, Noise std, Speed multiplier
      - Run / Stop / Clear
      - Status readout
    Binds to SimulationVM; emits no extra signals.
    """

    def __init__(self, vm: SimulationVM, parent=None):
        super().__init__(parent)
        self.vm = vm

        self.sp = self._spin(-1e6, 1e6, 0.1, 5.0)
        self.noise = self._spin(0.0, 1e6, 0.01, 0.0)
        self.speed = self._spin(0.1, 10.0, 0.1, 1.0)

        self.btn_run = QtWidgets.QPushButton("Run")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_clear = QtWidgets.QPushButton("Clear History")
        self.lbl_status = QtWidgets.QLabel("Stopped")

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("SP"), 0, 0)
        grid.addWidget(self.sp, 0, 1)
        grid.addWidget(QtWidgets.QLabel("Noise std dev"), 1, 0)
        grid.addWidget(self.noise, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Speed ×"), 2, 0)
        grid.addWidget(self.speed, 2, 1)

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.btn_run)
        btns.addWidget(self.btn_stop)
        btns.addWidget(self.btn_clear)
        btns.addStretch(1)
        btns.addWidget(QtWidgets.QLabel("Status:"))
        btns.addWidget(self.lbl_status)

        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(grid)
        v.addSpacing(8)
        v.addLayout(btns)
        v.addStretch(1)

        self._wire()
        self._vm_to_ui()

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
        # initial propagate
        t, sps, pvs, ops = self.vm.history()
        self.sp.setValue(self.vm._sp)      # using VM value; kept simple
        self.noise.setValue(self.vm._noise_std)
        self.speed.setValue(self.vm._speed)
        self.lbl_status.setText("Running" if self.vm._running else "Stopped")

    def _wire(self):
        # UI -> VM
        self.sp.valueChanged.connect(self.vm.set_sp)
        self.noise.valueChanged.connect(self.vm.set_noise)
        self.speed.valueChanged.connect(self.vm.set_speed)
        self.btn_run.clicked.connect(self.vm.start)
        self.btn_stop.clicked.connect(self.vm.stop)
        self.btn_clear.clicked.connect(self.vm.clear_history)

        # VM -> UI
        self.vm.runningChanged.connect(lambda r: self.lbl_status.setText("Running" if r else "Stopped"))
