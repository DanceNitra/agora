import math, statistics

# Smallest computable model of the claim (Garcia-Millan, Font-Clos, Corral 2015):
# "finite-size scaling of the survival probability in branching processes as a
#  function of the control parameter (m-1) and the maximum number of generations n".
#
# Mechanism: Galton-Watson process, Poisson(m) offspring. Survival probability to
# generation n is EXACT via probability-generating-function iteration (no MC noise):
#   q_0 = 0 (one founder, not yet extinct);  q_n = f(q_{n-1}),  f(s)=exp(m(s-1))
#   S_n = 1 - q_n  (prob. the lineage is still alive at generation n)
#
# FSS claim => near criticality (eps=m-1 -> 0, n large) the survival curve obeys
#   S_n ~ n^{-1} * G(eps * n),   i.e.  n*S_n  is a function of the single scaling
# variable x = eps*n only.  Test: does n*S_n COLLAPSE across different eps when
# plotted vs x?  Collapse (spread -> 0 as eps -> 0) confirms FSS exists.

def survival_curve(m, N):
    q = 0.0
    S = [0.0]*N
    for n in range(N):
        q = math.exp(m*(q-1.0))
        S[n] = 1.0 - q
    return S

eps_list = [0.0025, 0.005, 0.01, 0.02]
Nmax = 6000
curves = {e: survival_curve(1.0+e, Nmax) for e in eps_list}

# Critical (eps=0) check: Kolmogorov  S_n ~ 2/(sigma^2 n); Poisson sigma^2=1 => n*S_n->2
crit = survival_curve(1.0, Nmax)
print("CRITICALITY check (Poisson, expect n*S_n -> 2):")
for n in (100, 1000, 5000):
    print(f"  n={n:5d}  n*S_n = {n*crit[n-1]:.4f}")

print("\nCOLLAPSE test  (n*S_n at common x=eps*n; ONLY n>=NMIN, the asymptotic window):")
NMIN = 50   # FSS is asymptotic: a curve point needs large n to be in the scaling regime
xs = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
spreads = []
for x in xs:
    vals = []
    for e in eps_list:
        n = int(round(x/e))
        if NMIN <= n <= Nmax:
            vals.append(curves[e][n-1]*n)
    if len(vals) >= 2:
        rs = (max(vals)-min(vals))/statistics.mean(vals)
        spreads.append(rs)
        print(f"  x={x:5.2f}: n*S_n={[round(v,4) for v in vals]} (n>= {NMIN}) rel_spread={rs:.4f}")

maxspread = max(spreads)
print(f"\nMAX relative spread inside scaling window = {maxspread:.4f}")

# Does collapse IMPROVE toward criticality? compare smallest-eps pair vs largest-eps pair at x=2
def nS_at(e, x):
    n=int(round(x/e)); return curves[e][n-1]*n
fine = abs(nS_at(0.0025,2.0)-nS_at(0.005,2.0))/((nS_at(0.0025,2.0)+nS_at(0.005,2.0))/2)
coarse = abs(nS_at(0.01,2.0)-nS_at(0.02,2.0))/((nS_at(0.01,2.0)+nS_at(0.02,2.0))/2)
print(f"pair-spread at x=2  fine(eps 0.0025/0.005)={fine:.4f}  coarse(eps 0.01/0.02)={coarse:.4f}")
# FSS signature = (a) exact critical amplitude, (b) collapse in the asymptotic window,
# (c) collapse IMPROVES toward criticality (fine pair tighter than coarse pair).
crit_amp_ok = abs(5000*crit[4999] - 2.0) < 0.02
print("VERDICT_FSS =", "REPRODUCED" if (crit_amp_ok and maxspread < 0.10 and fine < coarse) else "WEAK/FAILED")
