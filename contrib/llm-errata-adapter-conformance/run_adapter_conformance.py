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
    """Record which adapter methods ran ON THE TARGET INSTANCE.

    The first version recorded `frame.f_code.co_name` globally, so a positive control asking for
    `coverage`, `retire` or `rebuild` was satisfied by ANY function of that name anywhere in the
    process -- the reference adapters, the controller, the standard library. Reported upstream as a
    false-pass gap and it was correct: a name is not a call on the object under test. Binding to
    `frame.f_locals['self'] is adapter` makes the control mean what it says.
    """

    def __init__(self, target=None):
        self.hits = set()
        self.target = target

    def _trace(self, frame, event, arg):
        if event == "call":
            if self.target is None or frame.f_locals.get("self") is self.target:
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
    with Tracer(target=adapter) as t:
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


def compare(case, observed, strict=True):
    """Compare observation to the case's stated expectation. Returns (ok, failures).

    STRICT means an outcome the case did not mention must still be conforming. Without it, a case
    declaring only `triad.preserve` reported PASS while its own baseline carried `aggregate=failed`
    and `triad.positive=fail`: preservation was observed, the repair was not conforming, and the
    partial expectation hid it. Reported upstream, correct, and it led to a real finding -- see
    probes/rebuildstrategy_loses_the_replacement_without_a_descendant.py. An unmentioned outcome is
    now required to be clean rather than assumed to be irrelevant.
    """
    exp, fails = case["expect"], []
    if strict:
        for arm, got in observed.get("triad", {}).items():
            if arm not in (exp.get("triad") or {}) and got != "pass":
                fails.append("unspecified triad.%s = %s (case did not declare it; it must still "
                             "conform)" % (arm, got))
        if "aggregate" not in exp and observed.get("aggregate") not in (None, "verified"):
            fails.append("unspecified aggregate = %s (case did not declare it; it must still "
                         "conform)" % observed.get("aggregate"))
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


def check_must_produce(wanted, observed):
    """Did the mutation produce the exact counter-result the case declared? Returns failures."""
    bad = []
    for key, want in wanted.items():
        if key == "triad":
            for arm, val in want.items():
                if observed.get("triad", {}).get(arm) != val:
                    bad.append("triad.%s expected %s, got %s"
                               % (arm, val, observed.get("triad", {}).get(arm)))
        elif key in ("store_property", "receipt_property"):
            for prop, val in want.items():
                if observed.get(key, {}).get(prop) != val:
                    bad.append("%s.%s expected %s, got %s"
                               % (key, prop, val, observed.get(key, {}).get(prop)))
        elif observed.get(key) != want:
            bad.append("%s expected %s, got %s" % (key, want, observed.get(key)))
    return bad


def verify_citation(case, pkg):
    """The quote must actually appear in the file the case names, inside the pinned source tree.

    A non-empty string was previously enough, so a citation could name any file and say anything.
    Reported upstream as a source-binding gap. Checking the text against the tree makes a wrong or
    invented citation a run failure instead of a formatting detail.
    """
    src = case["normative"]["source"].split(",")[0].strip()
    path = os.path.join(pkg, src)
    if not os.path.exists(path):
        return "cited source %r does not exist in the pinned tree" % src
    body = io.open(path, encoding="utf-8", errors="replace").read()
    # Normalise FORMATTING only, never content: collapse whitespace, because the sources wrap their
    # prose and a correct quote can differ from the file by a newline, and drop markdown emphasis and
    # code ticks, because `**No silent completeness:**` and "No silent completeness:" are the same
    # sentence. That second case is not hypothetical -- it is what this check caught on its first run
    # against the full tree, on our own citation.
    def norm(text):
        # `**` and backticks only. Stripping a bare `*` turned a quoted signature's keyword-only
        # marker into nothing and made a correct citation look wrong.
        return " ".join(text.replace("**", "").replace("`", "").split())

    quote = norm(case["normative"]["quote"])
    hay = norm(body)
    core = quote.split(" -- ")[0].strip().strip('"')
    if core not in hay:
        return "quoted text is not present in %s: %r" % (src, core[:70])
    return None


