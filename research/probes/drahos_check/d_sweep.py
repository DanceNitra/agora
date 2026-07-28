"""THE DECISIVE TEST, run with THEIR OWN code: is the "constant" just 1/sqrt(1+D^2)?

A uniform Dzyaloshinskii-Moriya / Rashba term on a chain is removed exactly by a local spin rotation,
which renormalises the exchange to J' = sqrt(J^2 + D^2). Everything measured in units of the exchange
then carries a factor 1/sqrt(1+(D/J)^2). At their D = 0.3 that is 0.95782629 — and their measured ratio
is 0.9578.

If that is what is happening, the ratio is not a constant at all: it is a function of the coupling THEY
CHOSE, and at D = 0.5 it must be 0.894427.

So: import their `graph_to_hamiltonian_sparse_memory_safe`, `diagnose_memory_safe`, `fine_diagnosis`
and `introduce_contradiction` unchanged, and sweep D. Nothing of mine is in the physics — only the
sweep. Either the ratio tracks the curve or it does not.
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from their_final_ed_scan import (chain_graph, diagnose_memory_safe,  # noqa: E402
                                 fine_diagnosis, introduce_contradiction)

STRENGTHS = np.linspace(0.0, 3.0, 9)
DS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
N = 10                      # 1024-dim: their exact code, small enough to sweep D

G = chain_graph(N)
center_edge = (N // 2 - 1, N // 2)
print(f"their code, chain N={N}, center_edge={center_edge}, dim={2**N}")
print(f"s grid: {[f'{x:.2f}' for x in STRENGTHS]}\n")

# baseline: pure Heisenberg (D=0) once per s
base = []
for s in STRENGTHS:
    Gs = introduce_contradiction(G, center_edge, s)
    _, _, gs = diagnose_memory_safe(Gs, D=0.0, num_eig=5)
    base.append(fine_diagnosis(Gs, gs))
base = np.array(base)

print(f"{'D':>5} {'predicted 1/sqrt(1+D^2)':>24} {'measured mean ratio':>21} {'sd':>9} {'|diff|':>9}")
rows = []
for D in DS:
    soc = []
    for s in STRENGTHS:
        Gs = introduce_contradiction(G, center_edge, s)
        _, _, gs = diagnose_memory_safe(Gs, D=D, num_eig=5)
        soc.append(fine_diagnosis(Gs, gs))
    soc = np.array(soc)
    r = soc / base
    pred = 1.0 / np.sqrt(1.0 + D * D)
    rows.append((D, pred, float(r.mean()), float(r.std(ddof=1))))
    print(f"{D:5.2f} {pred:24.6f} {r.mean():21.6f} {r.std(ddof=1):9.6f} "
          f"{abs(r.mean()-pred):9.6f}")

print("\n=== VERDICT ===")
arr = np.array(rows)
dev = np.abs(arr[:, 2] - arr[:, 1])
worst = dev.max()
print(f"  largest |measured - 1/sqrt(1+D^2)| across the sweep: {worst:.6f}")
if worst < 0.01:
    print("  -> the 'constant' IS the DM gauge factor. It is a function of D, not a constant.")
else:
    print("  -> the ratio does NOT follow 1/sqrt(1+D^2); the gauge explanation fails and the")
    print("     empirical factor is something else — which would itself be the finding.")
corr = float(np.corrcoef(arr[:, 1], arr[:, 2])[0, 1]) if len(arr) > 2 else float("nan")
print(f"  correlation between prediction and measurement across D: {corr:+.4f}")
