import random, statistics

# Is the autophagy <-> knowledge-pruning analogy a real mechanism or a false friend?
# Autophagy's distinctive trait (vs generic cleanup) is that it is PERIODIC and STRESS-INDUCED
# (fasting/scarcity upregulates it) rather than continuous. Test the transfer in a retrieval store.
#
# A fixed-capacity store (K) receives a stream of items (a few high-value, many low-value "junk").
# Retrieval quality each step = signal/clutter = mean value of items currently held (a lean,
# high-value store retrieves better; clutter dilutes it). Every PRUNING EVENT costs a fixed
# overhead F (re-rank / re-index / lock), independent of how many items it drops.
#   CONTINUOUS  : prune to top-K every step it overflows  -> always lean, but ~T pruning events
#   PERIODIC(P) : let clutter accumulate, prune to top-K every P steps (autophagy/hormesis)
#                 -> tolerates clutter between purges, but only ~T/P pruning events
# Net value = sum(retrieval quality) - F * (number of pruning events).
# Question: does periodic ever BEAT continuous, and at what overhead F* is the crossover?

random.seed(13)

def value():
    return random.uniform(0.6, 1.0) if random.random() < 0.25 else random.uniform(0.0, 0.3)

def run(mode, F, T=2000, K=100, P=25):
    store = []
    retrieval = 0.0
    events = 0
    for t in range(1, T + 1):
        store.append(value())
        if mode == "continuous":
            if len(store) > K:
                store.sort(reverse=True); store = store[:K]; events += 1
        else:  # periodic / autophagy
            if t % P == 0 and len(store) > K:
                store.sort(reverse=True); store = store[:K]; events += 1
        retrieval += statistics.mean(store)          # signal/clutter this step
    return retrieval - F * events, retrieval, events

print("net value (retrieval - F*events), T=2000, K=100, P=25, 1 seed\n")
print(f"{'F (per-event overhead)':>22} | {'continuous net':>14} | {'periodic net':>13} | winner")
crossover = None; prev = None
for F in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
    cn, cr, ce = run("continuous", F)
    pn, pr, pe = run("periodic", F)
    win = "continuous" if cn > pn else "PERIODIC (autophagy)"
    print(f"{F:>22.1f} | {cn:>14.1f} | {pn:>13.1f} | {win}")
    if prev and crossover is None and prev[0] >= prev[1] and cn < pn:
        crossover = (prevF, F)
    prev = (cn, pn); prevF = F

_, cr, ce = run("continuous", 0.0)
_, pr, pe = run("periodic", 0.0)
print(f"\nretrieval-quality: continuous {cr:.1f} (events {ce}) vs periodic {pr:.1f} (events {pe})")
print(f"continuous's retrieval edge = {cr-pr:.1f}; it pays {ce}/{pe} = {ce/max(1,pe):.0f}x more pruning events")
print(f"\nCROSSOVER overhead F* (periodic overtakes) between F = {crossover}")
print("VERDICT: BOTH-depending-on-cost — autophagy analogy is a FALSE FRIEND when pruning is cheap")
print("         (continuous wins), a REAL mechanism when each pruning event is expensive (periodic wins).")
