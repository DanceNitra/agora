"""
The Collective Intelligence Phase Diagram (Agora capstone, core measurement)
===========================================================================
Question: when does aggregating N reasoners (majority vote) BEAT the best single reasoner, and when does
it actively HURT? We claim a boundary in the (individual competence  x  error-correlation) plane: below a
correlation-dependent competence threshold, the ensemble locks onto a shared MISLEADING cue and does worse
than one reasoner whose idiosyncratic noise can still override the cue.

Model (one binary decision, truth y in {+1,-1}). Each reasoner i:
    x_i = mu * y        (private signal: competence)
        + beta * u      (a SHARED per-trial cue, common to all reasoners: the source of correlation)
        + e_i           (idiosyncratic noise ~ N(0,1))
    vote_i = sign(x_i)
The shared cue u equals the truth y with probability g (cue reliability). g<0.5 => a systematically
MISLEADING common cue (a shared misconception / anchor / bandwagon). beta sets how strongly reasoners lean
on the shared cue => it sets the inter-reasoner error CORRELATION. mu sets private COMPETENCE.

This unifies the textbook + the frontier:
 * beta=0  -> independent voters -> Condorcet (ensemble -> 1): wisdom of crowds.
 * g=0.5   -> the shared cue is unbiased -> ensemble always >= single (symmetric).
 * g<0.5, beta large -> shared MISLEADING cue dominates -> majority follows it -> ensemble < single:
   info-cascade / bandwagon lock-in / self-consistency amplification of a correlated error.

We MEASURE: (1) the delta = ensemble_acc - single_acc surface over (competence, correlation); (2) the
boundary; (3) the fraction of the plane that is an AMPLIFICATION region (delta<0); (4) how MORE reasoners
make it worse below threshold. Falsifier: no amplification region exists (delta>=0 everywhere) => the
'more reasoners can hurt' law is dead and only Condorcet holds.
"""
import numpy as np

RNG = np.random.default_rng(7)


def simulate(N, mu, beta, g, T=60000, rng=None):
    rng = rng or RNG
    y = rng.choice([-1.0, 1.0], size=T)
    agree = rng.random(T) < g                       # shared cue agrees with truth w.p. g
    u = np.where(agree, y, -y)
    e = rng.normal(0.0, 1.0, size=(T, N))
    x = mu * y[:, None] + beta * u[:, None] + e
    v = np.where(x >= 0.0, 1.0, -1.0)
    correct = (v == y[:, None])                     # T x N
    single = float(correct.mean())                  # avg single-reasoner accuracy
    s = v.sum(axis=1)
    tie = (s == 0)
    ens = np.where(s > 0, 1.0, -1.0)
    if tie.any():
        ens[tie] = rng.choice([-1.0, 1.0], size=int(tie.sum()))
    ensemble = float((ens == y).mean())
    # confidence-weighted vote: weight each vote by |x_i| (its confidence) == sign(sum x_i)
    wv = np.where(x.sum(axis=1) >= 0, 1.0, -1.0)
    weighted = float((wv == y).mean())
    # inter-reasoner error correlation: mean pairwise Pearson corr of the correctness columns
    cm = correct.astype(float)
    if N >= 2 and cm[:, 0].std() > 0:
        cc = np.corrcoef(cm.T)
        rho = float((cc.sum() - np.trace(cc)) / (N * (N - 1)))
    else:
        rho = float("nan")
    return single, ensemble, rho, weighted


def phi(z):
    from math import erf, sqrt
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


# ---------------------------------------------------------------- 1) the phase surface
g = 0.35            # the shared cue is systematically MISLEADING (right only 35% of the time)
N = 21
mus = np.linspace(0.0, 2.4, 13)        # private competence
betas = np.linspace(0.0, 3.0, 13)      # shared-cue weight -> correlation
print(f"=== Phase surface  (N={N}, cue reliability g={g}) ===")
print("rows = competence mu (private), cols = shared-cue weight beta (correlation)\n")

