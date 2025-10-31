
import numpy as np

def _largest_step(x):
    """Return (index_of_step, step_size) using largest absolute diff heuristic."""
    dx = np.diff(x)
    k = int(np.argmax(np.abs(dx)))
    return k, dx[k]

def _median_segment(arr, start_idx, end_idx):
    start = max(0, start_idx)
    end = min(len(arr), end_idx)
    if end <= start:
        return float(np.median(arr))
    return float(np.median(arr[start:end]))

def fit_fopdt_from_step(t, u, y):
    """
    Fit a simple FOPDT (no explicit measurement noise) to step test data.
    Assumptions:
      - Single step in u or sp occurs at time t0 (largest magnitude change)
      - y starts near steady, then transitions to a new steady
    Returns dict with K, tau, theta, t0, y0, yf, du, sse, and model curve yhat.
    """
    t = np.asarray(t, dtype=float)
    u = np.asarray(u, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(t)
    if n < 10:
        raise ValueError("Not enough data points")

    # detect step on u
    k0, du = _largest_step(u)
    t0 = t[k0+1] if k0+1 < n else t[k0]

    # steady estimates
    pre_med = _median_segment(y, 0, k0)
    post_med = _median_segment(y, int(0.8*n), n)  # last 20%

    # initial guesses
    if abs(du) < 1e-12:
        du = np.sign(post_med - pre_med) * 1.0  # fallback
    K_guess = (post_med - pre_med) / du if abs(du) > 0 else 1.0
    tau_guess = max( (t[-1]-t0)/5.0, (np.median(np.diff(t)))*5 )
    theta_guess = max(0.0, (t0 - t[0]))

    # grids for theta and tau
    T = t[-1] - t[0]
    dt = np.median(np.diff(t))
    theta_grid = np.linspace(0.0, min(T*0.6, max(dt, T/2)), 25)
    tau_grid = np.geomspace(max(dt, T/50), max(dt*5, T*2), 40)

    best = dict(sse=np.inf)
    for th in theta_grid:
        for tau in tau_grid:
            # determine K by least squares with fixed tau, theta
            # Model: yhat = y_pre + du*K*(1 - exp(-(t - (t0+th))/tau))_+
            tt = t - (t0 + th)
            resp = (1.0 - np.exp(-np.clip(tt, 0, None)/tau))
            # build linear least squares for K and offset y_pre
            A = np.vstack([du*resp, np.ones_like(resp)]).T
            sol, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            K_est, ypre_est = sol[0], sol[1]
            yhat = ypre_est + du*K_est*resp
            sse = float(np.sum((y - yhat)**2))
            if sse < best["sse"]:
                best = dict(sse=sse, K=K_est, tau=tau, theta=th, yhat=yhat, y0=ypre_est,
                            t0=t0, du=du, yf=float(yhat[-1]))

    # ensure reasonable signs
    if np.sign(best["K"]*du) != np.sign(post_med - pre_med):
        best["K"] = -best["K"]

    return best
