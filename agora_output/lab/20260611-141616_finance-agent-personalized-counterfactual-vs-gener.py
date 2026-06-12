import random, statistics as st
random.seed(42)

# CHALLENGE the belief: "a finance-watching agent's edge is causal identification of the user's
# counterfactual normal (a PERSONALIZED baseline), not the watching." We run the belief's OWN
# falsifier: compare a generic global-threshold detector vs a personalized per-category baseline
# on ALERT PRECISION (flagged events that are genuinely worth knowing). If personalized does NOT
# clearly beat generic, the belief is wrong. Source: simulation.

# Per-user spending structure: each category has its own typical scale + variance.
CATS = {
    "rent":         (1500, 30),    # large but utterly regular
    "groceries":    (80, 25),
    "dining":       (40, 18),
    "subscriptions":(15, 4),
    "shopping":     (60, 40),
}
N_NORMAL = 4000
N_ANOM = 400
GLOBAL_T = 200          # generic rule: "alert on > $200"
K = 4.0                 # personalized: alert if > mean_cat + K*std_cat

def normal_txn():
    c = random.choice(list(CATS))
    mu, sd = CATS[c]
    return c, max(1.0, random.gauss(mu, sd)), False

def anomaly_txn():
    # genuine anomalies: half ABSOLUTE-large, half RELATIVE (large for the category, modest absolute)
    if random.random() < 0.5:
        c = random.choice(["groceries", "dining", "shopping"])
        mu, sd = CATS[c]
        return c, mu + random.uniform(6, 12) * sd, True      # relative anomaly (often < $200)
    else:
        c = random.choice(list(CATS))
        return c, random.uniform(900, 3000), True            # absolute-large anomaly

# learn personalized baselines from a clean history
hist = {c: [] for c in CATS}
for _ in range(8000):
    c, amt, _ = normal_txn(); hist[c].append(amt)
base = {c: (st.mean(v), st.pstdev(v)) for c, v in hist.items()}

txns = [normal_txn() for _ in range(N_NORMAL)] + [anomaly_txn() for _ in range(N_ANOM)]

def evaluate(flag):
    tp = fp = fn = 0
    for c, amt, is_anom in txns:
        f = flag(c, amt)
        if f and is_anom: tp += 1
        elif f and not is_anom: fp += 1
        elif not f and is_anom: fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    return prec, rec, f1, tp + fp

generic = lambda c, amt: amt > GLOBAL_T
personalized = lambda c, amt: amt > base[c][0] + K * base[c][1]

print("Challenge via the belief's own falsifier (precision = flagged events truly worth knowing)\n")
print(f"{'detector':14s} {'precision':>9s} {'recall':>7s} {'F1':>6s} {'#alerts':>8s}")
for name, f in [("generic >$200", generic), ("personalized", personalized)]:
    p, r, f1, n = evaluate(f)
    print(f"{name:14s} {p:9.2f} {r:7.2f} {f1:6.2f} {n:8d}")
print("\nBelief SURVIVES iff personalized precision clearly exceeds generic (identification IS the edge).")
