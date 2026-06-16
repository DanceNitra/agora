# Severe test for Idea #3 (Agent Metabolism): does a hard CONVEX per-task spend cap
# clip the cost TAIL (the "agent bankrupted its operator" left-tail blowup) WITHOUT
# hurting NORMAL-task success? Barbell logic (Taleb): bound the downside, keep upside.
#
# Model: an agent works tasks. Each task needs W units of real progress. Each action
# makes progress with prob p_progress, else it is wasted. A fraction f of tasks are
# "trapped" (p_progress ~ 0) -> unbounded spend (Extremistan right tail). Each action
# costs 1 energy unit (stands in for tokens + $ + tool-calls + wall-clock).
#   no cap   : run until W progress (a trapped task eventually finishes, at huge cost)
#   convex   : hard per-task budget B; also early-halt on a tail-risk signature
#              (many actions, no progress) -> abort (bounded spend, task fails fast)
import random, statistics

def run_task(p_progress, W, cap=None, stall_halt=None):
    progress = spend = stall = 0
    while progress < W:
        spend += 1
        if random.random() < p_progress:
            progress += 1; stall = 0
        else:
            stall += 1
        if cap is not None and spend >= cap:
            return spend, False                      # hit hard convex cap -> abort
        if stall_halt is not None and stall >= stall_halt:
            return spend, False                      # tail-risk signature -> early abort
    return spend, True                               # completed

def trial(n_tasks, f_trapped, cap=None, stall_halt=None, seed=0):
    rng = random.Random(seed); random.seed(seed)
    spends, ok_normal, ok_trapped, n_normal, n_trapped = [], 0, 0, 0, 0
    for _ in range(n_tasks):
        W = rng.randint(2, 6)
        trapped = rng.random() < f_trapped
        p = 0.02 if trapped else 0.9
        s, ok = run_task(p, W, cap=cap, stall_halt=stall_halt)
        spends.append(s)
        if trapped:
            n_trapped += 1; ok_trapped += ok
        else:
            n_normal += 1; ok_normal += ok
    spends.sort()
    p99 = spends[min(len(spends) - 1, int(0.99 * len(spends)))]
    return {
        "total": sum(spends), "median": statistics.median(spends),
        "p99": p99, "max": max(spends),
        "normal_success": ok_normal / max(1, n_normal),
        "trapped_success": ok_trapped / max(1, n_trapped),
    }

N, F = 5000, 0.03
base = trial(N, F, cap=None, seed=42)
# Convex cap: ~6x the normal-task expectation (W/p ~ 4/0.9 ~ 4.4 -> cap 28), plus a
# stall-based tail-risk halt (abort after 15 consecutive no-progress actions).
capped = trial(N, F, cap=28, stall_halt=15, seed=42)

print(f"Agent-metabolism convex cap | {N} tasks, {F:.0%} trapped, cost=actions")
print(f"{'metric':<18}{'NO CAP':>14}{'CONVEX CAP':>14}")
for k, label in [("total","total spend"),("median","median/task"),("p99","p99/task"),
                 ("max","MAX single run"),("normal_success","normal success"),
                 ("trapped_success","trapped success")]:
    a, b = base[k], capped[k]
    fa = f"{a:,.2f}" if k in ("median",) else (f"{a:.1%}" if "success" in k else f"{a:,.0f}")
    fb = f"{b:,.2f}" if k in ("median",) else (f"{b:.1%}" if "success" in k else f"{b:,.0f}")
    print(f"{label:<18}{fa:>14}{fb:>14}")
print(f"\nMAX single-run spend cut: {base['max']/max(1,capped['max']):.0f}x   "
      f"total spend cut: {(1-capped['total']/base['total']):.0%}")
print(f"Normal-task success delta: {capped['normal_success']-base['normal_success']:+.2%}")
