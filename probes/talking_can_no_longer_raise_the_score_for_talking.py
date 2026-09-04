"""Can the seminar still raise its own ROI by producing more seminar output?

WHY. For 79 days the brain's largest spender scored itself. `seminar.value_points()` read 1 point
per grounded contribution and 2 per verified one out of `.contributions.json`, a file the seminar
writes. More talk meant more points, so the metabolism reported a healthy ROI and the churn
detector, which exists to flag an organ that grows in spend but not in value, never fired. Three
separate rewrites of the seminar left that formula alone, which is why none of them bit.

WHAT THIS CHECKS, on a COPY of the live ledgers, never the live ones:
  1. THE SELF-SCORE IS GONE. Appending 500 fresh grounded and verified contributions must not move
     the score. Under the old formula the same append is worth 1,500 points.
  2. THE SCORE STILL RESPONDS TO REAL USE. Citing one contribution id from a downstream ledger must
     raise it. A metric that never moves is not stricter, it is dead, and would pass check 1 too.
  3. THE SEARCH CAN SEE A REFERENCE AT ALL. Lab ids are the positive control: same short-hex shape,
     and they really are cited downstream. If the scan cannot find those, it cannot find anything
     and every zero it reports is void. This control already caught one broken run of this probe,
     where a `len(id) > 6` filter silently excluded every 6-character lab id.
  4. THE LIVE NUMBER. Reported, not asserted: how many of our real contributions any organ cites.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "server")
OUT = os.path.join(HERE, "talking_can_no_longer_raise_the_score_for_talking.result.json")

sys.path.insert(0, SERVER)


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def old_formula(contribs):
    """The formula this probe exists to keep dead."""
    return float(sum(1 for c in contribs if c.get("grounded"))
                 + 2 * sum(1 for c in contribs if c.get("verified")))


def main():
    from agora.execution import seminar

    live_contrib = os.path.join(SERVER, ".contributions.json")
    if not os.path.isfile(live_contrib):
        refuse("no .contributions.json, so this check would pass by measuring nothing")

    contribs = json.load(io.open(live_contrib, encoding="utf-8"))
    print("  live contributions: %d" % len(contribs))

    # CONTROL 3 first: if the scan is blind, nothing below means anything.
    lab = json.load(io.open(os.path.join(SERVER, ".lab.json"), encoding="utf-8"))
    lab = lab if isinstance(lab, list) else list(lab.values())
    lab_ids = {str(r["id"]) for r in lab if isinstance(r, dict) and r.get("id")
               and len(str(r["id"])) >= 6}
    seen_in = []
    for n in seminar._DOWNSTREAM:
        p = os.path.join(SERVER, ".%s.json" % n)
        if not os.path.isfile(p):
            continue
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        if any(i in txt for i in lab_ids):
            seen_in.append(n)
    print("  CONTROL: %d lab ids are cited in %d downstream ledger(s): %s"
          % (len(lab_ids), len(seen_in), ", ".join(seen_in[:8])))
    if not seen_in:
        refuse("the downstream scan finds no lab id either, so it cannot see a citation and every "
               "zero it reports is void")

    live = seminar.value_points()
    consumed = seminar._consumed_ids()
    print("  LIVE SCORE: %.1f  (%d of %d contributions cited by another organ)"
          % (live, len(consumed), len(contribs)))
    print("  the retired formula would score the same file: %.1f" % old_formula(contribs))

    # Work on a copy. The live ledgers are never written by this probe.
    tmp = tempfile.mkdtemp(prefix="seminar_value_")
    for n in list(seminar._DOWNSTREAM) + ["contributions", "topics", "lab"]:
        src = os.path.join(SERVER, ".%s.json" % n)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(tmp, ".%s.json" % n))
    from pathlib import Path
    seminar._SERVER = Path(tmp)
    seminar._CONTRIB = Path(tmp) / ".contributions.json"
    seminar._consumed_cache["key"] = None
    base = seminar.value_points()

    # CHECK 1: 500 more perfect contributions must be worth nothing.
    grown = contribs + [{"id": "zz%06d" % i, "claim": "a fresh grounded claim %d" % i,
                         "grounded": True, "verified": True, "topic": "t", "ts": 0}
                        for i in range(500)]
    json.dump(grown, io.open(seminar._CONTRIB, "w", encoding="utf-8"))
    seminar._consumed_cache["key"] = None
    after_talk = seminar.value_points()
    old_gain = old_formula(grown) - old_formula(contribs)
    print()
    print("  CHECK 1  500 new grounded+verified contributions:")
    print("           new metric %.1f -> %.1f   (gain %.1f)" % (base, after_talk, after_talk - base))
    print("           old metric would have gained %.1f" % old_gain)
    if after_talk != base:
        refuse("producing 500 contributions moved the score by %.1f; the organ can still pay itself"
               % (after_talk - base))
    if old_gain <= 0:
        refuse("the retired formula gained nothing either, so this fixture cannot tell the two "
               "apart and check 1 proves nothing")

    # CHECK 2: one real downstream citation must move it.
    cited = str(grown[0]["id"])
    canon = os.path.join(tmp, ".canon.json")
    body = json.load(io.open(canon, encoding="utf-8")) if os.path.isfile(canon) else []
    if isinstance(body, list):
        body.append({"id": "probe", "text": "builds on contribution %s" % cited})
    else:
        body["probe"] = "builds on contribution %s" % cited
    json.dump(body, io.open(canon, "w", encoding="utf-8"))
    seminar._consumed_cache["key"] = None
    after_use = seminar.value_points()
    print()
    print("  CHECK 2  one contribution cited from .canon.json:")
    print("           %.1f -> %.1f   (gain %.1f)" % (after_talk, after_use, after_use - after_talk))
    if after_use <= after_talk:
        refuse("a real downstream citation did not raise the score; the metric is dead, not strict")

    print()
    print("  VERDICT: the seminar cannot pay itself, and real use still pays.")
    json.dump({"script": os.path.basename(__file__),
               "live_contributions": len(contribs),
               "live_score": live, "live_consumed": len(consumed),
               "retired_formula_on_same_file": old_formula(contribs),
               "check_1_talk_gain": after_talk - base,
               "check_1_retired_formula_gain": old_gain,
               "check_2_citation_gain": after_use - after_talk,
               "control_lab_ids_found_in": seen_in,
               "verdict": "SELF_SCORING_REMOVED"},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
