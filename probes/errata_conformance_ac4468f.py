"""Run the LLM Errata conformance vectors at ac4468f, and MEASURE which layer each case tests.

WHY THIS EXISTS. We told the spec's author we would score inspeximus against
`spec/vectors/protocol-manifest.json`, `spec/vectors/receipt-binding-mutations.json` and the fixtures
under `spec/semantic/`, and publish the raw results whether they flatter us or not. This is that runner.

WHAT IT IS NOT: new coverage. `tests/test_schema.py` at this commit already executes every one of
these cases in CI -- the feed rules, the split-view pair, the confidentiality search and all fourteen
receipt-field mutations. This file was written against a PARTIAL local copy of the repository that
contained only `prototype/` and `spec/`, and on that evidence "the vectors ship with no consumer"
looked true and would have been sent upstream as a finding. It is false. The tree at ac4468f carries
seventeen test modules. A directory listing of an incomplete extract is not a claim about a repository.

So what this run contributes is two things, and neither is a runner:

  1. INDEPENDENT REPRODUCTION. A second implementation, written from the vector files rather than from
     his test code, reaches the same verdicts on all 28 cases.
  2. THE ATTRIBUTION MEASUREMENT BELOW, which his suite does not make and which is the actual finding.

THE HONEST PROBLEM WITH CALLING IT "OUR SCORE", which is the finding rather than a caveat: our
contribution is a StoreAdapter. Two of the three vector sets exercise the feed authenticator and the
receipt signer, which are the reference implementation's own code. A percentage over all three sets
would mostly be reporting how well the author's code passes the author's vectors, with our name on it.

So this runner does not assert which cases touch inspeximus. It MEASURES it: every case runs under
`sys.settrace` and records the set of functions executed inside the inspeximus package. Cases are then
attributed by evidence. The two controls below are what make that measurement worth anything:

  CONTROL 1 (the tracer can see us):  at least one case MUST record inspeximus frames.
  CONTROL 2 (the tracer is not stuck on): at least one case MUST record none. Without this, a tracer
      that returns every function it sees -- or one pointed at the wrong directory, matching nothing or
      everything -- would produce a clean-looking attribution table that means nothing at all.

Both controls have to hold or the run aborts, because an attribution table is exactly the kind of
artifact that looks authoritative while measuring nothing.

    python errata_conformance_ac4468f.py --pkg <dir containing prototype/ and spec/>
"""
import argparse
import io
import json
import os
import sys

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
SPEC = "ac4468faf73c2cc7949dd29b2a2a151f5bd23116"
DIGEST = "7e0d6c88c1ca3a87743ac70ba2a3dfea0b350d112d2d3c59a3c6cbb537568f12"


class Tracer:
    """Record which functions inside `root` actually executed.

    Returns None from the trace callback so only `call` events fire: we want the set of functions
    entered, not a line profile, and line tracing on a signature loop is needlessly slow.
    """

    def __init__(self, root):
        self.root = os.path.normcase(os.path.abspath(root))
        self.hits = set()

    def _trace(self, frame, event, arg):
        if event == "call":
            path = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
            if path.startswith(self.root):
                self.hits.add("%s:%s" % (os.path.basename(path), frame.f_code.co_name))
        return None

    def __enter__(self):
        self.hits = set()
        sys.settrace(self._trace)
        return self

    def __exit__(self, *exc):
        sys.settrace(None)
        return False


def _signer(label, key_id):
    from prototype.signing import Ed25519Signer
    return Ed25519Signer(label.encode("utf-8"), key_id=key_id)


def _erratum(ev, signers):
    """Build a well-formed erratum for a vector event, then sign it with the named key.

    The vectors state only the fields the case is about (sequence, signer, operation, target). The
    rest has to be well formed or `_check_shape` rejects every case for the wrong reason, which would
    make all four feed cases 'pass' as rejections and hide whatever they were each meant to test.
    """
    from prototype.errata import Erratum, Operation
    op = Operation(ev["operation"])
    post = {"negative": "vegetarian", "preserve": "quiet restaurants"}
    replacement = None
    if op is not Operation.ERASE:
        post["positive"] = "eats meat again"
        replacement = "eats meat again"
    err = Erratum(
        erratum_id=ev["erratum_id"], sequence=ev["sequence"], target_root=ev["target_root"],
        operation=op, valid_from="2026-08-01T00:00:00Z", postconditions=post,
        replacement=replacement)
    return signers[ev["signer"]].sign_erratum(err)


