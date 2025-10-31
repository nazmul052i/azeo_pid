
import numpy as np

def _largest_step(x):
    dx = np.diff(x)
    k = int(np.argmax(np.abs(dx)))
    return k, dx[k]

def _median_segment(arr, start_idx, end_idx):
    start = max(0, start_idx); end = min(len(arr), end_idx)
    if end <= start: return float(np.median(arr))
    return float(np.median(arr[start:end]))

def _sopdt_step_kernel(t, tau1, tau2):
    t = np.asarray(t, dtype=float)
    tau1 = max(1e-9, float(tau1)); tau2 = max(1e-9, float(tau2))
    if abs(tau1 - tau2) < 1e-9:
        tau = (tau1 + tau2)/2.0
        g = 1.0 - (1.0 + t/tau)*np.exp(-t/tau)
    else:
        g = 1.0 - (tau1*np.exp(-t/tau1) - tau2*np.exp(-t/tau2)) / (tau1 - tau2)
    g[t < 0] = 0.0
    return g

def fit_sopdt_from_step(t, u, y, theta_grid=None, tau1_grid=None, tau2_grid=None):
    t = np.asarray(t, dtype=float); u = np.asarray(u, dtype=float); y = np.asarray(y, dtype=float)
    n = len(t)
    if n < 12: raise ValueError("Not enough samples for SOPDT fit")

    k0, du = _largest_step(u); t0 = t[k0+1] if k0+1 < n else t[k0]

    pre_med  = _median_segment(y, 0, max(1, k0))
    post_med = _median_segment(y, int(0.8*n), n)

    T = t[-1] - t[0]; dt = np.median(np.diff(t))

    if theta_grid is None:
        theta_grid = np.linspace(0.0, min(T*0.6, max(dt, T/2)), 24)
    if tau1_grid is None:
        tau1_grid = np.geomspace(max(dt, T/50), max(dt*5, T*2), 28)
    if tau2_grid is None:
        tau2_grid = np.geomspace(max(dt, T/80), max(dt*3, T), 24)

    best = dict(sse=np.inf)
    for th in theta_grid:
        tt = t - (t0 + th)
        for tau1 in tau1_grid:
            for tau2 in tau2_grid:
                if tau1 < tau2: 
                    tau1, tau2 = tau2, tau1
                g = _sopdt_step_kernel(tt, tau1, tau2)
                A = np.vstack([du*g, np.ones_like(g)]).T
                sol, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                K_est, y0_est = sol[0], sol[1]
                yhat = y0_est + du*K_est*g
                sse = float(np.sum((y - yhat)**2))
                if sse < best["sse"]:
                    best = dict(sse=sse, K=K_est, tau1=tau1, tau2=tau2, theta=th,
                                yhat=yhat, y0=y0_est, t0=t0, du=du, yf=float(yhat[-1]))
    if np.sign(best["K"]*du) != np.sign(post_med - pre_med):
        best["K"] = -best["K"]
    return best
