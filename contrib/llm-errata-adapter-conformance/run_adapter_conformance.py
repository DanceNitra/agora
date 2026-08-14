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
        def persisted_root(self, handle):    # -> str, the directory it persists into

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


def _stub(adapter, method):
    """Replace one protocol method with an inert but well-formed answer.

    Inert, not broken: returning a plausible empty value is what a lazy implementation does, and it
    is the case that must notice. Raising would prove only that the call happens.
    """
    from prototype.adapters import Coverage
    stands_in = {
        "enumerate": [lambda *a, **k: ()],
        "repair_inputs": [lambda *a, **k: ()],
        "snapshot": [lambda *a, **k: {}],
        "dispositions": [lambda *a, **k: {}],
        "recall": [lambda *a, **k: ()],
        "is_quarantined": [lambda *a, **k: False, lambda *a, **k: True],
        "quarantine": [lambda *a, **k: None],
        "retire": [lambda *a, **k: None],
        "source_artifact": [lambda x, *a, **k: x],
        "rebuild": [lambda *a, **k: ""],
        "coverage_detail": [lambda *a, **k: {}],
        # BOTH DIRECTIONS. A single stand-in that happens to agree with the case's expected outcome
        # changes nothing, and the method then reads as inert when it is simply un-probed. Measured:
        # `lineage_complete -> True` left a case expecting `verified` untouched and was reported
        # INERT; `-> False` flips it immediately.
        "lineage_complete": [lambda *a, **k: True, lambda *a, **k: False],
        "coverage": [lambda *a, **k: Coverage.VERIFIED, lambda *a, **k: Coverage.UNKNOWN],
        "quarantine_coverage": [lambda *a, **k: Coverage.VERIFIED,
                                lambda *a, **k: Coverage.UNKNOWN],
    }
    options = stands_in.get(method)
    if not options:
        raise ValueError("no stand-in for %r" % method)
    return options


def evaluate(case, binding, pkg, mutate=False, stub_method=None):
    """Run one case and return what was observed. Never decides pass/fail; the caller compares."""
    from prototype.scenario import build_importer
    from prototype.signing import Ed25519Signer

    owner = Ed25519Signer(b"\x01" * 32, key_id="key-1")
    # THE RUNNER ALLOCATES THE OBSERVED DIRECTORY. Pointing `tempfile.tempdir` here for the duration
    # of build() means a store creating its files the ordinary way lands inside it whether or not the
    # binding admits where it writes. The previous design scanned a directory the BINDING named, so a
    # copy one level above it, or a decoy sub-root holding only a view file, was never looked at.
    channel_root = tempfile.mkdtemp(prefix="conformance-observed-")
    prior_tmp = tempfile.tempdir
    tempfile.tempdir = channel_root
    try:
        before = _scan(channel_root)
        adapter, handle = binding.build(case["store"]["records"])
    finally:
        tempfile.tempdir = prior_tmp
    importer = build_importer(owner)
    importer.adapters = [adapter]
    importer.roots = (case["erratum"]["target_root"],)
    err = build_erratum(case["erratum"], owner)
    if mutate:
        apply_mutation(adapter, importer, case["mutation"], binding, handle,
                       case["erratum"]["target_root"])
    if stub_method:
        options = _stub(adapter, stub_method[0] if isinstance(stub_method, tuple) else stub_method)
        idx = stub_method[1] if isinstance(stub_method, tuple) else 0
        if idx >= len(options):
            raise IndexError("no variant %d" % idx)
        setattr(adapter, stub_method[0] if isinstance(stub_method, tuple) else stub_method,
                options[idx])

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

    # CONCEALMENT. `active_texts` only says what is in present-tense recall, so an adapter whose
    # retire() copies the value into a side field and demotes the record satisfies every check
    # above. Measured: such an adapter scored a full PASS on the erasure case while the store still
    # held "is vegetarian" verbatim. Erasure has to be checked against the PERSISTED state, so the
    # binding must hand over everything it wrote.
    # deliberately not read yet -- see below

    # SELF-ATTESTATION. `active_texts` is written by the implementation under test; a binding that
    # returns a hard-coded list is never contradicted. Cross-check each answer against the adapter's
    # own recall(), which is the protocol's surface rather than the binding's.
    disagreements = []
    for term in set(texts):
        try:
            hits = adapter.recall(term)
        except Exception:
            continue
        if term and not any(term in getattr(h, "content", "") for h in hits):
            disagreements.append(term)

    observed["store_property"] = {
        "duplicate_active_assertions": len(texts) - len(set(texts)),
        "erased_text_absent": None, "preserved_text_present": None, "unrelated_text_present": None,
        "erased_text_absent_from_persisted_state": None,
        "binding_disagrees_with_recall": disagreements}
    observed["receipt_property"] = {
        "names_the_store": getattr(adapter, "name", "") in blob,
        "is_non_trivial": len(blob) > 200, "forbidden_value_absent": None,
        # An empty snapshot() makes pre_state_root == post_state_root while coverage still reads
        # `verified` and no limitation is recorded, so the receipt attests state roots that bind
        # nothing. Both are now observable.
        "snapshot_is_non_empty": bool(adapter.snapshot()),
        "state_roots_differ": (receipt.to_dict().get("pre_state_root")
                               != receipt.to_dict().get("post_state_root"))}
    # READ LAST. A store that re-persists the value on the next `recall()` -- a call this runner
    # itself makes for the cross-check -- would slip past a channel read any earlier. Everything
    # that touches the store has happened by this point.
    raw, channel_note = read_channel(channel_root, before)
    observed["_raw"] = raw
    observed["channel"] = channel_note
    observed["_texts"] = texts
    observed["_blob"] = blob
    observed["methods_reached"] = sorted(t.hits)
    return observed