def _schedule(case, signers):
    from prototype.errata import OwnerKeySchedule
    return OwnerKeySchedule(tuple(
        (s["sequence"], signers[s["key_id"]].public) for s in case["schedule"]))


def run_feed_cases(manifest, tracer):
    """protocol-manifest.json: key rotation, rotated-key reuse, sequence conflict, invalid target."""
    from prototype.errata import FeedError, RootRegistry, verify_feed
    rows = []
    for case in manifest["feed_cases"]:
        signers = {kid: _signer(label, kid) for kid, label in case["keys"].items()}
        roots = RootRegistry(tuple(case["roots"]))
        errata = [_erratum(ev, signers) for ev in case["events"]]
        expected = case["outcome"]
        with tracer as t:
            try:
                verify_feed(errata, owner=_schedule(case, signers), roots=roots)
                actual, detail = "accept", ""
            except FeedError as exc:
                actual, detail = "reject", str(exc)
        ok = actual == expected
        # A rejection for the WRONG reason is not a pass. `error_contains` is the vector's own way of
        # saying so, and without checking it every malformed fixture would score as a correct reject.
        if ok and expected == "reject" and case.get("error_contains"):
            ok = case["error_contains"].lower() in detail.lower()
        rows.append({"id": case["id"], "expected": expected, "actual": actual, "pass": ok,
                     "detail": detail[:160], "inspeximus_frames": sorted(t.hits)})
    return rows


def run_split_view(manifest, tracer):
    """The case whose expected outcome is that NEITHER importer can tell.

    Each view must verify on its own, and the two must be genuinely different events at the same
    sequence. If the fingerprints matched, the fixture would not be showing equivocation at all.
    """
    from prototype.errata import RootRegistry, event_fingerprint, verify_feed
    rows = []
    for case in manifest.get("split_view_cases", []):
        signers = {kid: _signer(label, kid) for kid, label in case["keys"].items()}
        roots = RootRegistry(tuple(case["roots"]))
        accepted, prints = [], []
        with tracer as t:
            for view in case["views"]:
                errata = [_erratum(ev, signers) for ev in view]
                try:
                    verify_feed(errata, owner=_schedule(case, signers), roots=roots)
                    accepted.append(True)
                except Exception:
                    accepted.append(False)
                prints.append(event_fingerprint(errata[0]))
        ok = all(accepted) and len(set(prints)) == len(prints)
        rows.append({"id": case["id"], "expected": case["outcome"],
                     "actual": "accept-each-view; fingerprints differ; no local detector"
                               if ok else "unexpected",
                     "pass": ok, "detail": "views accepted=%s distinct_fingerprints=%d/%d"
                     % (accepted, len(set(prints)), len(prints)),
                     "inspeximus_frames": sorted(t.hits)})
    return rows


def run_receipt_binding(mutations, tracer):
    """Every signed receipt field must be bound: reusing the signature after a mutation must fail.

    An UNBOUND field is the interesting outcome here, not a passing row -- it would mean a receipt
    could be altered in that field and still verify.
    """
    from prototype.adapters import Coverage
    from prototype.receipts import Receipt
    signer = _signer("synthetic-importer", "importer-v1")
    base = Receipt(
        importer="reference-importer", erratum_id="err_0001", sequence=1,
        target_root="mem_01HX", operation="supersede",
        pre_state_root="a" * 32, post_state_root="b" * 32,
        stores={"markdown": Coverage.VERIFIED},
        dispositions={"markdown": {"fact:diet": "superseded"}},
        triad={"negative": "pass", "positive": "pass", "preserve": "pass"},
        aggregate=Coverage.VERIFIED, limitations=["none"], history_retained=True,
        adapter_versions={"markdown": "1.0.0"})
    base = base.__class__(**{**base.__dict__, "signature": signer.sign(base.signable())})
    assert base.verify(signer.public), "the unmutated receipt must verify, or the test is vacuous"

    def coerce(field, value):
        if field == "stores":
            return {k: Coverage(v) for k, v in value.items()}
        if field == "aggregate":
            return Coverage(value)
        if field == "limitations":
            return list(value)
        return value

    rows = []
    for field, value in mutations["fields"].items():
        mutated = base.__class__(**{**base.__dict__, field: coerce(field, value)})
        with tracer as t:
            still_verifies = mutated.verify(signer.public)
        rows.append({"id": "receipt-field:%s" % field, "expected": "signature fails",
                     "actual": "signature still verifies" if still_verifies else "signature fails",
                     "pass": not still_verifies,
                     "detail": "UNBOUND FIELD" if still_verifies else "bound",
                     "inspeximus_frames": sorted(t.hits)})
    return rows


