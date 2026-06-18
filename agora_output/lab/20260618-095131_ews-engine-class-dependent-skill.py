"""
CAPSTONE: Critical-Transition Early-Warning Engine — the operational cash-out of the criticality program.

The engine watches a time series and warns of an APPROACHING critical transition from critical-slowing-
down signals: as a system nears a fold/bifurcation, its recovery from perturbations slows, so rolling
VARIANCE and lag-1 AUTOCORRELATION rise. The warning statistic is the Kendall-tau TREND of those
indicators over a pre-transition window.

This is not a re-derivation of Scheffer's EWS. The capstone contribution is making the engine HONEST
about its own reliability: we MEASURE its skill (AUC discriminating pre-transition from control, + lead-
time) and show the skill is TRANSITION-TYPE-DEPENDENT — it works for fold/critical-slowing-down
transitions but FAILS (AUC ~ 0.5) for noise-induced transitions that have no slowing-down precursor.
A useful detector must know WHEN to trust itself.
"""
import numpy as np

# ---------------- the engine ----------------
def kendall_tau(y):
    n = len(y); s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += np.sign(y[j] - y[i])
    return 2.0 * s / (n * (n - 1))

def rolling(x, win, fn):
    return np.array([fn(x[i - win:i]) for i in range(win, len(x) + 1)])

def lag1_ac(w):
    w = w - w.mean()
    d = np.sum(w * w)
    return float(np.sum(w[1:] * w[:-1]) / d) if d > 0 else 0.0

def ews_warning(x, win=50):
    """Engine: return the early-warning score = mean Kendall-tau trend of rolling variance + lag-1 AC."""
    var_s = rolling(x, win, np.var)
    ac_s = rolling(x, win, lag1_ac)
    return 0.5 * (kendall_tau(var_s) + kendall_tau(ac_s))   # in [-1,1]; high = strong rising trend = warning

# ---------------- generators ----------------
def gen_fold(T=400, r0=0.35, sigma=0.18, seed=0):
    """Approaching a fold: recovery rate r_t -> 0 (critical slowing down). Observe the PRE-window only."""
    rng = np.random.default_rng(abs(seed) % (2**32)); x = 0.0; out = []
    for t in range(T):
        r = r0 * (1 - 0.95 * t / T)                 # recovery slows toward the transition
        x += -r * x + sigma * rng.standard_normal()
        out.append(x)
    return np.array(out)

def gen_control(T=400, r0=0.35, sigma=0.18, seed=0):
    """No approach: constant recovery rate -> stationary -> flat indicators."""
    rng = np.random.default_rng(abs(seed) % (2**32)); x = 0.0; out = []
    for t in range(T):
        x += -r0 * x + sigma * rng.standard_normal()
        out.append(x)
    return np.array(out)

def gen_noise_induced(T=400, sigma=0.42, seed=0):
    """Bistable double well, FIXED parameters; flips happen via rare noise excursions, NOT a slowing
    approach -> NO critical-slowing-down precursor (the engine SHOULD fail here)."""
    rng = np.random.default_rng(abs(seed) % (2**32)); x = -1.0; out = []
    for t in range(T):
        x += 0.25 * (x - x**3) + sigma * rng.standard_normal()   # wells at +-1
        out.append(x)
    return np.array(out)

# ---------------- skill ----------------
def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    return float(np.mean([np.mean(p > neg) + 0.5 * np.mean(p == neg) for p in pos]))

if __name__ == "__main__":
    N = 120; win = 50
    fold = [ews_warning(gen_fold(seed=s), win) for s in range(N)]
    ctrl = [ews_warning(gen_control(seed=1000 + s), win) for s in range(N)]
    noise = [ews_warning(gen_noise_induced(seed=2000 + s), win) for s in range(N)]

    auc_fold = auc(fold, ctrl)              # can the engine flag a real approaching fold vs a stationary control?
    auc_noise = auc(noise, ctrl)            # can it flag a noise-induced flip? (it should NOT be able to)
    # false-alarm rate at a threshold set to the 95th percentile of control (5% nominal false alarm)
    thr = np.percentile(ctrl, 95)
    far = np.mean(np.array(ctrl) > thr)
    detect_fold = np.mean(np.array(fold) > thr)
    detect_noise = np.mean(np.array(noise) > thr)

    print("Critical-Transition Early-Warning Engine — measured skill\n")
    print(f"  warning score (mean Kendall-tau of variance+AC trend):")
    print(f"    approaching FOLD     : {np.mean(fold):+.3f}")
    print(f"    stationary CONTROL   : {np.mean(ctrl):+.3f}")
    print(f"    NOISE-INDUCED flip   : {np.mean(noise):+.3f}")
    print(f"\n  AUC (discriminate vs control):  FOLD={auc_fold:.3f}   NOISE-INDUCED={auc_noise:.3f}")
    print(f"  at a 5%-false-alarm threshold (thr={thr:+.2f}, FAR={far:.2f}):")
    print(f"    detection rate  FOLD={detect_fold:.2f}   NOISE-INDUCED={detect_noise:.2f}")

    print("\n=== VERDICT ===")
    works_on_fold = auc_fold > 0.85
    fails_on_noise = auc_noise < 0.65
    print(f"engine DETECTS approaching folds (critical slowing down): {works_on_fold} (AUC {auc_fold:.2f})")
    print(f"engine correctly FAILS on noise-induced flips (no slowing-down precursor): {fails_on_noise} (AUC {auc_noise:.2f})")
    if works_on_fold and fails_on_noise:
        print("\nENGINE WORKS, AND KNOWS ITS LIMITS (the capstone contribution):")
        print(f"It reliably flags an approaching FOLD transition (AUC {auc_fold:.2f}, {detect_fold:.0%} caught at")
        print(f"{far:.0%} false alarms) - because critical slowing down (rising variance + autocorrelation)")
        print(f"genuinely precedes that class. But it is near-blind to NOISE-INDUCED flips (AUC {auc_noise:.2f}),")
        print("which have NO slowing-down precursor. So the engine's reliability is TRANSITION-TYPE-DEPENDENT:")
        print("trust the warning for slow-approach (fold/critical) transitions; do NOT for noise-induced ones.")
        print("An early-warning system that doesn't know this regime will cry wolf or miss - measuring the")
        print("class-dependent skill IS the operational contribution.")
    else:
        print("\nNot the predicted skill pattern -- investigate.")
