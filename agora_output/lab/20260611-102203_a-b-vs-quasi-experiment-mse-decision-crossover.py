import random, math, statistics as st
random.seed(11)

# "When does an A/B test (RCT) beat a quasi-experiment, and vice versa?"
# RCT:  unbiased, but expensive -> small n. estimate ~ N(delta, 4*sigma^2/n_rct)
# Quasi (DiD-like): cheap observational data -> large n = k*n_rct, BUT carries a
#   parallel-trends bias b. estimate ~ N(delta + b, 4*sigma^2/n_quasi)
# Superiority = lower MSE of the effect estimate AND higher decision accuracy
#   (reject null at alpha=.05 with CORRECT sign).
# Goal: map the effect-size threshold delta* where the winner flips, as a function of bias b.

SIGMA = 1.0
N_RCT = 200            # 100/arm -- a realistic small experiment
RUNS  = 6000
ALPHA = 1.96           # z for 95%

def trial(delta, b, k):
    n_rct = N_RCT
    n_quasi = k * n_rct
    se_rct  = math.sqrt(4*SIGMA**2 / n_rct)
    se_quasi= math.sqrt(4*SIGMA**2 / n_quasi)
    rct_err=[]; quasi_err=[]; rct_dec=0; quasi_dec=0
    for _ in range(RUNS):
        e_rct  = random.gauss(delta,       se_rct)
        e_quasi= random.gauss(delta + b,   se_quasi)
        rct_err.append((e_rct-delta)**2)
        quasi_err.append((e_quasi-delta)**2)
        # decision: reject H0 with correct sign
        if abs(e_rct/se_rct) > ALPHA and (e_rct>0)==(delta>0): rct_dec+=1
        if abs(e_quasi/se_quasi) > ALPHA and (e_quasi>0)==(delta>0): quasi_dec+=1
    return (st.mean(rct_err), st.mean(quasi_err), rct_dec/RUNS, quasi_dec/RUNS)

print(f"N_rct={N_RCT}/total (100/arm), quasi n = k*N_rct, sigma={SIGMA}")
for b, k in [(0.10, 10), (0.25, 10), (0.40, 10), (0.25, 30)]:
    print(f"\n--- bias b={b}, sample ratio k={k} (quasi MSE floor = b^2 = {b*b:.3f}) ---")
    print(f"{'delta':>6} {'MSE_rct':>8} {'MSE_qsi':>8} {'acc_rct':>8} {'acc_qsi':>8}  winner(MSE)")
    flip=None
    for delta in [0.05,0.10,0.15,0.20,0.30,0.50,0.80]:
        mr,mq,ar,aq = trial(delta,b,k)
        w = "RCT" if mr<mq else "QUASI"
        if flip is None and mr<mq: flip=delta  # RCT overtakes at small delta? track crossover
        print(f"{delta:6.2f} {mr:8.4f} {mq:8.4f} {ar:8.2f} {aq:8.2f}  {w}")
    # analytic crossover: MSE_rct = MSE_quasi -> 4s^2/n_rct = b^2 + 4s^2/n_quasi
    var_rct=4*SIGMA**2/N_RCT; var_q=4*SIGMA**2/(k*N_RCT)
    print(f"  analytic: RCT beats quasi (lower MSE) whenever b^2 > {var_rct-var_q:.4f}"
          f"  -> |b|>{math.sqrt(max(var_rct-var_q,0)):.3f}; here b={b} {'>' if b*b>var_rct-var_q else '<'} threshold")
