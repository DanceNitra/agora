import random, statistics

# Severe test of the belief: "knowledge unit economics become measurable ONLY when you
# instrument the knowledge-to-decision FUNNEL; instrumented systems optimize value at least
# as well as non-instrumented ones." Its own falsifier: if a system that does NOT trace
# knowledge->outcome optimizes value as well as an instrumented one, the thesis fails.
#
# Disconfirming mechanism (our own Goodhart law e97ad5 + Johnson's slow hunch / Kauffman's
# unprestatable exaptation): the funnel trace can only measure value that is ATTRIBUTABLE to a
# decision = the LEGIBLE component. The highest-value knowledge often pays off later via
# combinatorial recombination = an ILLEGIBLE component the trace is structurally blind to.
#
# Model: N notes, each with legible value L and illegible value I. True value of a note is a
# blend V = (1-f)*L + f*I, where f = the illegible fraction of total knowledge value.
#   INSTRUMENTED policy keeps the top-K notes by the funnel trace, which sees only L (+noise).
#   REUSE policy (non-instrumented) keeps top-K by a reuse signal R ~ V*lognormal-noise
#     (notes get re-accessed in proportion to true usefulness, legible or not).
# Realized value = sum of TRUE V over kept notes. Compare to the oracle (top-K by true V).
# Question: at what illegible fraction f* does REUSE overtake INSTRUMENTED?  Below f* the
# belief holds; above it the belief's own falsifier fires.

random.seed(11)

def trial(N, K, f, trace_noise=0.10, reuse_noise=0.55):
    notes = []
    for _ in range(N):
        L = random.random(); I = random.random()
        V = (1 - f) * L + f * I
        trace = L * (1 + random.gauss(0, trace_noise))          # funnel sees legible only
        reuse = V * (2.718 ** random.gauss(0, reuse_noise))      # reuse ~ total usefulness, noisy
        notes.append((V, trace, reuse))
    oracle = sum(sorted((n[0] for n in notes), reverse=True)[:K])
    instr = sum(n[0] for n in sorted(notes, key=lambda n: n[1], reverse=True)[:K])
    reuse = sum(n[0] for n in sorted(notes, key=lambda n: n[2], reverse=True)[:K])
    return instr / oracle, reuse / oracle                       # fraction of oracle value captured

N, K, T = 400, 80, 400
print("f=illegible value fraction | instrumented vs reuse (frac of oracle value captured)")
print(f"{'f':>5} | {'instrumented':>12} {'reuse':>8} | winner")
crossover = None
prev = None
for fi in range(0, 11):
    f = fi / 10.0
    pairs = [trial(N, K, f) for _ in range(T)]
    instr = statistics.mean(p[0] for p in pairs)
    reuse = statistics.mean(p[1] for p in pairs)
    win = "instrumented" if instr > reuse else "REUSE (belief fails)"
    print(f"{f:>5.1f} | {instr:>12.3f} {reuse:>8.3f} | {win}")
    if prev and crossover is None and prev[0] > prev[1] and instr <= reuse:
        crossover = (prev_f, f)
    prev = (instr, reuse); prev_f = f

print(f"\nCROSSOVER f* (reuse overtakes instrumented) between f = {crossover}")
print("Belief holds for f below f*, FAILS (by its own falsifier) above it.")
