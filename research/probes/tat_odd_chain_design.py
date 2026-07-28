"""Marat asked us to separate three variables. Two of them are the same variable, and a third is constant.

His request (2026-07-28): "If you can separate the three variables -- primality, divisibility by 3, and
arm length -- I would be very grateful. My intuition says arm length is the real variable."

His geometry: an odd chain of N sites is a scale with a centre point and two arms of length k = (N-1)/2.
    N=3 -> 1+1     N=9 -> 4+4     N=15 -> 7+7     N=21 -> 10+10

Before running anything on data, the DESIGN has to be checked, because a factorial design whose columns
are collinear cannot separate its factors no matter how much data you feed it. Three things fall out, and
all three are arithmetic -- they are true before any measurement and cannot be fixed by measuring harder.

This script asserts nothing it has not computed. Run:  python research/probes/tat_odd_chain_design.py
"""
from __future__ import annotations

import itertools

import numpy as np


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    return all(n % d for d in range(2, int(n**0.5) + 1))


ODD = [n for n in range(3, 82, 2)]
ROWS = [{"N": n, "k": (n - 1) // 2, "prime": is_prime(n), "div3": n % 3 == 0} for n in ODD]

print("=== 1. Are the arms ever unequal? ===")
print("   His text: 'The arms can be longer or shorter, EQUAL OR UNEQUAL, and that determines whether")
print("   the scale oscillates or freezes.'")
unequal = [r["N"] for r in ROWS if (r["N"] - 1) % 2 != 0]
print(f"   odd N with unequal arms, N=3..81: {unequal or 'NONE'}")
print("   -> By construction every odd N has arms of exactly (N-1)/2 each. The unequal-arm case does not")
print("      occur anywhere in the odd family, so arm SYMMETRY cannot be what distinguishes {3,9,15,21}")
print("      from {5,7,11,13}. Whatever separates them, it is not that some scales are lopsided.\n")

print("=== 2. Is 'arm length' a different variable from 'divisible by 3'? ===")
mismatch = [(r["N"], r["k"]) for r in ROWS if (r["div3"]) != (r["k"] % 3 == 1)]
print(f"   N where div3 disagrees with k = 1 (mod 3), over N=3..81: {mismatch or 'NONE'}")
print("   arm lengths of his four examples:", [(r['N'], r['k']) for r in ROWS if r['N'] in (3, 9, 15, 21)])
print("   -> k = 1 (mod 3) exactly when N = 0 (mod 3), for every odd N. His 'arm length' selector and")
print("      'divisibility by 3' are the SAME COLUMN written two ways, not two variables to separate.")
print("      His intuition is not thereby wrong -- it is a different NAME for the same partition, and")
print("      names matter for mechanism. But no dataset can prefer one over the other.\n")

print("=== 3. Can primality and divisibility by 3 be separated at all? ===")
cells = {}
for r in ROWS:
    cells.setdefault((r["prime"], r["div3"]), []).append(r["N"])
for (p, d), ns in sorted(cells.items()):
    print(f"   prime={str(p):5s} div3={str(d):5s}  n={len(ns):2d}  {ns[:10]}{' ...' if len(ns) > 10 else ''}")
print("   -> The prime AND div3 cell contains exactly ONE member, N=3, and always will: 3 is the only")
print("      prime divisible by 3. So at N=3 the two factors are perfectly collinear. If the effect is")
print("      carried by N=3, no amount of data separates them -- that is arithmetic, not sample size.")
print("      The comparison that IS identifiable lives at N>3, where the cells are all populated.\n")

print("=== 4. Design-matrix rank: what the four proposed columns can actually support ===")
X = np.array([[1.0, r["N"], float(r["prime"]), float(r["div3"]), float(r["k"])] for r in ROWS])
names = ["intercept", "N", "prime", "div3", "k"]
print(f"   columns: {names}")
print(f"   rank = {np.linalg.matrix_rank(X)} of {X.shape[1]}")
for a, b in itertools.combinations(range(len(names)), 2):
    ca, cb = X[:, a], X[:, b]
    if ca.std() == 0 or cb.std() == 0:
        continue
    r = float(np.corrcoef(ca, cb)[0, 1])
    if abs(r) > 0.99:
        print(f"   COLLINEAR: {names[a]} vs {names[b]}  r={r:+.6f}")
print("   -> k = (N-1)/2 is an exact affine function of N, so 'arm length' as a CONTINUOUS predictor is")
print("      the chain length relabelled. It can only be a distinct predictor in its residue form")
print("      (k mod 3), which section 2 showed is div3.\n")

print("=== 5. So what IS testable? The design that survives ===")
groups = {"prime (N>3)": [r["N"] for r in ROWS if r["prime"] and r["N"] > 3],
          "div3 (N>3)": [r["N"] for r in ROWS if r["div3"] and r["N"] > 3],
          "neither": [r["N"] for r in ROWS if not r["prime"] and not r["div3"]]}
for g, ns in groups.items():
    print(f"   {g:14s} n={len(ns):2d}  {ns[:12]}{' ...' if len(ns) > 12 else ''}")
print("   -> A three-way comparison at N>3, with N itself as a covariate, is identifiable and answers")
print("      the question he actually asked. N=3 is reported separately, as the one point where the")
print("      design cannot speak.")
