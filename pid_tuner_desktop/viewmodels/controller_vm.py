from __future__ import annotations
from typing import Literal
from PySide6 import QtCore


class ControllerVM(QtCore.QObject):
    """
    PID controller parameters viewmodel.
    Supports P/PI/PID modes, derivative on PV or Error, setpoint weight β, filter α.
    Emits paramChanged(Kp, Ti, Td, beta, alpha, mode, d_on).
    """

    paramChanged = QtCore.Signal(float, float, float, float, float, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode: Literal["P", "PI", "PID"] = "PID"
        self._d_on: Literal["PV", "Error"] = "PV"
        self._Kp: float = 0.3
        self._Ti: float = 20.0
        self._Td: float = 0.0
        self._beta: float = 1.0
        self._alpha: float = 0.125  # derivative filter factor (0..1]

    # --- getters
    def mode(self) -> str: return self._mode
    def derivative_on(self) -> str: return self._d_on
    def Kp(self) -> float: return self._Kp
    def Ti(self) -> float: return self._Ti
    def Td(self) -> float: return self._Td
    def beta(self) -> float: return self._beta
    def alpha(self) -> float: return self._alpha

    # --- setters (emit on change)
    def set_mode(self, mode: str):
        mode = mode.upper()
        if mode not in ("P", "PI", "PID"):
            mode = "PID"
        if self._mode != mode:
            self._mode = mode
            self._normalize_by_mode()
            self._emit()

    def set_derivative_on(self, d_on: str):
        d_on = "PV" if str(d_on).lower().startswith("pv") else "Error"
        if self._d_on != d_on:
            self._d_on = d_on
            self._emit()

    def set_Kp(self, Kp: float):
        Kp = float(max(0.0, Kp))
        if self._Kp != Kp:
            self._Kp = Kp
            self._emit()

    def set_Ti(self, Ti: float):
        Ti = float(max(0.0, Ti))
        if self._Ti != Ti:
            self._Ti = Ti
            self._emit()

    def set_Td(self, Td: float):
        Td = float(max(0.0, Td))
        if self._Td != Td:
            self._Td = Td
            self._emit()

    def set_beta(self, beta: float):
        beta = float(max(0.0, min(2.0, beta)))
        if self._beta != beta:
            self._beta = beta
            self._emit()

    def set_alpha(self, alpha: float):
        alpha = float(max(1e-6, min(1.0, alpha)))
        if self._alpha != alpha:
            self._alpha = alpha
            self._emit()

    # --- utilities
    def as_tuple(self):
        return (self._Kp, self._Ti, self._Td, self._beta, self._alpha, self._mode, self._d_on)

    def apply(self, Kp: float, Ti: float, Td: float, beta: float | None = None, alpha: float | None = None):
        self._Kp = max(0.0, float(Kp))
        self._Ti = max(0.0, float(Ti))
        self._Td = max(0.0, float(Td))
        if beta is not None:
            self._beta = float(max(0.0, min(2.0, beta)))
        if alpha is not None:
            self._alpha = float(max(1e-6, min(1.0, alpha)))
        self._normalize_by_mode()
        self._emit()

    def _normalize_by_mode(self):
        if self._mode == "P":
            self._Ti = 0.0
            self._Td = 0.0
        elif self._mode == "PI":
            self._Td = 0.0

    def _emit(self):
        self.paramChanged.emit(self._Kp, self._Ti, self._Td, self._beta, self._alpha, self._mode, self._d_on)
