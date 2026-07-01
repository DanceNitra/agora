"""Independent re-derivation for audit #18 (we-hunted-for-the-tipping-point-in-8-systems).

The post's original lab scripts for the 8-mechanism criticality battery could not be located (likely
rotated out of the active .lab.json ledger, same situation as audit #16's "lab 2b7e05"). Rather than
cite unverifiable numbers, we build the smallest models that test the post's TWO load-bearing,
highest-stakes claims independently from scratch:

  (A) Self-amplification ("model collapse") is a DETERMINISTIC BLOW-UP, not a critical phase
      transition: susceptibility (variance response near the threshold) should be FLAT across a wide
      range of system sizes N (the hallmark of a fixed-point instability, not criticality), and single
      large runs should closely track the ensemble mean (self-averaging).
  (B) The herding/crowd model at bias q->0.5 (zero truth-signal / zero-grounding limit) is the ONE
      genuine critical transition: fluctuations (variance of the order parameter) should DIVERGE as
      system size N grows near q=0.5, and decay as a power law away from it - the actual signature of
      criticality, calibrated against an exact-solvable mean-field Ising control (beta=1/2 exactly).

Zero-dependency (numpy only). Run: python agora_output/lab/20260701_audit18_criticality_battery_verify.py
"""
import numpy as np


# ---------- (A) Self-amplification: deterministic blow-up, not criticality ----------
def self_train_step(x, g, s, rng):
    """One generation: mix a fraction g of real data (N(0,1)) with (1-g) synthetic data drawn from the
    CURRENT estimated distribution, amplified by factor s (s>1 inflates variance each synthetic pass)."""
    n = len(x)
    n_real = int(round(g * n))
    real = rng.standard_normal(n_real)
    n_synth = n - n_real
    mu, sigma = x.mean(), x.std()
    synth = rng.normal(mu, sigma * np.sqrt(s), n_synth) if n_synth > 0 else np.array([])
    return np.concatenate([real, synth]) if n_synth > 0 else real


