"""Re-derive the "Drahos Constant" from Guanghao's OWN files — three independent estimators.

He reports the ratio of the Rashba-SOC fine diagnostic to the pure-Heisenberg one as a constant:
    N=6 (ours) 0.95779 | N=12 mean 0.958572 sd 0.007039 | N=14 mean 0.965243 sd 0.022458

Three passes, deliberately different, so one parsing slip cannot manufacture agreement:
  (1) POINTWISE  mean of ratio_i = SOC_i / Heis_i          (his estimator)
  (2) AGGREGATE  mean(SOC) / mean(Heis)                    (weights points by magnitude)
  (3) SLOPE      least squares SOC = k * Heis through the origin
A "uniform rescaling" must give the same k under all three. If it does not, the factor depends on the
estimator and is a summary statistic, not a constant.

Then the sharper test: IS THE RATIO FLAT IN s? A uniform rescaling has no structure. Correlation of
ratio with s, and with the Heisenberg magnitude, would mean SOC acts differently in different regimes
— which is a physical result, but a different one from "a constant".
"""
import io
import sys
import zipfile

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Z = zipfile.ZipFile("drahos.zip")


def load_csv(name):
    raw = Z.read(name).decode("utf-8-sig", errors="replace")
    rows = [r.split(",") for r in raw.splitlines() if r.strip()]
    hdr = [h.strip() for h in rows[0]]
    out = {h: [] for h in hdr}
    for r in rows[1:]:
        if len(r) != len(hdr):
            continue
        for h, v in zip(hdr, r):
            out[h].append(float(v))
    return {h: np.array(v) for h, v in out.items()}


for name, label in ((".*N12.*csv", "N=12"), (".*N14.*csv", "N=14")):
    import re
    hit = [n for n in Z.namelist() if re.match(name, n.split("/")[-1])]
    if not hit:
        print(f"{label}: no csv found")
        continue
    d = load_csv(hit[0])
    s, H, S = d["strength"], d["Heisenberg"], d["SOC"]
    r_file = d.get("ratio")
    r = S / H
    print(f"================= {label}  ({hit[0].split('/')[-1]}, {len(s)} points) =================")
    if r_file is not None:
        maxdiff = float(np.max(np.abs(r - r_file)))
        print(f"  his 'ratio' column reproduces from SOC/Heisenberg to {maxdiff:.2e}  "
              f"-> {'OK' if maxdiff < 1e-5 else 'MISMATCH'}")
    p1 = float(r.mean())
    p2 = float(S.mean() / H.mean())
    p3 = float((H @ S) / (H @ H))
    print(f"  (1) POINTWISE  mean ratio      = {p1:.6f}   sd {r.std(ddof=1):.6f}")
    print(f"  (2) AGGREGATE  mean(S)/mean(H) = {p2:.6f}")
    print(f"  (3) SLOPE      lstsq origin    = {p3:.6f}")
    spread = max(p1, p2, p3) - min(p1, p2, p3)
    print(f"      estimator spread           = {spread:.6f}  "
          f"({'agree' if spread < 0.002 else 'DISAGREE — estimator-dependent'})")

    # is the ratio FLAT in s? a uniform rescaling has no structure
    A = np.vstack([s, np.ones_like(s)]).T
    slope, intercept = np.linalg.lstsq(A, r, rcond=None)[0]
    resid = r - (A @ [slope, intercept])
    se = float(np.sqrt((resid @ resid) / max(len(s) - 2, 1) / max(((s - s.mean()) ** 2).sum(), 1e-12)))
    t = slope / se if se else float("nan")
    cc = float(np.corrcoef(r, H)[0, 1])
    print(f"  ratio vs s     : slope {slope:+.5f} (SE {se:.5f}, t={t:+.2f})  "
          f"{'FLAT' if abs(t) < 2 else 'STRUCTURED — not a uniform rescaling'}")
    print(f"  ratio vs |Heisenberg| : r = {cc:+.3f}")
    print(f"  min ratio {r.min():.6f} at s={s[int(np.argmin(r))]:.2f} | "
          f"max {r.max():.6f} at s={s[int(np.argmax(r))]:.2f} | range {r.max()-r.min():.6f}")
    print()
