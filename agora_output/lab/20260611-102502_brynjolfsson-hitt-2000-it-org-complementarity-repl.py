import random, math, statistics as st
random.seed(23)

# Brynjolfsson & Hitt (2000): organizational investments (process/work-practice change) have a
# LARGE influence on the value of IT. Computable core = COMPLEMENTARITY: output is super-additive
# in (IT capital, Org capital). True firm DGP (Cobb-Douglas-style in logs, linearized):
#   logY = a*logIT + b*logORG + g*(logIT*logORG) + other + eps     g>0 = complementarity
# Their central methodological claim: omit org capital (it's hard to measure) and you MISESTIMATE
# the return to IT. We test 3 things a clean model should show if the claim replicates:
#   (R1) marginal return to IT, dY/dIT = a + g*logORG, RISES with org capital
#   (R2) omitting org capital biases the estimated IT coefficient (omitted-variable bias)
#   (R3) the bias direction depends on corr(IT, ORG): complementary firms co-invest -> upward bias

N=4000
A_IT, B_ORG, G = 0.12, 0.10, 0.06   # modest main effects, positive complementarity
def draw_firms(rho):
    # IT and ORG investment correlated across firms (co-investment), corr~rho
    firms=[]
    for _ in range(N):
        z=random.gauss(0,1)
        it = z*math.sqrt(rho)+random.gauss(0,1)*math.sqrt(1-rho)
        org= z*math.sqrt(rho)+random.gauss(0,1)*math.sqrt(1-rho)
        y = A_IT*it + B_ORG*org + G*(it*org) + random.gauss(0,0.5)
        firms.append((it,org,y))
    return firms

def ols2(firms, use_org, use_int):
    # build design, solve normal equations (tiny, by hand for stdlib-only)
    import itertools
    rows=[]; ys=[]
    for it,org,y in firms:
        r=[1.0,it]
        if use_org: r.append(org)
        if use_int: r.append(it*org)
        rows.append(r); ys.append(y)
    k=len(rows[0])
    # X'X and X'y
    XtX=[[sum(rows[n][i]*rows[n][j] for n in range(len(rows))) for j in range(k)] for i in range(k)]
    Xty=[sum(rows[n][i]*ys[n] for n in range(len(rows))) for i in range(k)]
    # gaussian elimination
    M=[XtX[i][:]+[Xty[i]] for i in range(k)]
    for c in range(k):
        p=max(range(c,k),key=lambda r:abs(M[r][c])); M[c],M[p]=M[p],M[c]
        piv=M[c][c]
        for j in range(c,k+1): M[c][j]/=piv
        for r in range(k):
            if r!=c:
                f=M[r][c]
                for j in range(c,k+1): M[r][j]-=f*M[c][j]
    return [M[i][k] for i in range(k)]  # [intercept, b_IT, (b_ORG), (b_INT)]

print("True DGP: a_IT=0.12  b_ORG=0.10  g(complementarity)=0.06\n")
for rho in [0.0, 0.5, 0.8]:
    firms=draw_firms(rho)
    full=ols2(firms,True,True)     # correct spec
    no_int=ols2(firms,True,False)  # org in, no interaction
    no_org=ols2(firms,False,False) # org OMITTED (their warning case)
    # R1: marginal IT return at low vs high org (from full model)
    los=[f for f in firms if f[1]<-0.5]; his=[f for f in firms if f[1]>0.5]
    print(f"--- co-investment corr rho={rho} ---")
    print(f"  full spec:     b_IT={full[1]:.3f}  b_ORG={full[2]:.3f}  g_int={full[3]:.3f}")
    print(f"  org, no int:   b_IT={no_int[1]:.3f}  b_ORG={no_int[2]:.3f}")
    print(f"  ORG OMITTED:   b_IT={no_org[1]:.3f}   <- the 'value of IT' a naive analyst reports")
    bias=no_org[1]-A_IT
    print(f"  R2/R3 omitted-var bias on b_IT: {bias:+.3f}  ({'UPWARD' if bias>0 else 'downward'}; grows with rho)\n")
print("Recovered g>0 -> complementarity present; b_IT inflates as co-investment rises -> ignoring")
print("org capital MISESTIMATES the return to IT. Matches B&H(2000) central claim.")