def run_self_train(g, s, N, T=40, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(N)
    variances = []
    for _ in range(T):
        x = self_train_step(x, g, s, rng)
        variances.append(float(x.var()))
        if not np.isfinite(variances[-1]) or variances[-1] > 1e8:
            variances[-1] = 1e8
            break
    return variances


def blowup_threshold(s, N=2000, T=40, trials=20):
    """Empirical g at which variance explodes (>50x initial) within T generations, averaged over trials."""
    gs = np.linspace(0.05, 0.95, 19)
    hits = []
    for g in gs:
        blew = 0
        for trial in range(trials):
            v = run_self_train(g, s, N, T, seed=trial)
            if v[-1] > 50.0:
                blew += 1
        hits.append(blew / trials)
    # g* = smallest g where blow-up probability drops below 50%
    g_star = next((float(g) for g, h in zip(gs, hits) if h < 0.5), None)
    return g_star, list(zip(gs.round(3).tolist(), hits))


def susceptibility_scan(g_near_threshold, s, Ns, T=40, trials=30):
    """Variance-of-final-variance across independent runs, at a range of system sizes N, right at the
    empirical threshold. FLAT across N (no growth with system size) => not critical (self-averaging)."""
    out = {}
    for N in Ns:
        finals = []
        for trial in range(trials):
            v = run_self_train(g_near_threshold, s, N, T, seed=1000 + trial)
            finals.append(min(v[-1], 1e6))
        out[N] = float(np.var(np.log1p(finals)))  # susceptibility proxy: variance of log(1+final variance)
    return out


# ---------- (B) Herding/crowd model: genuine criticality at q->0.5, vs Ising control ----------
def herding_step(m, q, K, rng, N):
    """Mean-field herding: agents flip to the majority sign with strength K (social pull) plus a private
    signal biased by q (q=0.5 => no informative signal at all - the zero-grounding limit). m in [-1,1]
    is the mean opinion; update via the standard sigmoid mean-field map with finite-N noise."""
    signal = (2 * q - 1)  # informative drift; 0 exactly at q=0.5
    field = K * m + signal
    p_up = 1.0 / (1.0 + np.exp(-2 * field))
    # finite-N sampling noise
    up = rng.binomial(N, p_up) / N
    return 2 * up - 1


def herding_run(q, K, N, T=400, burn=200, seed=0):
    rng = np.random.default_rng(seed)
    m = 0.0
    ms = []
    for t in range(T):
        m = herding_step(m, q, K, rng, N)
        if t >= burn:
            ms.append(m)
    return np.array(ms)


def fluctuation_growth(q, K, Ns, seed=0):
    """Variance of m across N -> does it GROW with N near q=0.5 (critical) or shrink like 1/N (non-critical,
    ordinary CLT)? Report variance*N (should DIVERGE/grow at criticality, stay flat/bounded off it)."""
    out = {}
    for N in Ns:
        ms = herding_run(q, K, N, seed=seed)
        out[N] = float(np.var(ms) * N)
    return out


def ising_beta_control(ts=None):
    """Exact-solvable Curie-Weiss Ising control: self-consistent m=tanh(m/T), Tc=1, exponent beta=1/2
    EXACTLY (m ~ sqrt(t) near Tc from below). Positive-root solve, no MC noise."""
    if ts is None:
        ts = np.logspace(-6, -3, 25)

    def solve_positive(K):
        lo, hi = 1e-12, 1.0
        if np.tanh(K * lo) - lo <= 0:
            return 0.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if np.tanh(K * mid) - mid > 0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    ms = [solve_positive(1.0 / (1.0 - t)) for t in ts]
    mask = np.array(ms) > 1e-9
    beta = float(np.polyfit(np.log(ts[mask]), np.log(np.array(ms)[mask]), 1)[0])
    return beta


def main():
    print("=== (A) Self-amplification: deterministic blow-up, not criticality ===")
    s = 2.0
    g_star, curve = blowup_threshold(s, N=1500, trials=12)
    print(f"amplification s={s}: empirical blow-up threshold g* = {g_star}  "
          f"(closed-form prediction: 1 - 1/s = {1 - 1/s:.3f})")
    Ns = [200, 400, 800, 1600, 3200, 12800]  # 64x range (200 -> 12800)
    susc = susceptibility_scan(g_star if g_star else 0.5, s, Ns, trials=20)
    print(f"susceptibility proxy across a {Ns[-1]//Ns[0]}x system-size range (N={Ns}):")
    for N, v in susc.items():
        print(f"   N={N:<6} susceptibility={v:.4f}")
    vals = list(susc.values())
    flat = (max(vals) - min(vals)) < 0.5 * max(vals)  # loose flatness test
    print(f"   -> roughly FLAT across N (non-critical / self-averaging signature): {flat}")

    print("\n=== (B) Herding/crowd model: criticality only at q=0.5 (zero grounding) ===")
    K = 1.5  # social-pull strength (K>1 => bistable/ordered regime is reachable)
    Ns2 = [100, 200, 400, 800, 1600]
    print("q      var(m)*N across N (should GROW with N near q=0.5 if critical, stay flat elsewhere):")
    for q in [0.50, 0.52, 0.55, 0.60]:
        fg = fluctuation_growth(q, K, Ns2, seed=3)
        vals2 = [fg[N] for N in Ns2]
        growth = vals2[-1] / vals2[0] if vals2[0] > 0 else float("inf")
        print(f"   q={q:<5} " + "  ".join(f"N={N}:{fg[N]:.2f}" for N in Ns2) + f"   growth(x)={growth:.2f}")

    print("\nIsing control (exact mean-field, beta should = 0.5 exactly):")
    beta_ising = ising_beta_control()
    print(f"   fitted beta = {beta_ising:.3f}  (exact theory: 0.500)")

    print("\n=== VERDICT ===")
    print(f"(A) self-amplification non-critical (flat susceptibility): {flat}")
    print("(B) herding fluctuation growth concentrated near q=0.5, decaying away from it: see table above")
    print(f"    Ising control recovers beta=0.5 within tolerance: {abs(beta_ising-0.5) < 0.05}")


if __name__ == "__main__":
    main()
