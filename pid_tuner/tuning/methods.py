# ===========================
# pid_tuner/tuning/methods.py
# ===========================
"""
PID Tuning Methods

Provides wrapper functions for various tuning methods including SIMC,
Lambda/IMC, and Ziegler-Nichols reaction curve.
"""

from typing import Dict, Any, Tuple
from .simc import (
    FOPDT as SIMC_FOPDT,
    SOPDT as SIMC_SOPDT,
    simc_pi_fopdt,
    simc_pid_sopdt,
    simc_integrator as _simc_integrator,
    simc_tau_c_recommendation,
)
from .lambda_method import (
    FOPDT as LAMBDA_FOPDT,
    lambda_fopdt,
    lambda_integrator as _lambda_integrator,
)


# === High-level wrappers that accept model dict ===

def simc_from_model(model: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    SIMC tuning from identified model dict.
    
    Args:
        model: Dict with keys 'type', 'K', 'tau'/'tau1', 'theta', etc.
    
    Returns:
        (Kp, Ti, Td) tuple
    """
    mtype = model.get("type", "").upper()
    
    if mtype == "FOPDT":
        K = model["K"]
        tau = model["tau"]
        theta = model["theta"]
        tau_c = simc_tau_c_recommendation(theta)
        return simc_pi_fopdt(SIMC_FOPDT(K, tau, theta), tau_c, improved=True)
    
    elif mtype == "SOPDT":
        K = model["K"]
        tau1 = model["tau"]
        tau2 = model.get("tau2", 0.0)
        theta = model["theta"]
        tau_c = simc_tau_c_recommendation(theta)
        return simc_pid_sopdt(SIMC_SOPDT(K, tau1, tau2, theta), tau_c, improved=True)
    
    elif mtype == "INTEGRATOR":
        K = model["K"]
        leak = model.get("leak", 0.0)
        # For integrator: k' = K (slope)
        # Assume small theta if not provided
        theta = model.get("theta", 0.0)
        tau_c = max(1.0, theta)  # reasonable default
        return _simc_integrator(K, theta, tau_c)
    
    else:
        raise ValueError(f"Unknown model type: {mtype}")


def lambda_from_model(model: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Lambda/IMC tuning from identified model dict.
    
    Args:
        model: Dict with keys 'type', 'K', 'tau', 'theta', etc.
    
    Returns:
        (Kp, Ti, Td) tuple
    """
    mtype = model.get("type", "").upper()
    
    if mtype == "FOPDT":
        K = model["K"]
        tau = model["tau"]
        theta = model["theta"]
        lam = max(theta, 1.0)  # Lambda ≥ theta for robustness
        return lambda_fopdt(LAMBDA_FOPDT(K, tau, theta), lam)
    
    elif mtype == "INTEGRATOR":
        K = model["K"]
        theta = model.get("theta", 0.0)
        lam = max(theta * 2, 1.0)
        return _lambda_integrator(K, theta, lam)
    
    else:
        # Fall back to SIMC for unsupported types
        return simc_from_model(model)


def zn_reaction_curve(model: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Ziegler-Nichols reaction curve tuning.
    
    For FOPDT model: uses classical ZN formulas based on K, tau, theta.
    
    Args:
        model: Dict with keys 'type', 'K', 'tau', 'theta'
    
    Returns:
        (Kp, Ti, Td) tuple for PID controller
    """
    mtype = model.get("type", "").upper()
    
    if mtype == "FOPDT":
        K = model["K"]
        tau = model["tau"]
        theta = model["theta"]
        
        # ZN reaction curve for PID:
        # Kp = 1.2*tau/(K*theta), Ti = 2*theta, Td = 0.5*theta
        if theta > 0:
            Kp = 1.2 * tau / (K * theta)
            Ti = 2.0 * theta
            Td = 0.5 * theta
            return (Kp, Ti, Td)
        else:
            # Degenerate case
            return (1.0, 1.0, 0.0)
    
    elif mtype == "INTEGRATOR":
        # ZN for integrator (Tyreus-Luyben variant)
        K = model["K"]
        theta = model.get("theta", 1.0)
        Kp = 0.5 / (K * theta) if theta > 0 else 1.0
        Ti = 4.0 * theta
        return (Kp, Ti, 0.0)
    
    else:
        # Fallback
        return simc_from_model(model)


# === Direct parameter wrappers (for programmatic use) ===

def imc_lambda_fopdt(K: float, tau: float, theta: float, lam: float) -> Tuple[float, float, float]:
    """Lambda/IMC for FOPDT process."""
    return lambda_fopdt(LAMBDA_FOPDT(K, tau, theta), lam)


def lambda_integrating(kprime: float, theta: float, lam: float) -> Tuple[float, float, float]:
    """Lambda for integrating process."""
    return _lambda_integrator(kprime, theta, lam)


def simc_pi(K: float, tau: float, theta: float, tau_c: float, improved: bool = False) -> Tuple[float, float, float]:
    """SIMC PI for FOPDT."""
    return simc_pi_fopdt(SIMC_FOPDT(K, tau, theta), tau_c, improved=improved)


def simc_pid(K: float, tau1: float, tau2: float, theta: float, tau_c: float, improved: bool = False) -> Tuple[float, float, float]:
    """SIMC PID for SOPDT."""
    return simc_pid_sopdt(SIMC_SOPDT(K, tau1, tau2, theta), tau_c, improved=improved)


def simc_integrating(kprime: float, theta: float, tau_c: float) -> Tuple[float, float, float]:
    """SIMC PI for integrating process."""
    return _simc_integrator(kprime, theta, tau_c)


def simc_tau_c(theta: float) -> float:
    """Recommended τc = θ (default SIMC tight-but-robust)."""
    return simc_tau_c_recommendation(theta)