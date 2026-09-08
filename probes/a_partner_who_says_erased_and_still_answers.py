"""Erasure across two systems, where the second one is not ours and may be wrong.

WHY THIS EXISTS. @yadu9989 asked, on DanceNitra/agora discussion #2 (2026-09-08): "I'd like us to
agree how revisions and deletion should work before we move beyond synthetic or approved public
records." His schema_v0 pilot names source revisions, retractions, erasure and deletion propagation
as out of scope, so the question is open and it is the one our product exists to answer.

The design problem is not the wire format. It is that a bitemporal ledger and an erasure request want
opposite things. His contract says "the earlier record remains in the history", which is correct for
supersession and is exactly what an erasure must undo. So a deletion contract needs three operations
where schema_v0 has one:

  SUPERSEDED  the value changed; the old value is kept and remains readable as history.
  RETRACTED   the record was wrong; it stops being evidence, the ACT stays auditable, and the content
              may remain for audit.
  ERASED      the subject withdrew consent; the content must not remain, in history either. Only a
              content-free tombstone and a proof of the act survive.

THE HARD PART IS NOT ERASING. It is knowing whether the OTHER side really did. inspeximus already has
the primitive: `ErasureTarget` is a two-method adapter (`erase`, `still_recoverable`) and
`DeletionManifest.execute` marks an erasure complete only if EVERY registered store verified the data
absent, naming the ones that still leak. This probe puts a partner ledger behind that protocol over
real HTTP, so the proposal is a running thing rather than a paragraph.

THE CONTROL IS THE POINT. Two partners are run against identical requests:

  HONEST   erases, and then answers still_recoverable = False.
  LYING    reports a healthy {"erased": 3}, and still returns the value when asked for it.

If the manifest cannot tell those apart, it is decoration. The assertion is that the lying partner
produces an INCOMPLETE manifest that NAMES it, while the honest one produces a complete one. A probe
that only ran the honest arm would pass while measuring nothing, which is this repository's
most expensive recurring defect.

AND ONE MEASURED GAP IN THE WIRE FORMAT WE ALREADY AGREED. schema_v0 carries sources as
{channel, principal}. inspeximus resolves erasure on a `doc` identifier and refuses a source without
one: "remember(source=...) needs a 'doc' key -- it is the identifier erasure, slashing and
attribution all resolve on." So "erase everything attributable to source X" cannot be expressed in
schema_v0 at all. That is a schema_v1 field, not an implementation detail, and the probe demonstrates
the failure rather than describing it.
"""
import http.server
import json
import os
import socket
import sys
import tempfile
import threading

try:
    from inspeximus import Inspeximus
    from inspeximus.deletion_manifest import DeletionManifest, ErasureTarget
except ImportError:
    Inspeximus = None

SUBJECT = "synthetic-runbook"
SECRET = "jane@example.com"
TOKEN = "local-fixture-token-not-a-secret"


class PartnerLedger:
    """Stands in for a read-side ledger. `honest` decides whether it tells the truth afterwards."""

    def __init__(self, honest):
        self.honest = honest
        self.rows = {}

    def write(self, rid, subject, text):
        self.rows[rid] = {"subject": subject, "text": text}

    def erase(self, subject):
        gone = [k for k, v in self.rows.items() if v["subject"] == subject]
        if self.honest:
            for k in gone:
                del self.rows[k]
        return len(gone)          # a LYING partner reports the same count and keeps the rows

    def recoverable(self, subject, values):
        hay = " ".join(v["text"] for v in self.rows.values() if v["subject"] == subject)
        return [v for v in values if v and v in hay]


def serve(ledger):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body):
            raw = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if self.headers.get("Authorization") != "Bearer " + TOKEN:
                return self._send(401, {"reason": "unauthorized"})
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if self.path == "/mnemo/v0/erase":
                return self._send(200, {"erased": ledger.erase(body.get("subject")),
                                        "request_id": body.get("request_id")})
            if self.path == "/mnemo/v0/still_recoverable":
                hits = ledger.recoverable(body.get("subject"), body.get("values") or [])
                return self._send(200, {"recoverable": bool(hits), "matched": len(hits)})
            self._send(404, {"reason": "unknown path"})

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def make_target(port, name):
    """The proposed extension, in the form inspeximus already accepts: two endpoints, two methods."""
    import urllib.request

    def call(path, payload):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/mnemo/v0/%s" % (port, path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    class HttpTarget(ErasureTarget):
        pass

    HttpTarget.name = name
    HttpTarget.erase = lambda self, subject: {"erased": call("erase", {
        "subject": subject, "request_id": "REQ-001", "basis": "GDPR Art.17",
        "authorized_by": "data-subject"})["erased"]}
    HttpTarget.still_recoverable = lambda self, subject, values: bool(
        call("still_recoverable", {"subject": subject, "values": list(values)})["recoverable"])
    return HttpTarget()


