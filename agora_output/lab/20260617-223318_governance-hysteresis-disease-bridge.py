"""
Forge analogy (inbox dc6765): Disease-as-phase-transition -> Corporate Governance, via the bridge's
DEEPER mechanism: HYSTERESIS ("you can't reverse disease by reversing the conditions; treatment fails
at the wrong point in the phase diagram"). Mapped to governance: the activist/faction stake that
CAPTURES a firm's control differs from the stake needed to RECOVER it -- entrenchment is path-dependent.

This is additive, NOT a duplicate of the already-canonized minority-tipping law (which measured only the
FORWARD capture threshold f_up). Here we measure the full hysteresis LOOP (f_up vs f_down) and the
governance-specific prediction: board/shareholder COUPLING widens the hysteresis -> captured firms stay
captured well below the stake that captured them. Structurally faithful to the disease bridge
(bistable attractors + hysteresis) and to Agora's Anchor Law (bistable/hysteretic).

Model (mean-field Glauber): N agents, opinions s in {-1,+1} over board control. Good governance =
+1 (aligned with fundamentals, favored by the grounding field h>0 = the firm's external reality). A
committed faction of fraction f is fixed at -1 (capture). Persuadable agents feel H = J*M + h.
  f_up   = smallest committed fraction that CAPTURES a firm starting in good control (+1 init).
  f_down = smallest committed fraction that keeps a firm captured when it STARTS captured (-1 init);
           below f_down the firm recovers to good. Hysteresis width = f_up - f_down (bistable region).
Prediction: f_up > f_down (entrenchment), and the gap WIDENS with coupling J.
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
    f_up = next((f for f in fgrid if p_captured(f, J, T, h, +1.0) >= 0.5), None)     # capture from good
    f_down = next((f for f in fgrid if p_captured(f, J, T, h, -1.0) >= 0.5), None)   # stays captured from captured
    return f_up, f_down

if __name__ == "__main__":
    T, h = 1.0, 0.15      # h>0: fundamentals favor good governance (the external-reality grounding)
    fgrid = [round(x, 3) for x in np.arange(0.0, 0.52, 0.02)]
    print(f"Governance capture/recovery hysteresis (h={h} favors good governance). f = committed faction at -1.\n")
    print("  coupling J | f_up (capture from good) | f_down (stays captured from captured) | hysteresis width")
    rows = []
    for J in [1.2, 2.0, 3.0, 4.0]:
        fu, fd = loop_edges(J, T, h, fgrid)
        width = None if (fu is None or fd is None) else round(fu - fd, 3)
        rows.append((J, fu, fd, width))
        fus = f"{fu:.0%}" if fu is not None else ">50%"
        fds = f"{fd:.0%}" if fd is not None else "0% (always recovers)"
        ws = f"{width:.0%}" if width is not None else "n/a"
        print(f"    J={J:<4} | {fus:<8} | {fds:<22} | {ws}")

    # verdicts (hysteresis is a COUPLING-INDUCED transition: absent at low J, emergent + widening above it)
    valid = [(J, fu, fd, w) for (J, fu, fd, w) in rows if fu is not None and fd is not None]
    widths = sorted([(J, w) for (J, fu, fd, w) in valid if w is not None])
    emergent = len(widths) >= 3 and widths[0][1] <= 0.05 and widths[-1][1] >= 0.15   # ~0 at low J, large at high J
    widens = len(widths) >= 3 and all(widths[i][1] <= widths[i + 1][1] for i in range(len(widths) - 1))
    # irreversibility: above the coupling threshold a captured firm cannot recover by shrinking the faction
    irreversible = any(fd == 0.0 and fu > 0.05 for (J, fu, fd, w) in valid)

    print("\n=== VERDICT ===")
    print(f"A) hysteresis EMERGES with coupling (width ~0 at low J, large at high J): {emergent}  {widths}")
    print(f"B) and WIDENS monotonically with coupling J: {widens}")
    print(f"C) irreversibility above the coupling threshold (captured firm can't recover by shrinking faction, f_down=0): {irreversible}")
    ok = emergent and widens and irreversible
    if ok:
        print("\nGOVERNANCE HYSTERESIS CONFIRMED (disease-bridge mapping is structurally valid + ADDITIVE):")
        print("Capturing a well-governed firm needs a larger committed faction than is needed to KEEP it")
        print("captured once it has flipped -- governance is path-dependent (entrenchment), exactly the")
        print("disease bridge's 'you can't reverse the transition by reversing the conditions'. And board/")
        print("shareholder COUPLING widens the loop: in highly-coupled ownership (proxy advisors, common")
        print("owners) a captured firm stays captured far below the stake that captured it. Novel, falsifiable,")
        print("and NOT a duplicate of the forward minority-tipping law (which measured f_up only).")
    else:
        print("\nMapping not additive under this test -> record 'no new mapping' (a dead forging is data).")
