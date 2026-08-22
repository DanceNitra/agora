"""VALIDATE gate: every number we would put in the EDRN reply, re-derived this cycle.

This is the first pass of the standing gate (validate -> storm -> audit -> verify). It refuses to
report unless each figure is reproduced from an artifact rather than quoted from a note. Two sources
are read and they are independent of each other:

  * OUR receipt, probes/edrn_his_valley_bottom_is_a_start_vector.result.json, written by a probe whose
    own controls all pass;
  * HIS posted archive, parsed directly out of the zip, so the claims about what his file says are
    checked against his file and not against our memory of it.

THE CONTROL, because a gate that cannot fail has measured nothing: after the real pass, every
assertion is re-run against a MUTATED copy of the receipt in which one figure is perturbed. If the
mutated run still passes, the gate is not reading what it claims to read and its verdict is void.

Run:  python probes/gate_edrn_reply_numbers.py
Exit 0 = every number is backed. Exit 1 = something is unbacked; do not send.
"""
from __future__ import annotations
import collections
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RECEIPT = os.path.join(HERE, "edrn_his_valley_bottom_is_a_start_vector.result.json")
OLD_RECEIPT = os.path.join(HERE, "edrn_valley_is_the_uniform_point.result.json")
ZIP = os.path.join(
    os.environ.get("TEMP", ""), "claude", "C--Users-Danculus-agora",
    "e6f8e2c8-b4c1-4269-a886-f10b2cd62521", "scratchpad", "edrn_zip", "ans.zip")


def his_rows(path):
    """Parse his 27-edge scan table straight out of the archive he posted."""
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if n.endswith("详细实验数据.txt")]
    if not names:
        raise RuntimeError("his data file is not in %s" % path)
    text = z.read(names[0]).decode("utf-8", "replace")
    pat = re.compile(r"\s*Original SG\(2\)\s+(\d+)\s+\((\d+), (\d+)\)\s+"
                     r"([\d.]+)\s+([\d.]+)\s+([\d.]+)")
    out = []
    for line in text.splitlines():
        m = pat.match(line)
        if m:
            out.append({"idx": int(m.group(1)),
                        "edge": (int(m.group(2)), int(m.group(3))),
                        "s": float(m.group(4)),
                        "e_global": float(m.group(5)),
                        "e_local": float(m.group(6))})
    return out


class Gate:
    def __init__(self):
        self.checks = []

    def eq(self, label, got, want, tol):
        ok = got is not None and abs(float(got) - float(want)) <= tol
        self.checks.append((label, ok, got, want))
        return ok

    def true(self, label, cond, detail=""):
        self.checks.append((label, bool(cond), detail, "True"))
        return bool(cond)

    def report(self, quiet=False):
        bad = [c for c in self.checks if not c[1]]
        if not quiet:
            for label, ok, got, want in self.checks:
                print("  %-4s %-62s got=%s want=%s" % ("ok" if ok else "FAIL", label, got, want))
        return not bad


