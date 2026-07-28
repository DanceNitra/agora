"""For EVERY write path: does a right-to-erasure request reach what it wrote?

One path at a time is how this month went — remember, then remember_decision, then route, each found by
asking the same question again. The systematic version asks it once, of everything that writes.

The shape that matters is not "does the path take a `source` parameter". It is: a subject's record exists,
the path writes something about that subject, and then `forget_subject(subject)` runs. Whatever survives
holding the subject's data is a defect, regardless of which parameter was or was not available.

Two ways a path can be fine:
  CALLER   the path takes a source and the caller supplied one
  OWNED    the path derives from a record it knows, and the cascade travels the edge

And one way it can be fine for a boring reason: it writes nothing at all.

Read-only. Measured on local HEAD.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

SUBJ = "hr/alice"
SECRET = "9OakAve"


def fresh(**kw):
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True, **kw)


def seeded():
    """A store already holding one record attributable to the subject."""
    m = fresh()
    rid = m.remember("alice home address is 5 Elm St", key="alice::addr", object="5 Elm St",
                     source={"doc": SUBJ})
    return m, rid


def survives(m):
    return any(SECRET in (r.get("text") or "") + str(r.get("object") or "")
               for r in m.items if r.get("status") != "erased")


def check(name, write, note=""):
    m, parent = seeded()
    before = len(m.items)
    try:
        write(m, parent)
    except Exception as e:
        print(f"   {name:26s} write raised {type(e).__name__}: {str(e)[:60]}")
        return
    wrote = len(m.items) - before
    res = m.forget_subject(SUBJ, request_id="DSAR", basis="art17")
    leak = survives(m)
    verdict = "WRITES NOTHING" if wrote == 0 else ("LEAKS" if leak else "reached")
    print(f"   {name:26s} wrote {wrote}  erased {res['erased']}  -> {verdict}   {note}")
    if leak:
        for r in m.items:
            if r.get("status") != "erased" and SECRET in (r.get("text") or "") + str(r.get("object") or ""):
                print(f"        SURVIVED: {r.get('text')!r}  source={r.get('source')} "
                      f"derived_from={r.get('derived_from')}")


print("=== does a DSAR reach what each write path wrote? ===")
print("   (the subject's own record is always present, so `erased` >= 1 everywhere)\n")

check("remember (no source)",
      lambda m, p: m.remember(f"alice moved to {SECRET}", key="alice::addr", object=SECRET),
      "caller omitted provenance -- expected to leak, and it is the caller's to fix")

check("remember (source given)",
      lambda m, p: m.remember(f"alice moved to {SECRET}", key="alice::addr", object=SECRET,
                              source={"doc": SUBJ}))

check("remember (derived_from)",
      lambda m, p: m.remember(f"summary: {SECRET}", derived_from=[p], source={"doc": "svc"}))

check("remember_decision",
      lambda m, p: m.remember_decision(f"we will mail her at {SECRET}", topic="mail::alice",
                                       source=SUBJ))

check("remember_decision (bare)",
      lambda m, p: m.remember_decision(f"we will mail her at {SECRET}", topic="mail::alice"),
      "no source -- caller's to fix")

check("route (correction)",
      lambda m, p: m.route(f"actually alice moved to {SECRET}", key="alice::addr", object=SECRET),
      "OWNED lineage: no caller source needed")

check("route (new key, no source)",
      lambda m, p: m.route(f"her backup address is {SECRET}", key="alice::backup", object=SECRET),
      "no parent to derive from AND no source -- caller's to fix")

check("revert",
      lambda m, p: (m.remember(f"alice moved to {SECRET}", key="alice::addr", object=SECRET,
                               source={"doc": SUBJ}), m.revert("alice::addr")))

check("rederive",
      lambda m, p: (m.remember(f"summary mentioning {SECRET}", derived_from=[p],
                               source={"doc": "svc"}), m.rederive(p) if hasattr(m, "rederive") else None))

check("consolidate",
      lambda m, p: (m.remember(f"alice note {SECRET}", source={"doc": SUBJ}), m.consolidate(keep=1)))

check("observe",
      lambda m, p: m.observe(f"neighbours say {SECRET}", key="alice::addr", object=SECRET),
      "measured earlier: writes no record")

print()
print("-> LEAKS is only a DEFECT where the path had a way to know the subject and did not use it.")
print("   A caller who passes no source anywhere is asking for an unattributable record and gets one;")
print("   that is the documented contract, and the write result says `attributable: false` so they can")
print("   see it. The interesting rows are the ones where the store KNEW and did not act.")
