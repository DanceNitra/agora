"""
Public runnable probe for the post
"The same classical tradeoff in four AI-memory mechanisms - and where it breaks"
(dancenitra.github.io/agora/public/posts/adaptation-corruption-separation-law.html).

Reproduces every SIMULATION number the post cites, self-contained, pure-numpy, no data files,
no cloud. (The 16-stream real-data asymmetry lives in nab_asymmetry.py, which needs a public
NAB checkout.)

WHAT THIS SHOWS (and what it does NOT). The "adaptation vs corruption" coupling is a classical
result, not a discovery here: it is Grossberg's stability-plasticity dilemma (1980); the fast +
slow-gated escape is Complementary Learning Systems (McClelland, McNaughton & O'Reilly 1995); the
delay/false-alarm floor is CUSUM optimality (Page 1954; Lorden 1971 asymptotic; Moustakides 1986
exact); the B<d boundary is transient change detection (Guepie, Fillatre & Nikiforov 2012). This
probe just makes the cross-mechanism measurement reproducible.

Prints, in order:
  [A] TRUST frontier + two-channel + latency floor           (post: 0.1/1.00, ~13, 2.51/0.04)
  [B] CUSUM red-team: naive EWMA vs two-channel vs CUSUM      (post: 6.08, 2.51, 2.42)
  [C] BOUNDARY: false-distrust(B, d) - escape holds iff B<d   (post: jumps to 1.00 at B>=d)
  [D] REGIME sweep: naive/CUSUM delay ratio across regimes    (post: up to ~2x; REVERSES to 0.92)
  [E] CONSOLIDATION: bounded gate vs unbounded EWMA under an   (post: ~0.5 vs 22.3 at a 150x spike)
      unbounded-magnitude spike

Run:  python separation_law.py
"""
import numpy as np
from collections import deque

# --------------------------------------------------------------------------------------
# [A] + [B]  TRUST / REPUTATION on a binary good/bad stream
# --------------------------------------------------------------------------------------
T, T0, W, MU0, TAU = 200, 100, 25, 0.9, 0.5
P_BAD, SEEDS = 0.1, 500


def gen_turn(rng):
    p = np.where(np.arange(T) < T0, MU0, P_BAD)
    return (rng.random(T) < p).astype(float)


def gen_poison1(rng):
    o = (rng.random(T) < MU0).astype(float)
    o[T0] = 0.0                                  # a single framed bad event in a good stream
    return o


def ewma_trust(o, alpha):
    tr = np.empty(T); s = MU0
    for t in range(T):
        s = alpha * o[t] + (1 - alpha) * s; tr[t] = s
    return tr


def two_channel(o, d, a_fast=0.5, a_slow=0.2, m=7, k=4):
    out = np.empty(T); slow = MU0; fast = MU0; badrun = 0; win = deque(maxlen=m)
    for t in range(T):
        win.append(o[t]); arr = np.asarray(win)
        if np.sum(arr == o[t]) >= k:             # gated slow channel: admit only if corroborated
            slow = a_slow * o[t] + (1 - a_slow) * slow
        fast = a_fast * o[t] + (1 - a_fast) * fast
        badrun = badrun + 1 if o[t] == 0 else 0
        out[t] = fast if badrun >= d else slow   # persistence selector
    return out


def cusum_trust(o, h, delta=0.4):
    S = 0.0; a = np.zeros(T)
    for t in range(T):
        S = max(0.0, S + (MU0 - o[t]) - delta)
        a[t] = 1.0 if S > h else 0.0             # 1 = distrust
    return a                                     # already a "distrust" indicator, not a trust level


def delay_turn_level(tr):
    below = np.where(tr[T0:] < TAU)[0]
    return int(below[0]) if len(below) else (T - T0)


def fd_poison_level(tr):
    return 1.0 if np.any(tr[T0:T0 + W] < TAU) else 0.0


def delay_turn_ind(a):
    below = np.where(a[T0:] > 0)[0]
    return int(below[0]) if len(below) else (T - T0)


def fd_poison_ind(a):
    return 1.0 if np.any(a[T0:T0 + W] > 0) else 0.0


def eval_ewma(alpha):
    dly = np.mean([delay_turn_level(ewma_trust(gen_turn(np.random.default_rng(s)), alpha)) for s in range(SEEDS)])
    fd = np.mean([fd_poison_level(ewma_trust(gen_poison1(np.random.default_rng(9000 + s)), alpha)) for s in range(SEEDS)])
    return float(dly), float(fd)


