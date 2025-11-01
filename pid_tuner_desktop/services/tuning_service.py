from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class TuningResult:
    Kp: float
    Ti: float
    Td: float


# -------- Lambda / IMC --------

def lambda_imc(rule_input: Dict) -> TuningResult:
    """
    Lambda/IMC rules.
    Inputs for FOPDT: {"type":"FOPDT","K":..,"tau":..,"theta":..,"lambda":..}
    SOPDT: {"type":"SOPDT","K":..,"tau1":..,"tau2":..,"theta":..,"lambda":..}
    Integrating: {"type":"Integrating","Ki":..,"theta":..,"lambda":..}
    """
    t = rule_input.get("type", "FOPDT")
    lam = float(rule_input.get("lambda", 10.0))
    if t == "FOPDT":
        K, tau, theta = float(rule_input["K"]), float(rule_input["tau"]), float(rule_input["theta"])
        Kp = tau / (K * (lam + theta)); Ti = tau; Td = 0.0
    elif t == "SOPDT":
        K, tau1, tau2, theta = float(rule_input["K"]), float(rule_input["tau1"]), float(rule_input["tau2"]), float(rule_input["theta"])
        tau_sum = tau1 + tau2
        Kp = tau_sum / (K * (lam + theta)); Ti = tau_sum; Td = (tau1 * tau2) / max(1e-12, tau_sum)
    else:
        Ki, theta = float(rule_input["Ki"]), float(rule_input["theta"])
        Kp = 1.0 / (Ki * (lam + theta)); Ti = 4.0 * (lam + theta); Td = 0.0
    return TuningResult(float(Kp), float(Ti), float(Td))


# -------- SIMC --------

def simc(rule_input: Dict) -> TuningResult:
    """
    SIMC rules (Skogestad simplified).
    Inputs same as lambda_imc but parameter name 'tauc' instead of 'lambda'.
    """
    t = rule_input.get("type", "FOPDT")
    tauc = float(rule_input.get("tauc", 10.0))
    if t == "FOPDT":
        K, tau, theta = float(rule_input["K"]), float(rule_input["tau"]), float(rule_input["theta"])
        Kp = tau / (K * (tauc + theta))
        Ti = min(tau, 4.0 * (tauc + theta))
        Td = 0.5 * theta
    elif t == "SOPDT":
        K, tau1, tau2, theta = float(rule_input["K"]), float(rule_input["tau1"]), float(rule_input["tau2"]), float(rule_input["theta"])
        tau_sum = tau1 + tau2
        Kp = tau_sum / (K * (tauc + theta))
        Ti = min(tau_sum, 4.0 * (tauc + theta))
        Td = (tau1 * tau2) / max(1e-12, tau_sum)
    else:
        Ki, theta = float(rule_input["Ki"]), float(rule_input["theta"])
        Kp = 1.0 / (Ki * (tauc + theta)); Ti = 4.0 * (tauc + theta); Td = 0.0
    return TuningResult(float(Kp), float(Ti), float(Td))


# -------- ZN reaction-curve (heuristic) --------

def zn_reaction_curve(rule_input: Dict) -> TuningResult:
    """
    Classic Ziegler–Nichols (reaction curve) PID.
    Inputs (FOPDT-like): {"type": "...", "K":..., "tau":..., "theta":...}
    For SOPDT, pass tau1+tau2 as 'tau'.
    For integrating: approximate using tau=4*theta, K=1/Ki.
    """
    t = rule_input.get("type", "FOPDT")
    if t == "FOPDT":
        K, tau, theta = float(rule_input["K"]), float(rule_input["tau"]), float(rule_input["theta"])
    elif t == "SOPDT":
        K = float(rule_input["K"])
        tau = float(rule_input["tau1"]) + float(rule_input["tau2"])
        theta = float(rule_input["theta"])
    else:
        Ki, theta = float(rule_input["Ki"]), float(rule_input["theta"])
        K = 1.0 / max(1e-12, Ki)
        tau = 4.0 * max(theta, 1e-12)
    theta = max(1e-9, theta)
    Kp = 1.2 * (tau / (K * theta)); Ti = 2.0 * theta; Td = 0.5 * theta
    return TuningResult(float(Kp), float(Ti), float(Td))
