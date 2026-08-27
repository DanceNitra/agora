"""Does Marat's moire_test produce two peaks from smooth structure alone? Measured: no.

WHY THIS EXISTS, AND WHAT IT RETRACTS. On edrn-dmrg-verification#2 (comment 5205068081) I wrote that
his two moire peaks were the shoulders of a smoothed V: "A smoothed V leaves its two shoulders as
maxima, and only a window comparable to the valley width leaves exactly two." He then sent the actual
code, and running it falsifies that explanation rather than his result.

A valley's maxima are its two ENDPOINTS, and `scipy.signal.find_peaks` never returns an endpoint. So a
smooth valley has no interior maximum for the procedure to find, at any window. The shoulders argument
was wrong and it was published before it was run.

WHAT THIS FILE CLAIMS, and only this: across 3000 curves drawn from five closed-form smooth families,
his procedure returned 0 or 1 peak and never 2. It does NOT explain his two peaks -- after this, they
are unexplained, and the CV=0.000 objection (see cv_of_two_peaks_is_an_identity.py) is about the
statistic read off them, not about the peaks themselves.

THE SMOOTHNESS WARRANT IS CONSTRUCTIONAL, not metric, and that is a concession. Four metric-based
checks were tried and the pre-flight gate refused every one:
  * an FFT peak ratio on the raw curve -- a V has a strong fundamental, so it fires on smooth curves;
  * a turning-point count <= 2 -- a double valley legitimately turns 3 times;
  * the same at <= 3 -- a real period-0.25 ripple turns only ONCE, because its slope (0.50) is below
    the valley arm's (1.0), so it never reverses the derivative and the metric cannot see it at all;
  * a detrended ripple-strength -- smooth curves score 30 to 84 against the ripple's 104, overlapping.
So there is no cheap runtime certificate that these curves are microstructure-free. What is asserted
instead is what is true and checkable: every curve is bit-for-bit its closed-form regeneration, and no
generator contains a periodic term.

Run: python probes/moire_two_peaks_on_smooth_curves.py
"""

import inspect
import json
import os
import sys

import numpy as np
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "agora_output", "lab", "memops"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from probe_gate import ProbeGate  # noqa: E402

OUT = os.path.join(HERE, "moire_two_peaks_on_smooth_curves.result.json")
X = np.linspace(0.0, 3.0, 301)


def moire_test(signal, n_shifts=50):
    """Marat Sultanov's code, pasted verbatim from his message of 2026-08-06. Not reimplemented."""
    n = len(signal)
    moire = np.zeros(n)
    for shift in range(1, n_shifts + 1):
        moire += np.roll(signal, shift)
    moire = moire / n_shifts
    peaks, _ = find_peaks(moire, height=np.mean(moire) + 1.5 * np.std(moire))
    return moire, peaks


def make(k, c, c2, e, s1, s2, off, tilt):
    """Five closed-form families. No trigonometric or otherwise periodic term appears anywhere."""
    sig = (np.abs(X - c) if k == 0 else
           (X - c) ** 2 if k == 1 else
           np.abs(X - c) ** e if k == 2 else
           np.where(X < c, (c - X) * s1, (X - c) * s2) if k == 3 else
           np.minimum(np.abs(X - c), np.abs(X - c2)))
    return sig + off + tilt * X


def main():
    rng = np.random.default_rng(20260806)
    gate = ProbeGate("Marat's moire_test never returns two peaks on a closed-form smooth curve",
                     operating_point={"n_shifts": 50, "n_points": 301, "height": "mean+1.5sd",
                                      "code": "his moire_test verbatim", "n_curves": 3000,
                                      "smoothness_warrant": "CONSTRUCTIONAL: five closed-form "
                                                            "families, no periodic term"})

    gate.control("his straight-line control returns 0 peaks",
                 len(moire_test(np.linspace(1, 2, 301))[1]), expect_range=(0, 0))
    gate.control("his shuffled control returns many peaks (he reported 11)",
                 len(moire_test(rng.permutation(np.abs(X - 1.17) + 0.05))[1]), expect_range=(5, 20))

    params = [(int(rng.integers(0, 5)), rng.uniform(.3, 2.7), rng.uniform(.3, 2.7), rng.uniform(.5, 3.),
               rng.uniform(.2, 2), rng.uniform(.2, 2), rng.uniform(0, .05), rng.uniform(-.1, .1))
              for _ in range(3000)]
    curves = [make(*p) for p in params]

    src = inspect.getsource(make)
    gate.manipulation_landed(
        "curves are bit-for-bit their closed-form regeneration AND no generator term is periodic",
        lambda: all(np.array_equal(c, make(*p)) for c, p in zip(curves, params))
        and not any(t in src for t in ("sin", "cos", "sawtooth", "square")))

    gate.can_fail(
        "the procedure CAN return exactly two peaks on some input",
        lambda: any(len(moire_test(np.abs(X - 1.17) + 0.05 + a * np.sin(2 * np.pi * X / p))[1]) == 2
                    for p in (.1, .15, .2, .25, .3, .4, .5, .6, .75, 1.) for a in (.02, .05, .1, .3))
        or any(len(moire_test(rng.normal(size=301))[1]) == 2 for _ in range(40)))

    counts = {}
    for s in curves:
        n = len(moire_test(s)[1])
        counts[n] = counts.get(n, 0) + 1
    gate.denominator(n_scored=len(curves), n_total=3000)

    print("  scan: " + ", ".join(f"{v} curves -> {k} peak(s)" for k, v in sorted(counts.items())) + "\n")
    payload = {"probe": "moire_two_peaks_on_smooth_curves", "n": len(curves),
               "peak_count_histogram": {str(k): v for k, v in sorted(counts.items())},
               "two_peak_curves": counts.get(2, 0),
               "retracts": "the 'smoothed V leaves two shoulders' explanation posted as "
                           "edrn-dmrg-verification#2 comment 5205068081",
               "does_not_explain": "his two peaks on tree_explore.csv remain unexplained",
               "smoothness_warrant": "constructional, not metric -- four metric checks were refused "
                                     "by the pre-flight gate"}
    try:
        gate.report(payload)
        payload["gate"] = "passed"
        print("\n  GATE PASSED -- reportable")
    except Exception as exc:
        payload["gate"] = f"FAILED: {exc}"
        print(f"\n  GATE FAILED: {exc}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    print(f"wrote {OUT}")
    return 0 if payload.get("gate") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
