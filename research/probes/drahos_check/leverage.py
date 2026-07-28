"""Pass 4: does one point carry N=14, and does the s=0.38 anomaly repeat across sizes?

s=0.38 is the physical valley. At N=12 the ratio is at its MINIMUM there (0.9431); at N=14 it is at its
MAXIMUM and above one (1.0236). A quantity that swings from the lowest to the highest value at the same
physical point, between two adjacent sizes, is not behaving like a constant — so before anything is
written down, find out how much of each size's summary rests on that single point.
"""
import re
import sys
import zipfile

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Z = zipfile.ZipFile("drahos.zip")


def csv(nm):
    raw = Z.read(nm).decode("utf-8-sig", errors="replace").splitlines()
    rows = [r.split(",") for r in raw[1:] if r.strip()]
    s = np.array([float(r[0]) for r in rows])
    H = np.array([float(r[1]) for r in rows])
    S = np.array([float(r[2]) for r in rows])
    return s, H, S


for tag in ("N12", "N14"):
    nm = [n for n in Z.namelist() if tag in n and n.endswith(".csv")][0]
    s, H, S = csv(nm)
    r = S / H
    print(f"================ {tag} ================")
    print("   s     Heisenberg      SOC        ratio")
    for a, b, c, d in zip(s, H, S, r):
        flag = "  <-- valley" if abs(a - 0.38) < 1e-9 else ""
        star = "  RATIO > 1" if d > 1 else ""
        print(f"  {a:4.2f}  {b:10.6f}  {c:10.6f}  {d:9.6f}{flag}{star}")
    full_m, full_sd = r.mean(), r.std(ddof=1)
    print(f"\n  all 9 points      : mean {full_m:.6f}  sd {full_sd:.6f}")
    # leave-one-out: which point moves the summary most?
    worst, wi = 0.0, None
    for i in range(len(r)):
        rr = np.delete(r, i)
        dm = abs(rr.mean() - full_m)
        if dm > worst:
            worst, wi = dm, i
        if abs(s[i] - 0.38) < 1e-9:
            print(f"  drop s=0.38       : mean {rr.mean():.6f}  sd {rr.std(ddof=1):.6f}   "
                  f"(mean moves {rr.mean()-full_m:+.6f}, sd {rr.std(ddof=1)/full_sd:.2f}x)")
    print(f"  most influential  : s={s[wi]:.2f} (drop moves the mean by {worst:+.6f})")
    print()

print("A constant should not care which point you leave out, and should not sit at the minimum for one")
print("size and above unity for the next at the SAME physical s.")