def _needle_forms(needle):
    """Every byte form a store might plausibly have written this proposition in.

    The previous search decoded files as utf-8 with errors="replace" and looked for a string. That is
    blind to anything not stored as readable utf-8 text: a gzip side copy, utf-16, base64. Since the
    check exists to prove a value is GONE, every form it cannot see is a false clean bill. Erasure
    requests are names and addresses, so the encodings involved are not exotic.
    """
    import base64
    forms = set()
    for enc in ("utf-8", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            forms.add(needle.encode(enc))
        except Exception:
            pass
    raw = needle.encode("utf-8")
    forms.add(base64.b64encode(raw))
    forms.add(base64.b64encode(raw).rstrip(b"="))
    forms.add(needle.encode("unicode_escape"))          # the ensure_ascii=True case
    forms.add(json.dumps(needle)[1:-1].encode("utf-8"))  # as JSON would embed it
    return {f for f in forms if f}


def _decompressed_views(data):
    """`data` plus anything it decompresses to, so a gzipped copy is not invisible."""
    import gzip
    import zlib
    views = [data]
    for opener in (gzip.decompress, zlib.decompress,
                   lambda d: zlib.decompress(d, -zlib.MAX_WBITS)):
        try:
            views.append(opener(data))
        except Exception:
            pass
    # a gzip member embedded inside a larger file
    idx = data.find(bytes((0x1F, 0x8B)))
    if idx > 0:
        try:
            views.append(gzip.decompress(data[idx:]))
        except Exception:
            pass
    return views


def present_in_bytes(needle, data):
    """Is this proposition present in these bytes, in ANY plausible encoding or container?"""
    forms = _needle_forms(needle)
    for view in _decompressed_views(data):
        for form in forms:
            if form in view:
                return True
    return False


def _present(needle, haystack):
    """Is `needle` in `haystack`, whatever encoding the binding chose to dump in?

    A binding is free to serialise with `json.dumps(..., ensure_ascii=True)`, which turns
    "je vegetarian" with an accent into "je vegetari\u00e1n". A plain substring search then misses
    it, and the runner reports a clean erasure over a store that kept the value verbatim. Erasure
    requests are overwhelmingly names and addresses, so the values most likely to be searched for
    are exactly the ones that carry non-ASCII characters. The runner cannot dictate a third party's
    encoding, so it searches for both forms.
    """
    if needle in haystack:
        return True
    escaped = needle.encode("unicode_escape").decode("ascii")
    if escaped != needle and escaped in haystack:
        return True
    try:                                    # and the reverse: an escaped dump decoded back
        return needle in haystack.encode("ascii", "ignore").decode("unicode_escape")
    except Exception:
        return False


def _scan(root):
    """Every file under `root` with its size and mtime. The observation primitive."""
    out = {}
    for base, _dirs, names in os.walk(root):
        for n in names:
            fp = os.path.join(base, n)
            try:
                st = os.stat(fp)
                out[fp] = (st.st_size, st.st_mtime_ns)
            except OSError:
                pass
    return out


def read_channel(root, before):
    """Read every byte written under a root THE RUNNER CHOSE, not one the binding named.

    THE FIFTH DESIGN. Each earlier one asked the subject something and was answered dishonestly:

      v1  `raw_dump()` -- returned "", or "{}", or a hard-coded list.
      v2  a canary the binding had to reproduce -- the sentinel was `hash(tuple(paths))`, a function
          of paths the BINDING chooses, computed in the same process, so a binding forged it, wrote
          it to a decoy, and passed with no store write at all.
      v3  `persisted_root()` plus a before/after scan -- the diff proves LIVENESS and never SCOPE, so
          a copy one directory above the declared root, or a decoy sub-root holding only a view file,
          was never looked at. And reading with errors="replace" was blind to a gzip side copy.

    So nothing about the location is asked. The runner allocates a private directory and points
    `tempfile.tempdir` at it while the store is built, so a store creating files the ordinary way
    lands inside it whether or not the binding admits where it writes. Files are read as BYTES and
    matched against every plausible encoding and container, because a value the reader cannot decode
    is a value it will certify as erased.

    THE GAP THAT REMAINS, stated rather than papered over: a write after this returns -- an atexit
    hook, a finalizer, a lazy flush -- is still missed. Closing it needs the case in a subprocess.
    """
    after = _scan(root)
    if not after:
        return None, "nothing was written under the runner-allocated root at all"
    touched = [f for f, meta in after.items() if before.get(f) != meta]
    chunks = []
    for fp in sorted(after):
        try:
            chunks.append(io.open(fp, "rb").read())
        except OSError:
            pass
    return chunks, "%d file(s) present, %d changed, read as bytes under a runner-allocated root" % (
        len(after), len(touched))


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
        if not (observed.get("_texts") or []):
            # `all([])` is True, so an empty list satisfied the faithfulness and cross-check tests
            # at once. A store that claims to assert nothing after a repair is a finding, not a pass.
            fails.append("the store reports no active propositions at all, so every check that reads "
                         "them is vacuous")
        if observed.get("store_property", {}).get("binding_disagrees_with_recall"):
            fails.append("the binding's active_texts disagrees with the adapter's own recall() for "
                         "%s; a self-reported store state is not evidence"
                         % observed["store_property"]["binding_disagrees_with_recall"][:3])
        for arm, got in observed.get("triad", {}).items():
            if arm not in (exp.get("triad") or {}) and got != "pass":
                fails.append("unspecified triad.%s = %s (case did not declare it; it must still "
                             "conform)" % (arm, got))
        if ("checkpoint_coverage" not in exp
                and observed.get("checkpoint_coverage") not in (None, "verified", "(absent)")):
            fails.append("unspecified checkpoint_coverage = %s (case did not declare it; it must "
                         "still conform)" % observed.get("checkpoint_coverage"))
        if "aggregate" not in exp and observed.get("aggregate") not in (None, "verified"):
            fails.append("unspecified aggregate = %s (case did not declare it; it must still "
                         "conform)" % observed.get("aggregate"))
    for key in ("checkpoint_coverage", "aggregate"):
        if key not in exp:
            continue
        want = exp[key]
        # A contract that permits a SET must be scored as a set. Our first version pinned `unknown`
        # where IDEA.md says "remain `partial` or `unknown`" -- the single value inspeximus happens
        # to emit -- so a conforming adapter answering `partial` would have failed our fixture. His
        # own reference test expects `partial` for a related shape.
        allowed = want if isinstance(want, list) else [want]
        if observed.get(key) not in allowed:
            fails.append("%s: expected one of %s, got %s" % (key, allowed, observed.get(key)))
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
        elif prop == "erased_text_absent_from_persisted_state":
            raw = observed.get("_raw")
            texts = observed.get("_texts") or []
            if not raw:
                fails.append("no persistence observed (%s), so erasure cannot be distinguished from "
                             "concealment. Absent evidence is not evidence of absence and this case "
                             "fails closed." % observed.get("channel", "unknown"))
            elif not all(any(present_in_bytes(t, c) for c in raw) for t in texts if t):
                fails.append("the observed bytes do not contain the store's own active propositions, "
                             "so what was scanned is not a faithful record of it")
            elif any(present_in_bytes(want, c) for c in raw):
                fails.append("CONCEALED, not erased: %r survives in the persisted state" % want)
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


def _implementation_identity(binding):
    """Digest the code actually graded. The spec tree was pinned to hex; the subject was anonymous.

    A conformance result that names its specification precisely and its implementation not at all
    cannot be re-checked by anyone, which is most of what a conformance result is for.
    """
    import hashlib
    out = {"binding_class": "%s.%s" % (type(binding).__module__, type(binding).__name__)}
    seen = {}
    for obj in (type(binding),):
        mod = sys.modules.get(obj.__module__)
        path = getattr(mod, "__file__", None)
        if path and os.path.exists(path):
            seen[os.path.basename(path)] = hashlib.sha256(
                io.open(path, "rb").read()).hexdigest()[:16]
    try:
        import inspeximus
        seen["inspeximus.__version__"] = getattr(inspeximus, "__version__", "unknown")
    except Exception:
        pass
    out["source_digests"] = seen
    return out


def source_digest(pkg, cited=()):
    """A deterministic digest of the source tree actually scored, so `--pkg` cannot be arbitrary.

    THE CITED FILES ARE PART OF THE TREE. An earlier version walked `prototype/` and `spec/` only,
    which left `IDEA.md` -- the normative source two of four cases quote -- outside the digest. A
    sentence forged into it was quoted by a case and the run went green with the digest UNCHANGED,
    so "a tampered tree is REFUSED" was false as published. Anything a case cites is now covered,
    wherever it lives, and the citation check reads the same bytes the digest binds.
    """
    import hashlib
    h = hashlib.sha256()
    roots = [os.path.join(pkg, "prototype"), os.path.join(pkg, "spec")]
    files = [os.path.join(pkg, c) for c in cited if os.path.exists(os.path.join(pkg, c))]
    for root in roots:
        for base, _dirs, names in os.walk(root):
            if "__pycache__" in base:
                continue
            for n in sorted(names):
                if n.endswith((".py", ".json", ".md")):
                    files.append(os.path.join(base, n))
    for path in sorted(set(files)):
        h.update(os.path.relpath(path, pkg).replace("\\", "/").encode("utf-8"))
        h.update(io.open(path, "rb").read())
    return h.hexdigest(), len(files)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/")
    ap.add_argument("--binding", default=None, help="module:Class implementing build/active_texts")
    ap.add_argument("--result", default=None,
                    help="write the result JSON here instead of beside the fixture")
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
    # The target is the FIXTURE's, not any implementation's. An earlier version imported
    # inspeximus here unconditionally, so a third party with their own binding got an ImportError
    # on line one of main() while the README promised nothing above InspeximusBinding named us.
    # It also meant the "source binding" compared two inspeximus-authored constants against an
    # inspeximus-authored fixture, which is a mirror, not a check.
    target = fixture.get("target", {})
    SPEC_COMMIT = target.get("commit", "(declared by the fixture only)")
    SPEC_G2_DIGEST = target.get("g2_digest", "")
    declared = getattr(binding, "spec_commit", None)
    if declared and target.get("commit") and declared != target["commit"]:
        raise AssertionError("the binding declares spec commit %s but the fixture targets %s"
                             % (declared[:12], target["commit"][:12]))
    cited = sorted({c["normative"]["source"].split(",")[0].strip()
                    for c in fixture["adapter_cases"] if c.get("normative", {}).get("source")})
    tree_digest, n_files = source_digest(a.pkg, cited)
    expected_tree = a.pkg_digest or target.get("source_tree_digest")
    if expected_tree and expected_tree.strip().lower() != tree_digest:
        a.pkg_digest = expected_tree
    if expected_tree and expected_tree.strip().lower() != tree_digest:
        raise AssertionError("REFUSED: --pkg does not match the declared source digest.\n"
                             "  declared : %s\n  scored   : %s" % (a.pkg_digest.strip(), tree_digest))

    out = {"fixture_status": fixture["status"],
           "binding": binding.name,
           # `binding.name` is self-declared: every adversarial binding in our own validation wrote
           # "inspeximus" into this file. Record the class that actually ran.
           "binding_class": "%s.%s" % (type(binding).__module__, type(binding).__name__),
           "spec_commit": SPEC_COMMIT, "g2_digest": SPEC_G2_DIGEST,
           "scored_tree_digest": tree_digest, "scored_files": n_files,
           "implementation": _implementation_identity(binding), "cases": []}
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

        # RULE 2: each declared method must be LOAD-BEARING, proven by stubbing it and requiring
        # the case to stop passing.
        #
        # The first version asked whether a function of that name was entered on the adapter. That
        # cannot fail: the controller drives 12 to 13 of the adapter's 14 methods on every run while
        # a case declares 3 or 4, so every case satisfied it automatically. The tell was in our own
        # audit, which had to require `sign` -- a method that is not on the adapter at all -- to make
        # the guard fire. It also had the opposite error: a real method supplied as a lambda reports
        # its code name as `<lambda>` and was scored MISSING despite running.
        required = list(case["positive_control"]["adapter_methods_required"])
        load_bearing, inert = [], []
        for method in required:
            noticed = False
            for variant in range(2):
                try:
                    stubbed = evaluate(case, binding, a.pkg, stub_method=(method, variant))
                    passes, _ = compare(case, stubbed)
                    if not passes:
                        noticed = True
                        break
                except IndexError:
                    break
                except ValueError:
                    # No stand-in exists for this name. That is not evidence of anything: it means
                    # the case declared a method this runner cannot probe, and crediting it was how
                    # `sign` and `absolutely_not_a_method` scored "load-bearing". Refuse the case.
                    raise AssertionError(
                        "case %r declares %r, which has no stand-in and therefore cannot be shown "
                        "load-bearing. A method the runner cannot probe must not be credited."
                        % (case["id"], method))
                except Exception:
                    noticed = True   # the case cannot even run without it: load-bearing
                    break
            (load_bearing if noticed else inert).append(method)
        control_ok = not inert
        missing = inert

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
        print("      control     : %d/%d declared methods are load-bearing%s"
              % (len(load_bearing), len(required),
                 "" if control_ok else " -- INERT (stubbing them changes nothing): %s" % inert))
        print("      mutation    : %s (%s)" % (case["mutation"]["flattering_behaviour"], mut_note))
        out["cases"].append({
            "id": case["id"], "pass": good, "expectation_met": ok, "failures": fails,
            "normative_source": case["normative"]["source"],
            "methods_required": sorted(required), "methods_load_bearing": sorted(load_bearing),
            "methods_inert": sorted(inert),
            "positive_control_ok": control_ok, "mutation_caught": mutation_caught,
            "observed": {k: v for k, v in observed.items() if not k.startswith("_")}})

    total = len(fixture["adapter_cases"])
    print("\n%d/%d candidate adapter cases pass for %s" % (passed, total, binding.name))
    print("This is not G2 or G4 evidence. %s" % fixture["authored_by"]["disclosure"])
    out["totals"] = {"cases": total, "passed": passed}
    # The audit runs with `--result` pointing at a throwaway file. Without that it overwrote the
    # PUBLISHED result, so the artifact we shipped was a mutant run from inside the audit.
    dest = a.result or RESULT
    io.open(dest, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("wrote %s" % os.path.basename(dest))
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

    def persisted_root(self, handle):
        """The DIRECTORY this store persists into. Not a file list, and not a dump.

        The runner scans it before and after the case and reads whatever changed, so sidecars this
        binding never mentions -- receipts, tombstones, indexes -- are covered without either side
        having to enumerate them. Declaring one file was how a previous version measured an erasure
        over a third of the persistence surface.
        """
        return os.path.dirname(os.path.abspath(getattr(handle, "path", "") or "."))


if __name__ == "__main__":
    sys.exit(main())
