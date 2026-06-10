
import numpy as np
rng = np.random.default_rng(42)

# MODEL: items arrive each window with heterogeneous FUTURE retrieval rates (skewed, like the
# vault's bimodal value distribution). A consolidation budget B of N candidates per window.
# Policies pick which items get consolidated; consolidated items then serve their future
# retrievals. Claim under test: (1) value-ranked beats FIFO/random; (2) the advantage GROWS
# as the budget shrinks (scarcity makes governance matter); (3) does it survive NOISY value
# estimates (the realistic regime)?

def simulate(policy, B, N=40, T=200, noise_sd=0.0):
    total_hits = 0.0
    for _ in range(T):
        true_rate = rng.lognormal(mean=0.0, sigma=1.2, size=N)   # skewed future-retrieval value
        if policy == 'value':
            est = true_rate * np.exp(rng.normal(0, noise_sd, N)) if noise_sd else true_rate
            pick = np.argsort(-est)[:B]
        elif policy == 'fifo':
            pick = np.arange(B)                                   # arrival order
        else:
            pick = rng.choice(N, B, replace=False)                # random
        total_hits += true_rate[pick].sum()
    return total_hits

print('budget  value(perfect)  value(noisy sd=1.0)  fifo    random   adv_perfect  adv_noisy')
for B in (20, 10, 5, 2):
    v  = simulate('value', B)
    vn = simulate('value', B, noise_sd=1.0)
    f  = simulate('fifo', B)
    r  = simulate('random', B)
    base = (f + r) / 2
    print(f'{B:>3}/40  {v:>12.0f}  {vn:>17.0f}  {f:>7.0f}  {r:>7.0f}   x{v/base:>5.2f}      x{vn/base:>5.2f}')

print()
print('CLAIM TESTS:')
adv = [simulate('value', B) / simulate('random', B) for B in (20, 10, 5, 2)]
print('1) value-ranked beats random at every budget:', all(a > 1.1 for a in adv))
print('2) advantage GROWS as budget shrinks (scarcity):', all(adv[i] < adv[i+1] for i in range(3)),
      '->', [round(a, 2) for a in adv])
advn = [simulate('value', B, noise_sd=1.0) / simulate('random', B) for B in (20, 10, 5, 2)]
print('3) advantage under REALISTIC NOISE (sd=1.0):', [round(a, 2) for a in advn])
advn2 = [simulate('value', B, noise_sd=2.0) / simulate('random', B) for B in (20, 10, 5, 2)]
print('   under HEAVY noise (sd=2.0):', [round(a, 2) for a in advn2])
