"""The paired write, run end to end through the partner's own client before any token exists.

WHY THIS EXISTS. On 2026-07-03 we proposed the paired-write test on DanceNitra/agora discussion #2:
send a fact, then a newer value for the same key, and check that one clean supersession happened end
to end. On 2026-09-08 @yadu9989 published the receiving side and asked us to run our half. The live
run needs credentials neither side has exchanged yet.

So the half we CAN run is run here: his published client (`memstrata-inspeximus-connector`, MIT,
92 tests green) sends real bytes over real HTTP to a receiver that implements the rules his
`docs/API_CONTRACT.md` states. When the token arrives, only the URL and the credentials change.

TWO CHECKS CARRY THE THIRD STEP, not one, and a mutation audit is why that is spelled out.
`replay_returned_its_original_receipt` tests the replay path: remove the receiver's replay branch and
it goes red. `the_value_after_the_replay_is_still_the_new_one` tests the outcome and survives that
mutation, because the valid_from ordering rule refuses the stale write instead. Citing the second
alone would credit the probe with power it does not have.

THE ASSERTION THAT MATTERS is the third step, not the first two. Sending a fact and then a newer one
is easy to get right. The failure that costs a reader a correct answer is a RETRY: the sender resends
the older record's exact bytes after a lost reply, and a naive receiver treats it as a fresh write and
makes the stale value current again. Re-enqueueing on the SAME outbox is not that test and the first
version of this probe made that mistake: identical bytes return the id and add no row, so nothing
becomes due. The restart his contract asks for is a second sender over a fresh database. His contract says "a replay of an older, already accepted source
ID must not make its evidence current again". This probe sends that replay and then reads the current
value back.

CONTROLS, because a receiver that accepts nothing would pass the assertion above by doing nothing:
  * the two writes must both COMMIT, so the path is not dead;
  * after the pair, the current value must be the NEW one, so supersession actually fired;
  * a changed byte under an already-used id must be refused. Measured, his client is stronger than
    his contract documents here: `enqueue` looks the source id up first and raises SourceConflict
    BEFORE any network call, so a revision never reaches the wire at all. The receiver-side 409 is
    checked separately, from a restarted sender that has no local record of the id;
  * a stale-restore attempt at an older valid_from must be REJECTED, so the rule can fire;
  * and the receiver is asked, at the end, for a value it never stored, which must come back empty.
    Without that last one a receiver that answers every read with the newest thing it ever saw would
    pass every check above.

AND IT MEASURES A HAZARD IN OUR OWN EMITTER. `effective_value` is `value * 0.5^(age/half_life)` with
the clock reset on access, so it is time-dependent by our own definition. Re-emitting one record
therefore produces different bytes under the same id, which his receiver answers with 409 rather than
with the original receipt. His fixtures omit the field and our schema marks it optional, so omitting
it on the wire is both conformant and stable. The probe demonstrates the collision rather than
asserting it away.
"""
import hashlib
import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import time

CONNECTOR = os.path.join(tempfile.gettempdir(), "claude", "C--Users-Danculus-agora",
                         "5d882efe-89a3-4f28-a05d-2f4c4390562b", "scratchpad", "connector")
TOKEN = "local-fixture-token-not-a-secret"


def _client():
    """His published client, or a clear skip. We never reimplement his sender."""
    try:
        from memstrata_mnemo_connector import DeliveryCredentials, DurableOutbox, canonical_bytes
        return DeliveryCredentials, DurableOutbox, canonical_bytes
    except ImportError:
        for cand in (os.path.join(CONNECTOR, "src"), CONNECTOR):
            if os.path.isdir(cand):
                sys.path.insert(0, cand)
        try:
            from memstrata_mnemo_connector import DeliveryCredentials, DurableOutbox, canonical_bytes
            return DeliveryCredentials, DurableOutbox, canonical_bytes
        except ImportError:
            return None, None, None


