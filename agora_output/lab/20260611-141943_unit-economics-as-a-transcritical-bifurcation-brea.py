# ANALOGY (structural): Bifurcation -> Unit Economics. A business's customer base evolves as
# N_{t+1} = N_t + g*N_t + A, with g = (referral*retention - churn) set by UNIT ECONOMICS and A =
# paid acquisition. The zero-growth state loses stability at g=0 (transcritical bifurcation):
#   g<0 -> base relaxes to a finite paid-only floor N* = A/|g|  (death-spiral, paid-supported)
#   g>0 -> base grows without bound (flywheel)
# Critical signature: the sustainable floor N* = A/|g| DIVERGES as g->0- (like a susceptibility
# blowing up near a critical point) - the SAME skeleton as a fold/transcritical bifurcation, with
# unit economics as the control parameter. Source: simulation.
A, T = 5.0, 6000
def long_run(g):
    N = 50.0
    for _ in range(T):
        N = max(0.0, N + g * N + A)
        if N > 1e12: return float('inf')         # flywheel: unbounded
    return N
print("Transcritical bifurcation, control g = referral*retention - churn (A=paid acq=5)\n")
print(f"{'g':>7} {'long-run N':>14} {'theory A/|g|':>13} {'regime':>14}")
for g in (-0.05, -0.02, -0.01, -0.004, -0.001, 0.001, 0.02):
    N = long_run(g)
    theory = A/abs(g) if g < 0 else float('inf')
    regime = "death-floor" if g < 0 else "flywheel"
    Ns = "inf" if N == float('inf') else f"{N:.0f}"
    Ts = "inf" if theory == float('inf') else f"{theory:.0f}"
    print(f"{g:7.3f} {Ns:>14} {Ts:>13} {regime:>14}")
print("\nFloor N*=A/|g| -> infinity as g->0-: the equilibrium DIVERGES at the unit-economics")
print("break-even, the structural signature of a bifurcation (control param crossing g=0).")
