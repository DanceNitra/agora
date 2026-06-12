import random, math, statistics as st
random.seed(42)

# ANALOGY (structural): Entropy -> Competitive Matrix. Skeleton of the 2nd law: a closed system's
# entropy S rises monotonically to a MAXIMUM (uniform distribution); holding S below max requires
# continuous WORK (a dissipative structure exports entropy). Map: a market = firms x capability
# dimensions. Imitation diffuses each firm's capability toward the cross-firm mean (entropy rise
# toward uniform = perfect competition). Economic profit ~ distance from max entropy (differentiation).
# Maintaining differentiation costs investment (work). Source: simulation.

N, K = 12, 6          # firms, capability dimensions
LAM = 0.06            # imitation/diffusion rate per period (advantages erode toward the mean)
T = 200

def fresh():
    return [[random.gauss(0, 1) for _ in range(K)] for _ in range(N)]

def col_entropy(C, j):
    # Shannon entropy of the (softmax-normalised) capability distribution across firms on dim j;
    # max = log(N) when all firms are identical (perfectly commoditised).
    xs = [C[i][j] for i in range(N)]
    m = max(xs); ex = [math.exp(x - m) for x in xs]; Z = sum(ex)
    p = [e / Z for e in ex]
    return -sum(pi * math.log(pi) for pi in p if pi > 0)

def metrics(C):
    Smax = math.log(N)
    S = st.mean(col_entropy(C, j) for j in range(K)) / Smax     # 1.0 = max entropy (commoditised)
    profit = st.mean(st.pstdev([C[i][j] for i in range(N)]) for j in range(K))  # differentiation
    return S, profit

def step(C, invest):
    means = [st.mean(C[i][j] for i in range(N)) for j in range(K)]
    for i in range(N):
        for j in range(K):
            C[i][j] += LAM * (means[j] - C[i][j])               # imitation: drift to the mean (entropy+)
    if invest:
        # WORK: each period the current leader on each dim invests to restore some dispersion
        for j in range(K):
            lead = max(range(N), key=lambda i: C[i][j])
            C[lead][j] += LAM * 1.5                             # push the frontier out (costs investment)

print(f"N={N} firms, K={K} dims, imitation rate {LAM}.  S=normalised entropy (1.0 = commoditised)\n")
for label, invest in [("NO investment (closed system)", False), ("sustained investment (work)", True)]:
    C = fresh()
    s0, p0 = metrics(C)
    for _ in range(T): step(C, invest)
    s1, p1 = metrics(C)
    print(f"{label:32s}  S: {s0:.3f} -> {s1:.3f}   profit(differentiation): {p0:.2f} -> {p1:.2f}")
print("\nNo investment -> entropy climbs toward max (S->1), differentiation/profit collapses to ~0")
print("(perfect competition). Investment is the WORK that holds entropy below max -> profit persists.")