def source_digest(pkg):
    """A deterministic digest of the source tree actually scored, so `--pkg` cannot be arbitrary."""
    import hashlib
    h = hashlib.sha256()
    roots = [os.path.join(pkg, "prototype"), os.path.join(pkg, "spec")]
    files = []
    for root in roots:
        for base, _dirs, names in os.walk(root):
            if "__pycache__" in base:
                continue
            for n in sorted(names):
                if n.endswith((".py", ".json", ".md")):
                    files.append(os.path.join(base, n))
    for path in sorted(files):
        h.update(os.path.relpath(path, pkg).replace("\\", "/").encode("utf-8"))
        h.update(io.open(path, "rb").read())
    return h.hexdigest(), len(files)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    ap.add_argument("--binding", default=None, help="module:Class implementing build/active_texts")
    ap.add_argument("--pkg-digest", default=None,
                    help="refuse to run unless the scored tree hashes to this")
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

    # SOURCE BINDING. The target commit and digest used to appear only in prose, so any tree handed
    # to --pkg could be scored and reported under this fixture's name. Reported upstream as a
    # source-binding gap. The adapter's own pin is asserted, the scored tree is digested, and
    # --pkg-digest makes that binding enforceable rather than merely recorded.
    from inspeximus.integrations.llm_errata import SPEC_COMMIT, SPEC_G2_DIGEST
    target = fixture.get("target", {})
    if target.get("commit") and SPEC_COMMIT != target["commit"]:
        raise AssertionError("the adapter is bound to %s but the fixture targets %s"
                             % (SPEC_COMMIT[:12], target["commit"][:12]))
    if target.get("g2_digest") and SPEC_G2_DIGEST != target["g2_digest"]:
        raise AssertionError("the adapter carries a different G2 digest than the fixture targets")
    tree_digest, n_files = source_digest(a.pkg)
    if a.pkg_digest and a.pkg_digest.strip().lower() != tree_digest:
        raise AssertionError("REFUSED: --pkg does not match the declared source digest.\n"
                             "  declared : %s\n  scored   : %s" % (a.pkg_digest.strip(), tree_digest))

    out = {"fixture_status": fixture["status"], "binding": binding.name,
           "spec_commit": SPEC_COMMIT, "g2_digest": SPEC_G2_DIGEST,
           "scored_tree_digest": tree_digest, "scored_files": n_files, "cases": []}
    print("Candidate adapter conformance -- binding: %s" % binding.name)
    print("adapter bound to %s | scored tree %s (%d files)"
          % (SPEC_COMMIT[:12], tree_digest[:16], n_files))
    print("%s\n" % fixture["status"])

    passed = 0
    for case in fixture["adapter_cases"]:
        # RULE 1: an expectation nobody wrote down is an opinion, not a conformance requirement.
        if not case.get("normative", {}).get("quote"):
            raise AssertionError("case %r has no normative citation; refusing to score it" % case["id"])
        bad_cite = verify_citation(case, a.pkg)
        if bad_cite:
            raise AssertionError("case %r: %s" % (case["id"], bad_cite))

        observed = evaluate(case, binding, a.pkg, mutate=False)
        ok, fails = compare(case, observed)

        # RULE 2: the case must have reached the surface it claims to test.
        required = set(case["positive_control"]["adapter_methods_required"])
        reached = required & set(observed["methods_reached"])
        control_ok = reached == required
        missing = sorted(required - reached)

        # RULE 3: the case must fail against the flattering implementation it names.
        # An exception is NOT a caught mutation. The first version credited any raise, so a mutation
        # that simply crashed on installation earned the same score as one that produced the semantic
        # counter-result it declared. Reported upstream as a false-pass and it was right: a broken
        # mutation proves nothing about the case. A raise now fails the case unless the case names the
        # exception it expects.
        expects_raise = case["mutation"].get("expected_exception")
        try:
            mutated = evaluate(case, binding, a.pkg, mutate=True)
            mut_ok, _ = compare(case, mutated)
            mutation_caught = not mut_ok
            mut_note = "case failed as required" if mutation_caught else "CASE STILL PASSED"
            # The mutation must produce the SPECIFIC counter-result it declared, not merely any
            # failure: a mutation that breaks the case for an unrelated reason is not evidence.
            wanted = case["mutation"].get("must_produce") or {}
            if mutation_caught and wanted:
                bad = check_must_produce(wanted, mutated)
                if bad:
                    mutation_caught = False
                    mut_note = "failed, but not as declared: %s" % "; ".join(bad)
        except Exception as exc:
            if expects_raise and type(exc).__name__ == expects_raise:
                mutation_caught, mut_note = True, "raised %s as declared" % expects_raise
            else:
                mutation_caught = False
                mut_note = ("raised %s, which is NOT a caught mutation: a crash is not the declared "
                            "counter-result" % type(exc).__name__)

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
