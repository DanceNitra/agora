
import numpy as np
rng=np.random.default_rng(17)
def refine(a, T, q0=0.5, delta=0.05, trials=20000):
    q=np.full(trials,q0)
    for _ in range(T):
        step=np.where(rng.random(trials)<a, delta, -delta)
        q=np.clip(q+step,0,1)
    return q.mean(), float(np.mean(q>q0))
print("Self-refinement final quality vs verifier accuracy a and iterations T (start q=0.50)")
print(f"{'a':>5} |"+"".join(f"  T={t:<4}" for t in (1,5,20,50)))
for a in (0.30,0.40,0.45,0.50,0.55,0.60,0.70,0.80):
    print(f"{a:>5.2f} | "+"  ".join(f"{refine(a,t)[0]:6.3f}" for t in (1,5,20,50)))
print("\nP(final quality improved over start):")
print(f"{'a':>5} |  T=5    T=50")
for a in (0.40,0.45,0.50,0.55,0.60,0.70):
    print(f"{a:>5.2f} | "+"  ".join(f"{refine(a,t)[1]:6.3f}" for t in (5,50)))
