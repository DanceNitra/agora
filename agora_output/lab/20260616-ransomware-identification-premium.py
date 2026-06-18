# A20 formal model of the belief: "Ransomware is a two-sided counterfactual-pricing market
# - the side with the better counterfactual model of the victim's value-at-risk wins."
# We test the MECHANISM (not the empirical claim, which needs Huang-style data):
#  1. Does a DEMAND-SIDE pricer (estimates each victim's value-at-risk V and prices to it)
#     out-earn a FLAT/SUPPLY-SIDE pricer? -> the "identification premium".
#  2. Does the premium RISE as the attacker's counterfactual model gets more precise?
#  3. Does demand-side pricing leave the predicted SIGNATURE in data: realized ransom
#     correlates with victim value-at-risk V, NOT with attacker capability (the falsifier)?
import numpy as np

rng = np.random.default_rng(42)
N = 40000
# Victim value-at-risk V (downtime + recovery + reputation), heterogeneous, log-normal.
V = rng.lognormal(mean=11.0, sigma=1.0, size=N)          # ~ tens-of-thousands EUR, fat-tailed
# Attacker "capability" - independent of the victim's value (supply-side attribute).
capability = rng.lognormal(mean=0.0, sigma=1.0, size=N)

def revenue_flat():
    """Supply-side: ONE price for everyone (no victim model). Victim pays iff R <= V."""
    grid = np.quantile(V, np.linspace(0.01, 0.99, 99))
    best = max(R * np.mean(V >= R) for R in grid)         # monopoly price on the V distribution
    return best * N

def revenue_supply_indexed():
    """Supply-side but priced to the attacker's OWN capability (not the victim). Pay iff R<=V."""
    scale = np.quantile(V, 0.5) / np.median(capability)
    R = capability * scale                                # ransom tracks attacker capability
    paid = R <= V
    return float(np.sum(R * paid)), R, paid

def revenue_demand(tau, betas=np.linspace(0.5, 1.0, 26)):
    """Demand-side: observe noisy signal V_hat = V * lognormal(0, tau); set R = beta * V_hat.
    beta optimized once for this precision. Returns (revenue, R, paid_mask)."""
    Vhat = V * rng.lognormal(mean=0.0, sigma=tau, size=N)
    best = (-1.0, None, None)
    for b in betas:
        R = b * Vhat
        paid = R <= V
        rev = float(np.sum(R * paid))
        if rev > best[0]:
            best = (rev, R, paid)
    return best

flat = revenue_flat()
total_value = float(np.sum(V))
print(f"Ransomware identification-premium model | N={N} victims, total value-at-risk={total_value:,.0f}")
print(f"FLAT (one price, no victim model): revenue {flat:,.0f}  ({flat/total_value:.1%} of total value)\n")

print(f"{'attacker model precision':<26}{'demand revenue':>16}{'% of value':>12}{'premium vs flat':>16}")
for tau in [2.0, 1.0, 0.5, 0.25, 0.1, 0.01]:
    rev, R, paid = revenue_demand(tau)
    label = f"tau={tau} ({'blind' if tau>=2 else 'sharp' if tau<=0.1 else 'partial'})"
    print(f"{label:<26}{rev:>16,.0f}{rev/total_value:>11.1%}{rev/flat:>15.2f}x")

# Signature test (the falsifier): under demand-side pricing, realized ransom should track V,
# not capability. Compare to a supply-side (capability-indexed) regime on the SAME victims.
rev_d, Rd, paid_d = revenue_demand(0.25)
rev_s, Rs, paid_s = revenue_supply_indexed()

def corr(a, b):
    return float(np.corrcoef(np.log(a), np.log(b))[0, 1])

print("\nSignature in realized (paid) ransoms - what real data would show:")
print(f"{'regime':<22}{'corr(R, victim V)':>20}{'corr(R, capability)':>22}")
print(f"{'DEMAND-side (tau=.25)':<22}{corr(Rd[paid_d], V[paid_d]):>20.2f}{corr(Rd[paid_d], capability[paid_d]):>22.2f}")
print(f"{'SUPPLY-side (capability)':<22}{corr(Rs[paid_s], V[paid_s]):>20.2f}{corr(Rs[paid_s], capability[paid_s]):>22.2f}")
print("\nVerdict hinges on: demand > flat AND premium rises with precision AND the two regimes")
print("leave OPPOSITE correlation signatures (so Huang-style data can distinguish them).")
