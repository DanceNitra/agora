"""@safal207 says the population threshold and the character headroom can disagree. Do they, on our code?

HIS CLAIM, from anthropics/claude-code#34556: on a heavily prefixed population the statistical
threshold confidently returns ZERO_AT_SCALE -- "we have enough data to prove this fold does not
collide" -- while the character headroom correctly warns that one character less would collapse
everything. He gives two: 50,000 monorepo paths sharing a 20-character prefix with a 21-character
fold, and 10,000 ULIDs minted in one millisecond sharing a 10-character timestamp with an
11-character fold.

THE PREDICTION MADE BEFORE RUNNING THIS, so it can be wrong in public: in both of his cases the fold
sits ONE character past the shared prefix, which leaves a single distinguishing character for tens of
thousands of keys. They therefore COLLIDE, and this library reports COST_MEASURED -- a measured
collision outranks the model, so the threshold never gets to say ZERO_AT_SCALE and the false comfort
he describes cannot arise here. If that holds, his mechanism is real but his examples land one
character short of demonstrating it, and the dangerous case is a fold just PAST the cliff rather than
on it.

FIDELITY. The shipped `identifier_contract()` offers prefix_8 and prefix_12, so his structure is
reproduced at those lengths rather than at 21 and 11 -- shared prefix of L-1 characters, unique
suffix after. Scaling the length keeps the structure (one distinguishing character) and lets the
SHIPPED function be measured instead of a reimplementation of it. The length sweep beneath uses the
same shipped threshold helper.

CONTROLS:
  * CONSTRUCTION -- the shared prefix of each population is MEASURED, not assumed. A generator that
    quietly failed to share a prefix would make every verdict below meaningless and look identical.
  * POSITIVE -- a population where ZERO_AT_SCALE is genuinely correct, so "we never saw that verdict"
    cannot be mistaken for "the verdict is unreachable".
  * PRECEDENCE -- an explicit check that a measured collision outranks the model, which is the whole
    reason his case may not reproduce.

Run: python probes/the_population_threshold_and_the_character_cliff_disagree.py
"""
from __future__ import annotations

import itertools
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
from inspeximus import Inspeximus                                      # noqa: E402
from inspeximus.core import _prefix_collision_threshold                # noqa: E402

OUT = pathlib.Path(__file__).with_suffix(".result.json")
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"                               # Crockford, as ULID uses


def shared_prefix_len(keys) -> int:
    """MEASURED, not assumed: how many leading characters every key really has in common."""
    a, b = min(keys), max(keys)
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def lost_at(keys, length: int) -> int:
    g: dict = {}
    for k in keys:
        g.setdefault(k[:length], []).append(k)
    return sum(len({*v}) - 1 for v in g.values() if len({*v}) > 1)


def store_of(keys):
    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), embed=False)
    for i, k in enumerate(keys):
        ix.remember("record %d" % i, key=k)
    ix.flush()
    return ix