def eval_tc(d):
    dly = np.mean([delay_turn_level(two_channel(gen_turn(np.random.default_rng(s)), d)) for s in range(SEEDS)])
    fd = np.mean([fd_poison_level(two_channel(gen_poison1(np.random.default_rng(9000 + s)), d)) for s in range(SEEDS)])
    return float(dly), float(fd)


def eval_cusum(h):
    dly = np.mean([delay_turn_ind(cusum_trust(gen_turn(np.random.default_rng(s)), h)) for s in range(SEEDS)])
    fd = np.mean([fd_poison_ind(cusum_trust(gen_poison1(np.random.default_rng(9000 + s)), h)) for s in range(SEEDS)])
    return float(dly), float(fd)


print("=" * 74)
print("[A] TRUST: single EWMA frontier (delay-on-turn vs false-distrust-on-1-poison)")
print(f"{'alpha':>6} | {'turn delay':>10} | {'false-distrust':>14}")
S = {}
for a in (0.05, 0.10, 0.20, 0.40, 0.70):
    S[a] = eval_ewma(a); print(f"{a:>6.2f} | {S[a][0]:10.2f} | {S[a][1]:14.2f}")
print("  -> fast (0.70) reacts in ~0.1 turns but false-distrust 1.00; slow (0.05) delay ~13, fd 0.")

print("\n[A] TWO-CHANNEL trust (gated-slow + fast + persistence selector d)")
print(f"{'d':>3} | {'turn delay':>10} | {'false-distrust':>14}")
TC = {}
for d in (1, 2, 3, 5):
    TC[d] = eval_tc(d); print(f"{d:>3} | {TC[d][0]:10.2f} | {TC[d][1]:14.2f}")
print(f"  -> two-channel(d=3): delay {TC[3][0]:.2f}, fd {TC[3][1]:.2f}  (beats every single rule on BOTH)")
print(f"  -> LATENCY FLOOR: at d=1 the false-distrust collapses back to {TC[1][1]:.2f}")

print("\n" + "=" * 74)
print("[B] CUSUM RED-TEAM: min detection-delay at false-distrust <= 0.05 (lower = better)")
def best_delay(evalfn, params):
    pts = [evalfn(p) for p in params]
    ok = [d for d, fd in pts if fd <= 0.05]
    return min(ok) if ok else float("inf")
b_ewma = best_delay(eval_ewma, [0.05, 0.10, 0.20, 0.40, 0.70])
b_tc = best_delay(eval_tc, [1, 2, 3, 5, 8])
b_cusum = best_delay(eval_cusum, [0.5, 1.0, 1.5, 2.0, 3.0])
print(f"  naive EWMA : {b_ewma:.2f}")
print(f"  two-channel: {b_tc:.2f}")
print(f"  CUSUM      : {b_cusum:.2f}   (provably optimal single statistic; two-channel is near-optimal)")

# --------------------------------------------------------------------------------------
# [C]  BOUNDARY: escape holds iff corruption burst length B < selector delay d
# --------------------------------------------------------------------------------------
print("\n" + "=" * 74)
print("[C] BOUNDARY false-distrust(B, d): poison BURST length B vs selector delay d")


def fd_burst(B, d, seeds=400):
    hits = 0
    for s in range(seeds):
        rng = np.random.default_rng(7000 + s)
        o = (rng.random(T) < MU0).astype(float)
        o[T0:T0 + B] = 0.0                       # a poison BURST of length B (transient corruption)
        tr = two_channel(o, d)
        if np.any(tr[T0:T0 + W] < TAU):
            hits += 1
    return hits / seeds


Bs, Ds = (1, 2, 4, 8, 16), (2, 4, 8)
print("  B \\ d | " + " | ".join(f"d={d:<3}" for d in Ds))
for B in Bs:
    print(f"   {B:>4} | " + " | ".join(f"{fd_burst(B, d):.2f} " for d in Ds))
print("  -> for d=8: escape holds (fd~0) while B<d; once B>=d the burst is indistinguishable from")
print("     real change and false-distrust jumps toward 1.00 (= transient-detection missed-detection).")

# --------------------------------------------------------------------------------------
# [D]  REGIME sweep: the naive/CUSUM advantage is regime-dependent AND REVERSES
# --------------------------------------------------------------------------------------
print("\n" + "=" * 74)
print("[D] REGIME sweep: min-delay@fd<=0.05 ratio naive/CUSUM across (mu0, p_bad)")