def run(receipt, rows, quiet=False):
    g = Gate()
    r = receipt

    # --- C1 degeneracy, and that it is specific to the valley bottom -----------------------------
    g.eq("C1 degeneracy at the uniform point", r.get("degeneracy_uniform"), 2, 0)
    g.eq("C1 gap at the uniform point", r.get("gap_uniform"), 0.1857, 5e-5)
    g.true("C1 degenerate at s=1 and nowhere else on his grid", r.get("degenerate_only_at_s1"),
           r.get("degenerate_only_at_s1"))
    grid = {round(d["s"], 4): d["degeneracy"] for d in r.get("degeneracy_by_s", [])}
    g.true("C1 his grid covered by our degeneracy scan", set([0.0, 0.25, 0.5, 0.75, 1.0, 1.25,
                                                              1.5, 2.0, 3.0]) <= set(grid),
           sorted(grid))

    # --- C2, CORRECTED. The first version of this gate asserted that the global diagnostic is
    # INVARIANT inside the ground space, on a sweep over REAL combinations only. That was our own
    # defect, not his: the density of cos(t)|v0> + e^{i phi} sin(t)|v1> carries the cross term
    # sin(2t) cos(phi) v0 v1, so real vectors only ever reach cos(phi) = +/-1. Sweeping the phase
    # moves the global number too. Both facts are asserted here, because the pair is the finding.
    g.true("C2 REAL-only sweep reports the global width as ~0 (the blind reading)",
           (r.get("rot_global_width_real_only") or 1) < 1e-9, r.get("rot_global_width_real_only"))
    g.eq("C2 with the PHASE swept, the global width is NOT zero",
         r.get("rot_global_width"), 0.049389, 5e-6)
    g.eq("C2 global range minimum = the ground-multiplet average", r.get("rot_global_min"),
         0.110269, 5e-6)
    g.eq("C2 global range maximum = his published value", r.get("rot_global_max"), 0.159658, 5e-6)

    # --- C3 the local diagnostic moves further ----------------------------------------------------
    g.eq("C3 local width under the full sweep", r.get("rot_local_width"), 0.140345, 5e-6)
    g.eq("C3 local maximum over the sweep", r.get("rot_local_max"), 0.217799, 5e-6)

    # --- LIT the published ground state of this exact lattice ------------------------------------
    # Voigt, Richter & Tomczak, Physica A 299/3-4, 107-120 (2001), arXiv:cond-mat/0108472,
    # TABLE II (Roman), s = 1/2 row: e_b = -0.231181, D = 2.
    g.eq("LIT our e_b reproduces the 2001 published value", r.get("energy_per_bond"), -0.231181,
         5e-7)
    g.eq("LIT and the published degeneracy is the one we measure", r.get("degeneracy_uniform"), 2, 0)

    # --- C4 six symmetry-equivalent edges --------------------------------------------------------
    g.eq("C4 tip-orbit spread, single vector", r.get("tip_orbit_spread_single"), 0.132163, 5e-6)
    g.true("C4 tip-orbit spread, ground-space mixture < 1e-9",
           (r.get("tip_orbit_spread_mixture") or 1) < 1e-9, r.get("tip_orbit_spread_mixture"))
    mix = r.get("tip_local_mixture") or []
    g.true("C4 the mixture gives all six tip edges 0.105706",
           len(mix) == 6 and all(abs(v - 0.105706) < 5e-6 for v in mix), mix[:2])
    g.eq("C4 largest within-orbit spread of the 27 correlations",
         r.get("within_orbit_spread_single"), 0.421998, 5e-6)

    # --- the positive control that makes all of the above about HIS computation -------------------
    g.eq("PC our seed-0 reproduces his published E_global(s=1)",
         r.get("reproduced_s1"), 0.159658, 5e-6)
    g.true("PC every control in the probe passed", r.get("all_controls_pass"),
           r.get("all_controls_pass"))
    g.eq("PC ring control", r.get("ring_value"), 0.0, 1e-9)
    g.true("PC at the non-degenerate s=1.5 single == mixture",
           abs((r.get("s15_single") or 0) - (r.get("s15_mixture") or 1)) < 1e-8,
           (r.get("s15_single"), r.get("s15_mixture")))
    g.eq("PC start-vector hypothesis refuted: seed spread ~ 0", r.get("seed_spread_s1"), 0.0, 1e-12)

    # --- C5, read out of HIS OWN FILE, not out of our memory of it -------------------------------
    at1 = [x for x in rows if abs(x["s"] - 1.0) < 1e-9]
    g.eq("C5 his file has 27 rows at s=1.00", len(at1), 27, 0)
    distinct_g = sorted({round(x["e_global"], 6) for x in at1})
    g.true("C5 all 27 share ONE E_global at s=1.00", len(distinct_g) == 1, distinct_g)
    g.eq("C5 and that value is 0.159658", distinct_g[0] if distinct_g else None, 0.159658, 5e-7)
    curves = collections.defaultdict(list)
    for x in rows:
        curves[x["edge"]].append((x["s"], round(x["e_global"], 6)))
    sig = collections.Counter(tuple(v for _, v in sorted(c)) for c in curves.values())
    g.eq("C5 his 27 edges give 5 distinct global curves", len(sig), 5, 0)
    g.true("C5 with multiplicities 6,6,6,6,3", sorted(sig.values(), reverse=True) == [6, 6, 6, 6, 3],
           sorted(sig.values(), reverse=True))
    g.eq("C5 orbit sizes we computed independently, same shape",
         len(r.get("orbit_sizes") or []), 5, 0)
    g.true("C5 |Aut(SG2)| = 6", r.get("automorphisms") == 6, r.get("automorphisms"))

    # --- C4 again, against his file rather than ours ---------------------------------------------
    tip_rows = [x for x in at1 if min(x["edge"]) < 3]
    g.eq("C4 his file has six tip-edge rows at s=1.00", len(tip_rows), 6, 0)
    his_tip = [round(x["e_local"], 6) for x in sorted(tip_rows, key=lambda x: x["idx"])]
    ours = [round(v, 6) for v in (r.get("tip_local_single") or [])]
    g.true("C4 our single-vector local values ARE his published ones", his_tip == ours,
           "%s vs %s" % (his_tip[:4], ours[:4]))
    g.true("C4 his own file spreads one orbit by > 0.13",
           len(his_tip) == 6 and (max(his_tip) - min(his_tip)) > 0.13,
           (max(his_tip) - min(his_tip)) if his_tip else None)
    g.true("C5 his E_local at s=1 takes far more values than the 5 orbits allow",
           len({round(x["e_local"], 6) for x in at1}) > 5,
           len({round(x["e_local"], 6) for x in at1}))

    return g


