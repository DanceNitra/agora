"""Round five: attacking round four's fixes, which added a WRITE endpoint and a persisted grant.

Round four added the first authenticated write route in the product and made `bootstrap` durable.
Both are new places to be wrong, and a persisted grant is more dangerous than an ephemeral one -- it
is the one thing in the state file that WEAKENS the witness, so anything that can plant one, or
stop one from being noticed, matters more than the rest of that file put together.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus
from inspeximus.audit_bundle import _derived_store_id
from inspeximus.witness_pool import Witness, verify_attestation
import inspeximus.witness_server as wsrv

FINDINGS = []


def finding(tag, ok, text):
    FINDINGS.append((tag, ok, text))
    print(f"  [{'clean' if ok else 'REAL'}] {tag}: {text}")


def mkstore(d, sub, n=3):
    os.makedirs(os.path.join(d, sub), exist_ok=True)
    ix = Inspeximus(path=os.path.join(d, sub, "s.json"), receipts=True)
    for i in range(n):
        ix.remember(f"r{i}", key=f"k{i}", object=str(i))
    ix.flush()
    return ix


# ══════════════════════ I1: a planted bootstrap is an edit, so it must show as one
print("\nI1  planting a bootstrap by editing the state file")
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w = Witness(state_path=sp, strict=True)
victim = mkstore(d, "v")
sid = _derived_store_id(victim)
w.bootstrap("something-else")                       # forces a MAC'd persist

st = json.load(open(sp, encoding="utf-8"))
st.pop("mac", None)
st["bootstrapped"] = sorted(set(st.get("bootstrapped") or []) | {sid})
json.dump(st, open(sp, "w", encoding="utf-8"))

w2 = Witness(w._secret, state_path=sp, strict=True)
planted_works = True
try:
    w2.cosign(sid, victim.anchor())
except ValueError:
    planted_works = False
att = w2.attest(sid)
finding("I1", att["memory_authenticated"] is False,
        f"the planted grant is usable ({planted_works}) but the witness REPORTS its memory as "
        f"unauthenticated, so the auditor sees the edit"
        if att["memory_authenticated"] is False else
        "a planted bootstrap was invisible: memory_authenticated stayed True")

# and require_authenticated_state refuses it outright.
#
# ITS OWN FIXTURE, and the first version did not have one: it reused the file above, where `w2` had
# already co-signed and therefore RE-PERSISTED it with a fresh MAC. The guard was handed an
# authentic file and correctly started, and I read that as the guard failing. A probe whose earlier
# step repairs the damage the later step is testing for measures the repair.
d1b = tempfile.mkdtemp()
sp1b = os.path.join(d1b, "w.json")
w1b = Witness(state_path=sp1b, strict=True)
w1b.bootstrap("s1")
st1b = json.load(open(sp1b, encoding="utf-8"))
assert st1b.pop("mac", None), "no MAC to strip: this probe would prove nothing"
st1b["bootstrapped"] = ["s1", "planted"]
json.dump(st1b, open(sp1b, "w", encoding="utf-8"))
refused = False
try:
    Witness(w1b._secret, state_path=sp1b, strict=True, require_authenticated_state=True)
except ValueError:
    refused = True
finding("I1b", refused, "require_authenticated_state refuses the stripped file outright"
        if refused else "the stripped file started even under require_authenticated_state")


# ══════════════════════ I2: does the bootstrap grant leak across stores?
print("\nI2  is a bootstrap scoped to the store it names?")
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w = Witness(state_path=sp, strict=True)
a, b = mkstore(d, "a"), mkstore(d, "b")
w.bootstrap(_derived_store_id(a))
w.cosign(_derived_store_id(a), a.anchor())
leaked = True
try:
    w.cosign(_derived_store_id(b), b.anchor())
except ValueError:
    leaked = False
finding("I2", not leaked, "a bootstrap for one store does not admit another"
        if not leaked else "bootstrapping one store admitted a different one")


# ══════════════════════ I3: does a bootstrap let a ROLLBACK through afterwards?
print("\nI3  a bootstrap must admit a first contact, not forgive a fork")
d = tempfile.mkdtemp()
w = Witness(state_path=os.path.join(d, "w.json"), strict=True)
ix = mkstore(d, "s", 4)
sid = _derived_store_id(ix)
w.bootstrap(sid)
w.cosign(sid, ix.anchor())
rolled = dict(ix.anchor()); rolled["n_writes"] = 1
forgiven = True
try:
    w.cosign(sid, rolled)
except ValueError:
    forgiven = False
finding("I3", not forgiven, "a rollback after a bootstrap is still refused"
        if not forgiven else "the bootstrap forgave a rollback")

# ...and re-bootstrapping must not clear the refusal it just recorded
finding("I3b", bool(w.refusals(sid)) and (w.bootstrap(sid) or True) and bool(w.refusals(sid)),
        "re-bootstrapping does not erase a refusal already recorded")


# ══════════════════════ I4: the token, and what an unauthenticated caller can still do
print("\nI4  the bootstrap route under load from a stranger")
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w0 = Witness(state_path=sp)
PORT = 9781
threading.Thread(target=wsrv.serve,
                 kwargs={"port": PORT, "state_path": sp, "secret_hex": w0._secret,
                         "strict": True, "bootstrap_token": "tok"}, daemon=True).start()
time.sleep(1.2)


def post(path, body, token=None, raw=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data,
                                 headers={"Content-Type": "application/json",
                                          **({"X-Bootstrap-Token": token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


# a token that is a PREFIX of the real one, and one that is longer: compare_digest, not startswith
codes = [post("/bootstrap", {"store_id": "x"}, token=t)[0] for t in ("t", "to", "tok ", "tokk", "")]
finding("I4a", all(c == 403 for c in codes), f"near-miss tokens all refused: {codes}")
finding("I4b", post("/bootstrap", {"store_id": "x"}, token="tok")[0] == 200,
        "the exact token still works (the must-not-brick control)")

# malformed bodies must not 500 or wedge the connection
odd = [post("/bootstrap", None, token="tok", raw=b"not json")[0],
       post("/bootstrap", {}, token="tok")[0],
       post("/cosign", None, raw=b"{")[0]]
finding("I4c", all(c in (400, 500) for c in odd) and 500 not in odd[:2],
        f"malformed bodies answered cleanly: {odd}")

# and the server is still alive after all of that
finding("I4d", post("/bootstrap", {"store_id": "y"}, token="tok")[0] == 200,
        "the server is still serving after the malformed traffic")


# ══════════════════════ I5: the attestation still verifies with the new field in the body
print("\nI5  the state body grew a key; does the MAC and the attestation still line up?")
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w = Witness(state_path=sp, strict=True)
ix = mkstore(d, "s")
sid = _derived_store_id(ix)
w.bootstrap(sid)
w.cosign(sid, ix.anchor())
reborn = Witness(w._secret, state_path=sp, strict=True, require_authenticated_state=True)
att = reborn.attest(sid)
v = verify_attestation(att, witness_pubkey=w.public)
finding("I5", v["ok"] and att["memory_authenticated"] is True,
        f"a witness that bootstrapped, co-signed and restarted verifies clean under "
        f"require_authenticated_state (ok={v['ok']})" if v["ok"] else
        f"ok={v['ok']} problems={v['problems']}")

print("\n" + "=" * 78)
bad = [f for f in FINDINGS if not f[1]]
print(f"ROUND 5: {len(bad)} real finding(s) of {len(FINDINGS)} probes")
for tag, _ok, text in bad:
    print(f"  * {tag}: {text}")
