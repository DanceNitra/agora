import random, statistics as st
random.seed(7)

# Demonstrate the regime where SC clearly beats DiD: a LARGE, SYSTEMATIC parallel-trends violation.
# One strongly-trending factor; the treated unit loads HIGH on it, the control AVERAGE loads low,
# but a subset of controls load high (so SC can match the treated pre-trend by upweighting them).
# Sweep pre-period length to show SC's weight-fitting needs enough pre-data. Source: simulation.

NC=8; TPOST=6; TAU=2.0; RUNS=120

def run_once(TPRE):
    g=0.25                                            # strong trend on factor 0
    F=[ g*t + random.gauss(0,.5) for t in range(TPRE+TPOST)]   # single dominant trending factor
    # control loadings on the trending factor: half high (~0.9), half low (~0.1)
    lam=[0.9 if i<NC//2 else 0.1 for i in range(NC)]
    lt=0.85                                            # treated loads HIGH (like the high subset)
    def out(load,t,treated=False):
        y=load*F[t]+random.gauss(0,.3)
        if treated and t>=TPRE: y+=TAU
        return y
    ctrl=[[out(lam[i],t) for t in range(TPRE+TPOST)] for i in range(NC)]
    trt=[out(lt,t,True) for t in range(TPRE+TPOST)]
    # DiD
    did=(st.mean(trt[TPRE:])-st.mean(trt[:TPRE]))-(st.mean(st.mean(c[TPRE:]) for c in ctrl)-st.mean(st.mean(c[:TPRE]) for c in ctrl))
    # SC
    best=None;bw=None
    for _ in range(800):
        w=[random.random() for _ in range(NC)]; s=sum(w); w=[x/s for x in w]
        err=sum((trt[t]-sum(w[i]*ctrl[i][t] for i in range(NC)))**2 for t in range(TPRE))
        if best is None or err<best: best=err; bw=w
    cf=[sum(bw[i]*ctrl[i][t] for i in range(NC)) for t in range(TPRE,TPRE+TPOST)]
    sc=st.mean(trt[TPRE:])-st.mean(cf)
    return abs(did-TAU), abs(sc-TAU)

print(f"true tau={TAU}. LARGE systematic violation (treated high-loading, control-avg low).\n")
print(f"{'pre-periods':>11} {'DiD |bias|':>11} {'SC |bias|':>10} {'winner':>8}")
for TPRE in (6,12,24,48):
    ds=[];ss=[]
    for _ in range(RUNS):
        d,s=run_once(TPRE); ds.append(d); ss.append(s)
    md=st.mean(ds); ms=st.mean(ss)
    print(f"{TPRE:11d} {md:11.3f} {ms:10.3f} {'SC' if ms<md else 'DiD':>8}")
print("\nDiD is badly biased here (treated trends up, control-average doesn't). SC fixes it ONCE there")
print("are enough pre-periods to fit weights reliably; at very short pre-periods SC's fitting noise")
print("can rival its bias reduction. So: SC > DiD under a big systematic pre-trend gap + adequate pre-data.")
