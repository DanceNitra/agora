"""Does our source fingerprint bind the bytes the agent OBSERVED, or the bytes at write time?

WHERE THIS COMES FROM. anthropics/claude-code#34556. safal207 found that OmniMemory recorded
`git rev-parse HEAD:<path>` -- the COMMITTED blob -- while an agent mid-session reads the WORKING
TREE. HEAD says A, the agent read B, provenance recorded A: the locator resolves perfectly, to the
wrong observation. Fixed there in 0.9.25 with `git hash-object`. He then named the distinction that
matters and asked for it as two independent metrics:

    refetchability      can the source be resolved again?
    observation binding does provenance identify the exact bytes the agent actually observed?

WE NEVER HAD THE GIT VERSION OF THE BUG -- we hash the file on disk, which IS the working tree. So
the first instinct is that this does not apply to us. It does, one layer in: we hash at WRITE time,
and an agent reads, reasons, and only then calls remember(). Anything that touches the file in
between is recorded as though it were the observation.

WHAT IS MEASURED:
  1. Read a file (A). Change it to B. Write the memory. Whose digest is recorded?
  2. What does check_sources() then say? A wrong-but-resolvable fingerprint reporting FRESH is worse
     than no fingerprint: it is false confidence rather than an absence.
  3. Can a caller supply the bytes it actually read? (If not, the property is unreachable, not
     merely unset.)

WHAT WOULD MAKE THE RESULT BAD, stated before running:
  BAD = the recorded digest is the write-time one AND check_sources reports FRESH.
  Also BAD, in the other direction = a caller who DOES supply the observed bytes still cannot get an
  honest verdict, i.e. the fix is unreachable from the API.

CONTROLS, because "we already do this" was my first answer and it was wrong twice:
  * The fingerprint is NOT in `source` -- it lives in reserved meta so the writer cannot forge it. My
    first probe looked in `source`, found nothing, and I nearly reported a gap we do not have.
  * An honest capture (file unchanged between read and write) must report FRESH, or the harness is
    measuring a broken fingerprint rather than a wrong one.
  * A store where nothing is checkable must NOT report ok -- inspeximus already refuses to let "0
    drifted over 0 checked" read like a clean store, and that must survive any change here.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "inspeximus-repo"))

from inspeximus import Inspeximus                    # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _store(d):
    return Inspeximus(path=os.path.join(d, "s.json"), receipts=True)


def main() -> int:
    out = {}

    # ── 1. the gap ───────────────────────────────────────────────────────────────────────────
    d = tempfile.mkdtemp()
    f = os.path.join(d, "cfg.py")
    open(f, "w").write("value='A'")
    observed = _sha(open(f, "rb").read())            # what the agent actually read
    ix = _store(d)
    open(f, "w").write("value='B'")                  # the file moves before the memory is written
    at_write = _sha(open(f, "rb").read())
    ix.remember("the config sets value to A", key="cfg", object="A", source={"doc": f})
    got = (ix.items[0].get("meta") or {}).get("source_sha256")
    counts = ix.check_sources()["counts"]

    out["binds_observed"] = got == observed
    out["binds_write_time"] = got == at_write
    out["reports_fresh"] = counts.get("FRESH", 0) == 1
    print("  1. read A, file becomes B, then remember()")
    print(f"     observed by the agent : {observed[:16]}")
    print(f"     file at write time    : {at_write[:16]}")
    print(f"     RECORDED              : {(got or '')[:16]}"
          f"   -> {'observed' if out['binds_observed'] else 'write-time' if out['binds_write_time'] else '?'}")
    print(f"     check_sources         : {counts}"
          f"{'   <-- FRESH over bytes that never produced this memory' if out['reports_fresh'] and not out['binds_observed'] else ''}")

    # ── 2. is the fix even reachable from the API? ───────────────────────────────────────────
    import inspect
    sig = str(inspect.signature(Inspeximus.remember))
    out["api_accepts_observed"] = "observed" in sig
    d2 = tempfile.mkdtemp()
    f2 = os.path.join(d2, "cfg.py")
    open(f2, "w").write("value='A'")
    obs2 = _sha(open(f2, "rb").read())
    iy = _store(d2)
    open(f2, "w").write("value='B'")
    try:
        iy.remember("claims A", key="c", object="A",
                    source={"doc": f2, "observed_sha256": obs2})
        stored = (iy.items[0].get("meta") or {}).get("source_sha256")
        out["source_dict_route_binds"] = stored == obs2
    except Exception as e:
        out["source_dict_route_binds"] = f"{type(e).__name__}"
    print(f"\n  2. can the caller supply what it read?")
    print(f"     remember(observed_...) parameter : {out['api_accepts_observed']}")
    print(f"     via source={{'observed_sha256'}}   : {out['source_dict_route_binds']}")

    # ── 3. the controls ──────────────────────────────────────────────────────────────────────
    d3 = tempfile.mkdtemp()
    f3 = os.path.join(d3, "cfg.py")
    open(f3, "w").write("value='A'")
    iz = _store(d3)
    iz.remember("cfg sets A", key="cfg", object="A", source={"doc": f3})
    honest = iz.check_sources()
    out["honest_capture_fresh"] = honest["counts"].get("FRESH") == 1
    open(f3, "w").write("value='CHANGED'")
    out["real_drift_caught"] = iz.check_sources()["counts"].get("DRIFTED") == 1

    d4 = tempfile.mkdtemp()
    iw = _store(d4)
    iw.remember("x", key="k", source={"doc": "agent:scholar"})     # a writer, not a document
    nothing = iw.check_sources()
    out["vacuous_check_refuses_ok"] = nothing["ok"] is False

    print(f"\n  3. controls")
    print(f"     honest capture reports FRESH        : {out['honest_capture_fresh']}")
    print(f"     a real later edit reports DRIFTED   : {out['real_drift_caught']}")
    print(f"     nothing checkable does NOT read ok  : {out['vacuous_check_refuses_ok']}")

    # ── 4. the four states, once the caller CAN speak ────────────────────────────────────────
    print()
    print("  4. all four states")
    import hashlib as _h

    def case(label, supply, move):
        dd = tempfile.mkdtemp()
        ff = os.path.join(dd, "cfg.py")
        open(ff, "w").write("value='A'")
        o = _h.sha256(open(ff, "rb").read()).hexdigest()
        st = _store(dd)
        if move:
            open(ff, "w").write("value='B'")
        src = {"doc": ff}
        if supply:
            src["observed_sha256"] = o
        st.remember("the config sets value to A", key="cfg", object="A", source=src)
        rep = st.check_sources()
        return ({k: v for k, v in rep["counts"].items() if v}, rep["ok"],
                rep["coverage"]["observation_binding_coverage"])

    states = {
        "no observed, unchanged":      case("", False, False),
        "no observed, moved first":    case("", False, True),
        "observed, unchanged":         case("", True, False),
        "observed, MOVED before write": case("", True, True),
    }
    for lab, (c, ok, bnd) in states.items():
        print(f"     {lab:30s} {str(c):26s} ok={str(ok):5s} bound={bnd}")
    out["states"] = {k: [v[0], v[1], v[2]] for k, v in states.items()}

    caught = states["observed, MOVED before write"][1] is False
    honest_gap = states["no observed, moved first"][2] == 0.0
    out["moved_capture_caught"] = caught
    out["unclaimed_binding_reported_as_zero"] = honest_gap

    print()
    if not (out["honest_capture_fresh"] and out["real_drift_caught"]
            and out["vacuous_check_refuses_ok"]):
        verdict = "INCONCLUSIVE"
        print("INCONCLUSIVE: a control failed, so the fingerprint is broken generally and nothing")
        print("above is specifically about observation binding.")
    elif caught and honest_gap:
        verdict = "SPLIT"
        print("SPLIT: refetchability and observation binding are now two numbers.")
        print("A caller that says what it read gets bound, and a capture whose source had already")
        print("moved is UNBOUND_CAPTURE rather than FRESH -- neither of the other verdicts fits, and")
        print("the remedy differs: re-read and re-capture, not re-derive.")
        print()
        print("THE HONEST LIMIT, row 2: with no claim from the caller we cannot detect that the file")
        print("moved between the read and the write -- the information is not ours to have. What we")
        print("no longer do is imply otherwise: observation_binding_coverage reports 0.0 there.")
    else:
        verdict = "WRITE-TIME-BOUND"
        print("WRITE-TIME-BOUND: still reporting one claim as if it were both.")
    json.dump({"verdict": verdict, **out},
              open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
