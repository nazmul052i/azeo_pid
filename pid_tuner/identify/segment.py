
import numpy as np

def moving_median(x, win):
    if win <= 1: return np.asarray(x, float)
    x = np.asarray(x, float)
    w = int(max(1, win))
    med = np.empty_like(x, dtype=float)
    for i in range(len(x)):
        a = max(0, i - w//2); b = min(len(x), i + w//2 + 1)
        med[i] = np.median(x[a:b])
    return med

def detect_steps_by_diff(t, act, *, min_step=0.01, dwell_pre=1.0, dwell_post=5.0, smooth_window=5):
    t = np.asarray(t, dtype=float); act = np.asarray(act, dtype=float)
    if len(t) != len(act): raise ValueError("t and act lengths differ")
    if len(t) < 4: return []

    sm = moving_median(act, smooth_window)
    d = np.diff(sm, prepend=sm[0])
    cand = np.where(np.abs(d) >= min_step)[0]

    out = []
    for k in cand:
        tt = t[k]
        if tt - t[0] < dwell_pre: continue
        if t[-1] - tt < dwell_post: continue
        du = d[k]
        if out and abs(tt - out[-1]['t']) < 0.5*(dwell_pre + dwell_post):
            if abs(du) > abs(out[-1]['du']):
                out[-1] = {'k': int(k), 't': float(tt), 'du': float(du)}
            continue
        out.append({'k': int(k), 't': float(tt), 'du': float(du)})
    return out

def cusum_change_points(x, k=0.5, h=5.0):
    x = np.asarray(x, float)
    gpos = 0.0; gneg = 0.0; idx = []
    mu = np.median(x); s = np.median(np.abs(x - mu)) + 1e-9
    for i, xi in enumerate(x):
        z = (xi - mu) / s
        gpos = max(0.0, gpos + z - k)
        gneg = min(0.0, gneg + z + k)
        if gpos > h:
            idx.append(i); gpos = 0.0; gneg = 0.0; mu = np.median(x[:i+1])
        elif gneg < -h:
            idx.append(i); gpos = 0.0; gneg = 0.0; mu = np.median(x[:i+1])
    return idx
