
import numpy as np
import time
from typing import Generator, Tuple
from ..utils.filters import deadtime_buffer
from ..valves.valve import characteristic, apply_deadband_stiction

def simulate_realtime(process, controller, *, sp: float, u0: float, y0: float,
                      dt: float, deadtime_s: float, d_profile, noise_std: float,
                      valve_char: str, deadband: float, stiction: float, pos_ov: float,
                      speed: float = 1.0) -> Generator[Tuple[float,float,float,float,float,float], None, None]:
    """
    Yields (t, sp, y, u, d, u_valve) at each step.
    d_profile: callable f(t) -> disturbance value
    speed: 1.0 = real-time; 2.0 = 2x faster; 0.5 = half-speed
    """
    t = 0.0
    process.reset(y0); controller.reset(u0=u0, I0=0.0)
    delay = deadtime_buffer(int(round(deadtime_s/dt)))
    v_prev = u0
    last_wall = time.perf_counter()
    while True:
        d = float(d_profile(t)) if callable(d_profile) else 0.0
        u = controller.step(sp, process.y, dt)
        v_eff = apply_deadband_stiction(u, v_prev, deadband=deadband, stiction=stiction, pos_overshoot=pos_ov)
        v_prev = v_eff
        u_valve = characteristic(v_eff, valve_char)
        u_delayed = delay(u_valve/100.0)
        y = process.step(u_delayed, d, dt)
        if noise_std>0.0:
            y += np.random.normal(0.0, noise_std)
        yield (t, sp, y, u, d, u_valve)
        t += dt
        # wall-clock pacing
        if speed > 0:
            target = dt / speed
            now = time.perf_counter()
            sleep_time = target - (now - last_wall)
            if sleep_time > 0:
                time.sleep(sleep_time)
            last_wall = time.perf_counter()
        else:
            # speed==0 → as fast as possible
            pass
