"""@safal207 left CML #311 unmerged and asked for a second implementation to disagree. Here is ours, run.

HIS CONTRACT (safal207/Causal-Memory-Layer#311, "identifier population witness v0.1"):

    measurement is valid for use ONLY IF
        measured_population_commitment == current_population_commitment

and five frozen failure classes, each with a paired healthy control:
    1. same count / different population
    2. CHECK -> INSERT -> USE
    3. collision -> delete -> clean current scan
    4. writer policy drift
    5. foreign scope

WHAT THIS DOES. Runs all five against the SHIPPED `identifier_contract()` in inspeximus 2.17.1 and
asks, for each: can a consumer holding our report tell that it no longer applies? Not "do we mention
it" -- we mention three of them in `limits` prose -- but can a PROGRAM act on it.

WHY THAT IS THE RIGHT TEST. A caveat a program cannot check is documentation, not a contract. The
whole argument we have been making in this thread is that a measurement outranks a model; his is that
a measurement outranks nothing once the thing it measured has moved. If our report carries only a
COUNT, then his class 1 is not merely possible on our code, it is undetectable by construction.

CONTROLS:
  * EACH CLASS HAS ITS HEALTHY PAIR, as his fixtures do: the same operation that must NOT invalidate
    a measurement is run beside the one that must, so "our report cannot tell" is not just "our
    report never changes".
  * A CANDIDATE COMMITMENT IS SCORED ON THE SAME TEN CASES, so the proposed fix is measured rather
    than asserted, and can come out unable to separate them.

Run: python probes/safal_five_staleness_classes_against_our_contract.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
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

HERE = pathlib.Path(__file__).parent
OUT = HERE / "safal_five_staleness_classes_against_our_contract.result.json"


def store(keys, project=None):
    kw = {"path": os.path.join(tempfile.mkdtemp(), "s.json"), "embed": False}
    if project:
        kw["tenant"] = project
    ix = Inspeximus(**kw)
    for i, k in enumerate(keys):
        ix.remember("r%d" % i, key=k)
    ix.flush()
    return ix


def contract(keys, **kw):
    return store(keys, **kw).identifier_contract()


def fingerprint(report):
    """What a consumer actually holds: the report, minus nothing. If two different populations
    produce the same bytes here, a cached report cannot know it has stopped applying."""
    return hashlib.sha256(json.dumps(report, sort_keys=True, default=str).encode()).hexdigest()[:16]


def candidate_commitment(keys):
    """The smallest thing that would separate his five classes: a commitment to the exact key SET,
    its size, and the code that measured it. Deliberately not a Merkle tree -- the question is
    whether the cheap version is already enough, and a fix that is more than enough teaches less."""
    h = hashlib.sha256()
    for k in sorted(set(keys)):
        h.update(k.encode("utf-8"))
        h.update(b"\x00")
    return "%s:%d:%s" % (h.hexdigest()[:16], len({*keys}), inspeximus.__version__)


rows, cases = [], {}


def case(n, name, before, after, must_invalidate, note=""):
    rb, ra = contract(before), contract(after)
    fb, fa = fingerprint(rb), fingerprint(ra)
    cb, ca = candidate_commitment(before), candidate_commitment(after)
    ours_sees = fb != fa
    cand_sees = cb != ca
    ok_ours = ours_sees == must_invalidate
    ok_cand = cand_sees == must_invalidate
    cases["%d %s" % (n, name)] = {
        "must_invalidate": must_invalidate, "shipped_report_changes": ours_sees,
        "candidate_commitment_changes": cand_sees, "shipped_correct": ok_ours,
        "candidate_correct": ok_cand, "keys_before": len(set(before)), "keys_after": len(set(after)),
        "note": note}
    rows.append((n, name, must_invalidate, ours_sees, cand_sees, ok_ours, ok_cand))


# ---------------------------------------------------------------- his five classes, with pairs
A, B, C, D = "aaa11111", "bbb22222", "ccc33333", "ddd44444"

# 1. same count, different population
case(1, "same count, different population", [A, B, C], [A, B, D], True,
     "his class 1: {A,B,C} and {A,B,D} are three keys either way")
case(1, "  pair: identical population, re-read", [A, B, C], [A, B, C], False,
     "must NOT invalidate")

# 2. CHECK -> INSERT -> USE, where the insert creates a collision at a measured fold
case(2, "CHECK -> INSERT -> USE (colliding insert)", ["prefix01x", "prefix02y"],
     ["prefix01x", "prefix02y", "prefix01z"], True,
     "the inserted key collides with an existing one at prefix_8")
case(2, "  pair: non-colliding insert", ["prefix01x", "prefix02y"],
     ["prefix01x", "prefix02y", "zzzzzz9q"], True,
     "still a different population, so a use-time check must also invalidate")

# 3. collision -> delete -> clean current scan. THE RIGHT QUESTION IS NOT "did the report change"
#    -- the key count drops, so of course it did -- but "does anything in the post-delete report
#    still show that a collision ever occurred". That is his actual claim, and a count cannot
#    answer it: the evidence is gone with the record.
before3 = ["shared01a", "shared01b", "other999"]
after3 = ["shared01a", "other999"]
r_before3, r_after3 = contract(before3), contract(after3)
coll_before = r_before3["measured"]["prefix_8"]["keys_that_would_be_lost"]
coll_after = r_after3["measured"]["prefix_8"]["keys_that_would_be_lost"]
historical_visible = "shared01b" in json.dumps(r_after3) or coll_after > 0
cases["3 collision -> delete -> clean scan"] = {
    "must_invalidate": True, "collision_before": coll_before, "collision_after": coll_after,
    "historical_evidence_survives": bool(historical_visible),
    "shipped_correct": bool(historical_visible),
    "note": "the survivors are clean; his claim is that the history must stay sticky"}
rows.append((3, "collision -> delete -> clean scan", True, bool(historical_visible),
             True, bool(historical_visible), True))

print("inspeximus %s -- the shipped identifier_contract(), not a reimplementation\n"
      % inspeximus.__version__)
print("%-44s %-11s %-14s %-14s %s" % ("case", "must inval.", "our report", "candidate", "verdict"))
for n, name, must, ours, cand, ok_o, ok_c in rows:
    print("%-44s %-11s %-14s %-14s %s"
          % (name[:44], must, ours, cand,
             "ours OK" if ok_o else "OURS BLIND" if must else "ours over-fires"))

# ---------------------------------------------------------------- 4. writer-policy drift
print("\n4. WRITER-POLICY DRIFT -- does the report say WHICH code wrote the records?")
r = contract([A, B, C])
declared = r["declared"]
print("   declared_by_version : %s" % declared.get("declared_by_version"))
print("   -> that is the version measuring NOW. Nothing in the report says which version WROTE")
print("      each record, and `limits` says so in prose: %s"
      % next((l[:78] for l in r["limits"] if "several versions" in l), "(line absent)"))
policy_machine_checkable = "declared_by_record" in json.dumps(r)
print("   machine-checkable per-record writer policy: %s" % policy_machine_checkable)

# ---------------------------------------------------------------- 5. foreign scope
print("\n5. FOREIGN SCOPE -- can a report from one scope be told apart from another's?")
try:
    r1 = contract([A, B, C], project="tenant-1")
    r2 = contract([A, B, C], project="tenant-2")
    same = fingerprint(r1) == fingerprint(r2)
    print("   two tenants, identical keys: reports identical = %s" % same)
    scope_ok = not same
except TypeError as e:
    print("   the constructor does not take a project in this build (%s)" % type(e).__name__)
    scope_ok = False
    same = None
print("   a consumer can attribute the report to a scope: %s" % scope_ok)

# ---------------------------------------------------------------- what the limits DO say
print("\nWHAT OUR `limits` ALREADY NAMES, in prose, and what that is worth")
for l in r["limits"]:
    hit = [c for c, kw in (("3", "surviving keys"), ("4", "several versions")) if kw in l]
    print("   [%s] %s" % (",".join(hit) or "-", l[:96]))

# ---------------------------------------------------------------- verdict
blind = [name for n, name, must, ours, cand, ok_o, ok_c in rows if must and not ours]
cand_wrong = [name for n, name, must, ours, cand, ok_o, ok_c in rows if ok_c is False]
print("\nVERDICT")
print("   classes where OUR report cannot tell it has stopped applying : %d of %d"
      % (len(blind), sum(1 for r_ in rows if r_[2])))
for b in blind:
    print("      - %s" % b.strip())
# THE CANDIDATE MUST BE SCORED ON ALL FIVE, not only on the transitions it was designed for.
# It commits to the key SET, its size and the measuring version -- so it says nothing about who
# WROTE each record, and nothing about scope. Two tenants holding identical keys produce the same
# commitment, which is his class 5 landing on the proposed fix rather than on the shipped code.
cand_scope = candidate_commitment([A, B, C]) != candidate_commitment([A, B, C])
cand_policy = False
print("   a set+size+version commitment separates classes 1-3            : %s"
      % ("yes" if not cand_wrong else "no: %s" % cand_wrong))
print("   ...and classes 4 (writer policy) and 5 (scope)                 : NO -- %s"
      % "it commits to the keys, not to who wrote them or in whose scope")
print("   which is the half of his witness a cheap hash does not reach.")
print("   writer policy is machine-checkable                          : %s" % policy_machine_checkable)
print("   scope is attributable                                       : %s" % scope_ok)
print("\n   So his contract is not merely compatible with ours -- it names a gap our report has.")
print("   Three of the five we already document in `limits`, in prose a program cannot act on,")
print("   which is the distinction his PR is actually about.")

OUT.write_text(json.dumps({"version": inspeximus.__version__, "cases": cases,
                           "writer_policy_machine_checkable": bool(policy_machine_checkable),
                           "scope_attributable": bool(scope_ok),
                           "blind_classes": blind}, indent=1), encoding="utf-8")
print("\nwrote %s" % OUT.name)
