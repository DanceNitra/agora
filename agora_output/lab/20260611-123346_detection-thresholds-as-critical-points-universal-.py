import random, math, statistics as st
random.seed(42)

# Model the belief: "detection thresholds are critical points with UNIVERSAL run-up dynamics."
# Mechanism = critical slowing down. A system near a fold/transcritical threshold behaves like
#   x_{t+1} = lam * x_t + noise,  with lam -> 1 as the control parameter -> the critical point.
# Predictions (universal early-warning signals):
#   (1) lag-1 autocorrelation AC1 -> lam -> 1
#   (2) stationary variance Var = s^2/(1-lam^2) DIVERGES as (1-lam)^(-1)  [exponent -1]
# UNIVERSALITY test: is the divergence exponent the SAME regardless of the noise distribution?
# Source: simulation.

def noise(kind):
    if kind == "gauss":   return random.gauss(0, 1)
    if kind == "uniform": return random.uniform(-math.sqrt(3), math.sqrt(3))   # var 1
    if kind == "laplace":                                                       # heavy tail, var 1
        u = random.random() - 0.5
        return -(1/math.sqrt(2)) * (1 if u >= 0 else -1) * math.log(1 - 2*abs(u))
    raise ValueError

def stationary_stats(lam, kind, n=60000, burn=2000):
    x = 0.0; xs = []
    for t in range(n + burn):
        x = lam * x + noise(kind)
        if t >= burn: xs.append(x)
    var = st.pvariance(xs)
    m = st.mean(xs)
    num = sum((xs[i]-m)*(xs[i+1]-m) for i in range(len(xs)-1))
    den = sum((v-m)**2 for v in xs)
    ac1 = num/den if den else 0.0
    return var, ac1

def fit_slope(xs, ys):                 # log-log slope
    n=len(xs); mx=st.mean(xs); my=st.mean(ys)
    cov=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); vx=sum((a-mx)**2 for a in xs)
    return cov/vx

lams = [0.80, 0.90, 0.95, 0.975, 0.99]
print("Approach to threshold (lam->1). Theory: Var ~ (1-lam)^-1, AC1 -> lam.\n")
print(f"{'noise':9s} " + " ".join(f"Var@{l}" for l in lams) + "   exponent  AC1@0.99")
for kind in ("gauss", "uniform", "laplace"):
    vars_, acs = [], []
    for l in lams:
        v, a = stationary_stats(l, kind)
        vars_.append(v); acs.append(a)
    # fit log(Var) vs log(1-lam)
    expo = fit_slope([math.log(1-l) for l in lams], [math.log(v) for v in vars_])
    print(f"{kind:9s} " + " ".join(f"{v:7.1f}" for v in vars_) + f"   {expo:+.3f}   {acs[-1]:.3f}")
print("\nVERDICT: run-up (AC1->1, Var diverges) is present; universality holds iff the exponent is")
print("~-1 and INVARIANT across noise distributions (microscopic details wash out).")