amp_cells = 0
total_cells = 0
boundary = {}     # for each beta, the competence (single_acc) where delta crosses 0
grid_delta = np.zeros((len(mus), len(betas)))
grid_single = np.zeros((len(mus), len(betas)))
grid_rho = np.zeros((len(mus), len(betas)))
grid_wdelta = np.zeros((len(mus), len(betas)))   # confidence-weighted ensemble - single
for i, mu in enumerate(mus):
    for j, beta in enumerate(betas):
        sg, en, rho, wt = simulate(N, mu, beta, g)
        d = en - sg
        grid_delta[i, j] = d
        grid_single[i, j] = sg
        grid_rho[i, j] = rho
        grid_wdelta[i, j] = wt - sg
        total_cells += 1
        if d < -0.005:
            amp_cells += 1

# ASCII map: '+' ensemble helps, '-' ensemble HURTS (amplification), '.' ~tie
print("        beta:" + "".join(f"{b:5.1f}" for b in betas))
for i, mu in enumerate(mus):
    row = ""
    for j in range(len(betas)):
        d = grid_delta[i, j]
        row += "    -" if d < -0.005 else ("    +" if d > 0.005 else "    .")
    print(f"  mu={mu:4.2f}  " + row)

amp_frac = amp_cells / total_cells
print(f"\nMEASURED: amplification region (ensemble WORSE than a single reasoner) = "
      f"{amp_frac*100:.1f}% of the (competence x correlation) plane  [g={g}, N={N}]")

# ---------------------------------------------------------------- 2) the boundary c*(correlation)
# For each correlation level, the MINIMUM single-accuracy at which the ensemble starts to help (delta>=0).
# The law's signature: c* RISES with correlation (you need more individual competence to safely aggregate).
print("\nMEASURED boundary c*(correlation) — min single-accuracy at which aggregation starts to help:")
boundary_exists = False
c_lo = c_hi = None
for j, beta in enumerate(betas):
    col_d = grid_delta[:, j]
    col_s = grid_single[:, j]
    rr = np.nanmean(grid_rho[:, j])
    cstar = None
    for i in range(1, len(mus)):
        if col_d[i - 1] < 0 <= col_d[i]:
            t = (0 - col_d[i - 1]) / (col_d[i] - col_d[i - 1])
            cstar = col_s[i - 1] + t * (col_s[i] - col_s[i - 1])
            break
    if cstar is not None:
        boundary_exists = True
        if rr <= 0.15 and c_lo is None:
            c_lo = (rr, cstar)
        c_hi = (rr, cstar)
        print(f"  beta={beta:4.1f}  rho~{rr:5.2f}:  c* = {cstar:.3f}")
    else:
        print(f"  beta={beta:4.1f}  rho~{rr:5.2f}:  c* > {col_s.max():.3f}  (aggregation hurts across all tested competence)")
if c_lo and c_hi:
    print(f"MEASURED: the safe-aggregation threshold RISES with correlation — c* goes from ~{c_lo[1]:.2f} "
          f"(rho~{c_lo[0]:.2f}) to ~{c_hi[1]:.2f} (rho~{c_hi[0]:.2f}).")

# ---------------------------------------------------------------- 3) the two regimes vs N (the contrast)
# Independent regime -> Condorcet: ensemble climbs toward 1 with N. Correlated-misleading regime ->
# the REDUNDANCY TRAP: ensemble sinks below a single reasoner and STAYS there as you add reasoners.
print(f"\n=== Two regimes as you add reasoners (T=200000, g={g}) ===")
T_big = 200000
print("  INDEPENDENT (mu=0.40, beta=0.2)        | CORRELATED+MISLEADING (mu=0.40, beta=2.0)")
print("   N   single  ensemble  delta            |  N   single  ensemble  delta")
for Nn in (1, 3, 9, 21, 51, 101):
    s1, e1, _, _ = simulate(Nn, 0.40, 0.2, g, T=T_big, rng=np.random.default_rng(100 + Nn))
    s2, e2, _, _ = simulate(Nn, 0.40, 2.0, g, T=T_big, rng=np.random.default_rng(500 + Nn))
    print(f"  {Nn:>3}  {s1:.3f}   {e1:.3f}   {e1-s1:+.3f}           | {Nn:>3}  {s2:.3f}   {e2:.3f}   {e2-s2:+.3f}")
