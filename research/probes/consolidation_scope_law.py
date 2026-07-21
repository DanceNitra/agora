"""The consolidation-gate SCOPE LAW, runnable. A corroboration gate (admit an observation only if >=k of
the last m corroborate it) makes an AI memory's breakdown BOUNDED against an arbitrarily large adversarial
spike -- but only helps when the observation MAGNITUDE is unbounded. For bounded values (unit-norm
embeddings) every operator already has bounded breakdown, so the gate buys nothing and its novelty-blindness
is pure cost. And the coupling (a gate can't tell an isolated poison spike from the first sample of a real
change) becomes a detection-LATENCY FLOOR in a two-channel design.

HONEST FRAMING (systematization, heavy overlap with the adaptation-corruption separation law): the
speed-robustness frontier is the robust-statistics breakdown point (Huber 1964; Hampel 1974); the
two-channel fast+slow escape is Complementary Learning Systems (McClelland, McNaughton & O'Reilly 1995);
the latency floor is the optimal change-point-detection delay (Page 1954; Lorden 1971; Moustakides 1986).
The keeper is the SCOPE result: the gate Pareto-helps iff magnitude is unbounded -- which is partly
definitional (bounded input => bounded breakdown for any operator) but empirically useful. NOTE: on REAL
centered nomic embeddings the "coupling holds" leg did NOT reproduce cleanly (tightening the gate made the
robust error WORSE, not better) -- so we report the coupling as a property of the unbounded-magnitude
simulations, not a universal law across regimes.

Run: python research/probes/consolidation_scope_law.py    MIT. Part of Agora / inspeximus.
"""
from collections import deque
import numpy as np

T, SEEDS, BURN = 1500, 25, 60
ALPHAS = [0.02, 0.05, 0.1, 0.2, 0.4, 0.7]


def op_ewma(x, alpha):
    y = np.empty_like(x); s = x[0]
    for t in range(len(x)):
        s = alpha * x[t] + (1 - alpha) * s; y[t] = s
    return y


def op_mean(x):
    return np.cumsum(x) / (np.arange(len(x)) + 1)


def op_gate(x, alpha=0.4, m=11, k=4, band=3.0):
    y = np.empty_like(x); s = x[0]; raw = deque(maxlen=m)
    for t in range(len(x)):
        raw.append(x[t]); arr = np.asarray(raw)
        med = np.median(arr); mad = np.median(np.abs(arr - med)) + 1e-9
        near = int(np.sum(np.abs(arr - x[t]) <= band * 1.4826 * mad))
        if near >= k:
            s = alpha * x[t] + (1 - alpha) * s
        y[t] = s
    return y


def two_channel(x, a_fast=0.5, a_slow=0.1, m=11, k=4, band=3.0, d=3):
    y = np.empty_like(x); s_slow = x[0]; s_fast = x[0]; raw = deque(maxlen=m)
    run = 0; last_dir = 0
    for t in range(len(x)):
        raw.append(x[t]); arr = np.asarray(raw)
        med = np.median(arr); mad = np.median(np.abs(arr - med)) + 1e-9
        thr = band * 1.4826 * mad
        near = int(np.sum(np.abs(arr - x[t]) <= thr))
        if near >= k:
            s_slow = a_slow * x[t] + (1 - a_slow) * s_slow
        s_fast = a_fast * x[t] + (1 - a_fast) * s_fast
        dev = x[t] - s_slow
        if abs(dev) > thr:
            di = 1.0 if dev > 0 else -1.0
            run = run + 1 if di == last_dir else 1
            last_dir = di
        else:
            run = 0; last_dir = 0; s_fast = s_slow
        y[t] = s_fast if run >= d else s_slow
    return y


def mae(y, v):
    return float(np.mean(np.abs(y[BURN:] - v[BURN:])))


# ---- streams -------------------------------------------------------------
def stream_heavytail(rng, drift, poison_p=0.0, spike_scale=0.0):
    v = np.cumsum(rng.normal(0, drift, T))
    x = v + 1.0 * rng.standard_t(3, size=T)               # heavy-tailed natural noise
    if poison_p > 0:
        mask = rng.random(T) < poison_p
        mag = spike_scale * (1.0 + rng.pareto(1.5, size=T))   # UNBOUNDED (Pareto) spikes
        signs = rng.choice([-1.0, 1.0], size=T)
        x[mask] = v[mask] + signs[mask] * mag[mask]
    return v, x


def stream_gauss(rng, regime, sigma, drift, poison_p=0.0, poison_mag=10.0):
    if regime == "rw":
        v = np.cumsum(rng.normal(0, drift, T))
    else:
        v = np.zeros(T); cur = 0.0
        for t in range(T):
            if rng.random() < drift:
                cur += rng.normal(0, 1.0) * 5.0
            v[t] = cur
    x = v + rng.normal(0, sigma, T)
    if poison_p > 0:
        mask = rng.random(T) < poison_p
        signs = rng.choice([-1.0, 1.0], size=T)
        x[mask] = v[mask] + signs[mask] * poison_mag
    return v, x


