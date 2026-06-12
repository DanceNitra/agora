
import numpy as np
rng = np.random.default_rng(11)
N = 8
TRIALS = 6000
def run(noise, heavy=False):
    pw_hits = cp_hits = 0
    for _ in range(TRIALS):
        q = rng.normal(size=N); best = int(np.argmax(q))
        def nz(size):
            if heavy: return noise * rng.standard_t(2, size=size) / np.sqrt(2)
            return noise * rng.normal(size=size)
        s = q + nz(N)
        if int(np.argmax(s)) == best: pw_hits += 1
        wins = np.zeros(N)
        for i in range(N):
            for j in range(i+1, N):
                if (q[i]-q[j]) + nz(1)[0] > 0: wins[i]+=1
                else: wins[j]+=1
        if int(np.argmax(wins)) == best: cp_hits += 1
    return pw_hits/TRIALS, cp_hits/TRIALS
print("Top-1 selection accuracy: pointwise (absolute) vs contrastive (pairwise Copeland), N=8")
print(f"{'noise sd':>9} | {'pointwise':>9} | {'contrastive':>11} | {'gap':>6}")
print("-- Gaussian judge --")
for s in (0.25, 0.5, 1.0, 2.0):
    pw, cp = run(s, False); print(f"{s:>9.2f} | {pw:>9.3f} | {cp:>11.3f} | {cp-pw:>+6.3f}")
print("-- Heavy-tailed judge (Student-t df=2, outliers) --")
for s in (0.25, 0.5, 1.0, 2.0):
    pw, cp = run(s, True); print(f"{s:>9.2f} | {pw:>9.3f} | {cp:>11.3f} | {cp-pw:>+6.3f}")