def adiabatic_check(g):
    """The red team's counter-prescription: does his own scan pick his value in the limit?"""
    path = os.path.join(HERE, "edrn_does_the_adiabatic_limit_pick_his_value.result.json")
    if not os.path.exists(path):
        g.true("ADIAB receipt exists", False, path)
        return
    d = json.load(open(path, encoding="utf-8"))
    g.true("ADIAB every approach point is non-degenerate",
           all(x["deg"] == 1 for x in d.get("approach", [])),
           [x["deg"] for x in d.get("approach", [])])
    g.eq("ADIAB global limit from below", d.get("limit_global_below"), 0.159682, 5e-6)
    g.eq("ADIAB global limit from above", d.get("limit_global_above"), 0.159665, 5e-6)
    g.true("ADIAB the global limit is CONTINUOUS through s=1 and lands on his value",
           abs(d["limit_global_below"] - d["limit_global_above"]) < 1e-4
           and abs(d["limit_global_below"] - 0.159658) < 1e-4,
           abs(d["limit_global_below"] - d["limit_global_above"]))
    g.eq("ADIAB local limit from below", d.get("limit_local_below"), 0.084976, 5e-6)
    g.eq("ADIAB local limit from above", d.get("limit_local_above"), 0.193341, 5e-6)
    g.true("ADIAB the local limits DISAGREE by > 0.10",
           abs(d["limit_local_below"] - d["limit_local_above"]) > 0.10,
           abs(d["limit_local_below"] - d["limit_local_above"]))
    g.true("ADIAB no adiabatic prescription exists for the local value",
           not d.get("two_sided_limits_agree"), d.get("two_sided_limits_agree"))
    g.true("ADIAB the degeneracy is SPATIAL, S = 1/2 on both members",
           d.get("degeneracy_is_spatial") and all(abs(x - 0.5) < 1e-6
                                                  for x in d.get("implied_spin", [])),
           d.get("implied_spin"))
    g.true("ADIAB <S^2> is quantized, 0.75 on both",
           all(abs(x - 0.75) < 1e-6 for x in d.get("s2_ground_doublet", [])),
           d.get("s2_ground_doublet"))


