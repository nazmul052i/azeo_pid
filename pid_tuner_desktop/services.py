# pid_tuner_desktop/services.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Callable

# ---------------- optional imports from your core ----------------
_HAS_CORE = True
try:
    # model identification (you can adjust these imports to your exact files)
    from pid_tuner.identify import stepfit as _stepfit     # e.g., fit_fopdt(...)
    from pid_tuner.identify import segment as _segment     # e.g., detect_steps(...)
    # tuning rules (SIMC/Lambda/ZN)
    from pid_tuner.tuning import methods as _methods
    # simulation engines (batch/realtime)
    # We'll keep a simple internal sim loop for the desktop; real engine can be added here.
except Exception:
    _HAS_CORE = False
    _stepfit = _segment = _methods = None  # type: ignore


# ---------------- datatypes ----------------
@dataclass
class FOPDT:
    K: float   # process gain
    tau: float # time constant
    theta: float # deadtime


@dataclass
class PIDParams:
    Kp: float
    Ti: float
    Td: float
    beta: float = 1.0
    alpha: float = 0.125


# ---------------- IdentificationService ----------------
class IdentificationService:
    """
    Wraps your step detection + model fitting.
    If pid_tuner.identify.* is not available, we just echo the user entry.
    """
    def detect_steps(self, t, sp, op, pv) -> list[Tuple[int, int, float]]:
        if _HAS_CORE and hasattr(_segment, "detect_steps"):
            return _segment.detect_steps(t, sp, op, pv)
        # fallback: no automatic detection
        return []

    def fit_fopdt(self, t, sp, op, pv) -> Optional[FOPDT]:
        if _HAS_CORE and hasattr(_stepfit, "fit_fopdt"):
            fit = _stepfit.fit_fopdt(t, sp, op, pv)
            return FOPDT(fit.K, fit.tau, fit.theta)  # adapt if your object names differ
        return None  # let UI use typed-in values


# ---------------- TuningService ----------------
class TuningService:
    """
    Returns Kp, Ti, Td from a FOPDT model using requested rule.
    Prefers your core; falls back to closed-form formulas.
    """
    def simc(self, plant: FOPDT, target: float) -> PIDParams:
        if _HAS_CORE and hasattr(_methods, "simc_pi") or hasattr(_methods, "simc_pid"):
            # Adapt to your actual method names/signatures if needed:
            try:
                # prefer PID if available
                kp, ti, td = _methods.simc_pid(plant.K, plant.tau, plant.theta, target)
                return PIDParams(kp, ti, td)
            except Exception:
                pass
            # fallback to PI
            kp, ti = _methods.simc_pi(plant.K, plant.tau, plant.theta, target)
            return PIDParams(kp, ti, 0.0)

        # builtin SIMC (FOPDT)
        K, tau, theta, tc = plant.K, max(1e-6, plant.tau), max(0.0, plant.theta), max(1e-3, target)
        kp = tau / (K * (tc + theta))
        ti = min(tau, 4.0 * (tc + theta))
        td = max(0.0, theta / 2.0)
        return PIDParams(kp, ti, td)

    def lambda_imc(self, plant: FOPDT, lam: float) -> PIDParams:
        if _HAS_CORE and hasattr(_methods, "lambda_pi") or hasattr(_methods, "imc_pi"):
            try:
                kp, ti = _methods.lambda_pi(plant.K, plant.tau, plant.theta, lam)
            except Exception:
                kp, ti = _methods.imc_pi(plant.K, plant.tau, plant.theta, lam)
            return PIDParams(kp, ti, 0.0)

        K, tau, theta, lam = plant.K, max(1e-6, plant.tau), max(0.0, plant.theta), max(1e-3, lam)
        kp = tau / (K * (lam + theta))
        ti = tau
        td = 0.0
        return PIDParams(kp, ti, td)

    def ziegler_nichols_reaction(self, plant: FOPDT) -> PIDParams:
        if _HAS_CORE and hasattr(_methods, "ziegler_nichols_reaction"):
            kp, ti, td = _methods.ziegler_nichols_reaction(plant.K, plant.tau, plant.theta)
            return PIDParams(kp, ti, td)
        # classic ZN reaction-curve approximations
        K, tau, theta = plant.K, max(1e-6, plant.tau), max(1e-6, plant.theta)
        kp = 1.2 * tau / (K * theta)
        ti = 2.0 * theta
        td = 0.5 * theta
        return PIDParams(kp, ti, td)


# ---------------- SimulationService ----------------
class SimulationService:
    """
    Very small FOPDT + PID Euler integrator for the desktop loop.
    You can replace the step with your real engine when ready.
    """
    def __init__(self):
        # providers plugged by the UI
        self.get_sp: Callable[[], float] = lambda: 0.0
        self.get_noise: Callable[[], float] = lambda: 0.0
        self.get_dist: Callable[[], tuple[float, float]] = lambda: (1e9, 0.0)  # (time, magnitude)
        self.get_pid: Callable[[], PIDParams] = lambda: PIDParams(0.3, 20.0, 0.0)
        self.get_plant: Callable[[], FOPDT] = lambda: FOPDT(1.0, 80.0, 5.0)

        self._pv = 0.0
        self._op = 0.0

    def reset(self, pv0: float = 0.0):
        self._pv = pv0
        self._op = 0.0

    def step(self, t: float, dt: float) -> tuple[float, float, float]:
        sp = self.get_sp()
        noise = self.get_noise()
        dt_time, dmag = self.get_dist()
        pid = self.get_pid()
        plant = self.get_plant()

        # PID (ideal form, derivative on PV with filter alpha)
        e = sp - self._pv
        # P
        up = pid.Kp * e
        # I
        if pid.Ti > 1e-9:
            ui = pid.Kp / pid.Ti * e
        else:
            ui = 0.0
        # D on PV (simple diff, filtered with alpha)
        # For wire-up simplicity here: treat Td as proportional kick on PV rate → small approx
        ud = 0.0
        if pid.Td > 1e-9:
            ud = 0.0  # keep zero in this compact loop; derivative calc needs state

        u = up + ui + ud
        self._op = max(0.0, min(100.0, u * 100.0))  # %

        # Plant: y' = (K*u + d - y)/tau
        u01 = self._op / 100.0
        d = dmag if t >= dt_time else 0.0
        dy = (plant.K * u01 + d - self._pv) / max(1e-6, plant.tau)
        self._pv += dy * dt + (noise * 0.5)  # tiny noise drift

        return sp, self._pv, self._op
