from __future__ import annotations
import threading, time, math, random
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple
from PySide6 import QtCore


@dataclass(slots=True)
class ProcessSpec:
    """Unified process description for the simulator."""
    type: str  # "FOPDT" | "SOPDT" | "Integrating"
    # FOPDT: K, tau, theta
    K: float = 1.0
    tau: float = 20.0
    theta: float = 1.0
    # SOPDT: tau1, tau2 (series), same K, theta
    tau1: float = 20.0
    tau2: float = 5.0
    # Integrating: Ki, theta (Ki dy/dt = u)
    Ki: float = 0.1


@dataclass(slots=True)
class PIDSpec:
    """Generic PID with setpoint weighting and D filter (no units enforcement)."""
    Kp: float = 0.3
    Ti: float = 20.0
    Td: float = 0.0
    beta: float = 1.0     # setpoint weight on P path
    alpha: float = 0.125  # derivative filter factor
    mode: str = "PID"     # "P"|"PI"|"PID"
    d_on: str = "PV"      # "PV"|"Error"
    u_min: float = 0.0
    u_max: float = 100.0
    bias: float = 0.0     # output bias (%)


def _sat(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class RealtimeSim(QtCore.QObject):
    """
    Threaded realtime toy simulator that emits (t, sp, pv, op) once per 'period_s'.
    Uses a simple closed-loop with the internal PID against a FOPDT-like process.
    Replace with a call into your true pid_tuner.simulate.realtime if desired.
    """
    tick = QtCore.Signal(float, float, float, float)

    def __init__(self, period_s: float = 1.0, parent=None):
        super().__init__(parent)
        self._period = max(1e-3, float(period_s))
        self._stop = threading.Event()
        self._thr: threading.Thread | None = None
        self._t = 0.0
        self.sp = 5.0
        self.pv = 0.0
        self.op = 0.0

        # default process & controller
        self.proc = ProcessSpec(type="FOPDT", K=1.0, tau=20.0, theta=1.0)
        self.pid = PIDSpec()

        # internal states
        self._e_int = 0.0
        self._d_state = 0.0
        self._aw = 0.0  # anti-windup backcalc term

    # ----- public control -----
    def start(self):
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()

    def configure(self, proc: ProcessSpec | None = None, pid: PIDSpec | None = None):
        if proc: self.proc = proc
        if pid: self.pid = pid

    # ----- internals -----
    def _pid_step(self, sp: float, pv: float, dt: float) -> float:
        p = self.pid
        if p.mode == "P":
            Ti = 0.0; Td = 0.0
        elif p.mode == "PI":
            Ti = p.Ti; Td = 0.0
        else:
            Ti = p.Ti; Td = p.Td

        e = sp - pv
        ep = p.beta * sp - pv  # setpoint-weighted proportional path
        # Integral (external reset: bias acts like remote output feedback)
        if Ti > 0:
            self._e_int += (e - self._aw) * dt / max(Ti, 1e-12)

        # Derivative (filtered)
        if p.d_on.upper().startswith("PV"):
            x = - (pv)  # derivative on measurement
        else:
            x = e
        # first-order filter: y' = ( (Td * x') - y ) / (alpha*Td)
        # discrete bilinear approx
        if Td > 0:
            a = p.alpha * Td
            self._d_state += (Td / max(a, 1e-12)) * ((x - getattr(self, "_x_prev", 0.0)) / max(dt, 1e-12)) - (self._d_state / max(a, 1e-12)) * dt
        else:
            self._d_state = 0.0
        self._x_prev = x

        u_unsat = p.bias + p.Kp * (ep + self._e_int + Td * self._d_state)
        u = _sat(u_unsat, p.u_min, p.u_max)
        # anti-windup back-calculation
        self._aw = (u - u_unsat) * 0.5  # tracking factor
        return u

    def _plant_step(self, u: float, dt: float):
        pr = self.proc
        if pr.type == "FOPDT":
            # deadtime approximated by a bucket delay line of length theta
            # implement as a circular buffer with step dt resolution
            qlen = max(1, int(round(pr.theta / dt)))
            if not hasattr(self, "_u_q"):
                self._u_q = [0.0] * qlen
                self._q_idx = 0
            self._u_q[self._q_idx] = u
            self._q_idx = (self._q_idx + 1) % qlen
            u_delayed = self._u_q[self._q_idx] if qlen > 0 else u
            # first-order dynamics: y' = (K*u - y)/tau
            self.pv += (pr.K * u_delayed - self.pv) * dt / max(pr.tau, 1e-12)

        elif pr.type == "SOPDT":
            # two first-orders in series with deadtime
            qlen = max(1, int(round(pr.theta / dt)))
            if not hasattr(self, "_u_q2"):
                self._u_q2 = [0.0] * qlen
                self._q2 = 0
                self._x1 = 0.0
            self._u_q2[self._q2] = u
            self._q2 = (self._q2 + 1) % qlen
            u_delayed = self._u_q2[self._q2] if qlen > 0 else u

            self._x1 += (pr.K * u_delayed - self._x1) * dt / max(pr.tau1, 1e-12)
            self.pv  += (self._x1 - self.pv) * dt / max(pr.tau2, 1e-12)

        else:  # Integrating with deadtime
            qlen = max(1, int(round(pr.theta / dt)))
            if not hasattr(self, "_u_qi"):
                self._u_qi = [0.0] * qlen
                self._qi = 0
            self._u_qi[self._qi] = u
            self._qi = (self._qi + 1) % qlen
            u_delayed = self._u_qi[self._qi] if qlen > 0 else u
            self.pv += pr.Ki * u_delayed * dt

    def _run(self):
        self._t = 0.0
        self._e_int = 0.0
        self._d_state = 0.0
        self._aw = 0.0
        self._x_prev = 0.0
        self.pv = 0.0
        self.op = 0.0

        dt = self._period
        while not self._stop.is_set():
            u = self._pid_step(self.sp, self.pv, dt)
            self.op = u
            self._plant_step(u, dt)

            self._t += dt
            self.tick.emit(self._t, self.sp, self.pv, self.op)
            time.sleep(self._period)


# -------- batch simulator (offline) --------

def simulate_batch(
    t_end: float,
    dt: float,
    proc: ProcessSpec,
    pid: PIDSpec,
    sp_schedule: Iterable[Tuple[float, float]],  # list of (time, sp_value)
    noise_std: float = 0.0,
) -> Dict[str, List[float]]:
    """
    Deterministic offline simulation. Returns dict with lists: t, sp, pv, op.
    Uses the same plant/controller equations as RealtimeSim.
    """
    rt = RealtimeSim(period_s=dt)
    rt.configure(proc=proc, pid=pid)

    # init internal states (mirror realtime)
    rt._t = 0.0
    rt._e_int = 0.0
    rt._d_state = 0.0
    rt._aw = 0.0
    rt._x_prev = 0.0
    rt.pv = 0.0
    rt.op = 0.0
    rt.sp = 0.0

    t = 0.0
    idx_sched = 0
    sched = sorted(list(sp_schedule), key=lambda x: x[0])
    if sched:
        rt.sp = sched[0][1]

    T, SP, PV, OP = [], [], [], []

    while t <= t_end + 1e-12:
        # update setpoint if needed
        while idx_sched + 1 < len(sched) and t >= sched[idx_sched + 1][0] - 1e-12:
            idx_sched += 1
            rt.sp = sched[idx_sched][1]

        u = rt._pid_step(rt.sp, rt.pv, dt)
        rt.op = u
        rt._plant_step(u, dt)

        pv_noisy = rt.pv + (random.gauss(0.0, noise_std) if noise_std > 0 else 0.0)

        T.append(t); SP.append(rt.sp); PV.append(pv_noisy); OP.append(rt.op)
        t += dt

    return {"t": T, "sp": SP, "pv": PV, "op": OP}
