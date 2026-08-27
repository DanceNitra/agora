"""Every number I computed on 2026-08-07 about Marat Sultanov's tree_explore.csv, in one run.

THE HEADLINE OF THIS FILE USED TO SAY "every number SENT to Marat Sultanov on 2026-08-07", and that
was false. Checked 2026-08-10 against both collaboration threads: 1.856 and 1.701 appear in no comment
on edrn-dmrg-verification#2 or #5. These numbers were never sent anywhere. The 7 August exchange was
on #5 and about the stability island, not about moire peaks.

The claim mattered, because on 2026-08-10 I cited this analysis publicly as a conclusion "we reached
together" with the collaborator whose data it is -- attributing to him a result he had never seen, and
omitting the controls in his own report (white noise gives many peaks at CV 0.69-2.18; a synthetic
curve with injected periodicity reproduces exactly two peaks at CV 0.000; shift counts of 30/70/100 do
not). A docstring that asserts delivery is a claim like any other, and this one was carrying weight it
had not earned. Corrected publicly, and corrected here.

SCOPE, stated properly: this tests ONE axis -- whether the two peaks are separable from a threshold
artifact by HEIGHT. It says nothing about the spacing regularity his CV controls address, and the two
results do not contradict each other.

WHAT WENT OUT, and it is deliberately weaker than what I first drafted:

    Peak 51 depends on the strength=0 boundary sample -- repair it with the height threshold
    FROZEN and the peak goes, while peak 34 stays. But the exit step is NECESSARY, NOT
    SUFFICIENT, and neither peak is robust: 1.856 sd and 1.701 sd, 0.155 sd apart, both gone at
    mean+1.9sd. Nothing in this data separates "real" from "artifact".

FOUR EXPLANATIONS OF THESE SAME TWO PEAKS DIED BEFORE THAT ONE, THREE OF THEM MINE:

  1. "the shoulders of a smoothed V" -- published, then retracted (see
     moire_two_peaks_on_smooth_curves.py). find_peaks never returns an endpoint, so a smooth
     valley has no interior maximum at any window.
  2. "float-noise quantisation" -- `gap` and `audit_gap_diff` DO sit at ~6e-14 with 50 and 47
     distinct values in 301 rows, but the two peaks are on `fine`, which has real magnitude.
     Tested and dropped before it was said out loud.
  3. "a smeared step" -- the arithmetic I offered as proof, (fine[50]-fine[0])/50 matching the
     observed jump to 2.6e-18, is the recursive moving-average identity (Smith, DSP Guide ch.15
     eq.15-3). It holds at ALL 301 indices. It confirms IEEE arithmetic, not causation.
  4. "the circular wrap causes it" -- it does not. The step is bit-identical under a
     non-circular window (test_non_circular below). The wrap is a real methodological defect on
     a non-periodic sweep axis, and it is a SEPARATE issue from these peaks.

AND TWO NULLS WERE REFUSED, one of them my own:

  * my 3000 smooth closed-form curves give 0 or 1 peak and never 2 -- true, and it has no power
    here: those curves cannot produce an interior maximum under this procedure at all.
  * phase-randomised surrogates preserve `fine`'s spectrum exactly and have a median of 188
    turning points against the data's 2. A null whose realizations look nothing like the data
    was not used to license a conclusion.

THE PRIOR ART IS TEXTBOOK: a moving average reacting twice to one extreme sample, on entry and
again on exit, is the standard "drop-off effect". Nothing here is a discovery.

DATA: `tree_explore.csv` is Marat's and is NOT redistributed in this repo. This probe reads it
from its original location and SKIPS if absent, rather than vendoring a collaborator's
unpublished data (which cost us two days and a history rewrite once already).

Run: python probes/marat_moire_peaks_are_not_separable.py
"""

import json
import os
import sys

import numpy as np
from scipy.signal import argrelextrema, find_peaks

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = r"C:\Users\Danculus\Desktop\Danchi grow plan\tree_explore.csv"
SEVEN = os.path.join(HERE, "edrn_valley_parity_independent_ed.result.json")
OUT = os.path.join(HERE, "marat_moire_peaks_are_not_separable.result.json")
N_SHIFTS = 50


