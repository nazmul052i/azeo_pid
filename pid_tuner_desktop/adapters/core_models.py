from __future__ import annotations
from typing import Dict, Tuple, Literal


# Optional imports if the python core is available;
# the adapters work with plain dicts even if it's not present.
try:
    # Example expected paths (adjust when wiring real core):
    # from pid_tuner.models import fopdt, sopdt, integrator
    HAS_CORE = True
except Exception:  # pragma: no cover
    HAS_CORE = False


def ui_to_core_process(model: str, params: Dict[str, float]) -> Dict:
    """
    Convert UI ProcessVM parameters to a normalized core payload.
    Returns a dict that the core can consume, e.g.:
      {"type":"FOPDT","K":..,"tau":..,"theta":..}
      {"type":"SOPDT","K":..,"tau1":..,"tau2":..,"theta":..,"zeta":..}
      {"type":"Integrating","Ki":..,"theta":..}
    """
    m = model.upper()
    if m == "FOPDT":
        return {
            "type": "FOPDT",
            "K": float(params["K"]),
            "tau": max(1e-12, float(params["tau"])),
            "theta": max(0.0, float(params["theta"])),
        }
    if m == "SOPDT":
        return {
            "type": "SOPDT",
            "K": float(params["K"]),
            "tau1": max(1e-12, float(params["tau1"])),
            "tau2": max(1e-12, float(params["tau2"])),
            "theta": max(0.0, float(params["theta"])),
            "zeta": max(0.1, float(params.get("zeta", 1.0))),
        }
    # Integrating
    return {
        "type": "Integrating",
        "Ki": float(params["Ki"]),
        "theta": max(0.0, float(params["theta"])),
    }


def core_to_ui_process(payload: Dict) -> Tuple[str, Dict[str, float]]:
    """
    Convert a core payload back to UI model type and params dict.
    """
    t = payload.get("type", "FOPDT")
    if t == "FOPDT":
        return "FOPDT", {
            "K": float(payload["K"]),
            "tau": float(payload["tau"]),
            "theta": float(payload["theta"]),
        }
    if t == "SOPDT":
        return "SOPDT", {
            "K": float(payload["K"]),
            "tau1": float(payload["tau1"]),
            "tau2": float(payload["tau2"]),
            "theta": float(payload["theta"]),
            "zeta": float(payload.get("zeta", 1.0)),
        }
    return "Integrating", {
        "Ki": float(payload["Ki"]),
        "theta": float(payload["theta"]),
    }


def fopdt_time_constants_to_series(tau1: float, tau2: float) -> float:
    """
    For certain conversions we need an 'equivalent' first-order time constant.
    Series two first orders → approximate equivalent tau ≈ tau1 + tau2.
    """
    return float(tau1) + float(tau2)


def is_valid_process(payload: Dict) -> bool:
    """
    Sanity checks to gate sending bad models into the core.
    """
    t = payload.get("type")
    if t not in ("FOPDT", "SOPDT", "Integrating"):
        return False
    try:
        if t == "FOPDT":
            return payload["tau"] > 0 and payload["theta"] >= 0
        if t == "SOPDT":
            return payload["tau1"] > 0 and payload["tau2"] > 0 and payload["theta"] >= 0
        return payload["theta"] >= 0  # Integrating
    except Exception:
        return False
