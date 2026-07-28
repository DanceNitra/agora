"""Pass 6: one script, one D, every size — because two of HIS scripts disagree at N=10.

His `constant_validation.py` (the 6-10 run) reports N=10 = 0.967717.
His `final_ed_scan.py` functions, which I just swept, give N=10 = 0.972092 at the same D = 0.3.

Both are his code and they differ by 0.0044 — larger than the sd he quotes for N=12 (0.0070/sqrt(9) =
0.0023 SEM). Before telling him anything about his own numbers, run ONE script across ALL sizes so the
series is internally consistent, and see whether the N-dependence is real or an artifact of comparing
two implementations.
"""
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from their_final_ed_scan import (chain_graph, diagnose_memory_safe,  # noqa: E402
                                 fine_diagnosis, introduce_contradiction)

STRENGTHS = np.linspace(0.0, 3.0, 9)
D = 0.3
PRED = 1.0 / np.sqrt(1.0 + D * D)

print(f"one script (final_ed_scan), D={D}, prediction 1/sqrt(1+D^2) = {PRED:.6f}\n")
print(f"{'N':>3} {'dim':>7} {'mean ratio':>12} {'sd':>9} {'no-valley mean':>15} {'no-valley sd':>13} {'secs':>7}")
out = []
for N in (6, 8, 10, 12):
    t0 = time.time()
    G = chain_graph(N)
    ce = (N // 2 - 1, N // 2)
    base, soc = [], []
    for s in STRENGTHS:
        Gs = introduce_contradiction(G, ce, s)
        _, _, g0 = diagnose_memory_safe(Gs, D=0.0, num_eig=5)
        base.append(fine_diagnosis(Gs, g0))
        _, _, g1 = diagnose_memory_safe(Gs, D=D, num_eig=5)
        soc.append(fine_diagnosis(Gs, g1))
    r = np.array(soc) / np.array(base)
    keep = np.abs(STRENGTHS - 0.38) > 1e-9          # drop the valley point
    out.append((N, r.mean(), r.std(ddof=1), r[keep].mean(), r[keep].std(ddof=1)))
    print(f"{N:>3} {2**N:>7} {r.mean():12.6f} {r.std(ddof=1):9.6f} "
          f"{r[keep].mean():15.6f} {r[keep].std(ddof=1):13.6f} {time.time()-t0:7.1f}")

a = np.array(out)
print(f"\n  his reported series (two different scripts): "
      f"N=6 0.982042 | N=8 0.960666 | N=10 0.967717 | N=12 0.958571")
print(f"  this one script                            : "
      + " | ".join(f"N={int(n)} {m:.6f}" for n, m, _, _, _ in out))
print(f"\n  spread across N (one script)  : {a[:,1].max()-a[:,1].min():.6f}")
print(f"  spread across N (his numbers) : {0.982042-0.958571:.6f}")
print(f"  distance of every size from 1/sqrt(1+D^2)={PRED:.6f}: "
      + ", ".join(f"{m-PRED:+.4f}" for _, m, _, _, _ in out))
