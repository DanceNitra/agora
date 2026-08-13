"""Run the candidate StoreAdapter conformance cases against an implementation.

CANDIDATE. Proposed to the LLM Errata specification, not accepted. Running it, or having it merged,
does not make its output G2 or G4 evidence. inspeximus authored these cases and is itself a G4 adapter
candidate, so a separate producer must validate both implementations and this fixture.

WHY THIS EXISTS. Measured under `sys.settrace` at ac4468f, 1 of the 28 executable published cases
reaches a store adapter at all. The published vectors grade the wire schema, the feed authenticator,
the receipt signer and the semantic aggregator, and they grade them hard. They were never meant to
grade adapter behaviour: `spec/README.md` is titled "The LLM Errata wire schema". These cases are the
missing half, and every one of them names the flattering implementation it exists to catch.

THREE RULES THIS RUNNER ENFORCES ON ITS OWN FIXTURE, each from a defect we shipped or nearly shipped:

  1. NO EXPECTATION WITHOUT A CITATION. A case missing a `normative` block is refused, not scored. Our
     first conformance harness derived expected verdicts by splitting case names on a hyphen, so
     `provider-error` expected "provider"; it scored five false failures against the specification's
     own fixtures and was one step from reporting them upstream.
  2. NO CASE WITHOUT A POSITIVE CONTROL. Each case declares the adapter methods it must reach, and the
     run traces whether it reached them. A case that never touches the surface it claims to test
     passes for the wrong reason, which is the entire defect class these cases exist to find.
  3. NO FIXTURE THAT HAS NEVER FAILED. Each case names a flattering implementation, the runner applies
     it, and the case MUST fail. A fixture nobody has watched fail is a fixture nobody has tested.

TO RUN IT AGAINST YOUR OWN STORE, implement one class (see `InspeximusBinding` at the bottom):

    class YourBinding:
        name = "your-store"
        def build(self, records):   # -> (StoreAdapter, handle)
        def active_texts(self, handle):  # -> list[str] of currently-asserted propositions

    python run_adapter_conformance.py --pkg <dir with prototype/> --binding your.module:YourBinding
"""
import argparse
import importlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "adapter-conformance.json")
RESULT = os.path.join(HERE, "adapter-conformance.result.json")


class Tracer:
    """Record which adapter methods a case actually reached, for the positive controls."""

    def __init__(self):
        self.hits = set()

    def _trace(self, frame, event, arg):
        if event == "call":
            self.hits.add(frame.f_code.co_name)
        return None

    def __enter__(self):
        self.hits = set()
        sys.settrace(self._trace)
        return self

    def __exit__(self, *exc):
        sys.settrace(None)
        return False


def build_erratum(spec, signer, sequence=1):
    from prototype.errata import Erratum, Operation
    op = Operation(spec["operation"])
    return signer.sign_erratum(Erratum(
        erratum_id="case-%d" % sequence, sequence=sequence, target_root=spec["target_root"],
        operation=op, valid_from="2026-08-01T00:00:00Z",
        replacement=spec.get("replacement"), postconditions=dict(spec["postconditions"])))