def run_semantic(probes_doc, obs_doc, config_doc, tracer):
    """spec/semantic: replay recorded observations and check the derived coverage.

    WHERE THE EXPECTATIONS COME FROM, and why not from the case name. Three cases are named
    `<coverage>-<operation>`, so splitting on the hyphen reads their expected value correctly. The
    other five are named for a FAILURE MODE (`provider-error`, `configuration-drift`), and the same
    split yields "provider" and "configuration", which match no coverage value and therefore score as
    failures no matter what the implementation does. This runner did exactly that on its first run and
    was about to report five defects in the author's own fixtures to the author.

    So the expectations are read from where the spec actually states them, spec/README.md: "The latter
    five prove coverage refuses provider error, missing evidence, duplicate evidence, binding drift,
    and a structurally parseable operation mismatch. They are semantic `unknown` outcomes."
    """
    degradation = {"provider-error", "missing-response", "duplicate-response",
                   "configuration-drift", "nonconforming-output"}
    from prototype.semantic import (RecordedSemanticVerifier, SemanticObservation, SemanticProbe,
                                    SemanticProbeRunner, VerifierConfig)
    config = VerifierConfig.from_dict(config_doc)
    runner = SemanticProbeRunner()
    rows = []
    for name, probe_items in probes_doc["cases"].items():
        expected = "unknown" if name in degradation else name.split("-")[0]
        assert expected in ("verified", "unknown", "failed"), (
            "case %r has no stated expectation; guessing one is how this runner nearly filed five "
            "false defects against the spec" % name)
        probes = [SemanticProbe.from_dict(p) for p in probe_items]
        obs = [SemanticObservation.from_dict(o) for o in obs_doc["cases"].get(name, [])]
        with tracer as t:
            try:
                report = runner.run(probes, config, RecordedSemanticVerifier(obs))
                actual = getattr(report.coverage, "value", str(report.coverage))
                detail = "%d probes, %d observations" % (len(probes), len(obs))
            except Exception as exc:
                actual, detail = "error", "%s: %s" % (type(exc).__name__, exc)
        rows.append({"id": "semantic:%s" % name, "expected": expected, "actual": actual,
                     "pass": actual == expected, "detail": detail[:160],
                     "inspeximus_frames": sorted(t.hits)})
    return rows


