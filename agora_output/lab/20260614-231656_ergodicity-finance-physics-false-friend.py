import random, statistics, math

# Dialectic kernel: does "Finance IS Physics" (our vault's structural-isomorphism belief) hold,
# or is it a false friend?  Both use the same SURFACE formalism (Gaussians, exponentials,
# "partition functions"). The load-bearing assumption that makes equilibrium statistical
# mechanics work is ERGODICITY: time-average = ensemble-average. Test whether that property
# survives the transfer to finance's MULTIPLICATIVE wealth dynamics.

random.seed(5)

def rates(multiplicative, mu, sigma, T, paths):
    # returns (ensemble-average growth rate, median per-trajectory time-average growth rate)
    finals_for_ensemble = []   # value at T per path (for ensemble mean)
    time_avg_rates = []        # (1/T) * total growth per path
    for _ in range(paths):
        x = 1.0 if multiplicative else 0.0
        for _ in range(T):
            step = random.gauss(mu, sigma)
            if multiplicative:
                x *= math.exp(step)
            else:
                x += step
        finals_for_ensemble.append(x)
        if multiplicative:
            time_avg_rates.append(math.log(x) / T)      # per-step log-growth of THIS trajectory
        else:
            time_avg_rates.append(x / T)                # per-step additive growth of THIS trajectory
    if multiplicative:
        ens_rate = math.log(statistics.mean(finals_for_ensemble)) / T
    else:
        ens_rate = statistics.mean(finals_for_ensemble) / T
    return ens_rate, statistics.median(time_avg_rates)

mu, sigma, T, P = 0.0, 0.30, 300, 20000

print("ERGODICITY TEST — time-average (what one actor lives) vs ensemble-average (the partition fn)")
print(f"params: mu={mu}, sigma={sigma}, T={T}, paths={P}\n")

add_ens, add_time = rates(False, mu, sigma, T, P)
print(f"ADDITIVE  (physics-like): ensemble rate={add_ens:+.5f}  time-avg rate={add_time:+.5f}  gap={abs(add_ens-add_time):.5f}")

mul_ens, mul_time = rates(True, mu, sigma, T, P)
print(f"MULTIPLIC.(finance-like): ensemble rate={mul_ens:+.5f}  time-avg rate={mul_time:+.5f}  gap={abs(mul_ens-mul_time):.5f}")
print(f"\npredicted non-ergodicity gap for multiplicative = sigma^2/2 = {sigma*sigma/2:+.5f}")

erg_add = abs(add_ens-add_time) < 0.01
nonerg_mul = abs(mul_ens-mul_time) > 5*abs(add_ens-add_time) + 0.005
print(f"\nADDITIVE ergodic (time==ensemble)? {erg_add}")
print(f"MULTIPLICATIVE non-ergodic (time!=ensemble by ~sigma^2/2)? {nonerg_mul}")
print("VERDICT:", "FALSE FRIEND — same surface math, ergodic foundation BREAKS in finance"
      if (erg_add and nonerg_mul) else "isomorphism holds")
