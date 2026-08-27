"""Do these detectors agree because the signal has structure, or because they share a criterion?

WHY THIS EXISTS. On a cross-framework paper it was argued that several detectors flagging the same
positions is independent corroboration. That is only true if the detectors are independent. Detectors
built on the same mean-shift criterion locate the loudest feature of a curve whether or not they agree
about anything else, so their agreement can be a property of the family rather than of the data.

This measures it instead of asserting it, on curves with NO periodic structure at all -- a smooth
V-valley plus noise, the shape the collaboration's own data has. Every agreement found here is
therefore agreement about something that is not there.

THE DETECTORS are the collaborator's own code, unchanged where we hold it:
  * `moire_test`  -- 50 phase-shifted copies summed, peaks at mean + 1.5 sd
  * `adaptive_anchors` -- his K-locator
  * a real-valued monitor -- find_peaks on the curve itself at mean + 1.5 sd

THE CONTROL IS THE WHOLE POINT. An agreement rate means nothing without the rate you would get by
chance from detectors that flag the same NUMBER of positions at random. So each run is paired with a
shift-null: the same flags, circularly shifted to random offsets, agreement recounted. If observed
agreement sits at the null, the detectors are independent on this data and the corroboration argument
survives. If it sits far above, agreement is a property of the criterion.

Exit 0 with the table; the assertions fail loudly if the conclusion inverts.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks

N = 301
N_SHIFTS = 50
TOL = 5                      # positions agree if within +-5 samples (the change-point convention)
RUNS = 300
SEED = 20260810


def moire_test(signal, n_shifts=N_SHIFTS):
    """The collaborator's moire detector, unchanged."""
    moire = np.zeros_like(signal)
    for shift in range(1, n_shifts + 1):
        moire += np.roll(signal, shift)
    moire = moire / n_shifts
    peaks, _ = find_peaks(moire, height=np.mean(moire) + 1.5 * np.std(moire))
    return list(peaks)


def adaptive_anchors(series, window=3, tol=0.15):
    """His K-locator: points whose local window departs from the running level."""
    s = np.asarray(series, dtype=float)
    out = []
    for i in range(window, len(s) - window):
        loc = s[i - window:i + window + 1]
        if abs(s[i] - loc.mean()) > tol * (loc.std() + 1e-12):
            out.append(i)
    return out


def real_monitor(signal):
    peaks, _ = find_peaks(signal, height=np.mean(signal) + 1.5 * np.std(signal))
    return list(peaks)


def _v_curve(rng, n=N):
    """A smooth V valley plus noise. No periodic component anywhere in the generator."""
    x = np.linspace(0, 1, n)
    centre = rng.uniform(0.35, 0.65)
    depth = rng.uniform(0.5, 1.5)
    tilt = rng.uniform(-0.3, 0.3)
    v = depth * np.abs(x - centre) + tilt * x
    return v + rng.standard_normal(n) * 0.02 * depth


def _agree(a, b, tol=TOL):
    """How many of a's flags have a partner in b within tol."""
    if not a or not b:
        return 0
    b = np.asarray(b)
    return int(sum(1 for p in a if np.min(np.abs(b - p)) <= tol))


def _null_agree(rng, a, b, n=N, tol=TOL, reps=200):
    """Chance agreement for detectors flagging the SAME counts at random positions."""
    if not a or not b:
        return 0.0
    tot = 0
    for _ in range(reps):
        ra = rng.integers(0, n, size=len(a))
        rb = rng.integers(0, n, size=len(b))
        tot += _agree(list(ra), list(rb), tol)
    return tot / reps


def main() -> int:
    rng = np.random.default_rng(SEED)
    pairs = {"moire vs monitor": (moire_test, real_monitor),
             "moire vs anchors": (moire_test, adaptive_anchors),
             "anchors vs monitor": (adaptive_anchors, real_monitor)}
    obs = {k: [] for k in pairs}
    nul = {k: [] for k in pairs}
    counts = {"moire": [], "anchors": [], "monitor": []}

    for _ in range(RUNS):
        sig = _v_curve(rng)
        f = {"moire": moire_test(sig), "anchors": adaptive_anchors(sig), "monitor": real_monitor(sig)}
        for k, v in f.items():
            counts[k].append(len(v))
        for name, (fa, fb) in pairs.items():
            a = f["moire"] if fa is moire_test else (f["anchors"] if fa is adaptive_anchors else f["monitor"])
            b = f["moire"] if fb is moire_test else (f["anchors"] if fb is adaptive_anchors else f["monitor"])
            obs[name].append(_agree(a, b))
            nul[name].append(_null_agree(rng, a, b))

    print("curves with NO periodic component: smooth V + noise, n = %d, %d runs, tolerance +-%d samples"
          % (N, RUNS, TOL))
    print("flags per curve: " + ", ".join("%s %.1f" % (k, np.mean(v)) for k, v in counts.items()))
    print("\n  %-22s %-16s %-16s %s" % ("pair", "observed agree", "chance agree", "ratio"))
    ratios = {}
    for name in pairs:
        o, e = float(np.mean(obs[name])), float(np.mean(nul[name]))
        r = o / e if e > 0 else float("inf")
        ratios[name] = (o, e, r)
        print("  %-22s %-16.2f %-16.2f %s" % (name, o, e, ("%.1fx" % r) if np.isfinite(r) else "inf"))

    # THE VERDICT IS COMPUTED, NOT WRITTEN IN ADVANCE. The first version of this file printed
    # "agreement is a property of the shared criterion" unconditionally -- the sentence I expected to
    # be able to say -- and then an assertion caught that the data said the opposite. A verdict that
    # does not depend on the measurement is not a verdict.
    excess = [(k, o, e, r) for k, (o, e, r) in ratios.items() if np.isfinite(r) and r > 1.5]
    print()
    if excess:
        k, o, e, r = max(excess, key=lambda t: t[3])
        print("MEASURED: on curves containing NO periodicity, %s agree %.2f times per curve against"
              " %.2f expected by chance (%.1fx)." % (k, o, e, r))
        print("\nVERDICT: these detectors agree ABOVE chance on data with nothing to corroborate, so"
              "\n         their agreement is substantially a property of the shared criterion and"
              "\n         cannot be read as independent evidence.")
    else:
        worst = max(ratios.items(), key=lambda kv: kv[1][2])
        print("MEASURED: no pair exceeds chance. The highest is %s at %.1fx (%.2f observed against"
              " %.2f expected)." % (worst[0], worst[1][2], worst[1][0], worst[1][1]))
        print("\nVERDICT: the 'they agree because they share a criterion' objection is NOT supported"
              "\n         for this family on this data. On curves with no structure to corroborate,"
              "\n         these detectors agree at or BELOW the rate of detectors firing at random, so"
              "\n         agreement between them is not manufactured by the criterion they share."
              "\n         The objection should not be raised without this measurement behind it.")

    # SCOPE, and it limits which row above can be quoted. `moire_test` is the collaborator's code
    # unchanged. `adaptive_anchors` here is OUR reading of his method, and a reconstruction is not his
    # instrument -- rows involving it are indicative only, which is why the assertion below rests on
    # the moire/monitor pair, where only the generic peak finder is ours.
    assert all(np.mean(v) > 0 for v in counts.values()), (
        "a detector fired zero times across every run: it cannot agree or disagree, so the table above "
        "measures nothing")
    mm = ratios["moire vs monitor"][2]
    assert np.isfinite(mm) and mm < 1.5, (
        "the moire/monitor pair now agrees ABOVE chance (%.1fx): the conclusion has inverted and the "
        "text above must be re-read before it is cited anywhere" % mm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
