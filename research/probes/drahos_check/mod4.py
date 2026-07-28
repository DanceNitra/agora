"""Pass 5: the red team says the sequence is not alternating noise but an N mod 4 split. Check it.

Heisenberg chains split on N mod 4, not just on parity, so "it bounces" and "there are two smooth
families" look identical if you only ever plot one line. All five sizes are EVEN, so ordinary parity
cannot explain the zig-zag — but 8,12 (= 0 mod 4) and 6,10,14 (= 2 mod 4) can.

If each subsequence is smooth and monotone, the "constant" is not noisy: it is two sequences, and the
right question stops being "what is the number" and becomes "do the two families share a limit".
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data = {6: 0.982042, 8: 0.960666, 10: 0.967717, 12: 0.958571, 14: 0.965242}
sd = {6: 0.068310, 8: 0.008087, 10: 0.028218, 12: 0.007038, 14: 0.022456}

print("  N   N mod 4   mean ratio      sd")
for n in sorted(data):
    print(f"  {n:>2}      {n % 4}      {data[n]:.6f}   {sd[n]:.6f}")

fam0 = [(n, data[n]) for n in sorted(data) if n % 4 == 0]
fam2 = [(n, data[n]) for n in sorted(data) if n % 4 == 2]
print(f"\n  N = 0 mod 4 : {[f'{n}:{v:.4f}' for n, v in fam0]}")
print(f"  N = 2 mod 4 : {[f'{n}:{v:.4f}' for n, v in fam2]}")


def mono(seq):
    d = np.diff([v for _, v in seq])
    if len(d) == 0:
        return "single point"
    return "monotone DECREASING" if all(x < 0 for x in d) else \
           "monotone INCREASING" if all(x > 0 for x in d) else "not monotone"


print(f"\n  0 mod 4 : {mono(fam0)}  diffs {['%+.4f' % x for x in np.diff([v for _, v in fam0])]}")
print(f"  2 mod 4 : {mono(fam2)}  diffs {['%+.4f' % x for x in np.diff([v for _, v in fam2])]}")

# Does the SPLIT explain the spread better than "one noisy constant"?
allv = np.array(list(data.values()))
within = []
for fam in (fam0, fam2):
    v = np.array([x for _, x in fam])
    if len(v) > 1:
        within.append(v - v.mean())
within = np.concatenate(within) if within else np.array([0.0])
print(f"\n  spread as ONE family    : sd {allv.std(ddof=1):.6f}")
print(f"  spread WITHIN families  : sd {within.std(ddof=1):.6f}  "
      f"({'the split explains most of it' if within.std(ddof=1) < 0.6*allv.std(ddof=1) else 'the split does not help'})")

# the valley point is the other candidate explanation — combine both
print("\n  ...and with the valley point (s=0.38) removed from the two ED sizes:")
clean = dict(data)
clean[12], clean[14] = 0.960507, 0.957952
for n in sorted(clean):
    tag = " (valley point removed)" if n in (12, 14) else ""
    print(f"     N={n:>2} ({n % 4} mod 4): {clean[n]:.6f}{tag}")
c0 = [clean[n] for n in sorted(clean) if n % 4 == 0]
c2 = [clean[n] for n in sorted(clean) if n % 4 == 2]
print(f"     0 mod 4 mean {np.mean(c0):.6f} | 2 mod 4 mean {np.mean(c2):.6f} | "
      f"gap {abs(np.mean(c0)-np.mean(c2)):.6f}")
cv = np.array(list(clean.values()))
print(f"     spread of all five, valley removed: sd {cv.std(ddof=1):.6f} "
      f"(was {allv.std(ddof=1):.6f}, {cv.std(ddof=1)/allv.std(ddof=1):.2f}x)")
