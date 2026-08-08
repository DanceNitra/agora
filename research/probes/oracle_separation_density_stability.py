"""Does the published separation ratio survive its own free parameters? (evidence for the #7707 correction)

We posted, on openclaw/openclaw#7707:

    "poison earns standing 100% of the time and the separation ratio stays below 1.0 at every
     density we tested, 0.77 to 0.94 across 1, 2, 4 and 8 uses per fact"

Both halves came from `research/probes/oracle_separation_density.py`. This harness measures what that
probe does when the two knobs it never disclosed are moved:

  * SEED COUNT — `measure()` hardcodes `for s in range(6)`. Six seeds.
  * ROD_THETA  — the standing bar, `os.environ.get("ROD_THETA", "2.0")`. Never swept.

WHAT THIS DOES NOT DO. It does not rehabilitate the number. The `minja@1.0` arm is degenerate by
construction (`good = random() < 1.0` is always true, so a poison record never accrues `bad`, so
`blocked()` cannot fire), and every statistic downstream of that branch inherits the defect. This
harness exists to size the SECOND defect — that a 6-seed point estimate of a knob-dependent quantity
was published as a range — not to produce a replacement figure.

METHOD, and why it is not a reconstruction. The engine is the ORIGINAL probe's own `run()`,
`build_corpus()` and `retrieve()`, loaded from the shipped source file by exec'ing it up to the start
of its script body. Nothing is reimplemented except the seed loop, which is the thing under test.

POSITIVE CONTROL (this is the point). At 6 seeds with theta=2.0 the harness must reproduce the four
published ratios to 1e-9. If it does not, the aggregation here differs from the probe's and every
other number this file prints is meaningless -- so it ABORTS instead of reporting. A harness that
cannot reproduce the number it was built to question has measured nothing.

Needs numpy + the probe's embedding cache (or a local nomic embedder). Deterministic. MIT.
Run: python -X utf8 research/probes/oracle_separation_density_stability.py
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "research" / "probes" / "oracle_separation_density.py"
PUBLISHED = ROOT / "research" / "probes" / "oracle_separation_density_result.json"
OUT = Path(__file__).with_suffix(".result.json")

# the published run: measure() loops `for s in range(6)` over seeds 4000+s
PUBLISHED_SEEDS = 6
SEED_BASE = 4000
DENS = [1, 2, 4, 8]
BOOT = 2000
TOL = 1e-9


def load_probe(theta: float):
    """Exec the shipped probe up to its script body and return its namespace.

    We take the real functions from the real file. The cut point is asserted, not assumed: if the
    probe is ever restructured this raises instead of silently measuring a different program.
    """
    src = PROBE.read_text(encoding="utf-8", errors="replace")
    marker = 'print(f"=== ORACLE SEPARATION'
    cut = src.find(marker)
    if cut < 0:
        raise SystemExit("ABORT: cannot find the probe's script body marker %r in %s -- refusing to "
                         "guess where the definitions end." % (marker, PROBE))
    ns: dict = {"__name__": "_rod_defs", "__file__": str(PROBE)}
    os.environ["ROD_THETA"] = repr(theta)
    exec(compile(src[:cut], str(PROBE), "exec"), ns)
    for need in ("run", "build_corpus", "retrieve", "THETA", "prefetch"):
        if need not in ns:
            raise SystemExit("ABORT: probe namespace is missing %r -- the cut point is wrong." % need)
    if abs(ns["THETA"] - theta) > 1e-12:
        raise SystemExit("ABORT: THETA is %r, expected %r." % (ns["THETA"], theta))
    return ns


def measure_seeds(ns, facts, qas, oracle: str, minja_p: float, n_seeds: int):
    """The probe's own measure(), with the seed count lifted out as a parameter.

    Returns the aggregate AND the per-seed rows, so the aggregate can be bootstrapped over seeds.
    Aggregation is character-for-character the probe's: reduction from the MEAN damage of each arm,
    legit_block from the SUMS, ratio = reduction / legit_block.
    """
    rows = []
    for s in range(n_seeds):
        b = ns["run"](facts, qas, "BASELINE", SEED_BASE + s, oracle, minja_p)
        g = ns["run"](facts, qas, "GATE", SEED_BASE + s, oracle, minja_p)
        if b and g:
            rows.append((b["irr_damage"], g["irr_damage"], g["legit_hi_blocked"],
                         g["legit_hi_total"], g["poison_earn_ever"]))
    if not rows:
        return None, []
    return aggregate(rows), rows


def aggregate(rows):
    bd = float(np.mean([r[0] for r in rows]))
    gd = float(np.mean([r[1] for r in rows]))
    lhb = float(np.sum([r[2] for r in rows]))
    lht = float(np.sum([r[3] for r in rows]))
    reduction = 1.0 - (gd / bd) if bd else 0.0
    legit_block = (lhb / lht) if lht else 0.0
    ratio = (reduction / legit_block) if legit_block > 0 else float("inf")
    return {"reduction": reduction, "legit_block": legit_block, "ratio": ratio,
            "poison_earn_ever": float(np.mean([r[4] for r in rows]))}


def bootstrap_ratio(rows, n=BOOT, seed=20260808):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        pick = [rows[rng.randrange(len(rows))] for _ in range(len(rows))]
        r = aggregate(pick)["ratio"]
        if r != float("inf"):
            out.append(r)
    out.sort()
    if not out:
        return None
    lo = out[int(0.025 * len(out))]
    hi = out[int(0.975 * len(out)) - 1]
    return {"lo": lo, "hi": hi, "n_boot": len(out)}


def main() -> int:
    published = json.loads(PUBLISHED.read_text(encoding="utf-8", errors="replace"))
    pub_ratio = {int(k): v["minja1"]["ratio"] for k, v in published["results"].items()}
    pub_earn = {int(k): v["minja1"]["poison_earn_ever"] for k, v in published["results"].items()}
    print("published (theta=%s, %d seeds): %s" % (
        published.get("theta"), PUBLISHED_SEEDS,
        ", ".join("D=%d %.6f" % (d, pub_ratio[d]) for d in DENS)))

    report: dict = {"scenario": "oracle_separation_density_stability",
                    "published_ratio": pub_ratio, "published_seeds": PUBLISHED_SEEDS,
                    "arms": {}}

    # ---------- POSITIVE CONTROL: theta=2.0, 6 seeds must reproduce the published numbers ----------
    ns2 = load_probe(2.0)
    corpora = {}
    print("\nbuilding corpora (embeddings from the probe's cache)...", flush=True)
    for D in DENS:
        corpora[D] = ns2["build_corpus"](D)
        print("  D=%d: %d facts, %d queries" % (D, len(corpora[D][0]), len(corpora[D][1])), flush=True)

    print("\n--- POSITIVE CONTROL: theta=2.0, %d seeds (must match published) ---" % PUBLISHED_SEEDS)
    control_rows = {}
    for D in DENS:
        f, q = corpora[D]
        agg, rows = measure_seeds(ns2, f, q, "minja", 1.0, PUBLISHED_SEEDS)
        control_rows[D] = rows
        delta = abs(agg["ratio"] - pub_ratio[D])
        ok = delta <= TOL
        print("  D=%d ratio %.9f vs published %.9f  delta %.2e  %s"
              % (D, agg["ratio"], pub_ratio[D], delta, "OK" if ok else "MISMATCH"))
        if not ok:
            print("\nABORT: the control does not reproduce the published number. This harness's "
                  "aggregation differs from the probe's, so nothing else it prints can be trusted.")
            return 2
        if abs(agg["poison_earn_ever"] - pub_earn[D]) > TOL:
            print("\nABORT: poison_earn_ever does not reproduce at D=%d." % D)
            return 2
    print("  control PASSED -- the aggregation here is the probe's.")
    report["control"] = {"passed": True, "tol": TOL}

    # ---------- ARM A: theta=2.0, 24 seeds ----------
    print("\n--- ARM A: theta=2.0, 24 seeds (the published run used 6) ---")
    armA = {}
    for D in DENS:
        f, q = corpora[D]
        agg, rows = measure_seeds(ns2, f, q, "minja", 1.0, 24)
        ci = bootstrap_ratio(rows)
        inside = ci and (ci["lo"] <= pub_ratio[D] <= ci["hi"])
        armA[str(D)] = {"ratio": agg["ratio"], "ci": ci, "earn": agg["poison_earn_ever"],
                        "published_inside_ci": bool(inside)}
        print("  D=%d ratio %.4f  95%% CI [%.3f, %.3f]  published %.4f is %s its own CI  (earn %.0f%%)"
              % (D, agg["ratio"], ci["lo"], ci["hi"], pub_ratio[D],
                 "INSIDE" if inside else "OUTSIDE", 100 * agg["poison_earn_ever"]))
    report["arms"]["theta2_seeds24"] = armA

    # ---------- ARM B: theta=1.0 ----------
    print("\n--- ARM B: theta=1.0 (the knob the published run never swept) ---")
    ns1 = load_probe(1.0)
    corpora1 = {D: ns1["build_corpus"](D) for D in DENS}
    armB = {}
    for D in DENS:
        f, q = corpora1[D]
        agg6, _ = measure_seeds(ns1, f, q, "minja", 1.0, PUBLISHED_SEEDS)
        agg24, rows24 = measure_seeds(ns1, f, q, "minja", 1.0, 24)
        ci = bootstrap_ratio(rows24)
        armB[str(D)] = {"ratio_6": agg6["ratio"], "ratio_24": agg24["ratio"], "ci_24": ci,
                        "earn": agg24["poison_earn_ever"]}
        print("  D=%d ratio %.4f (6 seeds) / %.4f (24 seeds)  95%% CI [%.3f, %.3f]  %s"
              % (D, agg6["ratio"], agg24["ratio"], ci["lo"], ci["hi"],
                 "ABOVE 1.0" if agg24["ratio"] > 1.0 else ""))
    report["arms"]["theta1"] = armB

    # ---------- the claim we published, restated as checks ----------
    pub_lo, pub_hi = min(pub_ratio.values()), max(pub_ratio.values())
    monotone = all(pub_ratio[DENS[i]] >= pub_ratio[DENS[i + 1]] for i in range(len(DENS) - 1)) or \
        all(pub_ratio[DENS[i]] <= pub_ratio[DENS[i + 1]] for i in range(len(DENS) - 1))
    any_above_1 = any(v["ratio_24"] > 1.0 for v in armB.values()) or \
        any(v["ratio_6"] > 1.0 for v in armB.values())
    any_outside = any(not v["published_inside_ci"] for v in armA.values())
    print("\nCHECKS ON THE PUBLISHED SENTENCE:")
    print("  %-5s  the published range %.2f-%.2f is MONOTONE in density" % (str(monotone), pub_lo, pub_hi))
    print("  %-5s  some published point falls OUTSIDE its own 24-seed bootstrap CI" % str(any_outside))
    print("  %-5s  'stays below 1.0 at every density' survives theta=1.0" % str(not any_above_1))
    print("  %-5s  poison_earn_ever == 1.0 everywhere (it is forced: random() < 1.0)"
          % str(all(abs(v - 1.0) < TOL for v in pub_earn.values())))
    report["checks"] = {"published_range_is_monotone": bool(monotone),
                        "a_published_point_falls_outside_its_own_ci": bool(any_outside),
                        "below_1_survives_theta1": bool(not any_above_1),
                        "earn_is_pinned_at_1": bool(all(abs(v - 1.0) < TOL for v in pub_earn.values()))}

    verdict = ("The published sentence does not survive its own free parameters." if
               (not monotone) or any_outside or any_above_1 else
               "The published sentence survives.")
    report["verdict"] = verdict
    print("\nVERDICT: %s" % verdict)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