def run_confidentiality(case, tracer, inspeximus_dir):
    """The erased content must not survive inside the evidence that proves it was erased.

    This is the one manifest case that runs against OUR store, so it is the one whose result is
    actually about inspeximus. The receipt is serialised and searched for the forbidden value.
    """
    import tempfile
    from prototype.errata import Erratum, Operation
    from prototype.scenario import build_importer
    from prototype.signing import Ed25519Signer
    from inspeximus import Inspeximus
    from inspeximus.integrations.llm_errata import InspeximusErrataAdapter

    owner = Ed25519Signer(b"\x01" * 32, key_id="key-1")
    m = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "m.json"), receipts=True)
    m.remember("is vegetarian", source={"doc": "fact:diet"}, key="diet")
    m.remember("prefers quiet restaurants", source={"doc": "fact:rest"}, key="rest")
    imp = build_importer(owner)
    imp.adapters = [InspeximusErrataAdapter(m)]
    imp.roots = ("fact:diet",)
    err = owner.sign_erratum(Erratum(
        erratum_id="e-erase", sequence=1, target_root="fact:diet", operation=Operation.ERASE,
        valid_from="2026-08-01T00:00:00Z",
        postconditions={"negative": case["negative_probe"], "preserve": "quiet restaurants"}))
    with tracer as t:
        imp.quarantine(err)
        receipt = imp.repair(err)
        blob = json.dumps(receipt.to_dict(), default=str)
    leaked = case["forbidden_value"] in blob
    return [{"id": case["id"], "expected": "erased content absent from the receipt",
             "actual": "LEAKED" if leaked else "absent", "pass": not leaked,
             "detail": "searched %d serialised bytes for %r" % (len(blob), case["forbidden_value"]),
             "inspeximus_frames": sorted(t.hits)}]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="directory containing prototype/ and spec/")
    ap.add_argument("--inspeximus", default=r"C:/Users/Danculus/inspeximus-repo")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, a.inspeximus)

    from inspeximus.integrations.llm_errata import SPEC_COMMIT, SPEC_G2_DIGEST
    assert SPEC_COMMIT == SPEC, "adapter is bound to %s, not the target" % SPEC_COMMIT[:12]
    assert SPEC_G2_DIGEST == DIGEST, "adapter carries a different G2 digest"

    def load(rel):
        return json.load(io.open(os.path.join(a.pkg, rel), encoding="utf-8"))

    manifest = load("spec/vectors/protocol-manifest.json")
    mutations = load("spec/vectors/receipt-binding-mutations.json")
    probes_doc = load("spec/semantic/probes.json")
    obs_doc = load("spec/semantic/observations.json")
    config_doc = load("spec/semantic/verifier-config.json")

    tracer = Tracer(os.path.join(a.inspeximus, "inspeximus"))
    sections = [
        ("protocol-manifest / feed", run_feed_cases(manifest, tracer)),
        ("protocol-manifest / split-view", run_split_view(manifest, tracer)),
        ("protocol-manifest / confidentiality",
         run_confidentiality(manifest["confidentiality_case"], tracer, a.inspeximus)),
        ("receipt-binding-mutations", run_receipt_binding(mutations, tracer)),
        ("semantic fixtures", run_semantic(probes_doc, obs_doc, config_doc, tracer)),
    ]

    out = {"spec_commit": SPEC, "g2_digest": DIGEST, "sections": {}}
    total = passed = touching = 0
    print("LLM Errata conformance vectors at %s\n" % SPEC[:12])
    for title, rows in sections:
        ours = sum(1 for r in rows if r["inspeximus_frames"])
        print("=== %s === (%d/%d pass; %d case(s) execute inspeximus code)"
              % (title, sum(1 for r in rows if r["pass"]), len(rows), ours))
        for r in rows:
            print("  [%s] %-34s %s%s" % ("PASS" if r["pass"] else "FAIL", r["id"],
                                         r["actual"], "  <- ours" if r["inspeximus_frames"] else ""))
            if not r["pass"] and r["detail"]:
                print("         %s" % r["detail"])
        out["sections"][title] = rows
        total += len(rows)
        passed += sum(1 for r in rows if r["pass"])
        touching += ours
        print()

    # THE CONTROLS. An attribution table is exactly the artifact that looks authoritative while
    # measuring nothing, so the tracer has to demonstrate it can answer both ways on this same run.
    assert touching > 0, "CONTROL 1 FAILED: the tracer saw inspeximus in no case; it is not wired up"
    assert touching < total, (
        "CONTROL 2 FAILED: the tracer claims every case runs inspeximus code, including pure "
        "signature checks that cannot. It is matching on the wrong directory.")

    out["totals"] = {"cases": total, "passed": passed,
                     "cases_executing_inspeximus": touching,
                     "cases_reference_only": total - touching}
    print("TOTAL          : %d/%d cases pass" % (passed, total))
    print("OURS (measured): %d of %d cases execute inspeximus code; %d exercise the reference"
          % (touching, total, total - touching))
    print("               : so %d/%d is NOT an inspeximus conformance score, and this run says so."
          % (passed, total))
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
