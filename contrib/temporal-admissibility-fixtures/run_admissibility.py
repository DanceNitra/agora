"""Run the candidate temporal-admissibility cases against any store, via a small binding.

CANDIDATE. Drafted from the six boundaries @safal207 named on anthropics/claude-code#34556, which
folded in the two @Stratogain proposed. Not accepted by anyone. inspeximus authored these cases and is
one of the implementations they grade, so nothing here is independent evidence about inspeximus.

THE INVARIANT, in @safal207's words: *historical evidence may remain valid without being admissible
evidence for the current session, current world-state, or current use.* The implementations can stay
completely different; what should interoperate is the falsification surface.

So this runner takes no position on how a store works. It replays a history of plain data steps
through a binding, asks one question, and compares a normalised {admissible, reason} against the
fixture. Six cases, each paired with a non-failure control.

FOUR RULES IT ENFORCES ON ITS OWN FIXTURE. Each is a defect we shipped or nearly shipped, and each is
checked before any score is reported:

  1. NO EXPECTATION WITHOUT A CITATION -- every case names the participant and the measurement it came
     from. An earlier conformance harness of ours derived expected verdicts by splitting case names on
     a hyphen and scored five false failures against a specification's own fixtures.
  2. NO CASE WITHOUT A PAIRED CONTROL -- @safal207's condition. `cries_wolf` (inadmissible for
     everything) passes every failure case, so without controls the whole set is satisfiable by a
     detector that is simply broken in the safe-looking direction.
  3. NO FIXTURE THAT HAS NEVER FAILED -- each case names degradations that must break it, and they are
     applied. A case that survives `always_admissible` is measuring nothing.
  4. NO CASE THAT NEVER REACHED ITS SUBJECT -- `reaches` is checked against what the binding reports
     consulting. A case satisfiable without touching the surface it names is the exact defect class
     these cases exist to find, and a suite that cannot tell "the property holds" from "the case never
     arose" has measured nothing.

TO RUN AGAINST YOUR OWN STORE, implement eight methods. (This said "six" and then listed seven,
omitting `collector_stops` -- which case T5 exercises and which both bindings had to implement. A
verification pass counted the AST rather than reading the prose. An interface described by hand and
never counted is the same defect one layer up from the ones this fixture is about.)

    class YourBinding:
        name = "your-store"
        def setup(self, workdir):                      -> handle
        def observe(self, h, *, doc, bytes_, session): -> None   # a session read these bytes
        def write(self, h, *, key, text, source, session): -> None
        def mutate_source(self, h, *, doc, bytes_):    -> None   # the world moves
        def delete_source(self, h, *, doc):            -> None
        def collector_stops(self, h):                  -> None   # the observation collector dies
        def verify(self, h, *, key, session):          -> None   # pin/checkpoint, if you have one
        def assess(self, h, *, key, window, session):  -> {"admissible": bool, "reason": str|None,
                                                           "consulted": [str]}

    python run_admissibility.py --binding your.module:YourBinding

`reason` must be one of the closed vocabulary in the fixture, or None. Return richer detail if you
like; map it onto exactly one code. That mapping IS the interoperable surface.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "admissibility-cases.json"
RESULT = HERE / "admissibility.result.json"


# ─────────────────────────────────────────────── the degradations rule 3 applies
def degrade(verdict: dict, how: str, question: dict) -> dict:
    """Return what a flattering implementation would have answered.

    These are applied to the BINDING'S OWN OUTPUT rather than to its internals, on purpose: a
    degradation expressed as "ignore this field of the answer" is portable across a Python store and
    a JS hook ledger, while one expressed as "skip this function" is not. The cost is that it models
    an implementation that computes the right thing and then discards it -- which is exactly the
    shape of every defect in this set, so the model fits the disease.
    """
    v = dict(verdict)
    if how == "always_admissible":
        return {**v, "status": "MATCH", "reason": None}
    if how == "cries_wolf":
        return {**v, "status": "DRIFT", "reason": v.get("reason")}
    ignore = {                       # (status, reason) pairs a degradation would flatten to MATCH
        "ignores_session": {("REVALIDATE", "source_observation_foreign_session")},
        "ignores_drift": {("DRIFT", None), ("ORPHAN", None)},
        "ignores_use_time": {("DRIFT", "source_drift_after_verification")},
        "ignores_collector_liveness": {("UNRESOLVABLE", "observation_collector_silent")},
        "normalises_identifiers": {("REVALIDATE", "source_observation_foreign_session")},
    }.get(how)
    if ignore is None:
        raise KeyError(f"unknown degradation {how!r}")
    if (v.get("status"), v.get("reason")) in ignore:
        return {**v, "status": "MATCH", "reason": None}
    return v


def replay(binding, handle, history):
    for s in history:
        k = s["step"]
        if k == "observe":
            binding.observe(handle, doc=s["doc"], bytes_=s["bytes"].encode(), session=s["session"])
        elif k == "write":
            binding.write(handle, key=s["key"], text=s["text"], source=s.get("source"),
                          session=s["session"])
        elif k == "mutate_source":
            binding.mutate_source(handle, doc=s["doc"], bytes_=s["bytes"].encode())
        elif k == "delete_source":
            binding.delete_source(handle, doc=s["doc"])
        elif k == "verify":
            binding.verify(handle, key=s["key"], session=s["session"])
        elif k == "collector_stops":
            binding.collector_stops(handle)
        elif k in ("advance_session", "advance_clock"):
            pass                     # both are expressed by the session/order of later steps
        else:
            raise KeyError(f"unknown step {k!r}; the fixture and the runner disagree")


def ask(binding, history, question, workdir):
    h = binding.setup(workdir)
    replay(binding, h, history)
    v = binding.assess(h, key=question["key"], window=question["window"],
                       session=question["session"])
    return {"status": v.get("status"), "reason": v.get("reason"),
            "consulted": list(v.get("consulted") or [])}


# ─────────────────────────────────────────────── the four rules, before any score
def audit_the_fixture(fx) -> list:
    problems = []
    vocab = {k for k in fx["reasons_this_set_proposes"] if not k.startswith("_")} | {None}
    statuses = {k for k in fx["status_vocabulary"] if not k.startswith("_")}
    known = set(fx["flattering_implementations"])
    seen = set()
    for c in fx["cases"]:
        cid = c.get("id", "<unnamed>")
        if cid in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(cid)
        if not c.get("from", "").strip():                                    # RULE 1
            problems.append(f"{cid}: no citation -- refused, not scored")
        if "control" not in c:                                               # RULE 2
            problems.append(f"{cid}: no paired control")
        elif (c["control"].get("expect") or {}).get("status") != "MATCH":
            # RULE 5, and it caught two of the first six. A "control" that expects INADMISSIBLE is a
            # second failure case wearing the control's name: `cries_wolf` passes the pair, which is
            # the exact thing @safal207 asked for paired NON-failure controls to prevent. Such a
            # scenario is still useful -- it becomes `discriminates`, which is scored separately.
            problems.append(f"{cid}: the control must expect MATCH, so it is a second failure "
                            f"case, not a control. Move it to `discriminates` and add a real one.")
        if (c.get("expect") or {}).get("status") == "MATCH":                  # RULE 5b
            problems.append(f"{cid}: the CASE must not expect MATCH; a case whose expectation is "
                            f"already the flattering answer cannot be broken by a degradation.")
        if c.get("reaches") and c["reaches"] not in fx.get("surface_vocabulary", {}):
            problems.append(f"{cid}: reaches {c['reaches']!r} is not in surface_vocabulary, so no "
                            f"foreign implementation can know what to report")
        if not c.get("must_fail_under"):                                     # RULE 3
            problems.append(f"{cid}: names no degradation it must fail under")
        for d in c.get("must_fail_under", []):
            if d not in known:
                problems.append(f"{cid}: unknown degradation {d!r}")
        if not c.get("reaches", "").strip():                                 # RULE 4
            problems.append(f"{cid}: does not declare what it reaches")
        for where, blk in (("case", c), ("control", c.get("control", {}))):
            e = blk.get("expect") or {}
            if e.get("reason") not in vocab:
                problems.append(f"{cid} [{where}]: reason {e.get('reason')!r} is not one this set "
                                f"proposes; a new reason needs a rationale beside the others")
            if e.get("status") not in statuses:
                problems.append(f"{cid} [{where}]: status {e.get('status')!r} is not one of CML's six")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binding", required=True, help="module:Class implementing the six methods")
    ap.add_argument("--json", action="store_true", help="write admissibility.result.json")
    a = ap.parse_args(argv)

    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))

    print("=" * 92)
    print("TEMPORAL ADMISSIBILITY -- candidate cases.  " + fx["status"].split(".")[0] + ".")
    print("Authored by an interested party: " + fx["authored_by"].split(".")[0] + ".")
    print("=" * 92)

    bad = audit_the_fixture(fx)
    if bad:
        print("\nTHE FIXTURE ITSELF IS REFUSED -- no score is reported:")
        for p in bad:
            print("  - " + p)
        return 2
    print(f"\nfixture audit: {len(fx['cases'])} case(s), each cited, controlled, "
          f"degradation-named and reach-declared.\n")

    mod, _, cls = a.binding.partition(":")
    binding = getattr(importlib.import_module(mod), cls)()
    rows, fails = [], 0

    for c in fx["cases"]:
        with tempfile.TemporaryDirectory() as d:
            got = ask(binding, c["history"], c["question"], d)
        want = c["expect"]
        ok = got["status"] == want["status"] and got["reason"] == want["reason"]

        with tempfile.TemporaryDirectory() as d:
            cgot = ask(binding, c["control"]["history"], c["control"]["question"], d)
        cwant = c["control"]["expect"]
        cok = cgot["status"] == cwant["status"] and cgot["reason"] == cwant["reason"]

        # RULE 4 -- did the binding actually consult the surface this case names?
        reached = c["reaches"] in got["consulted"]

        # RULE 3 -- every named degradation must break the case, and cries_wolf must break the control.
        survived = [d for d in c["must_fail_under"]
                    if degrade(got, d, c["question"]) == {"status": want["status"],
                                                          "reason": want["reason"],
                                                          "consulted": got["consulted"]}]
        wolf = degrade(cgot, "cries_wolf", c["control"]["question"])
        wolf_caught = not (wolf["status"] == cwant["status"] and wolf["reason"] == cwant["reason"])

        # OPTIONAL discrimination: does the detector tell two adjacent failure modes apart, or
        # report them identically? Same-verdict-different-remedy is the quiet way a report stops
        # being actionable, so it is scored rather than described.
        dok, dgot, dwant = True, None, None
        if "discriminates" in c:
            with tempfile.TemporaryDirectory() as d:
                dgot = ask(binding, c["discriminates"]["history"], c["discriminates"]["question"], d)
            dwant = c["discriminates"]["expect"]
            dok = dgot["status"] == dwant["status"] and dgot["reason"] == dwant["reason"]

        good = ok and cok and dok and reached and not survived and wolf_caught
        fails += 0 if good else 1
        print(f"[{'PASS' if good else 'FAIL'}] {c['id']}")
        print(f"        case    : {got['status']}/{got['reason']}   want "
              f"{want['status']}/{want['reason']}" + ("" if ok else "   <-- MISMATCH"))
        print(f"        control : {cgot['status']}/{cgot['reason']}   want "
              f"{cwant['status']}/{cwant['reason']}" + ("" if cok else "   <-- CRIES WOLF"))
        if dgot is not None:
            print(f"        discrim : {dgot['status']}/{dgot['reason']}   want "
                  f"{dwant['status']}/{dwant['reason']}" + ("" if dok else "   <-- LUMPED"))
        if not reached:
            print(f"        REACH   : never consulted {c['reaches']!r} -- consulted "
                  f"{got['consulted']}. A pass here would be for the wrong reason.")
        if survived:
            print(f"        VACUITY : survives {survived} -- a degradation that should have broken it")
        if not wolf_caught:
            print(f"        CONTROL : cries_wolf was not caught by the paired control")
        rows.append({"id": c["id"], "pass": good, "case": got, "control": cgot,
                     "discriminates": dgot, "reached": reached,
                     "survived_degradations": survived})

    print("\n" + "=" * 92)
    print(f"{len(rows) - fails}/{len(rows)} cases pass for {binding.name}")
    print("A pass is not a certificate. These cases are candidates, authored by one of the")
    print("implementations they grade, and they measure a falsification surface -- not correctness.")
    if a.json:
        RESULT.write_text(json.dumps(
            {"binding": binding.name, "fixture": FIXTURE.name, "rows": rows}, indent=2), encoding="utf-8")
        print(f"wrote {RESULT.name}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