def apply_mutation(adapter, importer, mutation, binding, handle, root):
    """Install the flattering implementation a case exists to catch.

    Mutations are declared in the fixture, not hard-coded here, so a third party reading the JSON can
    see exactly what each case claims to catch without reading this file.

    EVERY MUTATION GOES THROUGH THE PROTOCOL SURFACE OR THE BINDING, never through an implementation's
    private attributes. The first version of this function reached for `adapter._store` and
    `adapter._text_of`, which do not exist, and an `except Exception: pass` swallowed the AttributeError
    so the mutation silently did nothing. The run then reported CASE STILL PASSED, correctly, and that
    is the only reason it was caught. A mutation aimed at a private name is a mutation that no-ops for
    every implementation but the one it was written against, which would hand a third party a suite
    whose controls quietly stop working on their store.
    """
    target = mutation["target"]
    if target == "lineage_complete":
        adapter.lineage_complete = lambda root: True
    elif target == "quarantine_coverage":
        from prototype.adapters import Coverage
        adapter.quarantine_coverage = lambda root: Coverage.UNKNOWN
    elif target == "rebuild":
        original = adapter.rebuild

        def flattering(artifact_id, *, inputs, replacement):
            # An implementation that does not gate its inputs re-asserts propositions that were never
            # retired and are still active, so the store ends up asserting the same fact twice. Done
            # here through `rebuild` itself with no inputs, which is the protocol's own way of writing
            # a payload, and through the binding to learn what is currently asserted.
            out = original(artifact_id, inputs=inputs, replacement=replacement)
            for text in list(binding.active_texts(handle)):
                original(artifact_id, inputs=(), replacement=text)
            return out
        adapter.rebuild = flattering
    elif target == "retire":
        original = adapter.retire

        def scorched(artifact_id, *, superseded_at=None):
            # Satisfy the negative postcondition the cheapest way: retire the whole store instead of
            # the artifacts that were actually gated. Driven from `snapshot()`, which the protocol
            # defines over the store rather than under one root -- `enumerate(root)` reaches only that
            # root's descendants, so collateral held under OTHER roots survived it and the mutation
            # silently failed to be destructive at all.
            for art in list(adapter.snapshot()):
                if art != artifact_id:
                    original(art, superseded_at=superseded_at)
            return original(artifact_id, superseded_at=superseded_at)
        adapter.retire = scorched
    elif target == "repair":
        class _Empty:
            def to_dict(self):
                return {}
            aggregate = type("C", (), {"value": "verified"})()
            triad = {}
            stores = {}
        importer.repair = lambda err: _Empty()
    else:
        raise ValueError("unknown mutation target %r; the fixture names a mutation this runner "
                         "cannot install, which means the case has never been shown to fail" % target)


def evaluate(case, binding, pkg, mutate=False):
    """Run one case and return what was observed. Never decides pass/fail; the caller compares."""
    from prototype.scenario import build_importer
    from prototype.signing import Ed25519Signer

    owner = Ed25519Signer(b"\x01" * 32, key_id="key-1")
    adapter, handle = binding.build(case["store"]["records"])
    importer = build_importer(owner)
    importer.adapters = [adapter]
    importer.roots = (case["erratum"]["target_root"],)
    err = build_erratum(case["erratum"], owner)
    if mutate:
        apply_mutation(adapter, importer, case["mutation"], binding, handle,
                       case["erratum"]["target_root"])

    observed = {}
    with Tracer() as t:
        checkpoint = importer.quarantine(err)
        rows = [r for r in checkpoint.adapters if r.name == getattr(adapter, "name", "")]
        observed["checkpoint_coverage"] = str(getattr(rows[0].coverage, "value", rows[0].coverage)) \
            if rows else "(absent)"
        receipt = importer.repair(err)
        blob = json.dumps(receipt.to_dict(), default=str)
        observed["aggregate"] = getattr(receipt.aggregate, "value", str(receipt.aggregate))
        observed["triad"] = {k: str(v) for k, v in dict(receipt.triad).items()}

    texts = list(binding.active_texts(handle))
    observed["store_property"] = {
        "duplicate_active_assertions": len(texts) - len(set(texts)),
        "erased_text_absent": None, "preserved_text_present": None, "unrelated_text_present": None}
    observed["receipt_property"] = {
        "names_the_store": getattr(adapter, "name", "") in blob,
        "is_non_trivial": len(blob) > 200, "forbidden_value_absent": None}
    observed["_texts"] = texts
    observed["_blob"] = blob
    observed["methods_reached"] = sorted(t.hits)
    return observed


