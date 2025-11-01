from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(slots=True)
class StepEvent:
    t0: float            # step start time
    du: float            # OP step magnitude
    pv0: float           # PV just before step
    op0: float           # OP just before step
    idx0: int            # index in arrays
    idx1: int            # end index used for fit


@dataclass(slots=True)
class FitResult:
    model_type: str                 # "FOPDT" | "SOPDT" | "Integrating"
    params: Dict[str, float]        # e.g., {"K":..., "tau":..., "theta":...}
    stats: Dict[str, float]         # {"rss":..., "n":..., "r2":...}


# ------------------ STEP DETECTION ------------------

def detect_steps(t: List[float], op: List[float], min_du: float = 0.5, min_dt: float = 3.0) -> List[StepEvent]:
    """
    Simple median-diff based step detector on OP.
    A step is recognized when |ΔOP| >= min_du and spaced at least min_dt seconds apart.
    """
    if not (t and op) or len(t) != len(op):
        return []
    events: List[StepEvent] = []
    last_t = -1e9
    pv0 = 0.0
    op0 = op[0]
    for i in range(1, len(op)):
        du = op[i] - op[i-1]
        if abs(du) >= min_du and (t[i] - last_t) >= min_dt:
            idx0 = i
            t0 = t[i]
            # look ahead window ~ 5x previous spacing or 60s
            idx1 = min(len(op)-1, i + max(20, int((min_dt / max(t[1]-t[0], 1e-9)) * 5)))
            events.append(StepEvent(t0=t0, du=du, pv0=pv0, op0=op[i-1], idx0=idx0, idx1=idx1))
            last_t = t0
        pv0 = pv0  # pv0 will be set from external PV in fit; keep placeholder var unchanged
    return events


# ------------------ FOPDT FIT ------------------

def fit_fopdt(
    t: List[float],
    pv: List[float],
    op: List[float],
    event: StepEvent,
) -> FitResult:
    """
    Estimate FOPDT parameters (K, tau, theta) from a single OP step event,
    using a grid over theta and tau, solving K by linear least squares.
    PV model: y(t) = y0 + K*du*(1 - exp(-(t - (t0+theta))/tau))_+
    """
    if not (len(t) == len(pv) == len(op)):
        return FitResult("FOPDT", {"K": 1.0, "tau": 10.0, "theta": 1.0}, {"rss": 1e9, "n": 0, "r2": 0.0})

    y0 = pv[event.idx0 - 1] if event.idx0 > 0 else pv[event.idx0]
    t0 = event.t0
    du = event.du
    idx1 = event.idx1

    # search grids
    thetas = _linspace(0.0, (t[idx1] - t0) * 0.6, 25)
    taus = _geomspace(0.2, max(t[idx1]-t0, 1.0)*2.0, 30)

    best = (1e99, 1.0, 10.0, 0.0)  # rss, tau, theta, K
    for theta in thetas:
        for tau in taus:
            # build regressor phi = 1 - exp(-(t-(t0+theta))/tau) for t>t0+theta else 0
            phi = []
            y = []
            for i in range(event.idx0, idx1):
                tt = t[i]
                if tt <= t0 + theta:
                    phi.append(0.0)
                else:
                    phi.append(1.0 - math.exp(-(tt - (t0 + theta)) / tau))
                y.append(pv[i] - y0)
            # K by least squares: min || y - K*du*phi ||^2 ⇒ K = (phi·y)/(du*(phi·phi)+eps)
            num = sum(pi * yi for pi, yi in zip(phi, y))
            den = du * (sum(pi * pi for pi in phi) + 1e-12)
            K = num / den if abs(den) > 0 else 0.0

            rss = sum((yi - K * du * pi) ** 2 for yi, pi in zip(y, phi))
            if rss < best[0]:
                best = (rss, tau, theta, K)

    rss, tau, theta, K = best
    # compute r^2
    mean_y = sum(pv[event.idx0:idx1]) / max(1, (idx1 - event.idx0))
    tss = sum((yi - mean_y) ** 2 for yi in pv[event.idx0:idx1])
    r2 = 1.0 - (rss / (tss + 1e-12))

    return FitResult(
        "FOPDT",
        {"K": float(K), "tau": float(tau), "theta": float(theta)},
        {"rss": float(rss), "n": idx1 - event.idx0, "r2": float(r2)},
    )


# ------------------ SOPDT FIT (heuristic) ------------------

def fit_sopdt_from_fopdt(fopdt: FitResult) -> FitResult:
    """
    Convert an FOPDT fit into a SOPDT guess:
      tau1 + tau2 = tau_fopdt
      choose tau1 = 0.6*tau, tau2 = 0.4*tau (can be refined elsewhere)
    """
    K = float(fopdt.params["K"])
    tau = float(fopdt.params["tau"])
    theta = float(fopdt.params["theta"])
    tau1, tau2 = 0.6 * tau, 0.4 * tau
    return FitResult("SOPDT", {"K": K, "tau1": tau1, "tau2": tau2, "theta": theta, "zeta": 1.0},
                     {"rss": fopdt.stats["rss"], "n": fopdt.stats["n"], "r2": fopdt.stats["r2"]})


# ------------------ INTEGRATING FIT (simple) ------------------

def fit_integrating(
    t: List[float],
    pv: List[float],
    op: List[float],
    event: StepEvent,
) -> FitResult:
    """
    For an integrating process with deadtime:
      dy/dt = Ki * u(t - theta)
    Approximate Ki by linear regression over slope after delay.
    """
    t0 = event.t0
    y0 = pv[event.idx0 - 1] if event.idx0 > 0 else pv[event.idx0]
    du = event.du
    idx1 = event.idx1

    # scan theta to maximize correlation with slope
    best = (1e99, 0.0, 0.1)  # rss, Ki, theta
    thetas = _linspace(0.0, (t[idx1] - t0) * 0.5, 20)
    for theta in thetas:
        # use simple slope from (t0+theta) to idx1
        i_start = event.idx0
        while i_start < idx1 and t[i_start] < t0 + theta:
            i_start += 1
        if i_start + 1 >= idx1:
            continue
        dy = pv[idx1] - pv[i_start]
        dt = t[idx1] - t[i_start]
        slope = dy / max(dt, 1e-9)
        Ki = slope / max(du, 1e-12)
        # rss ~ squared error to linear ramp
        rss = 0.0
        for i in range(i_start, idx1):
            t_rel = t[i] - t[i_start]
            y_hat = pv[i_start] + Ki * du * t_rel
            rss += (pv[i] - y_hat) ** 2
        if rss < best[0]:
            best = (rss, Ki, theta)
    rss, Ki, theta = best
    r2 = 0.0  # keep simple
    return FitResult("Integrating", {"Ki": float(Ki), "theta": float(theta)},
                     {"rss": float(rss), "n": idx1 - event.idx0, "r2": float(r2)})


# ------------------ helpers ------------------

def _linspace(a: float, b: float, n: int) -> List[float]:
    if n <= 1:
        return [a]
    step = (b - a) / (n - 1)
    return [a + i * step for i in range(n)]

def _geomspace(a: float, b: float, n: int) -> List[float]:
    a = max(1e-9, a)
    b = max(a * 1.0001, b)
    if n <= 1:
        return [a]
    r = (b / a) ** (1.0 / (n - 1))
    v = a
    out = []
    for _ in range(n):
        out.append(v)
        v *= r
    return out
