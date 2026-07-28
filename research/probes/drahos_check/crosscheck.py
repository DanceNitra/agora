"""Passes 2 and 3: does the CSV match his printed log, and what does his OWN size series say?

Pass 2 — the console log `12-14.txt` prints fine= values to 4 decimals for both arms. Recompute the
ratios from the LOG and compare to the CSV. Two files written by the same run must agree; if they do
not, one of them is stale and every number drawn from it is suspect.

Pass 3 — his own `6-10.txt` reports mean ratios for N=6, 8, 10 from `constant_validation.py`. Put them
beside N=12 and N=14 and ask the only question that matters for the word "constant": is the sequence
settling, or bouncing?
"""
import re
import sys
import zipfile

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Z = zipfile.ZipFile("drahos.zip")


def read(name):
    raw = Z.read(name)
    for enc in ("utf-8-sig", "utf-8", "gb18030", "cp936"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("latin-1")


log = read([n for n in Z.namelist() if n.endswith("12-14.txt")][0])
print("=== PASS 2: log vs csv ===")
blocks = re.split(r"N=(\d+),\s*center_edge", log)
for i in range(1, len(blocks), 2):
    N = blocks[i]
    body = blocks[i + 1]
    rows = re.findall(r"s=([\d.]+):\s*Heisenberg.*?fine=([\d.]+)\s*SOC.*?fine=([\d.]+)", body)
    if not rows:
        continue
    s = np.array([float(a) for a, _, _ in rows])
    H = np.array([float(b) for _, b, _ in rows])
    S = np.array([float(c) for _, _, c in rows])
    r = S / H
    print(f"  N={N}: {len(rows)} points from the LOG -> mean ratio {r.mean():.6f} (sd {r.std(ddof=1):.6f})")
    csvn = [n for n in Z.namelist() if f"N{N}" in n and n.endswith(".csv")]
    if csvn:
        raw = read(csvn[0]).splitlines()
        cr = np.array([float(x.split(",")[3]) for x in raw[1:] if x.strip()])
        ch = np.array([float(x.split(",")[1]) for x in raw[1:] if x.strip()])
        print(f"        csv mean ratio {cr.mean():.6f} | max |log-csv| on Heisenberg = "
              f"{np.max(np.abs(np.round(ch,4)-H)):.6f}  "
              f"-> {'CONSISTENT' if np.max(np.abs(np.round(ch,4)-H)) < 5e-4 else 'MISMATCH'}")

print("\n=== PASS 3: his own size series ===")
small = read([n for n in Z.namelist() if n.endswith("6-10.txt")][0])
print("  from his constant_validation.py output (chain graph, D=0.3):")
for m in re.finditer(r"N=(\d+):\s*mean ratio=([\d.]+),\s*std=([\d.]+)", small):
    print(f"     N={m.group(1):>2}: mean {float(m.group(2)):.6f}  std {float(m.group(3)):.6f}")
print("  from the ED csvs (this archive):")
for N, mean, sd in (("12", 0.958571, 0.007038), ("14", 0.965242, 0.022456)):
    print(f"     N={N:>2}: mean {mean:.6f}  std {sd:.6f}")

seq = [0.982042, 0.960666, 0.967717, 0.958571, 0.965242]
lbl = [6, 8, 10, 12, 14]
print(f"\n  sequence N=6..14 : {['%.4f' % x for x in seq]}")
print(f"  range            : {max(seq)-min(seq):.4f}  ({100*(max(seq)-min(seq))/np.mean(seq):.2f}% of the mean)")
d = np.diff(seq)
print(f"  successive diffs : {['%+.4f' % x for x in d]}")
print(f"  monotone?        : {'yes' if all(x>0 for x in d) or all(x<0 for x in d) else 'NO — it alternates'}")
A = np.vstack([np.array(lbl, float), np.ones(len(lbl))]).T
sl, ic = np.linalg.lstsq(A, np.array(seq), rcond=None)[0]
res = np.array(seq) - A @ [sl, ic]
se = float(np.sqrt((res @ res) / (len(seq) - 2) / ((np.array(lbl) - np.mean(lbl)) ** 2).sum()))
print(f"  trend vs N       : slope {sl:+.5f} per site (SE {se:.5f}, t={sl/se:+.2f}) "
      f"-> {'no size trend' if abs(sl/se) < 2 else 'SIZE-DEPENDENT'}")
