from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Literal, Tuple
from PySide6 import QtCore
from .process_vm import ProcessVM
from .controller_vm import ControllerVM


@dataclass
class TuningResult:
    Kp: float
    Ti: float
    Td: float


class TuningVM(QtCore.QObject):
    """
    Implements SIMC, Lambda(IMC), and basic Ziegler–Nichols (reaction curve) rules.
    Works primarily with FOPDT parameters; has reasonable fallbacks for SOPDT/Integrator.

    Signals:
      ruleChanged(str)
      lambdaChanged(float) / taucChanged(float)
      resultChanged(Kp:float, Ti:float, Td:float)
      boundsChanged(dict)  # {name:(low,high)}
      optimizeMapChanged(dict)  # {name:bool}
    """

    ruleChanged = QtCore.Signal(str)
    lambdaChanged = QtCore.Signal(float)
    taucChanged = QtCore.Signal(float)
    resultChanged = QtCore.Signal(float, float, float)
    boundsChanged = QtCore.Signal(dict)
    optimizeMapChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rule: Literal["SIMC", "Lambda", "ZN"] = "SIMC"
        self._lambda: float = 10.0  # Lambda/IMC closed-loop time constant
        self._tauc: float = 10.0    # SIMC target closed-loop time
        # editable per-parameter bounds and optimize flags used by UI tables
        self._bounds: Dict[str, Tuple[float, float]] = {
            "Gain": (1e-4, 1e2), "Ti": (0.0, 1e4), "Td": (0.0, 1e4)
        }
        self._optimize: Dict[str, bool] = {"Gain": True, "Ti": True, "Td": True}

    # --- getters
    def rule(self) -> str: return self._rule
    def get_lambda(self) -> float: return self._lambda
    def get_tauc(self) -> float: return self._tauc
    def bounds(self) -> Dict[str, Tuple[float, float]]: return dict(self._bounds)
    def optimize_map(self) -> Dict[str, bool]: return dict(self._optimize)

    # --- setters
    def set_rule(self, rule: str):
        rule = rule.capitalize()
        if rule not in ("SIMC", "Lambda", "Ziegler–nichols", "Zn"):
            rule = "SIMC"
        rule = "ZN" if rule.lower().startswith("ziegler") or rule == "Zn" else rule
        if self._rule != rule:
            self._rule = rule
            self.ruleChanged.emit(rule)

    def set_lambda(self, lam: float):
        lam = max(1e-6, float(lam))
        if self._lambda != lam:
            self._lambda = lam
            self.lambdaChanged.emit(lam)

    def set_tauc(self, tauc: float):
        tauc = max(1e-6, float(tauc))
        if self._tauc != tauc:
            self._tauc = tauc
            self.taucChanged.emit(tauc)

    def set_bounds(self, mapping: Dict[str, Tuple[float, float]]):
        self._bounds.update(mapping)
        self.boundsChanged.emit(self.bounds())

    def set_optimize_map(self, mapping: Dict[str, bool]):
        self._optimize.update(mapping)
        self.optimizeMapChanged.emit(self.optimize_map())

    # --- main API
    def compute(self, proc: ProcessVM) -> TuningResult:
        """
        Compute Kp, Ti, Td per selected rule using process params.
        """
        m = proc.model()
        params = proc.get_params()

        if self._rule == "Lambda":
            res = self._lambda_rule(m, params, self._lambda)
        elif self._rule == "ZN":
            res = self._zn_reaction_curve(m, params)
        else:  # SIMC
            res = self._simc_rule(m, params, self._tauc)

        # clamp to bounds and respect optimize flags
        Kp, Ti, Td = res.Kp, res.Ti, res.Td
        if self._optimize.get("Gain", True):
            low, high = self._bounds["Gain"]; Kp = min(max(Kp, low), high)
        if self._optimize.get("Ti", True):
            low, high = self._bounds["Ti"]; Ti = min(max(Ti, low), high)
        if self._optimize.get("Td", True):
            low, high = self._bounds["Td"]; Td = min(max(Td, low), high)

        self.resultChanged.emit(Kp, Ti, Td)
        return TuningResult(Kp, Ti, Td)

    # --- rules implementations
    def _lambda_rule(self, model: str, p: Dict, lam: float) -> TuningResult:
        """
        Lambda/IMC for FOPDT: Kp = tau/(K*(lambda+theta)), Ti=tau, Td=0 (PI form)
        For SOPDT: use tau1+tau2; Td = tau1*tau2/(tau1+tau2) as heuristic.
        For Integrating: Kp = 1/(Ki*(lambda+theta)), Ti = 4*(lambda+theta)
        """
        if model == "FOPDT":
            K, tau, theta = float(p["K"]), float(p["tau"]), float(p["theta"])
            Kp = tau / (K * (lam + theta))
            Ti = tau
            Td = 0.0
        elif model == "SOPDT":
            K, tau1, tau2, theta = float(p["K"]), float(p["tau1"]), float(p["tau2"]), float(p["theta"])
            tau_sum = tau1 + tau2
            Kp = tau_sum / (K * (lam + theta))
            Ti = tau_sum
            Td = (tau1 * tau2) / max(1e-9, tau_sum)
        else:  # Integrating
            Ki, theta = float(p["Ki"]), float(p["theta"])
            Kp = 1.0 / (Ki * (lam + theta))
            Ti = 4.0 * (lam + theta)
            Td = 0.0
        return TuningResult(float(Kp), float(Ti), float(Td))

    def _simc_rule(self, model: str, p: Dict, tauc: float) -> TuningResult:
        """
        SIMC rules (Skogestad, simplified):
          FOPDT (PI or PID): Kp = (tau)/(K*(tauc+theta))
                              Ti = min(tau, 4*(tauc+theta))
                              Td (PID heuristic) = 0.5*theta
          SOPDT: replace tau by (tau1+tau2), Td = tau1*tau2/(tau1+tau2)
          Integrating: Kp = 1/(Ki*(tauc+theta)); Ti = 4*(tauc+theta)
        """
        if model == "FOPDT":
            K, tau, theta = float(p["K"]), float(p["tau"]), float(p["theta"])
            Kp = tau / (K * (tauc + theta))
            Ti = min(tau, 4.0 * (tauc + theta))
            Td = 0.5 * theta
        elif model == "SOPDT":
            K, tau1, tau2, theta = float(p["K"]), float(p["tau1"]), float(p["tau2"]), float(p["theta"])
            tau_sum = tau1 + tau2
            Kp = tau_sum / (K * (tauc + theta))
            Ti = min(tau_sum, 4.0 * (tauc + theta))
            Td = (tau1 * tau2) / max(1e-9, tau_sum)
        else:  # Integrating
            Ki, theta = float(p["Ki"]), float(p["theta"])
            Kp = 1.0 / (Ki * (tauc + theta))
            Ti = 4.0 * (tauc + theta)
            Td = 0.0
        return TuningResult(float(Kp), float(Ti), float(Td))

    def _zn_reaction_curve(self, model: str, p: Dict) -> TuningResult:
        """
        Classic Ziegler–Nichols based on FOPDT reaction curve heuristics:
          PID:  Kp = 1.2 * (tau/(K*theta)), Ti = 2*theta, Td = 0.5*theta
          PI:   Kp = 0.9 * (tau/(K*theta)), Ti = 3.33*theta
        For SOPDT: use tau = tau1+tau2. For Integrating: fallback to PI with theta as delay.
        """
        if model == "FOPDT":
            K, tau, theta = float(p["K"]), float(p["tau"]), float(p["theta"])
        elif model == "SOPDT":
            K, tau, theta = float(p["K"]), float(p["tau1"]) + float(p["tau2"]), float(p["theta"])
        else:  # Integrator fallback: use theta as apparent delay and tau=4*theta heuristic
            Ki, theta = float(p["Ki"]), float(p["theta"])
            # define equivalent gain K≈1/Ki with tau≈4*theta for a rough guess
            K = 1.0 / max(1e-9, Ki)
            tau = 4.0 * max(1e-9, theta)

        theta = max(1e-9, theta)
        Kp = 1.2 * (tau / (K * theta))
        Ti = 2.0 * theta
        Td = 0.5 * theta
        return TuningResult(float(Kp), float(Ti), float(Td))

    # --- convenience
    def apply_to_controller(self, ctrl: ControllerVM, proc: ProcessVM) -> TuningResult:
        res = self.compute(proc)
        ctrl.apply(res.Kp, res.Ti, res.Td, beta=ctrl.beta(), alpha=ctrl.alpha())
        return res
