import numpy as np
rng = np.random.default_rng(31)

# Replicate the qualitative claim: a non-Markovian spreading process on a timeline, where each
# active site triggers FUTURE sites after waiting times drawn from a heavy-tailed law ~ t^{-1-m},
# exhibits an absorbing-state phase transition (survival vs extinction) controlled by the mean
# offspring (branching ratio lambda). Test: (1) does a transition exist, and where? (2) does the
# heavy tail (m) shift the survival threshold, or only the timing?

def powerlaw_wait(n, m, tmin=1.0):
    # p(t) ~ t^{-1-m} for t>=tmin  (inverse-transform); heavier tail for smaller m
    u = rng.random(n)
    return tmin * (1 - u) ** (-1.0 / m)

def survival_fraction(lam, m, n_runs=400, t_horizon=2000.0, cap=20000):
    survived = 0
    for _ in range(n_runs):
        # event-driven branching: active "sites" each spawn Poisson(lam) offspring at future times
        times = [0.0]            # pending activation times (the timeline)
        alive = 0
        steps = 0
        import heapq
        heapq.heapify(times)
        while times and steps < cap:
            t = heapq.heappop(times)
            if t > t_horizon:
                break
            steps += 1
            k = rng.poisson(lam)
            if k:
                for w in powerlaw_wait(k, m):
                    heapq.heappush(times, t + w)
        # survived if the process was still producing events at the horizon (didn't die out)
        if times and min(times) <= t_horizon and steps >= cap * 0.5:
            survived += 1
        elif steps >= cap:
            survived += 1
    return survived / n_runs

print("Barato-Hinrichsen-type non-Markovian spreading: survival vs branching ratio")
print("(heavy-tailed waiting times t^{-1-m}; absorbing-state transition expected at lambda_c=1)\n")
print(f"{'lambda':>7} {'m=0.5':>8} {'m=1.5':>8}")
for lam in [0.7, 0.9, 0.95, 1.0, 1.05, 1.1, 1.3]:
    s_heavy = survival_fraction(lam, 0.5)
    s_light = survival_fraction(lam, 1.5)
    print(f"{lam:7.2f} {s_heavy:8.2f} {s_light:8.2f}")

print("\nReading: a sharp rise in survival near lambda=1 confirms the absorbing-state transition.")
print("If the threshold is the SAME for m=0.5 and m=1.5, the heavy tail sets TIMING not the")
print("survival threshold (branching-process universality) - the expected, reproducible result.")