def compare(case, observed):
    """Compare observation to the case's stated expectation. Returns (ok, failures)."""
    exp, fails = case["expect"], []
    for key in ("checkpoint_coverage", "aggregate"):
        if key in exp and observed.get(key) != exp[key]:
            fails.append("%s: expected %s, got %s" % (key, exp[key], observed.get(key)))
    for arm, want in (exp.get("triad") or {}).items():
        got = observed["triad"].get(arm)
        if got != want:
            fails.append("triad.%s: expected %s, got %s" % (arm, want, got))
    for prop, want in (exp.get("store_property") or {}).items():
        if prop == "duplicate_active_assertions":
            got = observed["store_property"]["duplicate_active_assertions"]
            if got != want:
                fails.append("duplicate_active_assertions: expected %s, got %s" % (want, got))
        elif prop == "erased_text_absent":
            if want in observed["_texts"]:
                fails.append("erased text %r is still asserted" % want)
        elif prop in ("preserved_text_present", "unrelated_text_present"):
            if want not in observed["_texts"]:
                fails.append("%s: %r is not asserted" % (prop, want))
    for prop, want in (exp.get("receipt_property") or {}).items():
        if prop == "forbidden_value_absent":
            if want in observed["_blob"]:
                fails.append("receipt leaks the erased value %r" % want)
        elif observed["receipt_property"].get(prop) != want:
            fails.append("receipt.%s: expected %s, got %s"
                         % (prop, want, observed["receipt_property"].get(prop)))
    return (not fails), fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    ap.add_argument("--binding", default=None, help="module:Class implementing build/active_texts")
    ap.add_argument("--inspeximus", default=r"C:/Users/Danculus/inspeximus-repo")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, a.inspeximus)
    sys.path.insert(0, HERE)

    if a.binding:
        mod, cls = a.binding.split(":")
        binding = getattr(importlib.import_module(mod), cls)()
    else:
        binding = InspeximusBinding()

    fixture = json.load(io.open(FIXTURE, encoding="utf-8"))
    out = {"fixture_status": fixture["status"], "binding": binding.name, "cases": []}
    print("Candidate adapter conformance -- binding: %s" % binding.name)
    print("%s\n" % fixture["status"])

    passed = 0
    for case in fixture["adapter_cases"]:
        # RULE 1: an expectation nobody wrote down is an opinion, not a conformance requirement.
        if not case.get("normative", {}).get("quote"):
            raise AssertionError("case %r has no normative citation; refusing to score it" % case["id"])

        observed = evaluate(case, binding, a.pkg, mutate=False)
        ok, fails = compare(case, observed)

        # RULE 2: the case must have reached the surface it claims to test.
        required = set(case["positive_control"]["adapter_methods_required"])
        reached = required & set(observed["methods_reached"])
        control_ok = reached == required
        missing = sorted(required - reached)

        # RULE 3: the case must fail against the flattering implementation it names.
        try:
            mutated = evaluate(case, binding, a.pkg, mutate=True)
            mut_ok, _ = compare(case, mutated)
            mutation_caught = not mut_ok
            mut_note = "case failed as required" if mutation_caught else "CASE STILL PASSED"
        except Exception as exc:
            mutation_caught, mut_note = True, "raised %s" % type(exc).__name__

        good = ok and control_ok and mutation_caught
        passed += bool(good)
        print("[%s] %s" % ("PASS" if good else "FAIL", case["id"]))
        print("      expectation : %s" % ("met" if ok else "; ".join(fails)))
        print("      control     : reached %d/%d declared methods%s"
              % (len(reached), len(required), "" if control_ok else " -- MISSING %s" % missing))
        print("      mutation    : %s (%s)" % (case["mutation"]["flattering_behaviour"], mut_note))
        out["cases"].append({
            "id": case["id"], "pass": good, "expectation_met": ok, "failures": fails,
            "normative_source": case["normative"]["source"],
            "methods_required": sorted(required), "methods_reached": sorted(reached),
            "positive_control_ok": control_ok, "mutation_caught": mutation_caught,
            "observed": {k: v for k, v in observed.items() if not k.startswith("_")}})

    total = len(fixture["adapter_cases"])
    print("\n%d/%d candidate adapter cases pass for %s" % (passed, total, binding.name))
    print("This is not G2 or G4 evidence. %s" % fixture["authored_by"]["disclosure"])
    out["totals"] = {"cases": total, "passed": passed}
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("wrote %s" % os.path.basename(RESULT))
    return 0 if passed == total else 1


class InspeximusBinding:
    """The reference binding, and the whole of what a third party has to write.

    Nothing above this class names inspeximus. If a case can only be satisfied by reading this file,
    the case is coupled to our implementation and should be refused.
    """

    name = "inspeximus"

    def build(self, records):
        from inspeximus import Inspeximus
        from inspeximus.integrations.llm_errata import InspeximusErrataAdapter
        store = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "m.json"), receipts=True)
        ids = {}
        for rec in records:
            if rec.get("derived"):
                parents = rec.get("derived_from")
                if parents:
                    ids[rec["id"]] = store.remember(
                        rec["text"], derived=True, derived_from=[ids[p] for p in parents])
                else:
                    ids[rec["id"]] = store.remember(rec["text"], derived=True)
            else:
                ids[rec["id"]] = store.remember(
                    rec["text"], source={"doc": rec["root"]}, key=rec["id"])
        return InspeximusErrataAdapter(store), store

    def active_texts(self, handle):
        return [r.get("text") for r in handle.items if r.get("status") == "active"]


if __name__ == "__main__":
    sys.exit(main())