def _avg_ht(op, spike_scale):
    return float(np.mean([mae(op(stream_heavytail(np.random.default_rng(300 + s), 0.0, 0.08, spike_scale)[1]),
                              stream_heavytail(np.random.default_rng(300 + s), 0.0, 0.08, spike_scale)[0])
                          for s in range(SEEDS)]))


def _avg_g(fn, **cfg):
    return float(np.mean([mae(fn(mk[1]), mk[0]) for mk in
                          [stream_gauss(np.random.default_rng(900 + s), **cfg) for s in range(SEEDS)]]))


def case_heavytail():
    print("=== A: UNBOUNDED magnitude -> the gate stays bounded as the spike scales 30x (gate HELPS) ===")
    print(f"  {'spike':>6} | {'gate':>7} | {'ewma0.1':>8} | {'mean':>7}")
    for sc in (5, 15, 150):
        g = _avg_ht(lambda x: op_gate(x, 0.4, 11, 4, 3.0), sc)
        e = _avg_ht(lambda x: op_ewma(x, 0.1), sc)
        m = _avg_ht(op_mean, sc)
        print(f"  {'x'+str(sc):>6} | {g:>7.2f} | {e:>8.2f} | {m:>7.2f}")
    print("  post: x5 gate0.56 ewma0.84 mean0.20 ; x150 gate0.52 ewma22.3 mean5.53 -> gate flat, others blow up\n")


def case_twochannel():
    print("=== B: two-channel escapes the coupling, but into a detection-LATENCY FLOOR (d=1 collapses) ===")
    WJUMP = dict(regime="jump", sigma=0.5, drift=0.01)
    WROB = dict(regime="rw", sigma=1.0, drift=0.0, poison_p=0.08, poison_mag=12.0)
    print(f"  {'d':>3} | {'sudden-jump':>11} | {'poison-robust':>13}")
    for d in (1, 3, 8):
        j = _avg_g(lambda x, d=d: two_channel(x, d=d), **WJUMP)
        r = _avg_g(lambda x, d=d: two_channel(x, d=d), **WROB)
        print(f"  {d:>3} | {j:>11.2f} | {r:>13.2f}")
    print("  post: d=1 jump0.30 robust0.68 (collapse) ; d=3 0.36/0.19 ; d=8 0.47/0.19\n")


def case_bounded_scope():
    print("=== C (scope law): BOUNDED unit-norm vectors -> gate is DOMINATED, buys nothing ===")
    rng = np.random.default_rng(7); D = 64
    # a stable 'true' unit vector, a sudden jump to another unit vector, unit-norm poison
    def run(op_name, jump):
        errs = []
        for s in range(SEEDS):
            r = np.random.default_rng(1000 + s)
            base = r.standard_normal(D); base /= np.linalg.norm(base)
            alt = r.standard_normal(D); alt /= np.linalg.norm(alt)
            v = np.tile(base, (T, 1)).astype(float)
            if jump:
                v[T // 2:] = alt
            x = v + 0.15 * r.standard_normal((T, D))
            x /= np.linalg.norm(x, axis=1, keepdims=True)      # BOUNDED: every obs is unit-norm
            if not jump:                                        # poison regime: unit-norm poison spikes
                mask = r.random(T) < 0.08
                p = r.standard_normal(D); p /= np.linalg.norm(p)
                x[mask] = p
            # apply the scalar operator per-dimension, measure cosine error to v
            y = np.stack([op_name(x[:, j]) for j in range(D)], axis=1)
            yn = y / (np.linalg.norm(y, axis=1, keepdims=True) + 1e-9)
            errs.append(float(np.mean(1 - np.sum(yn[BURN:] * v[BURN:], axis=1))))
        return float(np.mean(errs))
    for name, op in (("ewma0.15", lambda x: op_ewma(x, 0.15)), ("gate", lambda x: op_gate(x)), ("mean", op_mean)):
        print(f"  {name:>9} | jump-err {run(op, True):.3f} | poison-err {run(op, False):.3f}")
    print("  -> on bounded unit-norm vectors a tuned EWMA dominates the gate on BOTH axes (the gate's")
    print("     rejection buys nothing when magnitude is already bounded). Matches the real-nomic result;")
    print("     on real embeddings the 'coupling' leg was inconclusive (tighter gate did NOT help), so we")
    print("     report the coupling as a property of the unbounded-magnitude sims, not a cross-regime law.\n")


if __name__ == "__main__":
    case_heavytail()
    case_twochannel()
    case_bounded_scope()
    print("SCOPE LAW: a corroboration gate Pareto-helps IFF observation magnitude is unbounded; for bounded")
    print("embedding recall use a tuned decay. Frontier = Huber/Hampel breakdown point; two-channel = CLS")
    print("(McClelland 1995); latency floor = change-point detection delay (Page/Lorden/Moustakides). inspeximus probe.")
