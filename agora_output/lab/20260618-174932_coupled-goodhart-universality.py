import numpy as np, time

# Coupled-Goodhart, optimized: partition (not quantile) for threshold, damped fixed point.
# Up-sweep (init g=0) vs down-sweep (init g=GCAP) -> hysteresis = first-order signature.
W, H, Q, GCAP, ITERS = 2.0, 0.25, 0.10, 25.0, 160

def solve(a, k, J, init, iters=ITERS):
    S, N = a.shape
    n = max(1, int(round(Q * N)))
    kth = N - n
    g = np.full((S, N), init, dtype=float)
    inv = 1.0 / np.sqrt(2 * np.pi)
    for _ in range(iters):
        m = 1.0 + J * g.mean(axis=1, keepdims=True)
        P = a + g
        tau = np.partition(P, kth, axis=1)[:, kth][:, None]
        z = (P - tau) / H
        g_new = np.clip(k * m * (W / H) * (inv * np.exp(-0.5 * z * z)), 0.0, GCAP)
        g = 0.5 * g + 0.5 * g_new
    P = a + g
    tau = np.partition(P, kth, axis=1)[:, kth][:, None]
    sel = P >= tau
    idx = np.argsort(a, axis=1)[:, -n:]
    base = np.take_along_axis(a, idx, axis=1).mean(axis=1)
    eta = np.clip(np.nanmean(np.where(sel, a, np.nan), axis=1) / base, 0.0, 1.0)
    return eta

def run(N, Js, seeds, master=0):
    rng = np.random.default_rng(master + N)
    a = rng.standard_normal((seeds, N)); k = rng.uniform(0, 1, (seeds, N))
    up = np.array([solve(a, k, J, 0.0).mean() for J in Js])
    dn = np.array([solve(a, k, J, GCAP).mean() for J in Js])
    vu = np.array([solve(a, k, J, 0.0).var() for J in Js])
    return up, dn, vu

t0 = time.time()
Js = np.linspace(0, 12, 19)
print("COARSE SCAN — coupled Goodhart")
print("J grid:", " ".join(f"{j:.1f}" for j in Js))
res = {}
for N in [500, 2000, 8000]:
    seeds = {500: 200, 2000: 120, 8000: 50}[N]
    up, dn, vu = run(N, Js, seeds)
    res[N] = (up, dn, vu)
    hyst = np.abs(up - dn)
    chi = N * vu
    print(f"\nN={N}: up-sweep eta = " + " ".join(f"{x:.2f}" for x in up))
    print(f"N={N}: dn-sweep eta = " + " ".join(f"{x:.2f}" for x in dn))
    print(f"N={N}: max hysteresis |up-dn| = {hyst.max():.3f} at J={Js[hyst.argmax()]:.1f}  | peak chi=N*Var = {chi.max():.2f} at J={Js[chi.argmax()]:.1f}")

print("\n--- N-dependence (transition vs crossover) ---")
print("max |d eta/dJ| (up):", {N: round(np.max(np.abs(np.diff(res[N][0])/np.diff(Js))), 2) for N in res})
print("peak chi=N*Var(eta):", {N: round((N*res[N][2]).max(), 2) for N in res})
print("max hysteresis:", {N: round(np.abs(res[N][0]-res[N][1]).max(), 3) for N in res})
print(f"runtime {time.time()-t0:.0f}s")
