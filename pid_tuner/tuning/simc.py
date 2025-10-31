# pid_tuner/tuning/simc.py
from dataclasses import dataclass
from typing import Tuple

@dataclass
class FOPDT:
    K: float
    tau: float
    theta: float

@dataclass
class SOPDT:
    K: float
    tau1: float
    tau2: float
    theta: float

def simc_pi_fopdt(model: FOPDT, tau_c: float, improved: bool = False) -> Tuple[float, float, float]:
    """
    SIMC PI for FOPDT (PIDbook Ch. 5):
      Original:  Kp = tau/(K*(tau_c+theta)), Ti = min(tau, 4*(tau_c+theta))
      Improved:  replace tau by tau + theta/3
    """
    K, tau, theta = model.K, model.tau, model.theta
    tau_eff = tau + (theta/3.0 if improved else 0.0)
    Kp = tau_eff / (K * (tau_c + theta))
    Ti = min(tau_eff, 4.0 * (tau_c + theta))
    return (Kp, Ti, 0.0)

def simc_pid_sopdt(model: SOPDT, tau_c: float, improved: bool = False) -> Tuple[float, float, float]:
    """
    SIMC PID for SOPDT:
      Kp = tau1/(K*(tau_c+theta)), Ti = min(tau1, 4*(tau_c+theta)), Td = tau2
      Improved: replace tau1 by tau1 + theta/3
    """
    K, tau1, tau2, theta = model.K, model.tau1, model.tau2, model.theta
    tau1_eff = tau1 + (theta/3.0 if improved else 0.0)
    Kp = tau1_eff / (K * (tau_c + theta))
    Ti = min(tau1_eff, 4.0 * (tau_c + theta))
    Td = tau2
    return (Kp, Ti, Td)

def simc_integrator(kprime: float, theta: float, tau_c: float) -> Tuple[float, float, float]:
    """
    SIMC PI for integrating process:
      Kp = 1/(k'*(tau_c + theta)), Ti = 4*(tau_c + theta)
    """
    Kp = 1.0 / (kprime * (tau_c + theta))
    Ti = 4.0 * (tau_c + theta)
    return (Kp, Ti, 0.0)

def simc_tau_c_recommendation(theta: float) -> float:
    """Tight-but-robust default."""
    return theta