def moire_test(signal, n_shifts=N_SHIFTS):
    """Marat Sultanov's code, verbatim from his message of 2026-08-06. Never reimplemented."""
    n = len(signal)
    moire = np.zeros(n)
    for shift in range(1, n_shifts + 1):
        moire += np.roll(signal, shift)
    moire = moire / n_shifts
    peaks, _ = find_peaks(moire, height=np.mean(moire) + 1.5 * np.std(moire))
    return moire, peaks


def adaptive_anchors(series, window=3, tol=0.15):
    """Marat Sultanov's CORRECTED anchor, verbatim (2026-08-06). Never reimplemented."""
    n = len(series)
    smooth = np.convolve(series, np.ones(window) / window, mode="valid")
    anchors = argrelextrema(smooth, np.less, order=window)[0]
    if len(anchors) < 2:
        anchors = np.array([np.argmin(series)])
    elif len(anchors) > 2:
        anchor_vals = series[anchors]
        threshold = np.mean(anchor_vals) + tol * np.std(anchor_vals)
        anchors = anchors[anchor_vals < threshold]
    return anchors


def main():
    if not os.path.exists(CSV):
        print(f"SKIP: {CSV} not present (collaborator's data, not vendored).")
        return 0
    hdr = open(CSV, encoding="utf-8").readline().lstrip("#").strip().split(",")
    d = np.loadtxt(CSV, delimiter=",", comments="#")
    fine = d[:, hdr.index("fine")]
    n = len(fine)
    a, peaks = moire_test(fine)
    mu, sd = a.mean(), a.std()
    T = mu + 1.5 * sd                      # the ORIGINAL gate, frozen for every intervention
    out = {"n": n, "peaks": [int(p) for p in peaks]}

    # -- the transform is a 50-pt circular TRAILING boxcar -----------------------------------
    box = np.array([np.concatenate([fine[(i - N_SHIFTS) % n:], fine[:i]]).mean()
                    if i - N_SHIFTS < 0 else fine[i - N_SHIFTS:i].mean() for i in range(n)])
    out["is_circular_trailing_boxcar"] = bool(np.allclose(a, box))
    out["boxcar_residual"] = float(np.abs(a - box).max())

    # -- the identity is a tautology: it holds at EVERY index, so it is not evidence ----------
    lhs = np.array([a[(i + 1) % n] - a[i] for i in range(n)])
    rhs = np.array([(fine[i % n] - fine[(i - N_SHIFTS) % n]) / N_SHIFTS for i in range(n)])
    out["step_identity_holds_everywhere"] = bool(np.allclose(lhs, rhs))
    out["step_identity_max_dev"] = float(np.abs(lhs - rhs).max())

    # -- the boundary sample, and what it does to the window means ---------------------------
    out["fine_0"] = float(fine[0])
    out["neighbour_level"] = float(fine[1:6].mean())
    repaired = fine.copy()
    repaired[0] = 0.2430
    r = moire_test(repaired)[0]
    out["depression_of_windows_containing_it"] = float(r[50] - a[50])
    out["a51_unchanged_by_repair"] = float(r[51] - a[51])       # a[51] never contained fine[0]
    out["peaks_after_repair_frozen_gate"] = [int(p) for p in find_peaks(r, height=T)[0]]
    out["peaks_after_repair_recomputed_gate"] = [
        int(p) for p in find_peaks(r, height=r.mean() + 1.5 * r.std())[0]]

    # -- NECESSARY BUT NOT SUFFICIENT: relocate the identical value, expect no companion ------
    reloc = {}
    for j in (100, 150, 200):
        t = fine.copy()
        t[0] = (fine[1] + fine[-1]) / 2
        t[j] = fine[0]
        b = moire_test(t)[0]
        tgt = (j + N_SHIFTS + 1) % n
        pk = [int(p) for p in find_peaks(b, height=b.mean() + 1.5 * b.std())[0]]
        reloc[str(j)] = {"peaks": pk, "target": int(tgt),
                         "companion_present": bool(any(abs(p - tgt) <= 1 for p in pk)),
                         "height_at_target_sd": float((b[tgt] - b.mean()) / b.std())}
    out["relocation_control"] = reloc

    # -- the step is not exceptional: 18 larger steps produce no peak -------------------------
    steps = lhs
    s51 = a[51] - a[50]
    out["step_at_51"] = float(s51)
    out["step_rank_of_301"] = int((steps > s51).sum()) + 1
    out["step_z"] = float((s51 - steps.mean()) / steps.std())

    # -- NEITHER peak is robust: they are 0.155 sd apart and die together ---------------------
    out["peak_heights_sd"] = {str(int(p)): float((a[p] - mu) / sd) for p in peaks}
    out["height_separation_sd"] = float(abs((a[34] - mu) / sd - (a[51] - mu) / sd))
    out["peaks_vs_height_constant"] = {
        str(h): [int(p) for p in find_peaks(a, height=mu + h * sd)[0]]
        for h in (1.0, 1.25, 1.5, 1.7, 1.75, 1.9, 2.0)}

    # -- the wrap is NOT the cause: the step survives de-circularising bit-for-bit ------------
    lin = np.convolve(fine, np.ones(N_SHIFTS) / N_SHIFTS, mode="valid")
    out["non_circular_step"] = float(lin[1] - lin[0])
    out["non_circular_step_identical"] = bool(np.isclose(lin[1] - lin[0], s51))

    # -- the anchor: which BRANCH executes on the seven curves --------------------------------
    curves = json.load(open(SEVEN, encoding="utf-8"))
    br = []
    for c in curves:
        y = np.array(c["fines"])
        raw = argrelextrema(np.convolve(y, np.ones(3) / 3, mode="valid"), np.less, order=3)[0]
        br.append({"L": c["L"], "n_interior_minima": int(len(raw)),
                   "branch": "fallback" if len(raw) < 2 else "adaptive",
                   "equals_argmin": bool(list(adaptive_anchors(y)) == [int(np.argmin(y))])})
    out["seven_curves"] = br
    out["seven_all_fallback"] = all(b["branch"] == "fallback" for b in br)
    out["seven_all_equal_argmin"] = all(b["equals_argmin"] for b in br)

    # -- and the index space in the branch that never fires on his data -----------------------
    x = np.arange(60.0)
    y = np.sin(x / 3.0) + 0.02 * x
    raw = argrelextrema(np.convolve(y, np.ones(3) / 3, mode="valid"), np.less, order=3)[0]
    out["index_space"] = {"from_smooth": [int(v) for v in raw],
                          "true_minima": [int(v) for v in argrelextrema(y, np.less, order=3)[0]]}

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"  transform is a circular trailing boxcar : {out['is_circular_trailing_boxcar']} "
          f"(residual {out['boxcar_residual']:.1e})")
    print(f"  step identity holds at every index      : {out['step_identity_holds_everywhere']} "
          f"-> the 2.6e-18 'match' was arithmetic")
    print(f"  peaks                                   : {out['peaks']}")
    print(f"  heights (sd)                            : {out['peak_heights_sd']}, "
          f"separated by {out['height_separation_sd']:.3f}")
    print(f"  repair fine[0], gate FROZEN             : {out['peaks_after_repair_frozen_gate']}")
    print(f"  step rank among 301 steps               : {out['step_rank_of_301']} (z={out['step_z']:.2f})")
    print(f"  relocation companions present           : "
          f"{[v['companion_present'] for v in reloc.values()]}")
    print(f"  non-circular step identical             : {out['non_circular_step_identical']} "
          f"-> the wrap is NOT the cause")
    print(f"  seven curves all take the fallback      : {out['seven_all_fallback']}, "
          f"all equal argmin: {out['seven_all_equal_argmin']}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
