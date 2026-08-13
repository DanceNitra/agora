"""A falsification gate for the silent-detuning valley that CAN fail, built from Guanghao's own data.

THE PROBLEM. `detect_valley` fires when the dip exceeds `0.2 * np.std(fine_values)`, a fraction of the
curve's own spread. Measured previously (guanghao_tree_valley_audit.py): it declares a valley in white
noise 100% of the time, in a smooth random walk 98.8%, and in a monotone line with noise 75%. "15
falsification tests, 15 valleys" is what that gate returns for anything that is not flat.

THE INSTRUMENT HE ALREADY BUILT WITHOUT NOTICING. His depth-reproducibility audit (2026-08-13) reran
star N=7 five times with different Lanczos starting vectors:

    depth    0.1838 +/- 0.0116     (6.3% spread)
    position 1.000  +/- 0.000      (zero spread, five times out of five)

The depth is an artifact of where the eigensolver started. The POSITION is not. That asymmetry is a
discriminator, because a curve with no physics in it has no reason to put its minimum in the same place
twice. So the gate is: rerun the scan, and ask whether the minimum LANDS IN THE SAME PLACE.

    PASS  <=>  argmin is INTERIOR (not an endpoint) AND agrees across repeats to within `tol` grid steps

BOTH CLAUSES ARE LOad-BEARING, and the second control below is the one that proves it. A monotone curve
has its minimum at index 0 on every single repeat: position stability alone is PERFECTLY satisfied by a
curve with no valley at all. Stability without interiority would be a gate that cannot fail in a new
way, which is the defect this file exists to remove, not to relocate.

I am running the controls before proposing this, because last time I proposed a replacement gate
(phase-randomised surrogates) without one, and when I did run it, it rejected a genuine V 100% of the
time. A remedy that kills true positives is worse than the gate it replaces.

    python a_gate_built_from_his_own_reseeding_experiment.py --pkg <dir with his scripts>
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import zipfile

import numpy as np

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


# ---- the gate ----------------------------------------------------------------------------------
def position_gate(curves, tol_steps=1):
    """`curves`: a list of independently produced scans of the SAME system.

    Returns (passed, detail). Interior is required first: a minimum at an endpoint is a slope, not a
    valley, however reproducible it is.
    """
    arg = [int(np.argmin(c)) for c in curves]
    n = len(curves[0])
    interior = [0 < a < n - 1 for a in arg]
    spread = max(arg) - min(arg)
    passed = all(interior) and spread <= tol_steps
    return passed, {"argmins": arg, "all_interior": bool(all(interior)),
                    "spread_steps": int(spread), "n": n}


# ---- the nulls, each RE-DRAWN per repeat (that is what "reseeding" means for a null) -------------
def null_white(rng, n, r):
    return [rng.normal(size=n) for _ in range(r)]


def null_walk(rng, n, r):
    return [np.cumsum(rng.normal(size=n)) for _ in range(r)]


def null_monotone(rng, n, r):
    x = np.linspace(0, 1, n)
    return [x + 0.05 * rng.normal(size=n) for _ in range(r)]


def null_monotone_clean(rng, n, r):
    """THE CONTROL ON THE GATE ITSELF. A perfectly stable minimum, at an endpoint, with no valley.
    Position stability alone passes this. The interior clause is the only thing that stops it."""
    x = np.linspace(0, 1, n)
    return [x.copy() for _ in range(r)]


def null_fixed_v(rng, n, r):
    """A GENUINE V with no noise at all: the positive control for the gate's upper end."""
    x = np.linspace(-1, 1, n)
    return [x ** 2 for _ in range(r)]


# ---- his real system ---------------------------------------------------------------------------
def load_his_module(pkg, fix_falsy_zero=False):
    src = None
    for z in glob.glob(os.path.join(pkg, "**", "*.zip"), recursive=True):
        with zipfile.ZipFile(z) as zf:
            for nm in zf.namelist():
                if nm.endswith(".py") and b"detect_valley" in zf.read(nm):
                    src = zf.read(nm).decode("utf-8", "replace")
                    break
        if src:
            break
    if src is None:
        for p in glob.glob(os.path.join(pkg, "**", "*.py"), recursive=True):
            t = io.open(p, encoding="utf-8", errors="replace").read()
            if "detect_valley" in t and "fine_diagnosis" in t:
                src = t
                break
    if src is None:
        raise SystemExit("no module of his with detect_valley + fine_diagnosis under %r" % pkg)
    # Cut at the main guard rather than rewriting it. My first version regex-patched the line into
    # 'if False and ( == "__main__":' -- a SyntaxError, and a loader that mangles the artifact is not
    # measuring the artifact.
    if fix_falsy_zero:
        # HIS OWN ONE-LINE FIX, applied to the shipped package so the two are directly comparable.
        # `w = w if w else 1.0` rebuilds a contradiction strength of exactly 0.0 as 1.0, so s=0 carries
        # the s=1 value and every scan opens with a duplicate of one of its own interior points.
        before = src
        src = src.replace("w = w if w else 1.0", "w = 1.0 if w is None else float(w)")
        assert src != before, "the falsy-zero line is not in this package; nothing to fix"
    ns = {}
    exec(compile(src.split("if __name__")[0], "his_module", "exec"), ns)   # noqa: S102
    return ns


