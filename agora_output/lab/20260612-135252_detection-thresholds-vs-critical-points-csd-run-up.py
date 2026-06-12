"""
Model-belief test: "Detection thresholds are critical points with universal run-up dynamics."

Claim under test: ANY detection threshold (incl. a 5-sigma evidence-accumulation discovery)
is a critical point and shows the universal critical-slowing-down (CSD) run-up signature:
rising lag-1 autocorrelation (AC1) and rising variance of the order parameter as the
threshold is approached.

We pit two substrates against each other under ONE measurement protocol:
  Model A  — a genuine continuous (pitchfork/transcritical) transition driven through its
             critical point. Standard early-warning-signals normal form with additive noise.
             Order parameter = state x; control parameter slowly ramped toward r_c.
  Model B  — an evidence-accumulation detector: i.i.d. signal x_i ~ N(mu,1), accumulated
             evidence field S_n = sum x_i (the literal order parameter of the hypothesis),
             "detection" = standardized z_n = S_n/sqrt(n) crossing 5 sigma. We approach the
             firing point n* and compute the SAME CSD statistics on the order-parameter field.

If the universality claim is true, BOTH should show rising AC1 + variance (positive Kendall
tau) on the run-up. The falsifier: if B is flat while A diverges, detection thresholds are
NOT generically critical points -- only bifurcation-type ones are.
"""
import numpy as np

rng = np.random.default_rng(20260612)

def kendall_tau(y):
    # trend vs. index; subsample long series (EWS-standard tau on windowed statistic)
    y = np.asarray(y, float)
    if len(y) > 400:
        idx = np.linspace(0, len(y)-1, 400).astype(int)
        y = y[idx]
    n = len(y); s = 0
    for i in range(n):
        s += np.sign(y[i+1:] - y[i]).sum()
    return s / (n*(n-1)/2)

def rolling(x, w, fn):
    return np.array([fn(x[i-w:i]) for i in range(w, len(x)+1)])

def ac1(x):
    x = x - x.mean()
    if np.allclose(x, 0): return 0.0
    return float(np.corrcoef(x[:-1], x[1:])[0,1])

# ---------- Model A: true continuous transition (normal form, EWS standard) ----------
# dx = (-(x^3) + r*x) dt + sigma dW   (supercritical pitchfork; r -> 0^- = critical point)
# Canonical CSD protocol: independent LONG stationary runs at fixed control values approaching
# criticality; discard burn-in (>= a few relaxation times); measure AC1 + variance at each.
def model_A_stationary(r, sigma=0.05, dt=0.01, n_steps=150000, burn=80000):
    x = 0.0; xs = np.empty(n_steps)
    sdt = sigma*np.sqrt(dt)
    noise = rng.standard_normal(n_steps)
    for t in range(n_steps):
        x = x + (-(x**3) + r*x)*dt + sdt*noise[t]
        xs[t] = x
    return xs[burn:]

r_vals = [-1.0, -0.5, -0.25, -0.12, -0.06, -0.03]   # approach critical r_c = 0 from below
varA_pts = []; acA_pts = []
for r in r_vals:
    seg = model_A_stationary(r)
    varA_pts.append(float(np.var(seg)))
    acA_pts.append(ac1(seg[::20]))   # thin to ~1 relaxation step so AC1 isn't saturated at ~1
varA_pts = np.array(varA_pts); acA_pts = np.array(acA_pts)
tau_var_A = kendall_tau(varA_pts)
tau_ac_A  = kendall_tau(acA_pts)
print("=== Model A: genuine continuous (pitchfork) transition ===")
print(f"  control r (approaching r_c=0):  {r_vals}")
print(f"  var:  {np.array2string(varA_pts, precision=4)}  ratio(last/first)={varA_pts[-1]/varA_pts[0]:.1f}x  KendallTau={tau_var_A:+.3f}")
print(f"  AC1:  {np.array2string(acA_pts, precision=3)}  KendallTau={tau_ac_A:+.3f}")

