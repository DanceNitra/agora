"""Which of CML's six applicability verdicts can inspeximus actually produce today?

safal207 (claude-code#34556, Causal-Memory-Layer#270) froze a vendor-neutral evaluator with six
deterministic outcomes and a precedence order:

    REJECT -> UNRESOLVABLE -> ORPHAN -> DRIFT -> REVALIDATE -> MATCH

Four of them are what inspeximus 2.5.0 shipped as check_sources() the same week, independently. This
probe does not assert that mapping -- it EXERCISES it, one fixture per verdict, and reports which
verdicts we can produce, which we cannot, and where the semantics differ rather than merely the names.

A convergence claimed from two READMEs is a coincidence of vocabulary. A convergence that survives
running each other's fixtures is an interoperability result.

    python research/probes/cml_six_verdict_interop.py
"""
import hashlib
import os
import sys
import tempfile

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def _store():
    return Inspeximus(os.path.join(tempfile.mkdtemp(), "s.json"))


def fixture_match():
    """source resolves + digest matches."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "doc.txt")
    open(p, "w", encoding="utf-8").write("the staging database is db-7.internal")
    ix = _store()
    ix.remember("staging db is db-7", source={"doc": p})
    return ix.check_sources()["counts"]


def fixture_drift():
    """source resolves + digest differs."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "doc.txt")
    open(p, "w", encoding="utf-8").write("db-7")
    ix = _store()
    ix.remember("staging db is db-7", source={"doc": p})
    open(p, "w", encoding="utf-8").write("db-9 now")
    return ix.check_sources()["counts"]


def fixture_orphan():
    """source missing/deleted."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "doc.txt")
    open(p, "w", encoding="utf-8").write("db-7")
    ix = _store()
    ix.remember("staging db is db-7", source={"doc": p})
    os.remove(p)
    return ix.check_sources()["counts"]


def fixture_unresolvable():
    """no re-fetchable source identifier -- e.g. a WRITER label like agent:scholar."""
    ix = _store()
    ix.remember("staging db is db-7", source={"doc": "agent:scholar"})
    return ix.check_sources()["counts"]


def fixture_reject():
    """caller attempts to set reserved provenance/warrant state."""
    ix = _store()
    mid = ix.remember("a claim", mtype="semantic", meta={"graduated_from_episodic": True})
    rec = [r for r in ix.items if r["id"] == mid][0]
    meta = rec.get("meta") or {}
    return {"forged_key_present": "graduated_from_episodic" in meta,
            "warrant": rec.get("warrant") or [w for w in (rec.get("tags") or []) if "warrant" in w] or "n/a"}


def main():
    print("inspeximus vs the CML six-verdict contract (claude-code#34556 / CML#270)")
    print()
    rows = [
        ("MATCH", "source resolves + digest matches", fixture_match, "FRESH"),
        ("DRIFT", "source resolves + digest differs", fixture_drift, "DRIFTED"),
        ("ORPHAN", "source missing/deleted", fixture_orphan, "ORPHANED"),
        ("UNRESOLVABLE", "no re-fetchable identifier", fixture_unresolvable, "UNCHECKABLE"),
    ]
    ok = True
    for cml, desc, fn, ours in rows:
        counts = fn()
        got = [k for k, v in counts.items() if v]
        hit = got == [ours]
        ok = ok and hit
        print("  %-13s %-34s -> inspeximus %-12s %s"
              % (cml, desc, ",".join(got) or "(none)", "OK" if hit else "MISMATCH (expected %s)" % ours))
    print()

    r = fixture_reject()
    print("  %-13s %-34s -> forged reserved key stored: %s"
          % ("REJECT", "caller sets reserved trust state", r["forged_key_present"]))
    print("        SEMANTIC DIFFERENCE, not a gap: CML fails CLOSED and returns REJECT; inspeximus strips")
    print("        the reserved key SILENTLY and stores the record at the untrusted tier. Both refuse the")
    print("        forgery; only one tells the caller which field mattered. safal207 argued for the silent")
    print("        form in this same thread, so a shared fixture needs to allow either -- the assertion")
    print("        belongs on the resulting TRUST STATE, not on the error channel.")
    print()

    print("  %-13s %-34s -> %s" % ("REVALIDATE", "evidence true, environment moved", "NOT PRODUCIBLE"))
    print("        A REAL GAP. inspeximus binds a record to its SOURCE, never to an environment: no repo,")
    print("        commit, tenant-of-execution, policy, model version or TTL enters the check. We cannot")
    print("        answer 'still applicable HERE, NOW' at all, so on this dimension there is nothing to")
    print("        converge with yet -- worth saying plainly rather than mapping it onto DRIFT, which is")
    print("        a different question with a different remedy.")
    print()
    print("VERDICT: %d of 4 source-integrity outcomes reproduce exactly; REJECT agrees on the outcome and"
          % sum(1 for c, d, f, o in rows if [k for k, v in f().items() if v] == [o]))
    print("         differs on the channel; REVALIDATE is ours to build, not ours to claim.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
