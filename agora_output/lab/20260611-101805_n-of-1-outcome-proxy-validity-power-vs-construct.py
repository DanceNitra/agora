import random, math, statistics as st
random.seed(7)

# n-of-1: ONE subject, T sessions. A reasoning intervention raises latent quality Q by delta
# at the midpoint. Each candidate proxy P = beta*Q + noise. We ask, for each proxy:
#   (1) construct validity: corr(P, Q)
#   (2) detection power at realistic T: P(pre/post Welch t-test rejects at alpha=.05 | true delta>0)
#   (3) false-positive rate at delta=0 (does the proxy invent effects?)
# A proxy is VALID only if it both tracks Q AND has usable power at n-of-1 T.

# Proxy signal-to-noise, grounded in how each behaves in practice:
#  retrieval_accuracy: tracks reasoning well but bounded [0,1] -> ceiling compresses signal
#  time_to_answer    : weak, confounded by familiarity/practice (can drift independent of Q)
#  decision_reversal : moderate link but a RARE event -> Bernoulli variance dominates at small T
PROXIES = {
    "retrieval_accuracy": dict(beta=0.70, noise=0.55, bounded=True,  base=0.55, rare=False),
    "time_to_answer":     dict(beta=0.35, noise=1.00, bounded=False, base=0.0,  rare=False, drift=0.04),
    "decision_reversal":  dict(beta=0.50, noise=0.0,  bounded=False, base=0.0,  rare=True,  rate0=0.12),
}
ALPHA = 0.05
RUNS = 4000

def welch_t(a, b):
    na, nb = len(a), len(b)
    ma, mb = st.mean(a), st.mean(b)
    va, vb = st.pvariance(a) if na<2 else st.variance(a), st.pvariance(b) if nb<2 else st.variance(b)
    va = max(va, 1e-9); vb = max(vb, 1e-9)
    se = math.sqrt(va/na + vb/nb)
    if se == 0: return 0.0, 1.0
    t = (mb - ma) / se
    df = (va/na + vb/nb)**2 / ((va/na)**2/(na-1) + (vb/nb)**2/(nb-1))
    # two-sided p via survival of |t| with a normal approx (df>=14 here -> fine)
    z = abs(t)
    p = 2*(1 - 0.5*(1+math.erf(z/math.sqrt(2))))
    return t, p

def gen_proxy(name, q):
    c = PROXIES[name]
    if c["rare"]:
        # decision-reversal: higher Q -> fewer reversals; rate shifts with Q (bounded)
        rate = max(0.01, min(0.5, c["rate0"] - 0.06*q))
        return 1.0 if random.random() < rate else 0.0
    val = c["beta"]*q + random.gauss(0, c["noise"]) + c.get("drift",0.0)*random.gauss(0,1)
    if c["bounded"]:
        val = c["base"] + 0.18*val
        val = max(0.0, min(1.0, val))
    return val

def run(delta, T):
    half = T//2
    pcorr = {k: [] for k in PROXIES}
    qall  = {k: [] for k in PROXIES}
    rej   = {k: 0 for k in PROXIES}
    for _ in range(RUNS):
        pre = {k: [] for k in PROXIES}; post = {k: [] for k in PROXIES}
        for i in range(T):
            q = random.gauss(0,1) + (delta if i>=half else 0.0)
            for k in PROXIES:
                p = gen_proxy(k, q)
                (post[k] if i>=half else pre[k]).append(p)
                pcorr[k].append(p); qall[k].append(q + (0 if i>=half else 0))
        for k in PROXIES:
            _, pv = welch_t(pre[k], post[k])
            if pv < ALPHA: rej[k]+=1
    out={}
    for k in PROXIES:
        # construct correlation P vs Q over all sessions (Q already encodes the shift)
        xs, ys = pcorr[k], qall[k]
        mx,my=st.mean(xs),st.mean(ys)
        cov=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/len(xs)
        sx=math.sqrt(max(st.pvariance(xs),1e-12)); sy=math.sqrt(max(st.pvariance(ys),1e-12))
        out[k]=(cov/(sx*sy), rej[k]/RUNS)
    return out

print("=== n-of-1 proxy validity: construct r (delta=0.8) & detection power by T ===")
print(f"{'proxy':22s} {'r(P,Q)':>8s} {'pow@T15':>8s} {'pow@T25':>8s} {'pow@T40':>8s} {'FPR@T25':>8s}")
fp = run(0.0, 25)
for k in PROXIES:
    r,_ = run(0.8, 999 if False else 40)[k]  # r stable in large T
    pw = {T: run(0.8, T)[k][1] for T in (15,25,40)}
    print(f"{k:22s} {r:8.2f} {pw[15]:8.2f} {pw[25]:8.2f} {pw[40]:8.2f} {fp[k][1]:8.3f}")
print("\nVALIDITY RULE: usable proxy needs r>=0.4 AND power>=0.8 at T<=25 AND FPR~alpha.")
