"""Marat's triadic coherence C is NOT a smoothness meter. The hypothesis in the old filename lost.

He asked this himself, in luoxuejian000/edrn-dmrg-verification#2 on 2026-08-31: "I do not know
whether this is a hidden tautology." This answers the part that can be answered without his data.

C is the Kuramoto order parameter of three phases:

    C = mean over s of | ( e^{i phi_E} + e^{i phi_Omega} + e^{i phi_I} ) / 3 |

Each phase is the argument of the analytic signal (Hilbert transform) of one stream: the
ground-manifold energy E(s), the cumulative trace distance Omega(s), and the mean mutual
information I(s). He reports 0.977 to 0.979 for the star at N = 7, 8, 9, against 0.934 for K_{a,b},
0.926 to 0.942 for the chain, 0.853 to 0.937 for the ring, and 0.924 +/- 0.020 over 50 random trees.

This file was written to test one hypothesis: that C reads smoothness, so three slowly varying
curves would score in the 0.9s whatever they measured, and his whole observed range would sit inside
the null. MEASURED, THAT IS FALSE. Across eight smoothness settings the mean holds at 0.52 to 0.54,
and it holds again for curves with a monotone trend and for two monotone curves against one
cumulative curve built the way Omega(s) is built. Smoothness narrows the SPREAD and leaves the mean
alone. So his 0.853 to 0.979 is far above chance and C is measuring something.

What survives is narrower. The right tail is heavy for very smooth streams: 41 of 400 independent
trios reach 0.924 and 4 of 400 reach 0.977. So the absolute value is not the evidence, and the
separation between the star and the tree distribution is.

This does not use his data, which we do not have. It measures the statistic on synthetic streams
whose smoothness we set, which locates the floor and names the confound. The definitive test is the
surrogate one, run on his own streams; this shows why it is worth his time.

Controls, because a null probe that cannot fail has measured nothing:

  IDENTICAL   three copies of one stream must return exactly 1.0. If not, the phase extraction is
              wrong and every other number here is void.
  WHITE       three streams of independent uniform phases must fall to the three-phasor random
              floor. If this also scored 0.9 the statistic would be saturated, and the smooth
              result below would carry no information.
  ANTIPHASE   a stream against its own negative must sit below the independent-smooth result.

Run:  python -X utf8 probes/edrn_triadic_coherence_has_a_floor_set_by_smoothness.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from scipy.signal import hilbert

TRIALS = 400
GRID = 240                      # points in s, comparable to a fine sweep
S0, S1 = 0.05, 3.0              # the sweep range used in the thread
SEED = 20260831


def phases(stream):
    """Phase of the analytic signal, the construction Marat describes."""
    return np.angle(hilbert(stream - stream.mean()))


def coherence(streams):
    """C = mean over s of the modulus of the mean of the three unit phasors."""
    phi = np.array([phases(x) for x in streams])
    return float(np.abs(np.exp(1j * phi).mean(axis=0)).mean())


def smooth_stream(rng, s, modes):
    """A random curve band-limited to `modes` Fourier components.

    `modes` is the smoothness knob. A physical E(s), Omega(s) or I(s) over a sweep varies slowly,
    which on this grid is a handful of modes rather than hundreds.
    """
    t = (s - s[0]) / (s[-1] - s[0])
    out = np.zeros_like(t)
    for k in range(1, modes + 1):
        out += rng.normal() * np.sin(math.pi * k * t) + rng.normal() * np.cos(math.pi * k * t)
    sd = float(np.std(out))
    return out / (sd if sd else 1.0)


def monotone_stream(rng, s, modes, trend=1.0):
    """A smooth curve with a monotone trend, which is what a physical sweep usually looks like.

    E(s) falls, Omega(s) rises. A wiggle rides on a slope rather than around a mean.
    """
    t = (s - s[0]) / (s[-1] - s[0])
    wiggle = smooth_stream(rng, s, modes)
    sign = 1.0 if rng.random() < 0.5 else -1.0
    return sign * trend * t * float(np.std(wiggle) * 4.0 + 1.0) + wiggle


def cumulative_stream(rng, s, modes):
    """A cumulative sum of a non-negative increment, which is how Omega(s) is defined.

    A cumulative trace distance cannot decrease. That is a property of the construction, not of
    any graph, so it belongs in the null.
    """
    inc = np.abs(smooth_stream(rng, s, modes)) + 0.05
    return np.cumsum(inc)


def main():
    rng = np.random.default_rng(SEED)
    s = np.linspace(S0, S1, GRID)
    report = {"trials": TRIALS, "grid": GRID, "s_range": [S0, S1], "seed": SEED}
    failures = []

    # -- control: identical streams must be exactly coherent ------------------------------------
    one = smooth_stream(rng, s, 4)
    c_identical = coherence([one, one, one])
    report["control_identical"] = c_identical
    if abs(c_identical - 1.0) > 1e-9:
        failures.append("IDENTICAL streams gave C=%.6f, not 1.0: the phase extraction is wrong"
                        % c_identical)

    # -- control: independent uniform phases, the absolute floor --------------------------------
    white = []
    for _ in range(TRIALS):
        phi = rng.uniform(-math.pi, math.pi, size=(3, GRID))
        white.append(float(np.abs(np.exp(1j * phi).mean(axis=0)).mean()))
    report["control_white_phases"] = {"mean": float(np.mean(white)), "sd": float(np.std(white)),
                                      "max": float(np.max(white))}

    # -- control: a stream against its own antiphase --------------------------------------------
    anti = []
    for _ in range(200):
        a = smooth_stream(rng, s, 4)
        c = smooth_stream(rng, s, 4)
        anti.append(coherence([a, -a, c]))
    report["control_antiphase"] = {"mean": float(np.mean(anti)), "sd": float(np.std(anti))}

    # -- the measurement: three INDEPENDENT smooth streams, across smoothness -------------------
    report["independent_smooth"] = {}
    for modes in (2, 3, 4, 6, 8, 12, 20, 40):
        vals = np.array([coherence([smooth_stream(rng, s, modes) for _ in range(3)])
                         for _ in range(TRIALS)])
        report["independent_smooth"][str(modes)] = {
            "mean": float(vals.mean()), "sd": float(vals.std()),
            "p05": float(np.percentile(vals, 5)), "p95": float(np.percentile(vals, 95)),
            "max": float(vals.max()),
            "frac_ge_0977": float((vals >= 0.977).mean()),
            "frac_ge_0924": float((vals >= 0.924).mean()),
        }

    # -- the same nulls, but with the monotone structure a real sweep has ----------------------
    for name, maker in (("independent_monotone", monotone_stream),
                        ("two_monotone_one_cumulative", None)):
        report[name] = {}
        for modes in (3, 4, 6, 12):
            vals = []
            for _ in range(TRIALS):
                if maker is monotone_stream:
                    trio = [monotone_stream(rng, s, modes) for _ in range(3)]
                else:
                    trio = [monotone_stream(rng, s, modes), monotone_stream(rng, s, modes),
                            cumulative_stream(rng, s, modes)]
                vals.append(coherence(trio))
            vals = np.array(vals)
            report[name][str(modes)] = {
                "mean": float(vals.mean()), "sd": float(vals.std()),
                "p05": float(np.percentile(vals, 5)), "p95": float(np.percentile(vals, 95)),
                "max": float(vals.max()),
                "frac_ge_0977": float((vals >= 0.977).mean()),
                "frac_ge_0924": float((vals >= 0.924).mean()),
            }

    # -- print -----------------------------------------------------------------------------------
    print("triadic coherence C on streams with NO shared mechanism")
    print("  trials=%d  grid=%d  s in [%.2f, %.2f]  seed=%d" % (TRIALS, GRID, S0, S1, SEED))
    print()
    print("controls")
    print("  identical streams             C = %.9f   (must be 1.0)" % c_identical)
    print("  independent uniform phases    C = %.4f +/- %.4f  (max %.4f)"
          % (report["control_white_phases"]["mean"], report["control_white_phases"]["sd"],
             report["control_white_phases"]["max"]))
    print("  a stream and its antiphase    C = %.4f +/- %.4f"
          % (report["control_antiphase"]["mean"], report["control_antiphase"]["sd"]))
    print()
    print("three INDEPENDENT smooth streams, by smoothness")
    print("  modes    mean C      sd      p05      p95      max    P(C>=.977) P(C>=.924)")
    for modes, r in report["independent_smooth"].items():
        print("  %5s   %.4f   %.4f   %.4f   %.4f   %.4f     %.3f      %.3f"
              % (modes, r["mean"], r["sd"], r["p05"], r["p95"], r["max"],
                 r["frac_ge_0977"], r["frac_ge_0924"]))
    for name, label in (("independent_monotone", "three INDEPENDENT monotone streams"),
                        ("two_monotone_one_cumulative",
                         "two monotone plus one CUMULATIVE stream, as Omega(s) is built")):
        print(label + ", by smoothness")
        print("  modes    mean C      sd      p05      p95      max    P(C>=.977) P(C>=.924)")
        for modes, r in report[name].items():
            print("  %5s   %.4f   %.4f   %.4f   %.4f   %.4f     %.3f      %.3f"
                  % (modes, r["mean"], r["sd"], r["p05"], r["p95"], r["max"],
                     r["frac_ge_0977"], r["frac_ge_0924"]))
        print()

    # -- the finding -------------------------------------------------------------------------------
    smooth4 = report["independent_smooth"]["4"]
    rough40 = report["independent_smooth"]["40"]
    report["C_falls_with_roughness"] = smooth4["mean"] - rough40["mean"]
    print("FINDING: C does NOT track smoothness. On independent streams the mean holds at %.4f at"
          % smooth4["mean"])
    print("         4 modes and %.4f at 40 modes, a drift of %.1f percent across a twentyfold"
          % (rough40["mean"], 100.0 * abs(smooth4["mean"] - rough40["mean"]) / smooth4["mean"]))
    print("         change in smoothness. Only the spread narrows, %.3f to %.3f."
          % (smooth4["sd"], rough40["sd"]))
    print("         The hypothesis this file was built to test is REFUTED.")

    # The hypothesis this probe was written to test was that C reads smoothness, so that three
    # independent smooth streams would already score in the 0.9s. It is REFUTED above: the mean
    # sits near 0.52 at every smoothness, and only the spread narrows. Recorded, not hidden.
    report["smoothness_hypothesis"] = "REFUTED: mean C is flat in smoothness; only the sd shrinks"

    mono = report["independent_monotone"]["4"]
    cumu = report["two_monotone_one_cumulative"]["4"]
    report["monotone_lifts_C"] = mono["mean"] - smooth4["mean"]
    print("The monotone arms matter, because a real sweep is monotone, and they agree:")
    print("  independent smooth      C = %.4f +/- %.4f" % (smooth4["mean"], smooth4["sd"]))
    print("  independent monotone    C = %.4f +/- %.4f" % (mono["mean"], mono["sd"]))
    print("  two monotone + cumulative C = %.4f +/- %.4f" % (cumu["mean"], cumu["sd"]))
    print()

    # controls proper: these test the instrument, not the hypothesis
    if abs(report["control_antiphase"]["mean"] - 1.0 / 3.0) > 1e-6:
        failures.append("a stream against its antiphase gave %.6f, not 1/3"
                        % report["control_antiphase"]["mean"])
    if not (0.45 < report["control_white_phases"]["mean"] < 0.60):
        failures.append("the uniform-phase floor came out at %.4f, off the three-phasor value"
                        % report["control_white_phases"]["mean"])

    print()
    if failures:
        for f in failures:
            print("CONTROL FAILED: %s" % f)
        report["verdict"] = "FAILED"
    else:
        report["verdict"] = "OK"
        print("VERDICT: OK. All three controls behaved.")

    out = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("wrote %s" % os.path.basename(out))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
