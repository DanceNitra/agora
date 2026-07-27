"""Did the silent-dissonance valley DEEPEN under Rashba SOC, or did the whole curve just shrink?

Li Guanghao's data pack (edrn-dmrg-verification issue #1, 2026-07-27) compares the enhanced diagnostic
(std of edge correlations) across a contradiction-strength scan, with and without a Rashba-type DM term:

    pure Heisenberg : bottom at s=0.38, value 0.1041
    Rashba SOC D=0.3: bottom at s=0.38, value 0.0997
    -> "谷底加深了" — the valley deepened; SOC strengthens silent dissonance.

0.0997 is a LOWER value than 0.1041. Whether that is a deeper valley depends on where the valley's own
shoulders are, and the two Hamiltonians need not share an overall scale — a DM term can rescale the whole
correlation-fluctuation curve without touching its shape.

This is the same shape as the dilution artifact in the Sierpinski work, where a raw std shrank because a
growing flat bulk diluted a one-bond signal, and "the valley washes out with size" turned out to be about
the denominator rather than the physics. That one was ours; this reads the same way, so it gets the same
check: compare the curves POINTWISE, and measure depth RELATIVE to each curve's own shoulders.

Data: the two CSVs inside the published archive. No model, no re-simulation — only arithmetic on his numbers.

RUN:  python research/probes/soc_rashba_valley_audit.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import statistics as st
import sys
import urllib.request
import zipfile

ARCHIVE = ("https://github.com/luoxuejian000/edrn-dmrg-verification/raw/main/"
           "Rashba%20SOC%E4%B8%8B%E7%9A%84%E5%A2%9E%E5%BC%BA%E8%AF%8A%E6%96%ADgm.zip")


def _load(z, tag):
    name = [n for n in z.namelist() if n.endswith(tag)][0]
    rows = list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))
    return [(float(r["strength"]), float(r["fine"]), float(r["gap"])) for r in rows]


def _depth(rows):
    """Bottom, its shoulders, and depth as a FRACTION of the shoulders.

    The fraction is the quantity that survives a change of units. An absolute depth cannot be compared
    across two curves that may sit on different scales, which is the whole question here.
    """
    fine = [f for _, f, _ in rows]
    bottom = min(fine)
    i = fine.index(bottom)
    shoulders = (fine[i - 1] + fine[i + 1]) / 2 if 0 < i < len(fine) - 1 else max(fine)
    return {"bottom": bottom, "at_s": rows[i][0], "shoulders": shoulders,
            "absolute_depth": shoulders - bottom,
            "relative_depth": (shoulders - bottom) / shoulders}


def main() -> int:
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_soc_rashba.zip")
    if not os.path.exists(cache):
        urllib.request.urlretrieve(ARCHIVE, cache)
    z = zipfile.ZipFile(cache)
    heis, soc = _load(z, "heisenberg.csv"), _load(z, "D0.3.csv")

    print(f"{'s':>6} {'Heisenberg':>11} {'Rashba SOC':>11} {'ratio':>8}")
    ratios = []
    for (s, fh, _), (_, fr, _) in zip(heis, soc):
        ratios.append(fr / fh)
        print(f"{s:6.2f} {fh:11.4f} {fr:11.4f} {fr / fh:8.4f}")

    spread = max(ratios) - min(ratios)
    print(f"\nratio across all {len(ratios)} points: mean {st.mean(ratios):.5f}, "
          f"spread {spread:.5f}")

    d_h, d_s = _depth(heis), _depth(soc)
    print(f"\n{'':12}{'bottom':>9}{'shoulders':>11}{'abs depth':>11}{'RELATIVE depth':>16}")
    for label, d in (("Heisenberg", d_h), ("Rashba SOC", d_s)):
        print(f"{label:12}{d['bottom']:9.4f}{d['shoulders']:11.4f}"
              f"{d['absolute_depth']:11.4f}{d['relative_depth']:16.4f}")

    uniform = spread < 0.005
    same_depth = abs(d_h["relative_depth"] - d_s["relative_depth"]) < 0.005
    print()
    if uniform and same_depth:
        print("VERDICT: the SOC curve is the Heisenberg curve times a CONSTANT. The bottom moved down by\n"
              "         the same factor as its shoulders, so the valley did not deepen -- and did not\n"
              "         weaken either. It is the same valley on a uniformly rescaled curve.\n"
              "         The intended conclusion survives, in a stronger form: SOC leaves the relative\n"
              "         structure untouched, rather than merely failing to kill it.")
    else:
        print("VERDICT: the curves are NOT a uniform rescaling of one another; the depth comparison is\n"
              "         about the phenomenon after all.")

    # A column that is exactly zero at every point is usually a dead measurement, not a physical result.
    soc_gaps = [g for _, _, g in soc]
    heis_gaps = [g for _, _, g in heis]
    print(f"\ngap column -- Heisenberg: {min(heis_gaps):.3f}..{max(heis_gaps):.3f}; "
          f"SOC: all {set(soc_gaps)}")
    if set(soc_gaps) == {0.0} and max(heis_gaps) > 0:
        print("         The gap is identically 0.000000 at all nine SOC points while the Heisenberg run\n"
              "         gives 0.42..1.19. Worth confirming that is Kramers degeneracy and not a diagnostic\n"
              "         that stopped reporting under the DM term.")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soc_rashba_valley_audit_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"ratio_mean": st.mean(ratios), "ratio_spread": spread,
                   "heisenberg": d_h, "rashba_soc": d_s,
                   "uniform_rescaling": uniform, "relative_depth_unchanged": same_depth,
                   "soc_gap_all_zero": set(soc_gaps) == {0.0}}, fh, indent=1)
    print(f"\nwrote {os.path.basename(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