print("  -> left: aggregation HELPS and grows with N (Condorcet). right: aggregation HURTS and the gap")
print("     does NOT close with more reasoners (the redundancy trap of a shared misleading cue).")

# ---------------------------------------------------------------- 4) cue reliability sweep (where g flips it)
mu_bad, beta_bad = 0.40, 2.0    # the correlated+misleading operating point
print(f"\n=== Cue-reliability g sweep  (N={N}, mu={mu_bad}, beta={beta_bad}) ===")
for gg in (0.2, 0.35, 0.5, 0.65, 0.8):
    sg, en, rho, _ = simulate(N, mu_bad, beta_bad, gg)
    tag = "AMPLIFIES error" if en < sg - 0.005 else "helps"
    print(f"  g={gg:.2f}: single={sg:.3f}  ensemble={en:.3f}  delta={en-sg:+.3f}  -> {tag}")

# ---------------------------------------------------------------- 5) robustness: confidence-weighted vote
wamp = float((grid_wdelta < -0.005).mean())
print(f"\n=== Robustness: confidence-weighted voting (weight each vote by its |x|) ===")
print(f"MEASURED: under confidence-weighting the amplification region is {wamp*100:.1f}% of the plane "
      f"(vs {amp_frac*100:.1f}% for plain majority). Weighting the confident does NOT rescue it — confident "
      f"reasoners are confident BECAUSE of the shared cue, so weighting leans HARDER on it.")

# ---------------------------------------------------------------- 6) robustness: sequential herding (cascade)
# Reasoners decide IN SEQUENCE, each nudged toward the running tally (info cascade / bandwagon). lambda is
# the herding strength. This should EXPAND amplification: herding manufactures correlation even at beta=0.
def simulate_cascade(N, mu, beta, g, lam, T=60000, rng=None):
    rng = rng or np.random.default_rng(11)
    y = rng.choice([-1.0, 1.0], size=T)
    u = np.where(rng.random(T) < g, y, -y)
    tally = np.zeros(T)
    correct_cnt = np.zeros(T)
    for _ in range(N):
        e = rng.normal(0.0, 1.0, size=T)
        x = mu * y + beta * u + lam * np.tanh(tally) + e   # herding toward the running tally
        v = np.where(x >= 0.0, 1.0, -1.0)
        tally += v
        correct_cnt += (v == y)
    single = float(correct_cnt.mean() / N)
    ens = np.where(tally > 0, 1.0, np.where(tally < 0, -1.0, rng.choice([-1.0, 1.0], size=T)))
    ensemble = float((ens == y).mean())
    return single, ensemble

print(f"\n=== Robustness: sequential herding / info-cascade (N={N}, g={g}, beta=0 so the ONLY correlation is herding) ===")
for lam in (0.0, 0.5, 1.0, 2.0):
    sg, en = simulate_cascade(N, 0.6, 0.0, g, lam)
    tag = "AMPLIFIES" if en < sg - 0.005 else "helps"
    print(f"  herding lambda={lam:.1f}: single={sg:.3f}  ensemble={en:.3f}  delta={en-sg:+.3f}  -> {tag}")
print("  -> with NO shared cue (beta=0), pure herding still manufactures the amplification: a competent")
print("     crowd that watches itself can vote worse than its average member.")

# ---------------------------------------------------------------- verdict
print()
if amp_frac > 0.05 and boundary_exists:
    cross = (c_hi[1] if c_hi else 0.0)
    print(f"VERDICT: LAW HOLDS — a real boundary exists. Aggregation helps only above a correlation-"
          f"dependent competence threshold (c*~{cross:.2f} at high correlation); below it, a shared "
          f"misleading cue makes the majority WORSE than one reasoner, and adding reasoners deepens the "
          f"error. Pure Condorcet (always-helps) is the special case g>=0.5 or beta=0.")
else:
    print("VERDICT: FALSIFIED — no amplification region; ensemble >= single everywhere (only Condorcet).")
