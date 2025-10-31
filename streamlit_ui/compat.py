# streamlit_ui/compat.py
"""
Compatibility shims to decouple the UI from back-end names.
- simulate_closed_loop(...)  -> returns (t, y, sp, u)
- streaming_closed_loop(...) -> yields (t, y, sp, u) periodically
"""

from __future__ import annotations
from typing import Tuple, Iterator, List, Sequence
import time

# Back-end modules
from pid_tuner.simulate import sim as _sim
from pid_tuner.models.processes import FOPDT as P_FOPDT, IntegratorLeak as P_INT
from pid_tuner.models.processes import ProcessBase
from pid_tuner.control.pid import PID


# ---------- helpers ----------

def _build_process(model_type: str, K: float, tau: float, theta: float, tau2: float, leak: float) -> Tuple[ProcessBase, float]:
    """Return (process_instance, deadtime_s)."""
    model = model_type.upper()
    if model == "FOPDT":
        p = P_FOPDT(K=K, tau=max(1e-6, tau))
        return p, max(0.0, theta)
    elif model == "SOPDT":
        # If you have a real SOPDT class, swap it in here.
        eff_tau = max(1e-6, tau + max(0.0, tau2))
        p = P_FOPDT(K=K, tau=eff_tau)
        return p, max(0.0, theta)
    else:  # INTEGRATOR
        # Map integrating model to your class signature
        p = P_INT(K=K, Ki=max(1e-9, 1.0 / max(1e-6, tau)), leak=max(0.0, leak))
        return p, max(0.0, theta)


def _build_controller(mode: str, Kp: float, Ti: float, Td: float, beta: float, deriv_on: str, filt_N: float,
                      umin: float, umax: float, aw_track: bool) -> PID:
    form = mode.upper()
    return PID(
        Kp=float(Kp), Ti=max(1e-9, float(Ti)), Td=max(0.0, float(Td)),
        N=max(1.0, float(filt_N)), umin=float(umin), umax=float(umax),
        beta=float(beta), form=form, deriv_on=("PV" if deriv_on.upper() == "PV" else "ERROR"),
    )


# ---------- batch simulate ----------

def simulate_closed_loop(*, model_type: str, K: float, tau: float, theta: float, tau2: float, leak: float,
                         mode: str, Kp: float, Ti: float, Td: float, beta: float, deriv_on: str, filt_N: float,
                         aw_track: bool, umin: float, umax: float, sp_value: float, y0: float, u0: float,
                         dt: float, horizon: float):
    """UI-facing wrapper that returns (t, y, sp, u)."""
    process, deadtime_s = _build_process(model_type, K, tau, theta, tau2, leak)
    controller = _build_controller(mode, Kp, Ti, Td, beta, deriv_on, filt_N, umin, umax, aw_track)

    # Canonical back-end entry
    if hasattr(_sim, "simulate"):
        t, sp_arr, y, u, _d, _uvalve = _sim.simulate(
            process, controller,
            t_end=float(horizon), dt=float(dt), sp=float(sp_value),
            u0=float(u0), y0=float(y0), deadtime_s=float(deadtime_s)
        )
        return t, y, sp_arr, u

    # Optional alternate name if your back-end already provides it
    if hasattr(_sim, "simulate_closed_loop"):
        return _sim.simulate_closed_loop(
            model_type=model_type, K=K, tau=tau, theta=theta, tau2=tau2, leak=leak,
            mode=mode, Kp=Kp, Ti=Ti, Td=Td, beta=beta, deriv_on=deriv_on, filt_N=filt_N,
            aw_track=aw_track, umin=umin, umax=umax, sp_value=sp_value, y0=y0, u0=u0,
            dt=dt, horizon=horizon
        )

    raise ImportError("No usable simulate() or simulate_closed_loop() in pid_tuner.simulate.sim")


# ---------- streaming simulate (updates every ~update_period) ----------

def streaming_closed_loop(
    *,
    model_type: str, K: float, tau: float, theta: float, tau2: float, leak: float,
    mode: str, Kp: float, Ti: float, Td: float, beta: float, deriv_on: str, filt_N: float,
    aw_track: bool, umin: float, umax: float, sp_value: float, y0: float, u0: float,
    dt: float, horizon: float, update_period: float = 1.0
) -> Iterator[tuple[Sequence[float], Sequence[float], Sequence[float], Sequence[float]]]:
    """
    Yields (t, y, sp, u) growing arrays periodically.
    If a native realtime generator exists, use it; else re-sim up to elapsed.
    """
    # Try native realtime first
    try:
        from pid_tuner.simulate import realtime as _rt
        if hasattr(_rt, "simulate_stream"):
            process, deadtime_s = _build_process(model_type, K, tau, theta, tau2, leak)
            controller = _build_controller(mode, Kp, Ti, Td, beta, deriv_on, filt_N, umin, umax, aw_track)

            gen = _rt.simulate_stream(
                process, controller,
                dt=float(dt), sp=float(sp_value),
                u0=float(u0), y0=float(y0), deadtime_s=float(deadtime_s)
            )
            last_emit = time.time()
            t_list: List[float] = []
            y_list: List[float] = []
            sp_list: List[float] = []
            u_list: List[float] = []
            while True:
                t_chunk, sp_chunk, y_chunk, u_chunk = next(gen)
                t_list.extend(t_chunk)
                sp_list.extend(sp_chunk)
                y_list.extend(y_chunk)
                u_list.extend(u_chunk)
                if t_list and t_list[-1] >= horizon:
                    yield t_list, y_list, sp_list, u_list
                    break
                if (time.time() - last_emit) >= update_period:
                    yield t_list, y_list, sp_list, u_list
                    last_emit = time.time()
            return
    except Exception:
        pass  # fall back

    # Fallback: re-sim to current elapsed time and yield
    process, deadtime_s = _build_process(model_type, K, tau, theta, tau2, leak)
    controller = _build_controller(mode, Kp, Ti, Td, beta, deriv_on, filt_N, umin, umax, aw_track)

    start_wall = time.time()
    last_emit = start_wall
    elapsed = 0.0
    while elapsed < horizon:
        now = time.time()
        elapsed = min(now - start_wall, horizon)
        # guard to avoid zero-length run
        t_end = float(elapsed if elapsed > 0 else dt)

        t, sp_arr, y, u, _d, _uvalve = _sim.simulate(
            process, controller,
            t_end=t_end, dt=float(dt), sp=float(sp_value),
            u0=float(u0), y0=float(y0), deadtime_s=float(deadtime_s)
        )

        if (now - last_emit) >= update_period or elapsed >= horizon:
            yield t, y, sp_arr, u
            last_emit = now

        time.sleep(0.05)
