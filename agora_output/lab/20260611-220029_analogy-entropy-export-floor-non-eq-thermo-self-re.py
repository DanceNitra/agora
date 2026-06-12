"""
Forge analogy: Non-Equilibrium Thermodynamics (entropy export) -> self-rewriting code / RSI stack.

Structural skeleton (same in both): a system holds LOCAL order far from equilibrium only by
EXPORTING entropy to a coupled reservoir — the second law forbids reducing TOTAL disorder, only
relocating it. In code: refactoring reduces a module's local complexity but raises coupling/interface/
test debt elsewhere (Lehman's law of increasing complexity). So a self-rewriting system can make every
module look clean while its TOTAL disorder sits on an irreducible floor set by the export coupling k.

Severe test: improve the worst module each step (reduce its local disorder), routing a fraction k of
each reduction into a shared coupling-debt reservoir. Measure mean LOCAL disorder vs TOTAL disorder
(local + debt). Prediction: local disorder -> low, but total disorder plateaus at a floor that grows
with k; only k=0 (no export) lets total disorder reach ~0 (which would REFUTE the analogy).
"""
import numpy as np

rng = np.random.default_rng(2)
M, T = 20, 4000
r = 0.25   # fraction of a module's disorder removed per improvement


def run(k):
    x = np.full(M, 0.6)        # local disorder per module
    debt = 0.0                 # exported entropy (coupling/interface/test debt) — the reservoir
    for _ in range(T):
        i = int(np.argmax(x))  # refactor the worst module
        removed = r * x[i]
        x[i] -= removed
        debt += k * removed    # the second law: order here -> disorder exported there
    return float(x.mean()), float(debt), float(x.mean() + debt)


print(f"{'export k':>9} {'mean local disorder':>20} {'exported debt':>14} {'TOTAL disorder':>15}")
for k in (0.0, 0.2, 0.5, 1.0):
    loc, debt, tot = run(k)
    print(f"{k:>9.2f} {loc:>20.4f} {debt:>14.3f} {tot:>15.3f}")

# Does more self-rewriting beat the floor? (k=0.5, vary number of improvement steps)
print("\nfloor is irreducible — more rewriting does NOT lower TOTAL disorder (k=0.5):")
print(f"{'steps':>7} {'mean local':>11} {'TOTAL':>8}")
for steps in (250, 1000, 4000, 16000):
    x = np.full(M, 0.6); debt = 0.0
    for _ in range(steps):
        i = int(np.argmax(x)); removed = r * x[i]; x[i] -= removed; debt += 0.5 * removed
    print(f"{steps:>7} {x.mean():>11.4f} {x.mean()+debt:>8.3f}")

print("\nLocal modules -> spotless; TOTAL disorder floored by the export coupling. k=0 would let it")
print("reach 0 (falsifier). This is the second law / Lehman's increasing-complexity law, one skeleton.")
