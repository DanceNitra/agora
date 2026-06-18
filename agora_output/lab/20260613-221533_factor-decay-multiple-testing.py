
import numpy as np
rng = np.random.default_rng(8)
# Why published factors decay out of sample: with many candidates tested, the BEST in-sample is
# partly luck (multiple testing). Out of sample that luck doesn't repeat -> the premium shrinks.
# M candidate factors, T months split in half. Most are pure noise (true mean 0); a few are real.
M, T = 300, 240
half = T//2
frac_real, real_mu = 0.10, 0.12      # 10% of factors have a real monthly premium of 0.12 (sd 1)
def trial():
    mu_true = np.where(rng.random(M) < frac_real, real_mu, 0.0)
    R = rng.standard_normal((M, T)) + mu_true[:,None]
    IS, OOS = R[:,:half], R[:,half:]
    sharpe_is = IS.mean(1)/(IS.std(1)+1e-9)*np.sqrt(12)
    pick = int(np.argmax(sharpe_is))                 # data-mine: choose best in-sample Sharpe
    s_is = sharpe_is[pick]
    s_oos = OOS[pick].mean()/(OOS[pick].std()+1e-9)*np.sqrt(12)
    return s_is, s_oos, mu_true[pick] > 0
trials = 2000
res = np.array([trial()[:2] for _ in range(trials)])
real_rate = np.mean([trial()[2] for _ in range(trials)])
is_m, oos_m = res[:,0].mean(), res[:,1].mean()
print(f"{M} candidate factors, {frac_real:.0%} truly real (monthly mu={real_mu}); pick best in-sample Sharpe")
print(f"selected factor IN-SAMPLE Sharpe:  {is_m:.2f}")
print(f"selected factor OUT-OF-SAMPLE Sharpe: {oos_m:.2f}")
print(f"DECAY: {100*(1-oos_m/is_m):.0f}% of the in-sample Sharpe vanishes out of sample")
print(f"fraction of 'winning' factors that were actually real: {real_rate:.0%}")
