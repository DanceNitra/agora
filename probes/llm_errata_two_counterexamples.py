"""Two counterexamples against LLM Errata at commit 08b95263, using its own prototype.

Thomas Willner's review contract asks for "the smallest counterexample that breaks an invariant or
makes the contract impractical", scoped to quarantine ordering, equivocation, and undeclared lineage.
These are the two I found. Both run against his package as published; neither is a reimplementation.

CONFLICT DISCLOSURE: I maintain inspeximus, which his PRIOR_ART.md names as the closest local prior
art, and we sell into agent memory. This is interested-party evidence.

  1. EQUIVOCATION IS UNDETECTABLE BY A SINGLE IMPORTER, and the detector that exists cannot fire.
     `verify_feed` refuses a feed where two errata claim one sequence -- but `seen` is a dict local to
     one call, and `Controller.observe` calls it with a single-element list every time. So the check
     is structurally unreachable in the path that runs. Worse, the interesting attack does not need
     one importer to see both: an owner signs erratum A at sequence 5 for importer 1 and a different
     erratum B at sequence 5 for importer 2. Each sees a correctly signed, monotone, gap-free feed.
     Both attest. The receipts are individually valid and jointly contradictory, which is what
     equivocation means, and nothing in the contract lets either party notice.

  2. "I FOUND NO DESCENDANTS" AND "I VERIFIED THERE ARE NONE" ARE THE SAME RECEIPT. `_quarantine`
     treats an adapter that raises `CannotEnumerate` as coverage `unknown` -- correctly, and that is
     the honest half. But an adapter that CAN enumerate and returns an empty list gets
     `coverage="verified"` with an empty artifact set. Those are different facts: one store was
     walked and had nothing, the other declared no lineage for the walker to follow.

     This is not hypothetical for us. Our own dogfooded store holds 408 records with ZERO declared
     `derived_from` edges, so an adapter over it would enumerate cleanly, return nothing, and be
     recorded as verified for every root -- a perfect score from a store that has never been checked.
     His own `_attest` comment states the principle exactly ("there is no way to distinguish it from
     an unchecked one"); the empty-enumeration path is where it leaks. D2 is meant to catch a receipt
     that overstates coverage, and this is a receipt that overstates coverage while D1 and D2 both pass.

    python llm_errata_two_counterexamples.py --pkg <dir containing prototype/>
"""
import argparse
import io
import json
import os
import sys

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)

    from prototype.errata import Erratum, Operation, verify_feed, FeedError
    from prototype.scenario import DIET, DemoSigner, build_importer

    out = {}
    owner = DemoSigner(b"\x01" * 32)

    def erratum(eid, seq, replacement):
        return owner.sign_erratum(Erratum(
            erratum_id=eid, sequence=seq, target_root=DIET,
            operation=Operation.SUPERSEDE, valid_from="2026-08-01T00:00:00Z",
            replacement=replacement,
            postconditions={"negative": "vegetarian", "positive": replacement,
                            "preserve": "quiet restaurants|moderate budget"}))

    # ---- 1. equivocation ---------------------------------------------------------------------
    print("1. EQUIVOCATION")
    a1 = erratum("err_A", 1, "eats meat again")
    b1 = erratum("err_B", 1, "is vegan now")          # same sequence, different instruction

    print("   both errata are signed by the same owner key at sequence 1, with different content")
    imp1, imp2 = build_importer(owner), build_importer(owner)
    try:
        verify_feed([a1, b1], owner=imp1.owner, roots=imp1.roots, last_sequence=0)
        same_feed = "ACCEPTED"
    except FeedError as exc:
        same_feed = "refused: %s" % str(exc).split(".")[0]
    print("   seen together in ONE feed        : %s" % same_feed)

    r1 = imp1.repair(a1)
    r2 = imp2.repair(b1)
    print("   importer 1 attests err_A         : aggregate=%s" % r1.aggregate.value)
    print("   importer 2 attests err_B         : aggregate=%s" % r2.aggregate.value)
    print("   -> two valid receipts, same sequence, contradictory instructions, neither party can tell")
    out["equivocation"] = {"same_feed": same_feed,
                           "importer_1": r1.aggregate.value, "importer_2": r2.aggregate.value}

    # ---- 2. empty enumeration reads as verified ----------------------------------------------
    print("\n2. UNDECLARED LINEAGE")

    class SilentAdapter:
        """Enumerates perfectly. Declares nothing. This is our own store, measured: 408 records, 0
        with declared lineage -- so it answers every question with an empty set, truthfully."""

        name = "silent_store"
        required = True

        def enumerate(self, root):
            return []                                   # nothing declares a link to this root

        def quarantine(self, items):
            return None

        def is_quarantined(self, item):
            return True

        def coverage(self, root):
            return "verified"

        def rebuild(self, *a, **k):
            return None

    imp3 = build_importer(owner)
    imp3.adapters = tuple(list(imp3.adapters) + [SilentAdapter()])
    cp = imp3.quarantine(erratum("err_C", 1, "eats meat again"))
    rec = {r.name: (r.coverage, len(r.artifact_ids), r.limitation is not None) for r in cp.adapters}
    for name, (cov, n, lim) in sorted(rec.items()):
        print("   %-14s coverage=%-9s artifacts=%d  limitation=%s" % (name, cov, n, lim))
    silent = rec["silent_store"]
    print("   -> the silent store reports %r with %d artifacts and no limitation:" % (silent[0], silent[1]))
    print("      indistinguishable from a store that was walked and genuinely had none.")
    out["undeclared_lineage"] = {k: {"coverage": v[0], "artifacts": v[1], "limitation": v[2]}
                                 for k, v in rec.items()}

    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
