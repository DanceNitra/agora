"""A supersession whose root has NO mixed descendant loses the replacement, in BOTH implementations.

FOUND BY THE OTHER SIDE OF A REVIEW, which is why it is worth recording. Thomas Willner reviewed our
candidate adapter fixture and pointed out that `collateral-must-survive-a-supersession` was reported
PASS while its own baseline carried `aggregate=failed` and `triad.positive=fail`. Our expectation had
declared only the preservation arm, so a failing correction went unread. He was right, and following
it produced a finding neither of us had.

WHAT IT IS. `RebuildStrategy` introduces the replacement into a store ONLY through `rebuild()` of a
mixed descendant (strategies.py: pass one retires what descends from the root, pass two rebuilds the
mixed artifacts "from what survived plus the replacement"). When the superseded root has no mixed
descendant there is nothing to rebuild, so the old proposition is retired and the correction is never
asserted anywhere. The store ends up holding neither the retired claim nor its replacement.

WHY IT IS NOT AN ADAPTER DEFECT, and the control that establishes that: the reference MarkdownAdapter
driven through the same strategy with the same store shape fails identically. Both arms are measured
here. The reference fixture in `scenario.py` always registers `summary:dining`, so every published
case has a mixed descendant and this shape is never exercised.

WHAT IS NOT WRONG. The receipt is honest: `aggregate` is `failed` and the positive arm reports `fail`,
so nothing claims success. This is a repair that cannot succeed for this store shape, not a repair
that lies about succeeding. That distinction is the reason it is reportable as a design gap rather
than as a vulnerability.

    python rebuildstrategy_loses_the_replacement_without_a_descendant.py --pkg <dir with prototype/>
"""
import argparse
import io
import json
import os
import sys
import tempfile

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"

POST = {"negative": "vegetarian", "positive": "eats meat again", "preserve": "quiet restaurants"}


def _erratum(owner, target):
    from prototype.errata import Erratum, Operation
    return owner.sign_erratum(Erratum(
        erratum_id="e", sequence=1, target_root=target, operation=Operation.SUPERSEDE,
        valid_from="2026-08-01T00:00:00Z", replacement="eats meat again", postconditions=POST))


def reference_arm(with_descendant):
    """His adapter, his strategy, his ledger. The control that decides whose defect this is."""
    from prototype.adapters import MarkdownAdapter
    from prototype.controller import Importer
    from prototype.errata import RootRegistry
    from prototype.lineage import LineageLedger
    from prototype.signing import DemoSigner, Ed25519Signer

    led = LineageLedger()
    led.register_import("mem_01HX", "fact:diet", store="markdown", content="is vegetarian")
    led.register_import("mem_02KP", "fact:rest", store="markdown",
                        content="prefers quiet restaurants")
    if with_descendant:
        led.register_derivation("summary:dining", store="markdown",
                                inputs=("fact:diet", "fact:rest"),
                                content="is vegetarian; prefers quiet restaurants")
    owner = Ed25519Signer(b"\x01" * 32, key_id="key-1")
    imp = Importer("ref", ledger=led, adapters=[MarkdownAdapter(led)],
                   signer=DemoSigner(b"importer-secret"), owner=owner.public,
                   roots=RootRegistry({"mem_01HX", "mem_02KP"}), strategy=None)
    err = _erratum(owner, "mem_01HX")
    imp.quarantine(err)
    receipt = imp.repair(err)
    return {"positive": str(dict(receipt.triad).get("positive")),
            "aggregate": receipt.aggregate.value}


def inspeximus_arm(with_descendant):
    """Our adapter, same strategy, same shape."""
    from prototype.scenario import build_importer
    from prototype.signing import Ed25519Signer
    from inspeximus import Inspeximus
    from inspeximus.integrations.llm_errata import InspeximusErrataAdapter

    store = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "m.json"), receipts=True)
    diet = store.remember("is vegetarian", source={"doc": "fact:diet"}, key="diet")
    rest = store.remember("prefers quiet restaurants", source={"doc": "fact:rest"}, key="rest")
    if with_descendant:
        store.remember("is vegetarian; prefers quiet restaurants", derived=True,
                       derived_from=[diet, rest])
    owner = Ed25519Signer(b"\x01" * 32, key_id="key-1")
    imp = build_importer(owner)
    imp.adapters = [InspeximusErrataAdapter(store)]
    imp.roots = ("fact:diet",)
    err = _erratum(owner, "fact:diet")
    imp.quarantine(err)
    receipt = imp.repair(err)
    active = [r.get("text") for r in store.items if r.get("status") == "active"]
    return {"positive": str(dict(receipt.triad).get("positive")),
            "aggregate": receipt.aggregate.value,
            "replacement_asserted": "eats meat again" in active,
            "active_records": active}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--inspeximus", default=r"C:/Users/Danculus/inspeximus-repo")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, a.inspeximus)

    out = {"arms": {}}
    print("%-12s %-24s %-14s %s" % ("adapter", "store shape", "triad.positive", "aggregate"))
    for impl, fn in (("reference", reference_arm), ("inspeximus", inspeximus_arm)):
        for label, has in (("no mixed descendant", False), ("with mixed descendant", True)):
            row = fn(has)
            out["arms"]["%s/%s" % (impl, label)] = row
            print("%-12s %-24s %-14s %s" % (impl, label, row["positive"], row["aggregate"]))

    ref_no = out["arms"]["reference/no mixed descendant"]
    ins_no = out["arms"]["inspeximus/no mixed descendant"]
    ref_yes = out["arms"]["reference/with mixed descendant"]
    ins_yes = out["arms"]["inspeximus/with mixed descendant"]

    # THE CONTROL. Without the descendant arm passing, "it fails without a descendant" would be
    # consistent with the repair being broken for every shape, which is a different and much less
    # interesting claim. Both implementations must SUCCEED when a mixed descendant exists.
    assert ref_yes["positive"] == "pass" and ins_yes["positive"] == "pass", (
        "CONTROL FAILED: the repair does not succeed even WITH a mixed descendant, so the finding is "
        "not about the descendant at all: %s %s" % (ref_yes, ins_yes))
    assert ref_no["positive"] == "fail", (
        "the reference does NOT reproduce it, so this is an inspeximus defect and must be reported "
        "as one instead: %s" % ref_no)
    assert ins_no["positive"] == "fail", ins_no
    assert not ins_no["replacement_asserted"], (
        "the replacement IS present, so the positive arm is failing for some other reason")

    print("\nBoth implementations lose the replacement when the root has no mixed descendant.")
    print("Both succeed when one exists, so the descendant is the variable.")
    print("The receipt is honest in every failing arm (aggregate=failed); nothing claims success.")
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("wrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
