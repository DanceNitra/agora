"""D-sweep at N=12 — their code, their sizes, and all 24 cores.

N=10 was cheap enough to run serially; N=12 is 4096-dimensional and every (s, D) pair is an independent
diagonalisation, so there is no reason to do them one at a time. The pool is the point: this box has 24
logical cores and the earlier serial habit already cost an hour tonight.
"""
import multiprocessing as mp
import sys

import numpy as np

STRENGTHS = np.linspace(0.0, 3.0, 9)
DS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
N = 12


def one(args):
    """One (s, D) diagnosis, in a worker. Imports inside so each process is self-contained."""
    sys.path.insert(0, r"C:\Users\Danculus\agora\research\probes\drahos_check")
    from their_final_ed_scan import (chain_graph, diagnose_memory_safe,
                                     fine_diagnosis, introduce_contradiction)
    s, D = args
    G = chain_graph(N)
    ce = (N // 2 - 1, N // 2)
    Gs = introduce_contradiction(G, ce, s)
    _, _, gs = diagnose_memory_safe(Gs, D=D, num_eig=5)
    return (s, D, fine_diagnosis(Gs, gs))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    jobs = [(float(s), float(d)) for d in DS for s in STRENGTHS]
    workers = min(24, mp.cpu_count())
    print(f"N={N} (dim {2**N}), {len(jobs)} diagonalisations over {workers} processes")
    import time
    t0 = time.time()
    with mp.Pool(workers) as pool:
        res = pool.map(one, jobs)
    dt = time.time() - t0
    print(f"done in {dt:.1f}s ({len(jobs)/dt:.1f} diagonalisations/s)\n")

    fine = {(round(s, 6), round(d, 6)): v for s, d, v in res}
    base = np.array([fine[(round(float(s), 6), 0.0)] for s in STRENGTHS])

    print(f"{'D':>5} {'predicted 1/sqrt(1+D^2)':>24} {'measured mean':>14} {'sd':>9} {'|diff|':>8}")
    rows = []
    for D in DS:
        soc = np.array([fine[(round(float(s), 6), round(D, 6))] for s in STRENGTHS])
        r = soc / base
        pred = 1.0 / np.sqrt(1.0 + D * D)
        rows.append((D, pred, r.mean(), r.std(ddof=1)))
        print(f"{D:5.2f} {pred:24.6f} {r.mean():14.6f} {r.std(ddof=1):9.6f} "
              f"{abs(r.mean()-pred):8.6f}")

    a = np.array(rows)
    m = a[1:]                                  # drop D=0, where the ratio is 1 by construction
    print(f"\n  correlation prediction vs measurement (D>0): "
          f"{np.corrcoef(m[:,1], m[:,2])[0,1]:+.4f}")
    print(f"  largest deviation from the curve            : {np.abs(m[:,2]-m[:,1]).max():.6f}")
    print(f"  ratio at D=0.3                              : {a[3,2]:.6f} "
          f"(their reported N=12 value 0.958572)")
    print(f"  swing from D=0.1 to D=1.0                   : {m[0,2]:.4f} -> {m[-1,2]:.4f}")
