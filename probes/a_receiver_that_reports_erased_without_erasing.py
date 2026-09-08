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

AND THE OUTBOX ARMS REGISTER TWO TARGETS, the receiver and the queue. NO memory store is in them.
A first version of the reply that cites this probe said "inspeximus erased it" about that arm, which
described an experiment that was never run. The `Inspeximus(...)` further down is a separate fixture
for the source-handle check.

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

CONNECTOR = os.path.join(tempfile.gettempdir(), "claude", "C--Users-Danculus-agora",
                         "5d882efe-89a3-4f28-a05d-2f4c4390562b", "scratchpad", "connector")
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
            if self.path == "/mnemo/v0":
                fr = (body.get("fact_record") or {})
                sources = fr.get("sources") or [{}]
                receiver.rows[fr.get("id")] = {
                    "subject": (sources[0] or {}).get("principal"), "text": fr.get("text") or ""}
                return self._send(200, {
                    "source_id": fr.get("id"), "ledger_record_id": "L-" + str(fr.get("id")),
                    "transaction_id": "T-" + str(fr.get("id")), "status": "committed",
                    "committed_at": 1.0,
                    "payload_sha256": __import__("hashlib").sha256(
                        json.dumps(body, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode("utf-8")).hexdigest()})
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


class OutboxTarget(ErasureTarget):
    """The connector's own durable queue, as an erasure target.

    Real code, our side of the wire. `producer_outbox.payload` is the canonical bytes of the whole
    envelope, delivered rows are retained so a replay resends identical bytes, and the published
    client has no DELETE at all. `can_delete=False` models it as shipped; True models the delete path
    this probe proposes, so the arms differ by exactly the thing under discussion.
    """
    name = "connector-outbox"

    def __init__(self, db_path, can_delete):
        self.db_path = db_path
        self.can_delete = can_delete

    def _rows(self, subject):
        import sqlite3
        with sqlite3.connect(self.db_path) as c:
            return [(r[0], bytes(r[1])) for r in
                    c.execute("SELECT source_id, payload FROM producer_outbox").fetchall()
                    if subject.encode("utf-8") in bytes(r[1])]

    def erase(self, subject):
        hit = self._rows(subject)
        if self.can_delete:
            import sqlite3
            with sqlite3.connect(self.db_path) as c:
                c.executemany("DELETE FROM producer_outbox WHERE source_id=?",
                              [(sid,) for sid, _ in hit])
                c.commit()
        return {"erased": len(hit)}

    def still_recoverable(self, subject, values):
        blob = b" ".join(p for _, p in self._rows(subject))
        return any(v and v.encode("utf-8") in blob for v in values)


def run_outbox_arm(can_delete):
    """Send one record carrying the secret through his real client, then try to erase it."""
    import sys as _sys
    for cand in (os.path.join(CONNECTOR, "src"), CONNECTOR):
        if os.path.isdir(cand) and cand not in _sys.path:
            _sys.path.insert(0, cand)
    try:
        from memstrata_mnemo_connector import DeliveryCredentials, DurableOutbox
    except ImportError:
        return None

    receiver = Receiver(deletes=True)
    srv, port = serve(receiver)
    db = os.path.join(tempfile.mkdtemp(prefix="outbox-arm-"), "outbox.sqlite3")
    box = DurableOutbox(db, "http://127.0.0.1:%d/mnemo/v0" % port, allow_loopback_http=True,
                        max_attempts=2, base_backoff=0.01, max_backoff=0.02)
    env = {"version": "schema_v0", "fact_record": {
        "id": "synthetic-erasure-001", "valid_from": 1782700000.0, "recorded_at": 1782700000.4,
        "key": "example-billing::contact", "subject": "example-billing", "relation": "contact",
        "object": None, "text": "Contact for example-billing is %s." % SECRET,
        "sources": [{"channel": "doc", "principal": SUBJECT}],
        "corroboration_count": 1, "mtype": "semantic", "status": "active"}}
    box.enqueue(env)
    import time as _t
    t0 = _t.time()
    r = box.deliver_next(credentials=DeliveryCredentials(bearer_token=TOKEN))
    while r is None and _t.time() - t0 < 15:
        _t.sleep(0.02)
        r = box.deliver_next(credentials=DeliveryCredentials(bearer_token=TOKEN))

    m = DeletionManifest()
    m.register(make_target(port, "receiver-that-deletes"))
    target = OutboxTarget(db, can_delete)
    m.register(target)
    out = m.execute(SUBJECT, [SECRET], request_id="REQ-001", basis="GDPR Art.17",
                    authorized_by="data-subject")
    srv.shutdown()
    return {"delivered": r is not None and r.state == "delivered", "manifest": out,
            "still_there": target.still_recoverable(SUBJECT, [SECRET])}


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

    # THE ONE REAL STORE IN THIS PROBE, and it is ours. The connector's outbox retains the whole
    # envelope in plaintext and the published client has no DELETE, so a subject erased from both
    # memory stores is still in the queue that sent it.
    as_shipped = run_outbox_arm(can_delete=False)
    with_delete = run_outbox_arm(can_delete=True)
    if as_shipped is None or with_delete is None:
        print("\n  outbox arms SKIPPED: his client is not importable here")
    else:
        print("\n  D  outbox as shipped, no delete path: complete=%s residual=%s  secret still in queue=%s"
              % (as_shipped["manifest"].get("complete"), as_shipped["manifest"].get("residual_targets"), as_shipped["still_there"]))
        print("  E  outbox with the delete path:      complete=%s residual=%s  secret still in queue=%s"
              % (with_delete["manifest"].get("complete"), with_delete["manifest"].get("residual_targets"), with_delete["still_there"]))
        check("D_the_record_reached_the_receiver", as_shipped["delivered"], as_shipped["delivered"])
        check("D_OUR_OWN_OUTBOX_LEAKS_and_is_named",
              as_shipped["manifest"].get("complete") is False
              and "connector-outbox" in (as_shipped["manifest"].get("residual_targets") or [])
              and as_shipped["still_there"] is True,
              as_shipped["manifest"].get("residual_targets"))
        check("E_the_proposed_delete_path_closes_it",
              with_delete["manifest"].get("complete") is True
              and not with_delete["manifest"].get("residual_targets") and with_delete["still_there"] is False,
              with_delete["manifest"].get("complete"))
        check("CONTROL_D_and_E_differ_only_by_the_delete_path",
              as_shipped["manifest"].get("complete") != with_delete["manifest"].get("complete"),
              "so D is a measurement, not a broken target")

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
           "outbox_arms": ({"as_shipped": {"complete": as_shipped["manifest"].get("complete"),
                                           "residual_targets": as_shipped["manifest"].get("residual_targets"),
                                           "secret_still_in_queue": as_shipped["still_there"]},
                            "with_delete_path": {"complete": with_delete["manifest"].get("complete"),
                                                 "secret_still_in_queue": with_delete["still_there"]}}
                           if as_shipped and with_delete else None),
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
