"""Does a deletion receipt mean anything, and can our own check tell when it does not?

RENAMED from a_partner_who_says_erased_and_still_answers.py. The old name described a person: there
is exactly one partner in the conversation this feeds, so the filename read as a claim about him
rather than about a failure mode. It models a RECEIVER, and the two arms are now named for what they
do with the rows.

WHY THIS EXISTS. schema_v0 puts source revisions, retractions, erasure and deletion propagation out
of scope, and the read-side collaborator asked to settle them before either side leaves synthetic
data. The design problem is not the wire format. A bitemporal ledger and an erasure request want
opposite things: keeping the earlier record is right for supersession and is exactly what an erasure
must undo. So a deletion contract needs three operations where schema_v0 has one:

  SUPERSEDED  the value changed; the old value is kept and stays readable.
  RETRACTED   the record was wrong; it stops being evidence, the act stays auditable.
  ERASED      the content must not remain, in history either. Only a content-free tombstone survives.

THE CLAIM UNDER TEST is narrow and it is about our own instrument, not about anyone's honesty: an
`{"erased": N}` receipt cannot tell a caller whether the data is gone, and a manifest that re-asks
afterwards can. Three receivers, so that the count varies INDEPENDENTLY of the deletion:

  A  deletes, reports 2   -> the manifest must say complete
  B  does not delete, reports 2   -> the manifest must say incomplete, and name it
  C  deletes, reports 0   -> the manifest must STILL say complete

C is the arm that makes this a measurement. A and B alone share a fixture that computes its count
before it branches, so their counts are equal BY CONSTRUCTION and comparing them proves nothing. C
varies the count while holding the deletion fixed, which is the only way to show the verdict does not
consult the count. The first version of this probe had A and B only and called their equal counts a
control; it was a tautology, and it is recorded here rather than quietly removed.

AND THE VERIFIER IS GIVEN SOMETHING IT MUST REJECT. Two checks name `DeletionManifest.verify`. A
mutation audit replaced that method's body with `return (True, [])` and the probe still passed
everything, so neither check could see a verifier that had stopped verifying. A corrupted manifest is
now handed to it, and `verify` must return False on it or this probe fails.

WHAT THIS DOES NOT SHOW. `still_recoverable` here greps stored text. It cannot see a value that
survives in an embedding, in a cache, in freed database pages before a vacuum, or in the receiver's
own request log, and the last of those can be written by this very call. The manifest's own scope
statement excludes backups and embedding inversion; freed pages and request logs are not in that
list, and naming them is more useful than waiting to be told.
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


class Receiver:
    """A stand-in read-side store. `deletes` and `report` vary independently, which is the point."""

    def __init__(self, deletes, report=None):
        self.deletes = deletes
        self.report = report
        self.rows = {}

    def erase(self, subject):
        hit = [k for k, v in self.rows.items() if v["subject"] == subject]
        if self.deletes:
            for k in hit:
                del self.rows[k]
        return len(hit) if self.report is None else self.report

    def recoverable(self, subject, values):
        hay = " ".join(v["text"] for v in self.rows.values() if v["subject"] == subject)
        return [v for v in values if v and v in hay]


def serve(receiver):
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
                return self._send(200, {"erased": receiver.erase(body.get("subject")),
                                        "request_id": body.get("request_id")})
            if self.path == "/mnemo/v0/still_recoverable":
                hits = receiver.recoverable(body.get("subject"), body.get("values") or [])
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
    """The proposed extension in the shape inspeximus already accepts: two endpoints, two methods."""
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


def run_arm(name, deletes, report=None):
    r = Receiver(deletes, report)
    r.rows["L1"] = {"subject": SUBJECT, "text": "Contact for example-billing is %s." % SECRET}
    r.rows["L2"] = {"subject": SUBJECT, "text": "Billing authenticates with signed requests."}
    srv, port = serve(r)
    m = DeletionManifest()
    m.register(make_target(port, name))
    out = m.execute(SUBJECT, [SECRET], request_id="REQ-001", basis="GDPR Art.17",
                    authorized_by="data-subject")
    ok, problems = m.verify(out)
    srv.shutdown()
    reported = next((e.get("erased") for e in (out.get("entries") or [])
                     if e.get("target") == name), None)
    return {"name": name, "manifest": out, "verified": ok, "problems": problems,
            "reported": reported}


def main():
    if Inspeximus is None:
        print("  SKIPPED: inspeximus is not importable here.")
        return 0

    checks, ok_all = [], True

    def check(name, cond, got=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-54s %s" % ("YES" if cond else "NO", name, got))

    a = run_arm("receiver-that-deletes", deletes=True)
    b = run_arm("receiver-that-does-not-delete", deletes=False)
    c = run_arm("receiver-that-deletes-and-reports-zero", deletes=True, report=0)
    for arm in (a, b, c):
        print("  %-40s reported=%-4s complete=%-6s residual=%s"
              % (arm["name"], arm["reported"], arm["manifest"].get("complete"),
                 arm["manifest"].get("residual_targets")))
    print()

    check("A_deleting_receiver_is_complete", a["manifest"].get("complete") is True,
          a["manifest"].get("complete"))
    check("B_non_deleting_receiver_is_not_complete", b["manifest"].get("complete") is False,
          b["manifest"].get("complete"))
    check("B_and_the_manifest_names_it", b["name"] in (b["manifest"].get("residual_targets") or []),
          b["manifest"].get("residual_targets"))

    # THE ARM THAT MAKES THIS A MEASUREMENT. A and B report the same count because the fixture
    # computes it before it branches, so their equality is construction, not evidence. C holds the
    # deletion fixed and changes only the number, so a verdict that consulted the count would move.
    check("C_count_zero_but_data_gone_is_still_complete",
          c["reported"] == 0 and c["manifest"].get("complete") is True,
          "reported=%s complete=%s" % (c["reported"], c["manifest"].get("complete")))
    check("C_so_the_verdict_does_not_consult_the_count",
          a["manifest"].get("complete") == c["manifest"].get("complete")
          and a["reported"] != c["reported"],
          "A reported %s, C reported %s, both complete" % (a["reported"], c["reported"]))
    check("BY_CONSTRUCTION_A_and_B_report_the_same_count", a["reported"] == b["reported"],
          "%s and %s, equal because the fixture counts before it branches" % (a["reported"], b["reported"]))

    # POSITIVE CONTROL FOR THE VERIFIER. Replacing verify()'s body with `return (True, [])` used to
    # pass this probe, so both verify checks were blind. Hand it something it must reject.
    check("verify_accepts_an_intact_manifest", a["verified"], a["problems"])
    tampered = json.loads(json.dumps(b["manifest"]))
    if tampered.get("entries"):
        tampered["entries"][0]["still_recoverable"] = False
        tampered["complete"] = True
        tampered["residual_targets"] = []
    v_ok, v_problems = DeletionManifest().verify(tampered)
    check("CONTROL_verify_REJECTS_a_doctored_manifest", v_ok is False and bool(v_problems),
          v_problems[:2] if v_problems else "accepted it")

    # THE WIRE-FORMAT GAP, stated as narrowly as it is true.
    store = Inspeximus(os.path.join(tempfile.mkdtemp(prefix="erasure-handle-"), "store.json"))
    refused = None
    try:
        store.remember("x", key="k::v", source={"channel": "doc", "principal": SUBJECT})
    except ValueError as e:
        refused = str(e)
    store.remember("Contact for example-billing is %s." % SECRET, key="billing::contact",
                   source={"doc": SUBJECT, "channel": "doc", "principal": SUBJECT})
    erased = store.forget_subject(SUBJECT, request_id="REQ-001", basis="GDPR Art.17",
                                  authorized_by="data-subject")
    check("a_schema_v0_shaped_source_cannot_be_written_back",
          refused is not None and "'doc' key" in refused,
          "the value survives the hop; the ROLE does not")
    check("CONTROL_with_a_doc_handle_the_same_erasure_works", erased.get("erased", 0) >= 1,
          "erased=%s" % erased.get("erased"))

    out = {"probe": os.path.basename(__file__), "checks": checks, "all_passed": ok_all,
           "arms": {arm["name"]: {"reported": arm["reported"],
                                  "complete": arm["manifest"].get("complete"),
                                  "residual_targets": arm["manifest"].get("residual_targets")}
                    for arm in (a, b, c)},
           "proposed_endpoints": ["POST /mnemo/v0/erase", "POST /mnemo/v0/still_recoverable"],
           "not_covered_by_still_recoverable": [
               "a value surviving in an embedding", "a response or retrieval cache",
               "freed database pages before a vacuum",
               "the receiver's own request log, which this call can write"],
           "note": "The receivers are fixtures implementing the proposed contract. They model a "
                   "failure mode, not any party. Nothing here measures a real service."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("all checks passed" if ok_all else "FAILED",
                                    os.path.basename(path)))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
