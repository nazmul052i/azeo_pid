
import numpy as np
from ..utils.filters import deadtime_buffer
from ..valves.valve import characteristic, apply_deadband_stiction

def simulate(process, controller, *, t_end=100.0, dt=0.1, sp=1.0, u0=0.0, y0=0.0,
             deadtime_s=0.0, d_step=0.0, d_at=50.0, noise_std=0.0,
             valve_char="Linear", deadband=0.0, stiction=0.0, pos_ov=0.0):
    n = int(t_end/dt)+1
    t = np.linspace(0, t_end, n)
    sp_arr = np.zeros(n); y = np.zeros(n); u = np.zeros(n); d = np.zeros(n); u_valve = np.zeros(n)

    process.reset(y0); controller.reset(u0=u0, I0=0.0)
    delay = deadtime_buffer(int(round(deadtime_s/dt)))
    v_prev = u0

    for k in range(n):
        sp_arr[k] = sp
        d[k] = d_step if t[k] >= d_at else 0.0

        uk = controller.step(sp, y[k-1] if k>0 else y0, dt)  # controller OP (%)
        v_eff = apply_deadband_stiction(uk, v_prev, deadband=deadband, stiction=stiction, pos_overshoot=pos_ov)
        v_prev = v_eff
        v_char = characteristic(v_eff, valve_char)
        u_valve[k] = v_char

        u_delayed = delay(v_char / 100.0)  # normalize to 0..1
        yk = process.step(u_delayed, d[k], dt)
        if noise_std > 0.0:
            yk += np.random.normal(0.0, noise_std)
        y[k] = yk; u[k] = uk

    return t, sp_arr, y, u, d, u_valve