def run_arm(honest):
    ledger = PartnerLedger(honest)
    ledger.write("L1", SUBJECT, "Contact for example-billing is %s." % SECRET)
    ledger.write("L2", SUBJECT, "The example billing service authenticates with signed requests.")
    srv, port = serve(ledger)
    name = "memstrata-ledger" + ("" if honest else "-that-lies")
    m = DeletionManifest()
    m.register(make_target(port, name))
    out = m.execute(SUBJECT, [SECRET], request_id="REQ-001", basis="GDPR Art.17",
                    authorized_by="data-subject")
    ok, problems = m.verify(out)
    srv.shutdown()
    return name, out, ok, problems


def main():
    if Inspeximus is None:
        print("  SKIPPED: inspeximus is not importable here.")
        return 0

    checks, ok_all = [], True

    def check(name, cond, got=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-52s %s" % ("YES" if cond else "NO", name, got))

    print("\n  ARM 1: a partner that erases and says so truthfully")
    hname, honest, hverified, hproblems = run_arm(True)
    print("    complete=%s  residual=%s" % (honest.get("complete"), honest.get("residual_targets")))
    check("honest_partner_gives_a_complete_manifest", honest.get("complete") is True,
          honest.get("complete"))
    check("honest_partner_is_not_named_as_residual", not honest.get("residual_targets"),
          honest.get("residual_targets"))
    check("and_the_manifest_verifies", hverified, hproblems)

    print("\n  ARM 2: a partner that reports the SAME erased count and still answers")
    lname, lying, lverified, lproblems = run_arm(False)
    print("    complete=%s  residual=%s" % (lying.get("complete"), lying.get("residual_targets")))
    check("THE_POINT_lying_partner_is_not_complete", lying.get("complete") is False,
          lying.get("complete"))
    check("THE_POINT_and_the_manifest_names_it", lname in (lying.get("residual_targets") or []),
          lying.get("residual_targets"))
    check("the_lying_manifest_still_verifies_as_a_document", lverified, lproblems)

    print("\n  CONTROLS")
    he = [e for e in (honest.get("entries") or []) if e.get("target") == hname]
    le = [e for e in (lying.get("entries") or []) if e.get("target") == lname]
    check("CONTROL_both_arms_reported_the_same_erased_count",
          he and le and he[0].get("erased") == le[0].get("erased"),
          "%s vs %s" % (he and he[0].get("erased"), le and le[0].get("erased")))
    check("CONTROL_so_the_count_is_not_what_separated_them",
          honest.get("complete") != lying.get("complete"), "only the recheck did")

    # THE WIRE-FORMAT GAP, demonstrated rather than asserted.
    print("\n  THE schema_v0 GAP: its source shape carries no erasure handle")
    store = Inspeximus(os.path.join(tempfile.mkdtemp(prefix="erasure-handle-"), "store.json"))
    refused = None
    try:
        store.remember("x", key="k::v", source={"channel": "doc", "principal": SUBJECT})
    except ValueError as e:
        refused = str(e)
    print("    schema_v0 source {channel, principal}: %s"
          % ("REFUSED -- " + refused.split(".")[0] if refused else "accepted"))
    store.remember("Contact for example-billing is %s." % SECRET, key="billing::contact",
                   source={"doc": SUBJECT, "channel": "doc", "principal": SUBJECT})
    erased = store.forget_subject(SUBJECT, request_id="REQ-001", basis="GDPR Art.17",
                                 authorized_by="data-subject")
    check("schema_v0_source_has_no_doc_handle", refused is not None and "'doc' key" in refused,
          "so 'erase everything from source X' cannot be expressed on the wire")
    check("CONTROL_with_a_doc_handle_the_same_erasure_works", erased.get("erased", 0) >= 1,
          "erased=%s" % erased.get("erased"))

    out = {"probe": os.path.basename(__file__), "checks": checks, "all_passed": ok_all,
           "honest_arm": {"complete": honest.get("complete"),
                          "residual_targets": honest.get("residual_targets")},
           "lying_arm": {"complete": lying.get("complete"),
                         "residual_targets": lying.get("residual_targets")},
           "proposed_endpoints": ["POST /mnemo/v0/erase", "POST /mnemo/v0/still_recoverable"],
           "note": "The partner here is a fixture implementing the proposed contract, not MemStrata. "
                   "This shows the protocol catches a partner who reports success without erasing; "
                   "it shows nothing about any real service."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("all checks passed" if ok_all else "FAILED",
                                    os.path.basename(path)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
