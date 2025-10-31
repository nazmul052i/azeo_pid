# pid_tuner/tuning/lambda_method.py
from dataclasses import dataclass
from typing import Tuple

@dataclass
class FOPDT:
    K: float
    tau: float
    theta: float

def lambda_fopdt(model: FOPDT, lam: float) -> Tuple[float, float, float]:
    """
    Lambda/IMC for FOPDT:
      Kp = tau/(K*(lam + theta)), Ti = tau
    """
    K, tau, theta = model.K, model.tau, model.theta
    Kp = tau / (K * (lam + theta))
    Ti = tau
    return (Kp, Ti, 0.0)

def lambda_integrator(kprime: float, theta: float, lam: float) -> Tuple[float, float, float]:
    """
    Lambda for integrating process:
      Kp ≈ 1/(k' * lam), Ti = 2*lam + theta
    """
    Kp = 1.0 / (kprime * lam) if lam > 0 else 0.0
    Ti = 2.0 * lam + theta
    return (Kp, Ti, 0.0)
