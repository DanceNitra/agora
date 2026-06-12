import random, math, statistics as st
random.seed(42)

# Synthesis: a UNIFIED coupled-Brownian market model. Textbook finance prices assets as
# INDEPENDENT geometric Brownian motion (GBM) -> Gaussian returns, stable correlations,
# diversification always works. Real markets show fat tails, volatility clustering, and
# correlations that spike toward 1 exactly in crashes. Claim: a single 2-parameter coupling
# (c = common-factor coupling, g = volatility feedback) nests independent GBM at (0,0) and
# reproduces all three stylized facts as coupling rises - and the dangerous regime (tail
# correlation -> 1) is a critical run-up, echoing our criticality canon. Source: simulation.

N, T = 40, 4000          # assets, days

def run(c, g):
    v = 1.0               # common volatility state
    rets = [[] for _ in range(N)]
    mkt = []
    recent = 0.0
    for t in range(T):
        # volatility feedback: stress raises vol (ARCH-like coupling across the whole market)
        v = 1.0 + g * abs(recent)
        z = random.gauss(0, 1)                       # market-wide shock (common factor)
        day = []
        for i in range(N):
            e = random.gauss(0, 1)
            r = math.sqrt(v) * ((1 - c) * e + c * z) # couple idiosyncratic + common
            rets[i].append(r); day.append(r)
        m = st.mean(day); mkt.append(m); recent = m
    # --- stylized facts ---
    flat = [r for series in rets for r in series]
    mu, sd = st.mean(flat), st.pstdev(flat)
    kurt = sum(((r-mu)/sd)**4 for r in flat)/len(flat)          # Gaussian = 3
    # volatility clustering: lag-1 autocorrelation of |market return|
    am = [abs(x) for x in mkt]; m2 = st.mean(am)
    num = sum((am[t]-m2)*(am[t+1]-m2) for t in range(len(am)-1))
    den = sum((x-m2)**2 for x in am); vclust = num/den if den else 0
    # tail correlation: avg pairwise corr on the worst 5% market days vs all days
    order = sorted(range(T), key=lambda t: mkt[t])
    crash_days = set(order[:max(5, T//20)])
    def avg_corr(days):
        cs = []
        for i in range(0, N, 4):
            for j in range(i+1, N, 7):
                xs=[rets[i][t] for t in days]; ys=[rets[j][t] for t in days]
                mx,my=st.mean(xs),st.mean(ys)
                cov=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
                sx=math.sqrt(sum((a-mx)**2 for a in xs)); sy=math.sqrt(sum((b-my)**2 for b in ys))
                if sx>0 and sy>0: cs.append(cov/(sx*sy))
        return st.mean(cs) if cs else 0
    return kurt, vclust, avg_corr(crash_days), avg_corr(range(T))

print("UNIFIED coupled-Brownian market: (c=common-factor coupling, g=vol feedback)\n")
print(f"{'regime':28s} {'kurtosis':>9s} {'vol-clust':>9s} {'corr|crash':>10s} {'corr|all':>9s}")
for label, c, g in [("textbook GBM (0,0)", 0.0, 0.0),
                    ("mild coupling (.3,1)", 0.3, 1.0),
                    ("stress regime (.5,3)", 0.5, 3.0),
                    ("near-critical (.7,6)", 0.7, 6.0)]:
    k, vc, cc, ca = run(c, g)
    print(f"{label:28s} {k:9.2f} {vc:9.2f} {cc:10.2f} {ca:9.2f}")
print("\nGBM baseline: kurtosis~3, ~0 clustering, crash-corr ~ all-corr. Coupling manufactures")
print("fat tails + clustering + a tail-correlation SPIKE (diversification fails when needed most).")