class Ledger:
    """The receiver's rules, taken from his API_CONTRACT.md and nothing else.

    Deliberately minimal and deliberately NOT his implementation: this stands in for the endpoint so
    the client, the wire format and the ordering rules are exercised for real. It proves our side
    speaks the contract. It proves nothing about his service.
    """

    def __init__(self):
        self.by_id = {}          # source_id -> (digest, ack)
        self.current = {}        # key -> (valid_from, text, source_id)
        self.history = []
        self.n = 0

    def write(self, envelope, digest):
        fr = envelope.get("fact_record") or {}
        sid = fr.get("id")
        if not isinstance(sid, str) or not sid:
            return 400, {"status": "rejected", "reason": "missing id"}

        # Replay of the exact bytes returns the original receipt, and changes nothing.
        if sid in self.by_id:
            known, ack = self.by_id[sid]
            if known == digest:
                return 200, ack
            return 409, {"status": "rejected", "reason": "changed content under an existing id",
                         "source_id": sid, "ledger_record_id": "", "transaction_id": ""}

        if fr.get("status") != "active":
            return 400, {"status": "rejected", "reason": "this pilot accepts only active"}
        vf = fr.get("valid_from")
        if not isinstance(vf, (int, float)) or isinstance(vf, bool):
            return 400, {"status": "rejected", "reason": "valid_from must be a finite number"}

        key = fr.get("key")
        if key:
            cur = self.current.get(key)
            if cur and vf < cur[0]:
                return 409, {"status": "rejected", "reason": "older valid_from behind the current key",
                             "source_id": sid, "ledger_record_id": "", "transaction_id": ""}
            if cur and vf == cur[0] and fr.get("text") != cur[1]:
                return 409, {"status": "rejected", "reason": "conflicting value at the same valid time",
                             "source_id": sid, "ledger_record_id": "", "transaction_id": ""}

        self.n += 1
        ack = {"source_id": sid, "ledger_record_id": "L%04d" % self.n,
               "transaction_id": "T%04d" % self.n, "status": "committed",
               "committed_at": time.time(), "payload_sha256": digest}
        self.by_id[sid] = (digest, ack)
        if key:
            if key in self.current:
                self.history.append(self.current[key])
            self.current[key] = (vf, fr.get("text"), sid)
        return 200, ack

    def read(self, key):
        cur = self.current.get(key)
        return None if cur is None else {"valid_from": cur[0], "text": cur[1], "source_id": cur[2]}


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
                return self._send(401, {"status": "rejected", "reason": "unauthorized"})
            if self.path != "/mnemo/v0":
                return self._send(404, {"status": "rejected", "reason": "unknown path"})
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            digest = hashlib.sha256(raw).hexdigest()
            try:
                env = json.loads(raw.decode("utf-8"))
            except Exception:
                return self._send(400, {"status": "rejected", "reason": "invalid json"})
            code, body = ledger.write(env, digest)
            self._send(code, body)

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def main():
    Creds, Outbox, canon = _client()
    if Outbox is None:
        print("  SKIPPED: his client is not importable here, and this probe never reimplements it.")
        print("  pip install -e %s" % CONNECTOR)
        return 0

    fixtures = os.path.join(CONNECTOR, "fixtures")
    if not os.path.isdir(fixtures):
        print("  SKIPPED: his fixtures are not on this machine: %s" % fixtures)
        return 0
    before = json.load(open(os.path.join(fixtures, "before.json"), encoding="utf-8"))
    after = json.load(open(os.path.join(fixtures, "after.json"), encoding="utf-8"))
    key = before["fact_record"]["key"]

    ledger = Ledger()
    srv, port = serve(ledger)
    db = os.path.join(tempfile.mkdtemp(prefix="paired-"), "outbox.sqlite3")
    default_box = Outbox(db, "http://127.0.0.1:%d/mnemo/v0" % port, allow_loopback_http=True,
                 max_attempts=2, base_backoff=0.01, max_backoff=0.02)
    creds = Creds(bearer_token=TOKEN)

    def send(env, label, deadline_s=15.0, box=None):
        """Bounded. `deliver_next` returns None when nothing is due, so an unbounded loop here is a
        hang rather than patience: the first run of this probe wedged for two minutes and printed
        nothing, because the wait had no ceiling and the output was behind a pipe."""
        box = box if box is not None else default_box
        box.enqueue(env)
        t0 = time.time()
        r = box.deliver_next(credentials=creds)
        while r is None:
            if time.time() - t0 > deadline_s:
                print("    %-26s NOTHING BECAME DUE in %.0fs" % (label, deadline_s), flush=True)
                return None
            time.sleep(0.02)
            r = box.deliver_next(credentials=creds)
        print("    %-26s state=%-10s http=%s%s"
              % (label, r.state, r.http_status, "  " + (r.reason or "")), flush=True)
        return r

    checks, ok = [], True

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)})
        print("  %-4s %-46s %s" % ("YES" if cond else "NO", name, got))

    print("\n  1. the pair, through his client, over real HTTP:")
    r1 = send(before, "before (stale value)")
    r2 = send(after, "after  (current value)")
    cur = ledger.read(key)
    check("both_writes_committed", r1.state == "delivered" and r2.state == "delivered",
          "%s / %s" % (r1.state, r2.state))
    check("CONTROL_supersession_fired", cur and cur["text"] == after["fact_record"]["text"],
          cur and cur["text"])

    # A RE-ENQUEUE ON THE SAME OUTBOX IS NOT A RETRY, and the first run of this probe assumed it
    # was. His `enqueue` looks the source id up first: identical bytes return the id and add no row,
    # so nothing becomes due and the wait times out. The retry his contract describes is the sender
    # itself resending its retained bytes, and the check he asks for is "restart the client and
    # repeat the retry check". A second outbox over a fresh database is that restart.
    print("\n  2. the retry that matters: a RESTARTED sender resends the old record's exact bytes:")
    db2 = os.path.join(tempfile.mkdtemp(prefix="paired-restart-"), "outbox.sqlite3")
    box2 = Outbox(db2, "http://127.0.0.1:%d/mnemo/v0" % port, allow_loopback_http=True,
                  max_attempts=2, base_backoff=0.01, max_backoff=0.02)
    r3 = send(json.loads(json.dumps(before)), "retry of before", box=box2)
    cur_after_replay = ledger.read(key)
    first_receipt = ledger.by_id[before["fact_record"]["id"]][1]["ledger_record_id"]
    check("replay_returned_its_original_receipt",
          r3 is not None and r3.state == "delivered" and first_receipt == "L0001", first_receipt)
    # NOT the check with power over replay handling, despite what its first name said. Deleting
    # the receiver's replay branch leaves this green, because the valid_from ordering rule
    # refuses the stale write instead and the value ends up right for another reason. The check
    # above it is the one that goes red. Both are needed: one tests the replay path, one tests
    # the outcome.
    check("the_value_after_the_replay_is_still_the_new_one",
          cur_after_replay and cur_after_replay["text"] == after["fact_record"]["text"],
          cur_after_replay and cur_after_replay["text"])

    print("\n  3. controls, so the checks above are not passing by inertia:")
    # His client refuses a revision LOCALLY, before any network call, which is stronger than the
    # receiver-side 409 the contract documents. Both are checked: the client-side refusal on the
    # outbox that already holds the id, and the receiver-side 409 from a restarted sender.
    mutated = json.loads(json.dumps(before))
    mutated["fact_record"]["text"] = before["fact_record"]["text"] + " (edited)"
    try:
        default_box.enqueue(mutated)
        client_refused = False
    except Exception as e:
        client_refused = type(e).__name__ == "SourceConflict"
        print("    %-26s %s: %s" % ("changed bytes, same id", type(e).__name__, e), flush=True)
    check("CONTROL_client_refuses_a_revision_offline", client_refused,
          "raised before any network call")

    box3 = Outbox(os.path.join(tempfile.mkdtemp(prefix="paired-mut-"), "outbox.sqlite3"),
                  "http://127.0.0.1:%d/mnemo/v0" % port, allow_loopback_http=True,
                  max_attempts=1, base_backoff=0.01, max_backoff=0.02)
    r4 = send(mutated, "changed bytes, restarted", box=box3)
    check("CONTROL_receiver_answers_409", r4 is not None and r4.http_status == 409,
          r4 and r4.http_status)

    restore = json.loads(json.dumps(before))
    restore["fact_record"]["id"] = "synthetic-restore-attempt-003"
    r5 = send(restore, "stale restore, new id")
    check("CONTROL_stale_restore_rejected", r5 is not None and r5.http_status == 409,
          r5 and r5.http_status)
    check("CONTROL_and_it_did_not_take", ledger.read(key)["text"] == after["fact_record"]["text"],
          ledger.read(key)["text"])
    check("CONTROL_a_key_never_written_reads_empty", ledger.read("never::written") is None,
          ledger.read("never::written"))

    print("\n  4. our own emitter's field, measured rather than argued:")
    a = json.loads(json.dumps(before))
    a["fact_record"]["effective_value"] = 3.10
    b = json.loads(json.dumps(before))
    b["fact_record"]["effective_value"] = 3.09
    same = canon(a) == canon(b)
    print("    effective_value = value * 0.5^(age/half_life), clock reset on access.")
    print("    3.10 -> %s" % hashlib.sha256(canon(a)).hexdigest()[:16])
    print("    3.09 -> %s" % hashlib.sha256(canon(b)).hexdigest()[:16])
    # Renamed: this compares two canonical digests locally and never contacts the receiver, so
    # it observes no HTTP status. The consequence is a 409, and the contract says so; this check
    # measures the cause.
    check("effective_value_changes_the_bytes_under_one_id", not same,
          "so send it once and keep the bytes, or omit the field as his fixtures do")

    srv.shutdown()
    out = {"probe": os.path.basename(__file__), "checks": checks,
           "all_passed": ok, "current_value_at_end": ledger.read(key),
           "history_depth": len(ledger.history),
           "connector_commit": "yadu9989/memstrata-inspeximus-connector@HEAD",
           "note": "The receiver here implements his stated contract and is NOT his service. "
                   "This shows our side speaks schema_v0 end to end; it shows nothing about "
                   "MemStrata."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("all checks passed" if ok else "FAILED", os.path.basename(path)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
