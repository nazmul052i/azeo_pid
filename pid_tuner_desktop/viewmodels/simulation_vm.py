from __future__ import annotations
from typing import List, Tuple
from PySide6 import QtCore
from services.simulation_service import RealtimeSim


class SimulationVM(QtCore.QObject):
    """
    Simulation configuration + history buffer.
    Owns a RealtimeSim service and mirrors its ticks.
    Signals:
      runningChanged(bool)
      spChanged(float)
      noiseChanged(float)
      speedChanged(float)
      tick(t, sp, pv, op)
      historyCleared()
    """

    runningChanged = QtCore.Signal(bool)
    spChanged = QtCore.Signal(float)
    noiseChanged = QtCore.Signal(float)
    speedChanged = QtCore.Signal(float)
    tick = QtCore.Signal(float, float, float, float)
    historyCleared = QtCore.Signal()

    def __init__(self, period_s: float = 1.0, parent=None):
        super().__init__(parent)
        self._sim = RealtimeSim(period_s=period_s)
        self._sim.tick.connect(self._on_tick)
        self._sp: float = 5.0
        self._noise_std: float = 0.0    # not used by stub engine yet
        self._speed: float = 1.0        # multiplier (future)
        self._running: bool = False

        self._ts: List[float] = []
        self._sps: List[float] = []
        self._pvs: List[float] = []
        self._ops: List[float] = []

    # --- controls
    def start(self):
        if not self._running:
            self._sim.start()
            self._running = True
            self.runningChanged.emit(True)

    def stop(self):
        if self._running:
            self._sim.stop()
            self._running = False
            self.runningChanged.emit(False)

    def clear_history(self):
        self._ts.clear(); self._sps.clear(); self._pvs.clear(); self._ops.clear()
        self.historyCleared.emit()

    # --- config
    def set_sp(self, sp: float):
        sp = float(sp)
        self._sp = sp
        # push into service (stub exposes attribute)
        try:
            self._sim._sp = sp  # noqa: accessing stub directly
        except Exception:
            pass
        self.spChanged.emit(sp)

    def set_noise(self, std: float):
        self._noise_std = max(0.0, float(std))
        self.noiseChanged.emit(self._noise_std)

    def set_speed(self, mult: float):
        self._speed = max(0.1, float(mult))
        self.speedChanged.emit(self._speed)

    # --- history access
    def history(self) -> Tuple[List[float], List[float], List[float], List[float]]:
        return self._ts, self._sps, self._pvs, self._ops

    # --- tick propagation
    @QtCore.Slot(float, float, float, float)
    def _on_tick(self, t: float, sp: float, pv: float, op: float):
        self._ts.append(t); self._sps.append(sp); self._pvs.append(pv); self._ops.append(op)
        self.tick.emit(t, sp, pv, op)
