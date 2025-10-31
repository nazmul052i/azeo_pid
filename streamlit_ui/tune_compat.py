# ===========================
# streamlit_ui/tune_compat.py
# ===========================

"""Compatibility wrappers for identification and tuning APIs.
This module tries multiple function names so the UI doesn't break
if the backend uses different names.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

# Import candidate backends lazily and defensively
try:
    from pid_tuner.identify import stepfit as _stepfit
except Exception:  # pragma: no cover
    _stepfit = None  # type: ignore

try:
    from pid_tuner.identify import sopdtfit as _sopdtfit
except Exception:  # pragma: no cover
    _sopdtfit = None  # type: ignore

try:
    from pid_tuner.identify import intfit as _intfit
except Exception:  # pragma: no cover
    _intfit = None  # type: ignore

try:
    from pid_tuner.tuning import methods as _methods
except Exception:  # pragma: no cover
    _methods = None  # type: ignore


# ---------- Identification ----------

def _call_first(obj: Any, names: Tuple[str, ...], *args, **kwargs):
    for n in names:
        if obj is not None and hasattr(obj, n):
            return getattr(obj, n)(*args, **kwargs)
    raise AttributeError("None of the candidate functions exist: " + ", ".join(names))


def identify_model(*, mtype: str, t, sp, pv) -> Optional[Dict[str, Any]]:
    m = mtype.upper()
    try:
        if m == "FOPDT":
            K, tau, theta = _call_first(
                _stepfit,
                ("fit_fopdt", "fit_fopdt_from_step", "identify_fopdt"),
                t, sp, pv,
            )
            return {"type": m, "K": float(K), "tau": float(tau), "theta": float(theta)}
        elif m == "SOPDT":
            K, tau1, tau2, theta = _call_first(
                _sopdtfit,
                ("fit_sopdt", "fit_sopdt_from_step", "identify_sopdt"),
                t, sp, pv,
            )
            return {"type": m, "K": float(K), "tau": float(tau1), "tau2": float(tau2), "theta": float(theta)}
        else:  # INTEGRATOR
            K, leak = _call_first(
                _intfit,
                ("fit_integrator", "fit_integrator_from_step", "identify_integrator"),
                t, sp, pv,
            )
            return {"type": m, "K": float(K), "leak": float(leak)}
    except Exception:
        return None


# ---------- Tuning ----------

def tuning_simc(model: Dict[str, Any]):
    # Try several SIMC entry points
    return _call_first(
        _methods,
        ("simc_from_model", "simc_tuning", "tune_simc"),
        model,
    )


def tuning_lambda(model: Dict[str, Any]):
    return _call_first(
        _methods,
        ("lambda_from_model", "imc_from_model", "tune_lambda"),
        model,
    )


def tuning_zn_reaction(model: Dict[str, Any]):
    return _call_first(
        _methods,
        ("zn_reaction_curve", "zn_from_reaction_curve", "tune_zn_reaction"),
        model,
    )