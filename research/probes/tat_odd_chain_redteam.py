"""Attacking our own answer to Marat before it goes anywhere near him.

The claim we are about to make is that of his three variables, two are one column and one is chain length
relabelled. That is a strong thing to say to someone about their own idea, so it gets attacked first.

A1  Is k = 1 (mod 3) <-> N = 0 (mod 3) actually a theorem, or did a finite scan get lucky?
A2  THE DANGEROUS ONE. "Arm length is chain length relabelled" is true for k as a CONTINUOUS predictor.
    But a residue property of k need not be a residue property of N with the same modulus. If k mod 2
    (say) partitions the odd N differently from anything we tested, then "arm length" IS a separable
    variable in a form we did not check, and telling him otherwise would be wrong.
A3  Does detrending in N actually remove the group/size confound, or only the linear part of it?
A4  Is the N=3 collinearity really permanent?
"""
from __future__ import annotations

import numpy as np


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n**0.5) + 1))


ODD = [n for n in range(3, 2002, 2)]

print("=== A1: k = 1 (mod 3)  <->  N = 0 (mod 3), for odd N ===")
bad = [n for n in ODD if ((n % 3 == 0) != (((n - 1) // 2) % 3 == 1))]
print(f"   counterexamples over N=3..2001: {bad or 'NONE'}")
print("   PROOF, so it does not rest on a scan: N odd means N = 2k+1. N = 0 (mod 3) iff 2k+1 = 0 (mod 3)")
print("   iff 2k = 2 (mod 3). 2 is invertible mod 3 (2*2 = 4 = 1), so k = 1 (mod 3). Both directions.\n")

print("=== A2: is EVERY residue form of arm length the same as a residue form of N? ===")
print("   If yes, 'arm length' can never be separable. If no, we must NOT say that it cannot be.")
for m in (2, 3, 4, 5, 6):
    part_k = tuple(sorted({n for n in ODD[:40] if ((n - 1) // 2) % m == 1}))
    # the best-matching partition by N mod M, over every modulus and residue we could reasonably mean
    match = None
    for M in range(2, 13):
        for r in range(M):
            part_n = tuple(sorted({n for n in ODD[:40] if n % M == r}))
            if part_n == part_k:
                match = (M, r)
                break
        if match:
            break
    print(f"   k = 1 (mod {m}) selects {list(part_k)[:8]}...  -> "
          f"{'equals N = %d (mod %d)' % (match[1], match[0]) if match else 'NO simple N-residue match found'}")
print("   -> k mod 2 is N mod 4; k mod 3 is N mod 3. Each arm-length residue maps to SOME residue of N,")
print("      because k is affine in N -- but to a DIFFERENT modulus. So 'arm length' is not one variable:")
print("      it is a family, and only the mod-3 member of that family is the same column as div3.")
print("      His four examples {3,9,15,21} pick out exactly that member. Other members are untested and")
print("      would be genuinely separable. Our claim must be scoped to the partition his examples name.\n")

print("=== A3: does linear detrending remove the size confound, or only its linear part? ===")
rng = np.random.default_rng(7)
N = np.array(ODD[:29], float)


def groups_of(N):
    return np.array(["N3" if n == 3 else ("prime" if is_prime(int(n)) else
                     ("div3" if n % 3 == 0 else "neither")) for n in N])


g = groups_of(N)
for shape, y in (("linear in N", 0.05 * N),
                 ("QUADRATIC in N", 0.002 * N**2),
                 ("log in N", np.log(N))):
    keep = g != "N3"
    A = np.vstack([np.ones(keep.sum()), N[keep]]).T
    c, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
    resid = (y - (c[0] + c[1] * N))[keep]
    lab = g[keep]
    means = {q: resid[lab == q].mean() for q in ("prime", "div3", "neither")}
    spread = max(means.values()) - min(means.values())
    print(f"   {shape:16s} residual group means "
          f"{ {k: round(v, 4) for k, v in means.items()} }  spread={spread:.4f}")
print("   -> a purely NONLINEAR trend leaves a residual group difference even with no group structure at")
print("      all, because the groups sit at different N. This is a real limitation to state, not hide:")
print("      the test answers 'beyond a LINEAR trend', and a curved metric needs the covariate widened.\n")

print("=== A4: is the prime-and-div3 cell permanently a singleton? ===")
both = [n for n in range(3, 100001, 2) if is_prime(n) and n % 3 == 0]
print(f"   odd N < 100000 that are prime AND divisible by 3: {both}")
print("   -> any such N has 3 as a proper divisor unless N = 3 itself, so it cannot be prime. Permanent.")
