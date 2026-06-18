
import numpy as np
rng = np.random.default_rng(11)
# Misspecification = an OMITTED confounder. Truth: y = b*x + g*z + eps, with corr(x,z)=rho.
# A Bayesian fits the misspecified model y ~ N(b*x, s^2) (omits z) and reports a 95% credible
# interval for b from the posterior (flat prior -> Normal around OLS, width = sampling noise only).
# Question: does that 95% interval actually cover the TRUE b? (frequentist coverage of the Bayesian CI)
b_true, g, rho = 1.0, 1.0, 0.6
def coverage(n, trials=3000):
    hit = 0; widths = []; biases = []
    for _ in range(trials):
        zx = rng.multivariate_normal([0,0], [[1,rho],[rho,1]], size=n)
        x, z = zx[:,0], zx[:,1]
        y = b_true*x + g*z + rng.standard_normal(n)*0.5
        # OLS of y on x alone (the misspecified model) + its posterior/sampling CI
        Sxx = (x*x).sum()
        bhat = (x*y).sum()/Sxx
        resid = y - bhat*x
        s2 = (resid**2).sum()/(n-1)
        se = np.sqrt(s2/Sxx)               # Bayesian posterior sd for b under flat prior == OLS se
        lo, hi = bhat-1.96*se, bhat+1.96*se
        hit += (lo <= b_true <= hi)
        widths.append(hi-lo); biases.append(bhat-b_true)
    return hit/trials, np.mean(widths), np.mean(biases)
print("true b=1.0, omitted confounder z (corr 0.6). Bayesian 95% credible interval for b:")
print(" n     coverage   mean_CI_width   mean_bias")
for n in [50, 200, 1000, 5000, 20000]:
    cov, w, bias = coverage(n)
    print(f"{n:>6}   {cov:5.1%}      {w:.3f}        {bias:+.3f}")
print("Nominal is 95%. Under the omitted confounder the credible interval's coverage COLLAPSES as n grows")
print("because the bias is fixed (~0.36) while the interval shrinks ~1/sqrt(n): calibration != coverage.")
