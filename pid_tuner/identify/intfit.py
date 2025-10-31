
import numpy as np

def _largest_step(x):
    dx = np.diff(x)
    k = int(np.argmax(np.abs(dx)))
    return k, dx[k]

def fit_integrator_from_step(t, u, y, theta_grid=None):
    t = np.asarray(t, dtype=float); u = np.asarray(u, dtype=float); y = np.asarray(y, dtype=float)
    n = len(t)
    if n < 10: raise ValueError("Not enough samples")

    k0, du = _largest_step(u)
    t0 = t[k0+1] if k0+1 < n else t[k0]

    T = t[-1] - t[0]; dt = np.median(np.diff(t))
    if theta_grid is None:
        theta_grid = np.linspace(0.0, min(0.6*T, max(dt, T/2)), 40)

    best = dict(sse=np.inf)
    for th in theta_grid:
        tt = np.clip(t - (t0 + th), 0, None)
        A = np.vstack([du*tt, np.ones_like(tt)]).T  # (k', y0)
        sol, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        kprime, y0_est = sol[0], sol[1]
        yhat = y0_est + du*kprime*tt
        sse = float(np.sum((y - yhat)**2))
        if sse < best["sse"]:
            best = dict(sse=sse, kprime=kprime, theta=th, t0=t0, du=du, y0=y0_est, yhat=yhat)
    return best
