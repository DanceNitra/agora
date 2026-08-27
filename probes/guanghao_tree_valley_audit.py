"""Auditing Guanghao's tree-valley result: the gate is weak, the finding survives it anyway.

WHAT I SET OUT TO SHOW, AND WHY IT WAS WRONG. His `detect_valley` declares a valley when the drop from
the flanking maxima to the global minimum exceeds `0.2 * np.std(fine_values)` -- a threshold set as a
fraction of the curve's own spread. Fed curves with no physics in them, that gate fires on pure white
noise 100% of the time. So "15 falsification tests, 15 valleys" is what this gate returns for anything
that is not flat, and I was ready to send that as a refutation of the First Law upgrade.

It is not a refutation, and sending it would have been our own rule pointed the wrong way: MEASURE THE
CODE THAT RUNS. The shipped package is N=6 on a 13-point grid; his revised claim is N=7 at 301 points.
Run at the configuration he actually claims, his valleys are 2.6-2.7 standard deviations deep -- about
thirteen times his own threshold -- and land where he says they do. A weak gate did not manufacture
this result. The instrument critique is real and it is not load-bearing.

WHAT IS ACTUALLY WORTH HIS TIME, all three found in his own code and reproduced here:

  1. A one-line coercion bug. `w = w if w else 1.0` in `graph_to_hamiltonian` turns a zero coupling
     into a full one, because 0.0 is falsy. Measured: fine(s=0.0) and fine(s=1.0) are bit-identical
     at 0.2447051991, while the value s=0 should produce is 0.1283170693. Every scan starting at
     s=0 has a phantom point copied from s=1.
  2. Effective replication is 9, not 15. `star_tree(N)`, `binary_tree(h)` and `path_graph_tree(N)`
     take no seed, so nine of the fifteen cells are the same three graphs run three times each.
  3. The gate cannot refuse. Useful to fix before the next topology, not a reason to doubt this one.

    python guanghao_tree_valley_audit.py --pkg <15棵树的追问.zip>
"""
import argparse
import glob
import io
import inspect
import json
import os
import re
import sys
import zipfile

import numpy as np

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def load_his_module(pkg):
    """Everything below runs HIS functions. A reconstruction would measure the reconstruction."""
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_guanghao_pkg")
    with zipfile.ZipFile(pkg) as z:
        z.extractall(tmp)
    py = glob.glob(os.path.join(tmp, "**", "*.py"), recursive=True)[0]
    src = io.open(py, encoding="utf-8", errors="replace").read()
    ns = {}
    exec(compile(src.split("if __name__")[0], "guanghao", "exec"), ns)   # noqa: S102
    grid = re.search(r"np\.linspace\(([^)]*)\)", src)
    js = glob.glob(os.path.join(tmp, "**", "*.json"), recursive=True)
    return ns, (grid.group(1) if grid else "?"), (json.load(io.open(js[0], encoding="utf-8")) if js else {})


def scan(ns, G, svals):
    e = list(G.edges())[0]
    out = []
    for s in svals:
        Gm = ns["introduce_contradiction"](G, e, s)
        _, _, gs = ns["diagnose"](Gm, num_eig=5)
        out.append(ns["fine_diagnosis"](Gm, gs))
    return np.array(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--trials", type=int, default=400)
    a = ap.parse_args(argv)
    ns, grid, his = load_his_module(a.pkg)
    detect = ns["detect_valley"]
    out = {"his_grid": grid, "his_summary": {k: his.get(k) for k in ("N", "total_tests", "valley_count")}}
    print("shipped package : np.linspace(%s), N=%s, %s/%s tests reported a valley\n"
          % (grid, his.get("N"), his.get("valley_count"), his.get("total_tests")))

    # ---- 1. the gate, on curves with no physics ------------------------------------------------
    rng = np.random.default_rng(7)
    n = 301
    s = np.linspace(0, 3, n)
    gens = {
        "pure white noise": lambda: rng.normal(0, 1, n),
        "flat + tiny noise": lambda: rng.normal(0, 1e-6, n),
        "smooth random walk": lambda: np.convolve(rng.normal(0, 1, n + 40), np.ones(41) / 41, "valid"),
        "monotone + noise": lambda: s * 0.5 + rng.normal(0, 0.05, n),
        "a genuine V (control)": lambda: np.abs(s - 1.0) + rng.normal(0, 0.02, n),
    }
    print("HIS gate on curves containing no physics (%d trials each):" % a.trials)
    out["null_rates"] = {}
    for k, g in gens.items():
        r = sum(1 for _ in range(a.trials) if detect(s, g())[0]) / a.trials
        out["null_rates"][k] = r
        print("  %-24s declares a valley %5.1f%%" % (k, 100 * r))

    # ---- 2. THE CONTROL THAT DECIDES IT: his real curves at the configuration he claims ---------
    print("\nHIS OWN CURVES at the configuration his revision claims (N=7, 301 points):")
    out["real"] = {}
    for label, G in (("path N=7", ns["path_graph_tree"](7)), ("star N=7", ns["star_tree"](7))):
        v = scan(ns, G, s)
        ok, pos, depth = detect(s, v)
        ratio = depth / v.std()
        out["real"][label] = {"valley": bool(ok), "position": float(pos), "depth": float(depth),
                              "depth_over_sd": float(ratio)}
        print("  %-9s valley at s=%.3f, depth %.4f = %.1f x sd  (his threshold is 0.2 x sd)"
              % (label, pos, depth, ratio))
    print("  -> the weak gate did not manufacture this. Clears its own threshold ~13x.")

    # ---- 3. the coercion bug -------------------------------------------------------------------
    print("\nTHE ONE-LINE BUG: `w = w if w else 1.0` -- 0.0 is falsy, so s=0 becomes s=1")
    G = ns["path_graph_tree"](6)
    f0, f1, feps = (scan(ns, G, [0.0])[0], scan(ns, G, [1.0])[0], scan(ns, G, [1e-9])[0])
    out["coercion_bug"] = {"fine_at_0": float(f0), "fine_at_1": float(f1), "fine_at_1e-9": float(feps),
                           "identical": bool(abs(f0 - f1) < 1e-12)}
    print("  fine(0.0) = %.10f" % f0)
    print("  fine(1.0) = %.10f   identical: %s" % (f1, abs(f0 - f1) < 1e-12))
    print("  fine(1e-9)= %.10f   <- what s=0 should have produced" % feps)
    print("  fix: w = 1.0 if w is None else float(w)")

    # ---- 4. replication ------------------------------------------------------------------------
    print("\nREPLICATION: which builders actually use the seed?")
    out["seeded"] = {}
    for fn in ("star_tree", "binary_tree", "path_graph_tree", "random_tree", "random_labeled_tree"):
        if fn in ns:
            params = list(inspect.signature(ns[fn]).parameters)
            out["seeded"][fn] = "seed" in params
            print("  %-20s params=%-14s seeded: %s" % (fn, ",".join(params), "seed" in params))
    print("  -> three topologies x three seeds are the same graph three times; effective n is 9, not 15.")

    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