# ---------- Model B: evidence-accumulation detection threshold (5-sigma discovery) ----------
mu = 0.05  # small true signal; many samples needed to reach 5-sigma
def model_B_run():
    # generate in chunks until standardized z crosses 5 sigma (running sum, O(n))
    chunk = 2000; xs = []; S = 0.0; n = 0
    while True:
        block = mu + rng.standard_normal(chunk)
        cs = np.cumsum(block) + S
        ns = np.arange(n+1, n+chunk+1)
        z = cs/np.sqrt(ns)
        hit = np.where((z >= 5.0) & (ns > 1000))[0]
        xs.append(block)
        if len(hit):
            k = hit[0]
            allx = np.concatenate(xs)[:n+k+1]
            return allx, n+k+1
        S = cs[-1]; n += chunk
        if n > 300000:
            return np.concatenate(xs), n  # safety

# Aggregate the CSD run-up across many detector runs, aligned to the firing point n*.
runs = 40
# We measure AC1 and variance of the order-parameter increments (the evidence field's local
# fluctuations) in windows positioned at increasing fractions of the way to firing.
fracs = np.linspace(0.5, 0.98, 12)
var_curves = []; ac_curves = []
for _ in range(runs):
    xs, nstar = model_B_run()
    S = np.cumsum(xs)               # the accumulated-evidence order-parameter field
    incr = np.diff(S)              # fluctuations of the order parameter
    ww = max(50, nstar//20)
    vc = []; ac = []
    for f in fracs:
        c = int(f*nstar)
        lo = max(0, c-ww); hi = min(len(incr), c)
        seg = incr[lo:hi]
        vc.append(np.var(seg)); ac.append(ac1(seg))
    var_curves.append(vc); ac_curves.append(ac)
varB = np.mean(var_curves, axis=0)
acB  = np.mean(ac_curves, axis=0)
tau_var_B = kendall_tau(varB)
tau_ac_B  = kendall_tau(acB)
print("\n=== Model B: evidence-accumulation detection threshold (5-sigma) ===")
print(f"  reached 5-sigma in ~{nstar} samples (last run)")
print(f"  var:  first={varB[0]:.4f}  last={varB[-1]:.4f}  ratio={varB[-1]/varB[0]:.2f}x  KendallTau={tau_var_B:+.3f}")
print(f"  AC1:  first={acB[0]:+.4f}  last={acB[-1]:+.4f}  KendallTau={tau_ac_B:+.3f}")

# Also: the order parameter S itself / posterior -- does it sharpen smoothly (no susceptibility blowup)?
# Susceptibility analog: variance of z across runs as a function of n (should NOT diverge near n*).
print("\n=== Verdict inputs ===")
print(f"  A var-trend tau = {tau_var_A:+.3f}, A AC1-trend tau = {tau_ac_A:+.3f}  (expect strongly +)")
print(f"  B var-trend tau = {tau_var_B:+.3f}, B AC1-trend tau = {tau_ac_B:+.3f}  (CSD claim predicts +; null predicts ~0)")
# CSD requires BOTH a strong monotone trend AND a materially large effect size
csd_A = (tau_var_A > 0.5 and tau_ac_A > 0.3 and varA_pts[-1]/varA_pts[0] > 3.0)
csd_B = (tau_var_B > 0.5 and tau_ac_B > 0.3 and varB[-1]/varB[0] > 3.0)
print(f"  A var blow-up = {varA_pts[-1]/varA_pts[0]:.1f}x ; B var blow-up = {varB[-1]/varB[0]:.2f}x")
print(f"  CSD present in A? {csd_A}   CSD present in B? {csd_B}")
if csd_A and not csd_B:
    print("  RESULT: universality claim FALSIFIED -- detection thresholds are NOT generically critical points.")
elif csd_A and csd_B:
    print("  RESULT: claim SUPPORTED -- both substrates show CSD run-up.")
else:
    print("  RESULT: inconclusive / Model A failed to show CSD (check setup).")
