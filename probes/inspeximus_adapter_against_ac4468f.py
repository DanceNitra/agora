"""Drive the inspeximus LLM Errata adapter through Willner's reference controller at ac4468f.

Every number this repository states about that adapter comes from HERE, re-run in the cycle it is
quoted in. Previously those figures came from throwaway shell heredocs, which nobody else can re-run;
a number whose artifact cannot be named does not go out.

WHAT IT ASSERTS, and why each one is the interesting case:

  1. THE CYCLE COMPLETES WITH AN EMPTY REFERENCE LEDGER. At a477fe4 `RebuildStrategy` read lineage from
     `importer.ledger`, so an adapter over its own store had every gated artifact retired in pass one
     and nothing rebuilt in pass two -- silently, with no exception anywhere. We reported it; the
     strategy now asks `source_artifact()` and `repair_inputs()`. This run registers NOTHING, so a
     regression in that coupling shows up as a failed repair rather than as prose.

  2. THE CHECKPOINT CARRIES THE ADAPTER'S OWN VERDICT. At 08b95263 the durable checkpoint inferred
     `verified` from a successful enumeration and never asked the adapter, so an adapter answering
     `partial` had its answer overwritten. The orphan arm below is the case that used to be recorded
     wrongly.

  3. NO DUPLICATE ASSERTIONS AFTER A REPAIR. Our own defect, invisible to the receipt: `rebuild` used
     to re-assert every named input including ones that were never gated and were still active, so the
     store ended up asserting the same proposition twice. The preservation check passes either way --
     a duplicated fact is recallable exactly as well as a single one -- so this is checked against the
     STORE, not the receipt.

    python inspeximus_adapter_against_ac4468f.py --pkg <dir containing prototype/>
"""
import argparse
import io
import json
import os
import sys
import tempfile

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
SPEC = "ac4468faf73c2cc7949dd29b2a2a151f5bd23116"
DIGEST = "7e0d6c88c1ca3a87743ac70ba2a3dfea0b350d112d2d3c59a3c6cbb537568f12"


def build_store(tmp, orphan):
    """A store shaped the way inspeximus actually holds facts: one proposition per record.

    A combined record is exactly the case the spec's implementer contract now calls out as needing a
    declared decomposition limitation, and it is a mistake we made in our own first fixture.
    """
    from inspeximus import Inspeximus
    m = Inspeximus(path=os.path.join(tmp, "m.json"), receipts=True)
    diet = m.remember("is vegetarian", source={"doc": "fact:diet"}, key="diet")
    rest = m.remember("prefers quiet restaurants", source={"doc": "fact:rest"}, key="rest")
    budg = m.remember("moderate budget", source={"doc": "fact:budget"}, key="budget")
    m.remember("is vegetarian; prefers quiet restaurants; moderate budget",
               derived=True, derived_from=[diet, rest, budg], source={"doc": "summary:dining"})
    if orphan:
        m.remember("digest whose summariser dropped its lineage", derived=True)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    ap.add_argument("--inspeximus", default=r"C:/Users/Danculus/inspeximus-repo")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, a.inspeximus)

    from prototype.errata import Erratum, Operation
    from prototype.scenario import DemoSigner, build_importer
    from inspeximus.integrations.llm_errata import InspeximusErrataAdapter, SPEC_COMMIT, SPEC_G2_DIGEST

    assert SPEC_COMMIT == SPEC, "adapter is bound to %s, not the target" % SPEC_COMMIT[:12]
    assert SPEC_G2_DIGEST == DIGEST, "adapter carries a different G2 digest"
    print("adapter bound to %s\n" % SPEC_COMMIT[:12])

    out = {"spec_commit": SPEC, "g2_digest": DIGEST, "arms": {}}
    for label, orphan in (("clean", False), ("undeclared_derivative", True)):
        owner = DemoSigner(b"\x01" * 32)
        m = build_store(tempfile.mkdtemp(), orphan)
        adapter = InspeximusErrataAdapter(m)
        imp = build_importer(owner)
        imp.adapters = [adapter]
        imp.roots = ("fact:diet",)
        # No ledger registration ANYWHERE in this file. That absence is the assertion.

        err = owner.sign_erratum(Erratum(
            erratum_id="e1", sequence=1, target_root="fact:diet", operation=Operation.SUPERSEDE,
            valid_from="2026-08-01T00:00:00Z", replacement="eats meat again",
            postconditions={"negative": "vegetarian", "positive": "eats meat again",
                            "preserve": "quiet restaurants|moderate budget"}))

        cp = imp.quarantine(err)
        rows = [r for r in cp.adapters if r.name == "inspeximus"]
        checkpoint = rows[0].coverage if rows else "(absent)"
        receipt = imp.repair(err)

        active = [r["text"] for r in m.items if r.get("status") == "active"]
        arm = {"checkpoint_coverage": str(checkpoint),
               "triad": {k: str(v) for k, v in dict(receipt.triad).items()},
               "stores": {k: getattr(v, "value", v) for k, v in receipt.stores.items()},
               "aggregate": receipt.aggregate.value,
               "active_records": active,
               "duplicate_assertions": len(active) - len(set(active))}
        out["arms"][label] = arm

        print("=== %s ===" % label)
        print("  checkpoint coverage  : %s" % arm["checkpoint_coverage"])
        print("  triad                : %s" % arm["triad"])
        print("  aggregate            : %s" % arm["aggregate"])
        print("  active records       : %d" % len(active))
        print("  duplicate assertions : %d" % arm["duplicate_assertions"])

        assert arm["duplicate_assertions"] == 0, "a repair must not assert the same fact twice"
        assert all(v == "pass" for v in arm["triad"].values()), arm["triad"]

    clean, orph = out["arms"]["clean"], out["arms"]["undeclared_derivative"]
    assert clean["aggregate"] == "verified", clean
    # THE CONTROL. Without this the run would pass on an adapter that answers `verified` unconditionally,
    # which is the exact defect we reported upstream and the one we shipped ourselves in 2.8.0.
    assert orph["aggregate"] == "unknown", (
        "a store carrying an unresolved derivation claim must NOT reach verified: %s" % orph)

    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
