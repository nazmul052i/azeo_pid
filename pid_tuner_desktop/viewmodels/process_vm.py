from __future__ import annotations
from typing import Literal, Tuple
from PySide6 import QtCore


class ProcessVM(QtCore.QObject):
    """
    Process model parameters for FOPDT / SOPDT / Integrating.
    Signals:
      modelChanged(model_type:str)
      paramsChanged(dict)
    """

    modelChanged = QtCore.Signal(str)
    paramsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: Literal["FOPDT", "SOPDT", "Integrating"] = "FOPDT"
        # FOPDT: K, tau, theta
        self._K: float = 1.0
        self._tau: float = 20.0
        self._theta: float = 1.0
        # SOPDT extra: tau2, zeta (use series form)
        self._tau2: float = 5.0
        self._zeta: float = 1.0  # damping factor
        # Integrating: Ki (gain of integrator), theta
        self._Ki: float = 0.1

    # --- getters
    def model(self) -> str: return self._model
    def get_params(self) -> dict:
        d = {"model": self._model}
        if self._model == "FOPDT":
            d.update({"K": self._K, "tau": self._tau, "theta": self._theta})
        elif self._model == "SOPDT":
            d.update({"K": self._K, "tau1": self._tau, "tau2": self._tau2, "theta": self._theta, "zeta": self._zeta})
        else:
            d.update({"Ki": self._Ki, "theta": self._theta})
        return d

    # --- setters
    def set_model(self, model: str):
        model = model.upper()
        if model not in ("FOPDT", "SOPDT", "INTEGRATING"):
            model = "FOPDT"
        model = "Integrating" if model == "INTEGRATING" else model
        if model != self._model:
            self._model = model
            self.modelChanged.emit(model)
            self.paramsChanged.emit(self.get_params())

    def set_fopdt(self, K: float, tau: float, theta: float):
        self._model = "FOPDT"
        self._K = float(K)
        self._tau = max(1e-9, float(tau))
        self._theta = max(0.0, float(theta))
        self.modelChanged.emit(self._model)
        self.paramsChanged.emit(self.get_params())

    def set_sopdt(self, K: float, tau1: float, tau2: float, theta: float, zeta: float = 1.0):
        self._model = "SOPDT"
        self._K = float(K)
        self._tau = max(1e-9, float(tau1))
        self._tau2 = max(1e-9, float(tau2))
        self._theta = max(0.0, float(theta))
        self._zeta = max(0.1, float(zeta))
        self.modelChanged.emit(self._model)
        self.paramsChanged.emit(self.get_params())

    def set_integrator(self, Ki: float, theta: float):
        self._model = "Integrating"
        self._Ki = float(Ki)
        self._theta = max(0.0, float(theta))
        self.modelChanged.emit(self._model)
        self.paramsChanged.emit(self.get_params())

    # convenience accessors
    def K_tau_theta(self) -> Tuple[float, float, float]:
        return self._K, self._tau, self._theta