def regime_ratio(mu0, pbad):
    global MU0, P_BAD
    save = (MU0, P_BAD); MU0, P_BAD = mu0, pbad
    r = best_delay(eval_ewma, [0.05, 0.10, 0.20, 0.40, 0.70]) / max(1e-9, best_delay(eval_cusum, [0.5, 1.0, 1.5, 2.0, 3.0]))
    MU0, P_BAD = save
    return r


print(f"{'mu0':>5} {'p_bad':>6} | {'naive/CUSUM':>11}")
ratios = []
for mu0, pbad in [(0.8, 0.1), (0.9, 0.1), (0.9, 0.4), (0.95, 0.1), (0.95, 0.4)]:
    r = regime_ratio(mu0, pbad); ratios.append(r)
    print(f"{mu0:>5} {pbad:>6} | {r:>11.2f}")
print(f"  -> ranges from ~{max(ratios):.1f}x (subtle+noisy) DOWN THROUGH 1.0 to {min(ratios):.2f} in the")
print("     easy regime (large clean change) -- i.e. the persistence advantage REVERSES, it does not")
print("     merely 'shrink to zero'. Regime-dependent, not universal.")

# --------------------------------------------------------------------------------------
# [E]  CONSOLIDATION: bounded gate vs unbounded EWMA under unbounded-magnitude spikes
#      (exact port of the heavy-tailed unbounded-check: a random-walk-free latent held at 0,
#       heavy-tailed Student-t natural noise, 8% Pareto-magnitude adversarial spikes)
# --------------------------------------------------------------------------------------
print("\n" + "=" * 74)
print("[E] CONSOLIDATION robust-error (MAE) under UNBOUNDED adversarial spikes (heavy-tailed stream)")
print("    a corroboration/magnitude gate stays bounded; a single EWMA grows ~linearly with spike scale")

TE, SEEDSE, BURNE, TDF = 1500, 25, 60, 3


def _stream(rng, poison_p, spike_scale):
    v = np.zeros(TE)                              # latent value held at 0
    x = v + rng.standard_t(TDF, size=TE)          # heavy-tailed NATURAL noise
    if poison_p > 0:
        mask = rng.random(TE) < poison_p
        mag = spike_scale * (1.0 + rng.pareto(1.5, size=TE))   # UNBOUNDED Pareto magnitude
        signs = rng.choice([-1.0, 1.0], size=TE)
        x[mask] = v[mask] + signs[mask] * mag[mask]
    return v, x


def _ewma(x, alpha):
    y = np.empty_like(x); s = x[0]
    for t in range(len(x)):
        s = alpha * x[t] + (1 - alpha) * s; y[t] = s
    return y


def _gate(x, alpha=0.4, m=11, k=4, band=3.0):
    y = np.empty_like(x); s = x[0]; raw = deque(maxlen=m)
    for t in range(len(x)):
        raw.append(x[t]); arr = np.asarray(raw)
        med = np.median(arr); mad = np.median(np.abs(arr - med)) + 1e-9
        if int(np.sum(np.abs(arr - x[t]) <= band * 1.4826 * mad)) >= k:
            s = alpha * x[t] + (1 - alpha) * s     # admit only a corroborated observation
        y[t] = s
    return y


def _mae_avg(op, spike_scale):
    out = []
    for sd in range(SEEDSE):
        rng = np.random.default_rng(300 + sd)
        v, x = _stream(rng, 0.08, spike_scale)
        y = op(x)
        out.append(float(np.mean(np.abs(y[BURNE:] - v[BURNE:]))))
    return float(np.mean(out))


print(f"{'spike x':>8} | {'gate':>7} | {'ewma0.1':>8} | {'mean':>7}")
for sc in (5, 15, 50, 150):
    gv = _mae_avg(lambda x: _gate(x), sc)
    ev = _mae_avg(lambda x: _ewma(x, 0.1), sc)
    mv = _mae_avg(lambda x: np.cumsum(x) / (np.arange(len(x)) + 1), sc)
    print(f"{sc:>8} | {gv:7.2f} | {ev:8.2f} | {mv:7.2f}")
print("  -> gate stays ~0.5 flat; ewma0.1 reaches ~22 at a 150x spike (the post's headline pair).")
print("     NB: any bounded-influence estimator (median / Huber / trimmed) also stays bounded --")
print("     the honest claim is 'use a bounded-influence + persistence rule', which IS the two-channel form.")
print("\nAll numbers above are pure-numpy and reproducible; see README.md for the mapping to the post.")
