import random, statistics as st
random.seed(42)

# Deepens flywheel 20156b19 (campaign d9b09872): threats to causal inference in n-of-1
# self-experiments. TRUE treatment effect tau = 0 throughout. We measure how much SPURIOUS
# effect three threats manufacture, and which DESIGN control removes each:
#   (1) regression to the mean (RTM): you start the intervention when you feel WORST
#   (2) practice/secular trend: you drift better over time regardless of treatment
#   (3) placebo/expectancy: believing it works adds bias on treated days (unless blinded)
# Source: simulation.

T = 40                 # days
TREND = 0.03           # secular improvement/day (practice, seasonality, natural recovery)
PHI, SD = 0.6, 1.0     # AR(1) day-to-day mood so troughs exist for RTM to bite
PLACEBO = 0.4          # expectancy bias added on treated days when UNBLINDED
TAU = 0.0              # TRUE treatment effect = ZERO
RUNS = 4000

def gen_series():
    y = [0.0]*T
    e = 0.0
    for t in range(T):
        e = PHI*e + random.gauss(0, SD)
        y[t] = TREND*t + e
    return y

def naive_start_when_worst(y):
    # start treatment at the trough of the first half (selection on a low baseline = RTM)
    half = T//2
    start = min(range(half), key=lambda t: y[t])
    pre = y[:start+1]; post = [v + TAU + PLACEBO for v in y[start+1:]]   # unblinded
    return st.mean(post) - st.mean(pre)

def randomized_crossover(y, blinded):
    # each day independently randomized to treat/control (no baseline selection -> kills RTM,
    # balances trend in expectation). placebo only on treated days if UNBLINDED.
    tr, ct = [], []
    for t in range(T):
        if random.random() < 0.5:
            tr.append(y[t] + TAU + (0.0 if blinded else PLACEBO))
        else:
            ct.append(y[t])
    if not tr or not ct: return None
    return st.mean(tr) - st.mean(ct)

def summary(vals):
    vals = [v for v in vals if v is not None]
    m = st.mean(vals); sd = st.pstdev(vals)
    # false-positive rate of a naive 1-sample test that the effect>0 (|m/se|>1.96)
    se = sd/(len(vals)**0.5)
    return m, sd

naive, cross_u, cross_b = [], [], []
for _ in range(RUNS):
    y = gen_series()
    naive.append(naive_start_when_worst(y))
    cross_u.append(randomized_crossover(y, blinded=False))
    cross_b.append(randomized_crossover(y, blinded=True))

print(f"TRUE effect tau = {TAU} (any nonzero estimate is pure artifact)\n")
for name, vals in [("NAIVE pre/post, start-when-worst (RTM+trend+placebo)", naive),
                   ("RANDOMIZED crossover, UNBLINDED (kills RTM+trend)", cross_u),
                   ("RANDOMIZED crossover, BLINDED (kills all three)", cross_b)]:
    m, sd = summary(vals)
    print(f"{name:54s} apparent effect = {m:+.3f}  (sd {sd:.2f})")
print("\nRTM+trend contribution  = naive - unblinded-crossover")
print(f"  = {st.mean(naive) - st.mean([v for v in cross_u if v is not None]):+.3f}")
print(f"placebo contribution    = unblinded - blinded crossover = "
      f"{st.mean([v for v in cross_u if v is not None]) - st.mean([v for v in cross_b if v is not None]):+.3f}  (true placebo set {PLACEBO})")
