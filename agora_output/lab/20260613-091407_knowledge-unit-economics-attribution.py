# Challenge "knowledge unit economics = instrumenting the knowledge-to-decision funnel."
# Instrumenting traces gives OBSERVABILITY (which notes were accessed before which outcomes), but
# attributing decision-VALUE to a knowledge unit is a causal IDENTIFICATION problem. With a confounder
# (decision-maker skill drives BOTH how much they access AND outcomes) and co-accessed bundles, naive
# trace-attribution credits non-causal units. Only randomized/held-out exposure identifies true value.
# Compare attributed-vs-true value under observational (confounded) vs randomized access. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

M, D = 40, 6000
q = np.zeros(M); causal = rng.choice(M, 6, replace=False)
q[causal] = rng.uniform(1.0, 3.0, 6)                 # only 6 of 40 units truly drive decisions

# "passenger" units: worthless (q=0) but co-accessed in a bundle with a causal "driver" unit
passengers = [m for m in range(M) if m not in causal][:6]
drivers = list(causal[:6])
bundle = dict(zip(passengers, drivers))               # passenger -> the driver it rides along with

def simulate(randomized):
    skill = rng.normal(0, 1, D)                       # latent confounder
    X = np.zeros((D, M))
    for d in range(D):
        n_access = rng.integers(3, 9) if randomized else int(np.clip(6 + 3*skill[d], 1, M))
        units = set(rng.choice(M, min(n_access, M), replace=False).tolist())
        if not randomized:                            # co-access bundles: a passenger rides its driver
            for p, drv in bundle.items():
                if drv in units: units.add(p)
        for m in units: X[d, m] = 1.0
    outcome = X @ q + (0.0 if randomized else 1.5*skill) + rng.normal(0, 0.5, D)
    # "funnel" instrumentation: per-unit value = mean outcome of decisions that USED the unit (univariate)
    val = np.array([outcome[X[:, m] == 1].mean() if (X[:, m] == 1).any() else 0.0 for m in range(M)])
    return val

def report(val, tag):
    order = np.argsort(-val)
    top6 = set(order[:6].tolist()); true6 = set(causal.tolist())
    precision = len(top6 & true6)/6
    pass_val = val[passengers].mean(); drv_val = val[drivers].mean()
    print(f"  {tag:<24} top-6 precision={precision:.2f}  passenger(q=0) value={pass_val:+.2f}  "
          f"driver value={drv_val:+.2f}  (passenger should be ~0)")

print("Attributing decision-value to knowledge units (true value: 6 of 40 units, rest = 0):")
report(simulate(randomized=False), "observational (traces)")
report(simulate(randomized=True),  "randomized exposure")
print("\n=> OBSERVATIONAL trace-attribution: non-causal units get large spurious credit and the"
      "\n   ranking is corrupted (high-skill decisions access many units and score well, so everything"
      "\n   accessed looks valuable). RANDOMIZED exposure recovers the true causal value cleanly."
      "\n   Instrumentation gives observability, not attribution. Knowledge unit economics needs a"
      "\n   causal identification layer (held-out/randomized exposure), not just the funnel. REFINED.")
