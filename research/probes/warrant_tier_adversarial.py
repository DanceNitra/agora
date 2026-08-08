"""Can a WRITER set our top warrant tier directly? (adversarial extension)

`warrant_tier_semantics.py` passed 5/5 — and it could not have failed on the two things that matter.
It never set `mtype` at write time and never enabled either hardening flag, so it exercised only the
paths that behave. A probe that cannot reach the defect reports SAFE, which is the failure this repo
keeps paying for; here it happened inside the validation for a reply about that very failure.

WHAT THIS TESTS, all by execution against the installed library:

  A1  remember(text, mtype="semantic") -> does the record report `earned` with ZERO outcome credit,
      ZERO corroboration and NO lineage? If yes, our TOP tier is writer-settable in one call, which
      fails the Biba test ("integrity requires a label the writer cannot set") that we invoked
      publicly on openclaw#7707 one hour before drafting the reply.
  A2  with credit_requires_warrant=True, does a SELF-GRADED record (good=3, good_warranted=0) still
      report `earned`? The draft claimed this flag makes only warranted good count toward the tier.
  A3  the control: does the flag work where it IS wired (graduation), so we describe its real scope
      rather than calling it broken?
  A4  does the code carry a marker that WOULD distinguish an earned semantic from a declared one
      (meta['graduated_from_episodic']), i.e. is the fix available rather than hypothetical?

Exit 1 if the top tier turns out to be writer-settable. That is the answer we need before replying,
in whichever direction it comes out.

Run: python -X utf8 research/probes/warrant_tier_adversarial.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from inspeximus import Inspeximus

FINDINGS: list[str] = []


def tier(store, query: str, needle: str):
    for h in store.recall(query, k=10, with_warrant=True):
        if needle in (h.get("text") or ""):
            return h.get("warrant")
    return None


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="warradv_"))

    # ---- A1: is `semantic` settable at write time, and does it alone confer `earned`? ----------
    print("A1 — remember(..., mtype='semantic'), no credit, no corroboration, no lineage")
    s1 = Inspeximus(path=str(tmp / "a1.json"))
    try:
        rid = s1.remember("the vault master key rotates every 90 days", mtype="semantic")
        accepted = True
    except Exception as ex:
        accepted = False
        rid = None
        print(f"  remember(mtype='semantic') REJECTED: {type(ex).__name__}: {ex}")
    if accepted:
        rec = next((r for r in s1.items if r.get("id") == rid), None)
        t = tier(s1, "vault master key rotation", "master key")
        print(f"  accepted at write time: mtype={rec.get('mtype')!r}  good={rec.get('good')} "
              f"bad={rec.get('bad')}  links={rec.get('links')!r}")
        print(f"  reported tier: {t!r}")
        if t == "earned":
            FINDINGS.append("A1 the TOP tier `earned` is settable by the writer in one call "
                            "(remember(mtype='semantic')) with no credit, corroboration or lineage")
        marker = (rec.get("meta") or {}).get("graduated_from_episodic")
        print(f"  meta['graduated_from_episodic'] on this declared record: {marker!r}")

    # ---- A2: does credit_requires_warrant gate the TIER? ---------------------------------------
    print("\nA2 — credit_requires_warrant=True with SELF-GRADED credit (good=3, good_warranted=0)")
    try:
        s2 = Inspeximus(path=str(tmp / "a2.json"), credit_requires_warrant=True)
        flag_ok = True
    except TypeError as ex:
        s2 = Inspeximus(path=str(tmp / "a2.json"))
        setattr(s2, "credit_requires_warrant", True)
        flag_ok = False
        print(f"  (ctor kwarg unavailable: {ex}; set as attribute instead)")
    print(f"  store.credit_requires_warrant = {getattr(s2, 'credit_requires_warrant', None)!r}"
          f"{'' if flag_ok else '  [set post-hoc]'}")
    rid2 = s2.remember("the beta queue runs on redis")
    r2 = next(r for r in s2.items if r.get("id") == rid2)
    r2["good"] = 3.0
    r2["bad"] = 0.0
    r2["good_warranted"] = 0.0            # self-graded: NO exogenous warrant behind the credit
    s2._save()
    t2 = tier(s2, "beta queue redis", "beta queue")
    print(f"  good=3 good_warranted=0 -> reported tier: {t2!r}")
    if t2 == "earned":
        FINDINGS.append("A2 credit_requires_warrant does NOT gate the warrant TIER: a self-graded "
                        "record (good_warranted=0) still reports `earned` with the flag ON")

    # ---- A3: control — does the flag do what it WAS built for? ----------------------------------
    print("\nA3 — control: the same flag on the path it was built for (graduation)")
    try:
        by_id = {r.get("id"): r for r in s2.items}
        grad = s2._graduation_corroborated(r2, by_id)
        print(f"  _graduation_corroborated(self-graded record) with flag ON -> {grad!r}")
        if grad is False:
            print("  control PASSES: the flag DOES block graduation, so its scope is real "
                  "but does not reach the tier label.")
        else:
            print("  control did not fire; the flag's scope needs re-checking before we describe it.")
    except Exception as ex:
        print(f"  control unavailable: {type(ex).__name__}: {ex}")

    # ---- A4: is the distinguishing marker actually present on a genuinely graduated record? -----
    print("\nA4 — does the code stamp a marker that could distinguish earned-semantic from declared?")
    src = Path("C:/Users/Danculus/inspeximus-repo/inspeximus/core.py").read_text(
        encoding="utf-8", errors="replace")
    has_marker = "graduated_from_episodic" in src
    uses_good_earned_in_tier = "_good_earned" in src.split("_o[\"warrant\"] = \"earned\"")[0][-600:] \
        if "_o[\"warrant\"] = \"earned\"" in src else False
    print(f"  'graduated_from_episodic' present in core.py: {has_marker}")
    print(f"  tier branch consults _good_earned: {uses_good_earned_in_tier}")

    print("\n" + ("FINDINGS — the draft is WRONG on %d point(s):\n  " % len(FINDINGS)
                  + "\n  ".join(FINDINGS) if FINDINGS else
                  "No writer-settable path to the top tier found; the draft's claims hold."))
    return 1 if FINDINGS else 0


if __name__ == "__main__":
    raise SystemExit(main())