def main() -> int:
    rng = random.Random(20260819)

    # ---- his two populations, structure preserved, scaled to the folds the product ships
    #      monorepo: a shared directory prefix, then a component name -- fold = prefix + 1 character
    mono = ["src/co/%s/index.ts" % "".join(rng.choice(string.ascii_letters) for _ in range(8))
            for _ in range(4000)]
    mono = sorted(set(mono))
    #      ULID burst: one millisecond of timestamp, then randomness
    ts = "01JBKQ8V"                                                    # 8 chars of shared timestamp
    ulid = sorted({ts + "".join(rng.choice(B32) for _ in range(18)) for _ in range(4000)})
    #      a population where ZERO_AT_SCALE is genuinely right: short keys over a tiny alphabet
    binary = ["".join(b) for b in itertools.islice(itertools.product("01", repeat=8), 60)]
    #      and one with no structure at all, for contrast
    uuidish = sorted({"".join(rng.choice("0123456789abcdef") for _ in range(32)) for _ in range(4000)})

    pops = {"monorepo paths": mono, "ULID burst": ulid,
            "binary alphabet (positive control)": binary, "unstructured hex": uuidish}

    print("CONSTRUCTION CONTROL -- the shared prefix is measured, not assumed")
    print("%-36s %-8s %-16s %s" % ("population", "keys", "shared prefix", "example"))
    built = {}
    for name, keys in pops.items():
        sp = shared_prefix_len(keys)
        built[name] = dict(keys=len(keys), shared_prefix=sp, example=keys[0])
        print("%-36s %-8d %-16d %s" % (name, len(keys), sp, keys[0][:44]))
    assert built["monorepo paths"]["shared_prefix"] >= 6, "the monorepo population lost its prefix"
    assert built["ULID burst"]["shared_prefix"] >= 8, "the ULID population lost its timestamp"
    assert built["unstructured hex"]["shared_prefix"] <= 2, "the contrast population is not unstructured"

    # ---- the SHIPPED function, on the folds it ships
    print("\nTHE SHIPPED identifier_contract(), prefix_8 and prefix_12")
    print("%-36s %-9s %-24s %-8s %-7s %-6s %s"
          % ("population", "fold", "verdict", "lost", "thresh", "sat", "headroom"))
    report = {}
    for name, keys in pops.items():
        c = store_of(keys).identifier_contract()
        for fold in ("prefix_8", "prefix_12"):
            m = c["measured"][fold]
            report["%s|%s" % (name, fold)] = dict(
                verdict=m["verdict"], lost=m["keys_that_would_be_lost"],
                threshold=m.get("threshold_population"), saturated=m.get("positions_saturated"),
                collides_at=m.get("collides_at_length"), headroom=m.get("headroom_chars"))
            print("%-36s %-9s %-24s %-8d %-7s %-6s %s"
                  % (name, fold, m["verdict"], m["keys_that_would_be_lost"],
                     m.get("threshold_population"), m.get("positions_saturated"),
                     m.get("headroom_chars")))

    # ---- PRECEDENCE CONTROL: does a measured collision really outrank a permissive threshold?
    both = [(k, v) for k, v in report.items() if v["lost"] > 0]
    ok = all(v["verdict"] == "COST_MEASURED" for _k, v in both)
    permissive = [(k, v) for k, v in both if v["threshold"] is not None and v["threshold"] <= built[k.split("|")[0]]["keys"]]
    print("\nPRECEDENCE CONTROL: %d cells collide; all report COST_MEASURED: %s" % (len(both), ok))
    print("   of those, %d ALSO sit above their own threshold -- the cells where the model alone "
          "would have said ZERO_AT_SCALE" % len(permissive))
    for k, v in permissive[:6]:
        print("      %-46s thresh %-7s keys %s" % (k, v["threshold"], built[k.split("|")[0]]["keys"]))
    assert ok, "a collision was reported as anything other than COST_MEASURED"

    # ---- does ZERO_AT_SCALE with a one-character headroom exist at all? sweep the fold length
    print("\nSWEEPING THE FOLD LENGTH with the shipped threshold helper, to find the cliff")
    print("%-36s %-6s %-8s %-9s %-11s %s" % ("population", "fold", "lost", "thresh", "verdict", "headroom"))
    sweep = {}
    for name in ("monorepo paths", "ULID burst"):
        keys = pops[name]
        for L in range(6, 20):
            lost = lost_at(keys, L)
            thr = _prefix_collision_threshold(keys, L)
            sat = sum(1 for i in range(L)
                      if len({(k[i] if i < len(k) else "") for k in keys}) >= len({*keys}))
            if lost:
                verdict = "COST_MEASURED"
            elif sat or len(keys) < thr:
                verdict = "NOT_YET_MEASURABLE"
            else:
                verdict = "ZERO_AT_SCALE"
            collides_at = max((x for x in range(1, L) if lost_at(keys, x)), default=0)
            sweep["%s|%d" % (name, L)] = dict(lost=lost, threshold=thr, verdict=verdict,
                                              headroom=L - collides_at)
            if L <= 16:
                print("%-36s %-6d %-8d %-9d %-11s %d"
                      % (name, L, lost, thr, verdict, L - collides_at))

    danger = {k: v for k, v in sweep.items() if v["verdict"] == "ZERO_AT_SCALE" and v["headroom"] <= 2}
    print("\nCELLS WHERE HIS DISAGREEMENT IS REAL -- ZERO_AT_SCALE with two characters or less of "
          "headroom: %d" % len(danger))
    for k, v in sorted(danger.items())[:8]:
        print("   %-30s headroom %d, threshold %d" % (k, v["headroom"], v["threshold"]))

    OUT.write_text(json.dumps(dict(construction=built, shipped=report, sweep=sweep,
                                   danger=sorted(danger)), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