def rescaling_check(g):
    """C7 lives in the OTHER receipt; check it there or drop the claim."""
    if not os.path.exists(OLD_RECEIPT):
        g.true("C7 rescaling receipt exists", False, OLD_RECEIPT)
        return
    d = json.load(open(OLD_RECEIPT, encoding="utf-8"))
    rows = [x for x in d.get("rows", []) if x.get("kind") == "ratio"]
    by = collections.defaultdict(list)
    for x in rows:
        by[x["j0"]].append(x)
    best = {j0: min(v, key=lambda x: x["E"]) for j0, v in by.items()}
    g.true("C7 three backgrounds measured", sorted(best) == [0.6, 1.0, 1.4], sorted(best))
    g.true("C7 argmin tracks the background exactly (s/J0 = 1)",
           all(abs(b["s"] / j0 - 1.0) < 1e-6 for j0, b in best.items()),
           {j0: b["s"] for j0, b in best.items()})
    depths = [b["E"] for b in best.values()]
    g.true("C7 identical depth across backgrounds",
           (max(depths) - min(depths)) < 1e-9, depths)
    g.eq("C7 that depth is 0.110269137", depths[0] if depths else None, 0.110269137, 5e-9)
    g.eq("C7 cross-check: his sector (N_up=7) ground-space value agrees",
         json.load(open(RECEIPT, encoding="utf-8")).get("global_s1_mixture"), 0.110269, 5e-6)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not os.path.exists(RECEIPT):
        print("no receipt: run probes/edrn_his_valley_bottom_is_a_start_vector.py first")
        return 1
    receipt = json.load(open(RECEIPT, encoding="utf-8"))
    rows = his_rows(ZIP)
    print("his archive parsed: %d scan rows" % len(rows))
    print("our receipt: %s\n" % os.path.basename(RECEIPT))

    g = run(receipt, rows)
    adiabatic_check(g)
    rescaling_check(g)   # C7 is MEASURED here but CUT from the message: H(kJ) = k H(J) is trivial
    ok = g.report()

    # ---- THE CONTROL: perturb one figure and the gate MUST fail ---------------------------------
    print("\nCONTROL, one figure at a time perturbed by 1%; the gate must fail on each:")
    control_ok = True
    for key in ("rot_local_width", "tip_orbit_spread_single", "reproduced_s1",
                "within_orbit_spread_single", "gap_uniform", "rot_global_width",
                "rot_global_max", "energy_per_bond"):
        mutated = json.loads(json.dumps(receipt))
        if not isinstance(mutated.get(key), (int, float)):
            print("  FAIL %-34s not a number in the receipt" % key)
            control_ok = False
            continue
        mutated[key] = mutated[key] * 1.01 + 1e-6
        caught = not run(mutated, rows).report(quiet=True)
        print("  %-4s %-34s mutated -> gate %s" % ("ok" if caught else "FAIL", key,
                                                   "fails" if caught else "STILL PASSES"))
        control_ok = control_ok and caught
    # and a mutation of HIS data, so the his-file half is not vacuous either
    bad_rows = [dict(x) for x in rows]
    for x in bad_rows:
        if abs(x["s"] - 1.0) < 1e-9 and x["idx"] == 0:
            x["e_global"] += 0.01
    caught = not run(receipt, bad_rows).report(quiet=True)
    print("  %-4s %-34s mutated -> gate %s" % ("ok" if caught else "FAIL", "his e_global at s=1",
                                               "fails" if caught else "STILL PASSES"))
    control_ok = control_ok and caught

    print("\n" + "=" * 84)
    print("VALIDATE: %s   CONTROL: %s" % ("PASS" if ok else "FAIL",
                                          "PASS" if control_ok else "FAIL"))
    print("=" * 84)
    return 0 if (ok and control_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