def his_curves(ns, n_points, repeats):
    """Rerun HIS scan `repeats` times. `diagnose` calls eigsh with no fixed v0, so each run starts the
    Lanczos iteration somewhere else -- which is exactly the variation his own audit measured."""
    G = ns["star_tree"](7)
    e = list(G.edges())[0]
    svals = np.linspace(0, 3, n_points)
    out = []
    for _ in range(repeats):
        row = []
        for s in svals:
            Gm = ns["introduce_contradiction"](G, e, s)
            _, _, gs = ns["diagnose"](Gm, num_eig=5)
            row.append(ns["fine_diagnosis"](Gm, gs))
        out.append(np.array(row))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--points", type=int, default=151)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--trials", type=int, default=200)
    a = ap.parse_args(argv)

    rng = np.random.default_rng(11)
    out = {"repeats": a.repeats, "points": a.points, "trials": a.trials}

    print("GATE: argmin must be INTERIOR and agree across %d reseeds to within 1 grid step\n"
          % a.repeats)
    print("%-34s %-12s %s" % ("curve", "fires", "what it should do"))
    print("-" * 78)

    specs = [("genuine V (noiseless)", null_fixed_v, "PASS"),
             ("white noise", null_white, "fail"),
             ("random walk", null_walk, "fail"),
             ("monotone + noise", null_monotone, "fail"),
             ("monotone, perfectly stable", null_monotone_clean, "fail")]
    for name, fn, want in specs:
        hits = 0
        for _ in range(a.trials):
            ok, _d = position_gate(fn(rng, a.points, a.repeats))
            hits += bool(ok)
        rate = 100.0 * hits / a.trials
        flag = ""
        if want == "PASS" and rate < 100:
            flag = "   <-- KILLS A TRUE POSITIVE"
        if want == "fail" and rate > 5:
            flag = "   <-- CANNOT REFUSE"
        print("%-34s %6.1f%%      %s%s" % (name, rate, want, flag))
        out[name] = rate

    # the same three nulls through HIS gate, for the comparison that makes the number mean something
    print()
    ns = load_his_module(a.pkg)
    detect = ns["detect_valley"]
    for name, fn in (("white noise", null_white), ("random walk", null_walk),
                     ("monotone + noise", null_monotone)):
        hits = 0
        for _ in range(a.trials):
            c = fn(rng, a.points, 1)[0]
            r = detect(np.linspace(0, 3, a.points), c)
            hits += bool(r[0] if isinstance(r, (tuple, list)) else r)
        print("%-34s %6.1f%%      his detect_valley" % (name, 100.0 * hits / a.trials))
        out["his_gate_" + name] = 100.0 * hits / a.trials

    svals = np.linspace(0, 3, a.points)
    for label, fix in (("SHIPPED package (falsy-zero bug present)", False),
                       ("SAME package, his one-line fix applied", True)):
        print("\n%s -- star N=7, %d points, %d reseeds" % (label, a.points, a.repeats))
        nsx = load_his_module(a.pkg, fix_falsy_zero=fix)
        curves = his_curves(nsx, a.points, a.repeats)
        ok, detail = position_gate(curves)
        detail["argmin_s"] = [round(float(svals[i]), 4) for i in detail["argmins"]]
        detail["depths"] = [round(float(np.max(c) - np.min(c)), 4) for c in curves]
        print("  argmin s per run : %s" % detail["argmin_s"])
        print("  depth per run    : %s" % detail["depths"])
        print("  GATE             : %s" % ("PASS" if ok else "FAIL"))
        out["real_fixed" if fix else "real_shipped"] = {"passed": bool(ok), **detail}

    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
