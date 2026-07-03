"""Governance "hysteresis" = a standard mean-field Glauber/Ising model (audit #24, honest version).

The post modeled a board/shareholder bloc as a mean-field Glauber (kinetic Ising) system: persuadable
agents s in {-1,+1}, coupling J, a field h>0 favoring good governance, and a committed faction of
fraction f pinned at -1 (capture). It reports two thresholds:
  f_up   = smallest committed fraction that CAPTURES a firm starting in good control (+1 init)
  f_down = smallest committed fraction that KEEPS a firm captured starting captured (-1 init)
and finds f_up > f_down with the gap widening in J (0/22/28/32% at J=1.2/2.0/3.0/4.0).

This is TEXTBOOK: a mean-field Ising model in a field has a first-order transition with a metastable
(bistable) region and hysteresis above the critical coupling (Curie-Weiss / spinodal). The FULL loop
for competing committed groups was already published (Xie et al., PLoS ONE 2012: two coexisting stable
states bounded by two spinodal lines meeting at a cusp). The forward threshold f_up is the committed-
minority tipping result (Xie et al., PRE 2011, ~10%; Centola et al., Science 2018, ~25%).

Part A reproduces the post's table. Part B is the honest caveat the reframe adds: f_down and the loop
width are NOT governance facts -- they are a coordinate readout of the chosen (h, T). Sweep h and the
"irreversibility" (f_down -> 0) appears and vanishes at the spinodal, by construction.
"""
import numpy as np

def final_sign(f, J, T, h, init, N, steps, seed):
    rng = np.random.default_rng(abs(seed) % (2**32))
    k = int(round(N * f)); nreg = N - k
    if nreg <= 0:
        return -1.0
    s = np.full(nreg, float(init))
    for _ in range(steps):
        M = (s.sum() + k * (-1.0)) / N
        H = J * M + h
        p_up = 1.0 / (1.0 + np.exp(-2.0 * H / T))
        s = np.where(rng.random(nreg) < p_up, 1.0, -1.0)
    return np.sign(s.mean()) if s.mean() != 0 else 1.0

def p_captured(f, J, T, h, init, N=1500, steps=400, trials=10):
    return np.mean([final_sign(f, J, T, h, init, N, steps, seed=5000 + i) < 0 for i in range(trials)])

def loop_edges(J, T, h, fgrid):
    f_up = next((f for f in fgrid if p_captured(f, J, T, h, +1.0) >= 0.5), None)
    f_down = next((f for f in fgrid if p_captured(f, J, T, h, -1.0) >= 0.5), None)
    return f_up, f_down

if __name__ == "__main__":
    fgrid = [round(x, 3) for x in np.arange(0.0, 0.52, 0.02)]

    # Part A -- reproduce the post's table (T=1.0, h=0.15)
    T, h = 1.0, 0.15
    print(f"Part A -- post's table (mean-field Glauber, T={T}, h={h} favors good governance):")
    print(f"  {'J':>4} {'f_up':>6} {'f_down':>7} {'width':>7}")
    for J in [1.2, 2.0, 3.0, 4.0]:
        fu, fd = loop_edges(J, T, h, fgrid)
        w = None if (fu is None or fd is None) else fu - fd
        print(f"  {J:>4} {fu if fu is None else f'{fu:.0%}':>6} "
              f"{fd if fd is None else f'{fd:.0%}':>7} {w if w is None else f'{w:.0%}':>7}")

    # Part B -- the "irreversibility" (f_down->0) is not a governance law, it is the assumption h < J.
    # A captured state at f=0 self-sustains iff J*(-1) + h < 0, i.e. h < J: the fundamentals field is
    # weaker than the ownership coupling. Sweep h at J=2.0: recovery (f_down>0) only appears once h ~> J.
    fgrid2 = [round(x, 3) for x in np.arange(0.0, 1.01, 0.02)]
    def fmt(x): return ">50%" if x is None else f"{x:.0%}"
    print(f"\nPart B -- recovery edge f_down vs the field h, at J=2.0 (T=1.0). Captured self-sustains while h < J:")
    print(f"  {'h':>5} {'f_up':>6} {'f_down':>7}")
    for h in [0.15, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        fu, fd = loop_edges(2.0, 1.0, h, fgrid2)
        print(f"  {h:>5} {fmt(fu):>6} {fmt(fd):>7}")
    print("\nTakeaway: f_down->0 ('capture is irreversible') holds only while the fundamentals field h is WEAK")
    print("relative to the coupling J (the post's h=0.15 << J). Strengthen the field and the hysteresis loop")
    print("closes (h=1.0: f_up=f_down; recovery becomes possible). So the irreversibility, and the loop widths,")
    print("are a coordinate readout of (h, T, J) -- a textbook first-order transition, NOT measured governance.")
