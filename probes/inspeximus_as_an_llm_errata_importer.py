"""Run inspeximus as a real LLM Errata importer adapter, end to end, on Willner's own controller.

This is the second independent implementation of his conformance boundary, by someone who did not write
the spec -- which is the only way either party finds out whether it is implementable from the document
rather than from the author's head.

It also carries the finding that only appears when you IMPLEMENT rather than review:

  `Controller.quarantine()` builds each AdapterCheckpoint with
      coverage="unknown" if adapter.name in unknown else "verified"
  which is a binary derived solely from whether `enumerate()` raised CannotEnumerate. It never calls
  `adapter.coverage(root)`. `_attest()` DOES call it, and `Coverage` has a PARTIAL member his own
  adapters return (adapters.py:176, 284; sqlite_store.py:281). So an adapter that honestly answers
  PARTIAL has that answer discarded at checkpoint time and recorded as `verified`, and
  `_validate_checkpoint` then re-validates against that record. The durable artifact carries a coverage
  claim the adapter never made.

    python inspeximus_as_an_llm_errata_importer.py --pkg <dir containing prototype/>
"""
import argparse
import io
import json
import os
import sys
import tempfile

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def _store(tmp, orphan=False):
    """A store shaped like the demo scenario: a root fact plus a summary derived from it."""
    from inspeximus import Inspeximus
    m = Inspeximus(path=os.path.join(tmp, "m.json"), receipts=True)
    root = m.remember("is vegetarian", source={"doc": "fact:diet"}, key="diet")
    m.remember("is vegetarian; prefers quiet restaurants; moderate budget",
               derived=True, derived_from=[root], source={"doc": "summary:dining"})
    if orphan:
        # A writer that ANNOUNCED derivation and resolved no parent. Real, common, and the whole
        # reason a third coverage state has to exist.
        m.remember("dining digest assembled by a summariser that dropped its lineage", derived=True)
    return m, root


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                                    "inspeximus-repo")))

    from prototype.errata import Erratum, Operation
    from prototype.scenario import DemoSigner, build_importer
    from inspeximus.integrations.llm_errata import InspeximusErrataAdapter

    out = {}
    owner = DemoSigner(b"\x01" * 32)

    for label, orphan in (("clean store", False), ("store with an undeclared derivative", True)):
        tmp = tempfile.mkdtemp()
        store, root_id = _store(tmp, orphan=orphan)
        adapter = InspeximusErrataAdapter(store)
        ROOT = "fact:diet"

        imp = build_importer(owner)
        imp.adapters = [adapter]                 # OUR store is the only importer-local store
        imp.roots = type(imp.roots)((ROOT,)) if not isinstance(imp.roots, (list, tuple)) else (ROOT,)

        print("\n=== %s ===" % label)
        print("  enumerate(%r) -> %d record(s)" % (ROOT, len(adapter.enumerate(ROOT))))
        detail = adapter.coverage_detail(ROOT)
        print("  coverage_detail:", json.dumps(detail))

        erratum = owner.sign_erratum(Erratum(
            erratum_id="err-1", sequence=1, target_root=ROOT,
            operation=Operation.SUPERSEDE, valid_from="2026-08-01T00:00:00Z",
            replacement="eats meat again",
            postconditions={"negative": "vegetarian", "positive": "eats meat again",
                            "preserve": "quiet restaurants|moderate budget"}))

        cp = imp.quarantine(erratum)
        rec = [r for r in cp.adapters if r.name == "inspeximus"]
        checkpoint_says = rec[0].coverage if rec else "(absent)"
        cov = adapter.coverage(ROOT)
        adapter_says = getattr(cov, "value", cov)   # .value: str(enum) is "Coverage.VERIFIED", not "verified"
        print("  adapter.coverage()   ->", adapter_says)
        print("  CHECKPOINT recorded  ->", checkpoint_says,
              "   <-- MISMATCH" if checkpoint_says != adapter_says else "")

        out[label] = {"coverage_detail": detail, "adapter_says": adapter_says,
                      "checkpoint_says": checkpoint_says,
                      "agree": checkpoint_says == adapter_says}

    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
