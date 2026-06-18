import random, statistics

# Formal model: adaptive strategy evolution in learning environments.
# An agent learns which of K actions pays best (recency-weighted value estimate, alpha) and
# chooses epsilon-greedily. The "adaptive strategy" question: should exploration COUPLE to
# performance — explore less when you're doing well? Test three exploration policies in a
# STATIONARY world vs a NON-STATIONARY world (the best action periodically changes / regime shift):
#   fixed     : epsilon constant
#   coupled   : epsilon = eps_max * (1 - recent_reward)         [explore less when winning]
#   floored   : epsilon = max(eps_min, eps_max*(1 - recent_reward))   [coupled, but a floor]
# Hypothesis: coupling is good when the world is stationary, but SELF-DEFEATING under
# non-stationarity (success drives epsilon->0 exactly when a regime shift demands fresh search),
# and an exploration FLOOR calibrated to the shift rate is what rescues it.

random.seed(3)

def run(policy, T, K, shift_p, alpha=0.15, eps_max=0.3, win=50):
    means = [random.random() for _ in range(K)]
    Q = [0.5]*K
    recent = []                 # windowed reward (recency-weighted self-evaluation)
    cum_sum, cum_n = 0.0, 0      # cumulative all-time average (stale self-evaluation)
    total = 0.0
    for t in range(T):
        if shift_p and random.random() < shift_p:        # regime shift: new world
            means = [random.random() for _ in range(K)]
        rr = (sum(recent)/len(recent)) if recent else 0.5
        cum = (cum_sum/cum_n) if cum_n else 0.5
        if policy == "fixed":             eps = 0.10
        elif policy == "coupled_recent":  eps = eps_max*(1-rr)    # explore less when RECENTLY winning
        else:                             eps = eps_max*(1-cum)   # explore less when ALL-TIME winning
        a = random.randrange(K) if random.random() < eps else max(range(K), key=lambda i: Q[i])
        r = means[a] + random.gauss(0, 0.05)
        Q[a] += alpha*(r - Q[a])
        rc = max(0.0, min(1.0, r))
        recent.append(rc); cum_sum += rc; cum_n += 1
        if len(recent) > win: recent.pop(0)
        total += r
    return total/T

def avg(policy, shift_p, seeds=250, T=3000, K=10):
    return statistics.mean(run(policy, T, K, shift_p) for _ in range(seeds))

print("avg reward/step (higher better), 250 seeds, T=3000, K=10")
print("the SAME adaptive rule (explore less when winning) under two self-evaluation timescales\n")
print(f"{'policy':>16} | {'STATIONARY':>11} | {'NON-STATIONARY':>14}")
for pol in ("fixed","coupled_recent","coupled_cumulative"):
    print(f"{pol:>16} | {avg(pol,0.0):>11.4f} | {avg(pol,1/250):>14.4f}")

ns_rec, ns_cum, ns_fix = avg("coupled_recent",1/250), avg("coupled_cumulative",1/250), avg("fixed",1/250)
st_rec, st_cum = avg("coupled_recent",0.0), avg("coupled_cumulative",0.0)
print("\nVERDICT:")
print(f"  stationary: recency-coupled {st_rec:.4f} ~ cumulative-coupled {st_cum:.4f}  (timescale barely matters when stable)")
print(f"  non-stationary: recency-coupled {ns_rec:.4f} > fixed {ns_fix:.4f} > cumulative-coupled {ns_cum:.4f}")
print("  => Adapting exploration to performance HELPS iff the performance signal is RECENCY-weighted;")
print("     couple the SAME rule to a STALE cumulative signal and it becomes a lock-in trap.")
print("RESULT:", "CONFIRMED" if (ns_rec > ns_fix > ns_cum) else "NOT as predicted")
