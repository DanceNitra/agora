"""@Stratogain says our cliff warning cannot fire on path-shaped keys. Measured on our own code: he is right, twice.

HIS CLAIM, from anthropics/claude-code#34556, measured on his own store rather than on a
construction: `at_cliff_edge` fires only when `verdict == ZERO_AT_SCALE and headroom_chars == 1`,
and on a structurally-keyed population that conjunction is not merely false but UNSATISFIABLE -- the
first non-merging fold sits at character 149, and the population threshold there is 1.56e57 against
516 keys, so the verdict at that fold can never be ZERO_AT_SCALE no matter how the store grows. He
adds a second, independent silencer: on a 3-key store `positions_saturated` blocks the verdict for a
different reason. Same empty field, opposite meanings, nothing in the output telling them apart.

WHAT THIS MEASURES, on the shipped 2.17.1 rather than on his description:
  1. REACHABILITY. Sweeping every fold length, is there ANY length at which a path-shaped
     population returns ZERO_AT_SCALE? And for a tiny hash-shaped one?
  2. THE SHIPPED SURFACE. `identifier_contract()` measures folds 8 and 12 only, and computes
     `collides_at_length` by searching lengths BELOW the fold. So a cliff at 149 is outside the
     instrument entirely -- a plainer defect than the one he reported, and it arrives first.
  3. HIS CONTROLS, RUN AS HIS. The planted cliff must fire, the same keys one character shorter must
     report COST_MEASURED, and an unstructured population must not declare a cliff. Without these a
     "cannot fire" result is indistinguishable from a broken instrument.
  4. HIS PROPOSED REPLACEMENT -- `headroom_chars == 1 and keys_lost == 0` plus a minimum key count --
     scored on the same four populations, to see whether it fires where the structure does the damage
     and stays quiet on the ordinary stores it must not become a banner on.

Run: python probes/the_cliff_warning_is_unsatisfiable_on_path_shaped_keys.py
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import string
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

REPO = pathlib.Path(r"C:\Users\Danculus\inspeximus-repo")
sys.path.insert(0, str(REPO))
import inspeximus                                                      # noqa: E402
from inspeximus import Inspeximus                                      # noqa: E402
from inspeximus.core import _prefix_collision_threshold                # noqa: E402

HERE = pathlib.Path(__file__).parent
OUT = HERE / "the_cliff_warning_is_unsatisfiable_on_path_shaped_keys.result.json"


def store(keys):
    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), embed=False)
    for i, k in enumerate(keys):
        ix.remember("r%d" % i, key=k)
    ix.flush()
    return ix


def lost_at(keys, L):
    g: dict = {}
    for k in keys:
        g.setdefault(k[:L], []).append(k)
    return sum(len({*v}) - 1 for v in g.values() if len({*v}) > 1)


def saturated_at(keys, L):
    """The shipped rule, reproduced: a position whose observed alphabet is as large as the sample."""
    return sum(1 for i in range(L)
               if len({(k[i] if i < len(k) else "") for k in keys}) >= len({*keys}))


def verdict_at(keys, L):
    """What the shipped logic WOULD say at fold L, if the contract measured that fold."""
    lost = lost_at(keys, L)
    thr = _prefix_collision_threshold(keys, L)
    if lost:
        return "COST_MEASURED", thr
    if thr is None:
        return "ZERO_NO_THRESHOLD_MODEL", thr
    if len(keys) < thr or saturated_at(keys, L):
        return "NOT_YET_MEASURABLE", thr
    return "ZERO_AT_SCALE", thr


# ---------------------------------------------------------------- his two live populations, rebuilt
rng = random.Random(20260820)
# A: session keys -- 8 hex characters taken from a UUID, three of them
sessions = sorted({"".join(rng.choice("0123456789abcdef") for _ in range(8)) for _ in range(3)})
while len(sessions) < 3:
    sessions = sorted(set(sessions) | {"".join(rng.choice("0123456789abcdef") for _ in range(8))})

# B: paths -- a shallow common root, and one deep scratch directory whose four files are
# distinguished only after character 148, which is the shape he reports arriving on its own.
DEEP = "c:/users/x/agora/scratchpad/probe/assets-monitor/finder-v05/nested/deeper/deepest/leafdir/"
DEEP = DEEP + "x" * max(0, 148 - len(DEEP))
paths = [DEEP + n for n in ("lib/tg.mjs", "run-v05.mjs", "scan-s1.mjs", "mutation-probe.mjs")]
while len(paths) < 516:
    d = "/".join("".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(3, 9)))
                 for _ in range(rng.randint(2, 5)))
    paths.append("c:/%s/%s.py" % (d, "".join(rng.choice(string.ascii_lowercase) for _ in range(6))))
paths = sorted(set(paths))[:516]

# his controls. THE PLANTED CLIFF IS CONSTRUCTED, NOT DRAWN: a first attempt drew 400 random
# "ab"+6-hex keys and collided at 6 characters rather than 7, so headroom at fold 8 was 2, the
# gate stayed quiet, and the probe reported that HIS control does not fire on OUR code -- a false
# alarm about his claim, caused by my fixture. The state a control exists to reproduce is built.
planted = ["ab" + "%04d" % i + "xy" for i in range(398)]
planted += ["ab0000zz", "ab0000zw"]           # one pair sharing exactly the first 7 characters
planted = sorted(set(planted))
unstructured = sorted({"".join(rng.choice(string.digits + string.ascii_lowercase) for _ in range(20))
                       for _ in range(400)})

POPS = {"A  session keys (hash-shaped)": sessions,
        "B  paths (structured)": paths,
        "C  planted cliff (his control)": planted,
        "D  unstructured (his control)": unstructured}

print("inspeximus %s -- the shipped contract, not a reimplementation\n" % inspeximus.__version__)
print("%-32s %6s %12s %14s" % ("population", "keys", "common root", "deepest prefix"))
for name, keys in POPS.items():
    root = os.path.commonprefix(list(keys))
    deepest = max((L for L in range(1, max(len(k) for k in keys) + 1) if lost_at(keys, L)), default=0)
    print("%-32s %6d %12d %14d" % (name, len(keys), len(root), deepest))

# ---------------------------------------------------------------- 1. what the SHIPPED contract says
print("\n1. WHAT `identifier_contract()` ACTUALLY REPORTS TODAY (it measures folds 8 and 12 only)")
print("%-32s %-12s %-16s %-9s %s" % ("population", "fold", "verdict", "headroom", "at_cliff_edge"))
shipped = {}
for name, keys in POPS.items():
    c = store(keys).identifier_contract()
    shipped[name] = {"at_cliff_edge": c["at_cliff_edge"], "folds": {}}
    for fold in ("prefix_8", "prefix_12"):
        m = c["measured"][fold]
        shipped[name]["folds"][fold] = {"verdict": m["verdict"],
                                        "headroom": m.get("headroom_chars"),
                                        "collides_at": m.get("collides_at_length"),
                                        "lost": m["keys_that_would_be_lost"]}
        print("%-32s %-12s %-16s %-9s %s" % (name, fold, m["verdict"],
                                             m.get("headroom_chars"), c["at_cliff_edge"] or "[]"))

# ---------------------------------------------------------------- 2. reachability, his question
print("\n2. IS `ZERO_AT_SCALE` REACHABLE AT ANY FOLD LENGTH? (his 'no, at no length' claim)")
print("%-32s %-10s %-30s %s" % ("population", "lengths", "verdicts seen", "ZERO_AT_SCALE anywhere?"))
reach = {}
for name, keys in POPS.items():
    top = min(max(len(k) for k in keys), 200)
    seen, zero_at = {}, []
    for L in range(1, top + 1):
        v, _ = verdict_at(keys, L)
        seen[v] = seen.get(v, 0) + 1
        if v == "ZERO_AT_SCALE":
            zero_at.append(L)
    reach[name] = {"scanned": top, "verdicts": seen, "zero_at_scale_lengths": zero_at[:6],
                   "reachable": bool(zero_at)}
    print("%-32s 1-%-8d %-30s %s" % (name, top, ", ".join("%s:%d" % kv for kv in sorted(seen.items()))[:30],
                                     ("yes, from %d" % zero_at[0]) if zero_at else "NO"))

# ---------------------------------------------------------------- 3. the cliff, and its threshold
print("\n3. WHERE THE CLIFF SITS, AND WHAT THE THRESHOLD THERE COSTS")
cliffs = {}
for name, keys in POPS.items():
    top = max(len(k) for k in keys)
    collide = max((L for L in range(1, top + 1) if lost_at(keys, L)), default=0)
    first_clean = collide + 1
    thr = _prefix_collision_threshold(keys, first_clean)
    v, _ = verdict_at(keys, first_clean)
    cliffs[name] = {"collides_at": collide, "first_clean_fold": first_clean,
                    "threshold_there": thr, "verdict_there": v, "keys": len(keys)}
    print("   %-32s cliff at %3d -> first clean fold %3d, threshold %-12s verdict %s"
          % (name, collide, first_clean,
             ("%.3g" % thr) if thr else "-", v))

# ---------------------------------------------------------------- 4. his proposed replacement
print("\n4. HIS PROPOSAL, READ TWO WAYS -- because WHICH FOLD it is evaluated at decides everything.")
print("   (a) at the folds the contract reports, 8 and 12.")
print("   (b) at the CLIFF FOLD, which is what makes it fire on his live paths -- and needs an")
print("       instrument that looks past 12, which ours does not.")
print("%-32s %-9s %-12s %-12s %s" % ("population", "shipped", "(a) at 8/12", "(b) at cliff", "keys"))
MIN_KEYS = 20
proposal = {}
for name, keys in POPS.items():
    c = cliffs[name]
    at_fixed = False
    for F in (8, 12):
        below = max((x for x in range(1, F) if lost_at(keys, x)), default=0)
        if lost_at(keys, F) == 0 and F - below == 1 and len(keys) >= MIN_KEYS:
            at_fixed = True
    at_cliff = lost_at(keys, c["first_clean_fold"]) == 0 and len(keys) >= MIN_KEYS
    shipped_fires = bool(shipped[name]["at_cliff_edge"])
    proposal[name] = {"shipped_fires": shipped_fires, "at_fixed_folds": at_fixed,
                      "at_cliff_fold": at_cliff, "cliff_fold": c["first_clean_fold"]}
    print("%-32s %-9s %-12s %-12s %d" % (name, shipped_fires, at_fixed, at_cliff, len(keys)))
print("\n   Read (a), his rule fires nowhere except where a cliff happens to land on 8 or 12.")
print("   Read (b) it fires on B and C -- and also on D, whose cliff sits at fold %d. A cliff exists"
      % cliffs["D  unstructured (his control)"]["first_clean_fold"])
print("   somewhere in almost every store; what makes one worth a warning is that the fold the")
print("   store ACTUALLY USES sits next to it.")
print("\nVERDICT")
a = reach["A  session keys (hash-shaped)"]
b = reach["B  paths (structured)"]
c = reach["C  planted cliff (his control)"]
ok_control = bool(shipped["C  planted cliff (his control)"]["at_cliff_edge"])
print("   his planted cliff fires on our SHIPPED code   : %s" % ("YES -- the instrument works"
      if ok_control else "no -- suspect the fixture before the claim"))
print("   ZERO_AT_SCALE reachable on structured paths   : %s"
      % ("yes" if b["reachable"] else "NO, at no length 1-%d -- unsatisfiable, as he says" % b["scanned"]))
print("   ZERO_AT_SCALE reachable on a 3-key hash store : %s"
      % ("yes" if a["reachable"] else "NO -- saturation blocks it, a second and different silencer"))
print("   and before either argument is reached, the shipped contract measures folds 8 and 12 only,")
print("   so a cliff at %d is outside the instrument entirely."
      % cliffs["B  paths (structured)"]["collides_at"])

OUT.write_text(json.dumps({"version": inspeximus.__version__, "shipped": shipped,
                           "reachability": reach, "cliffs": cliffs, "proposal": proposal,
                           "control_fires": bool(ok_control)}, indent=1), encoding="utf-8")
print("\nwrote %s" % OUT.name)
