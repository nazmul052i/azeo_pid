
import numpy as np

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def deadtime_buffer(dt_steps: int):
    buf = [0.0] * max(1, int(dt_steps))
    idx = 0
    def push(x: float) -> float:
        nonlocal idx
        buf[idx] = x
        idx = (idx + 1) % len(buf)
        return buf[idx]  # returns value dt_steps steps ago
    return push

def lowpass(prev: float, x: float, tau: float, dt: float) -> float:
    """First-order low-pass. If tau<=0 -> passthrough."""
    if tau <= 0.0:
        return x
    a = np.exp(-dt / max(1e-12, tau))
    return a*prev + (1.0 - a)*x
