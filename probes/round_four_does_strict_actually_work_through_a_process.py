"""Round four: does `--strict` work through the surfaces it was just exposed on?

The two findings this closes were both about a mechanism nobody could reach, so the only measurement
that counts is an end-to-end one THROUGH A FRESH PROCESS. A signature check would pass on a flag
that is accepted and dropped, and that is worse than an absent flag because it reads as protection.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus
from inspeximus.audit_bundle import _derived_store_id

ENV = {**os.environ, "PYTHONUTF8": "1"}
FINDINGS = []


def finding(tag, ok, text):
    FINDINGS.append((tag, ok, text))
    print(f"  [{'clean' if ok else 'REAL'}] {tag}: {text}")


def cli(*argv):
    return subprocess.run([sys.executable, "-m", "inspeximus.cli", *argv],
                          capture_output=True, text=True, env=ENV)


d = tempfile.mkdtemp()
key = os.path.join(d, "w.key")
state = key + ".state.json"
cli("witness", "keygen", "--out", key)

ix = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
for i in range(3):
    ix.remember(f"r{i}", key=f"k{i}", object=str(i))
ix.flush()
SID = _derived_store_id(ix)
ap = os.path.join(d, "anchor.json")
json.dump(ix.anchor(), open(ap, "w", encoding="utf-8"))


def cosign(anchor_path, *extra):
    return cli("witness", "cosign", anchor_path, "--store-id", SID, "--key", key,
               "--state", state, *extra)


# ══════════════════════════════════════════ H1: the CLI flow, across processes
print("\nH1  strict + bootstrap, each in its own process")
r = cosign(ap, "--strict")
finding("H1a", r.returncode != 0 and "no record" in (r.stdout + r.stderr),
        f"unbootstrapped strict cosign refused (rc={r.returncode})" if r.returncode
        else f"a strict witness co-signed a store it had never heard of: {r.stdout[:100]}")

b = cli("witness", "bootstrap", "--store-id", SID, "--key", key, "--state", state)
finding("H1b", b.returncode == 0, f"bootstrap rc={b.returncode} {b.stdout.strip()[:80] or b.stderr[:80]}")

r = cosign(ap, "--strict")
finding("H1c", r.returncode == 0,
        "a SEPARATE process co-signed after the bootstrap -- the declaration is durable"
        if r.returncode == 0 else
        f"the bootstrap did not survive the process: {(r.stdout + r.stderr)[:120]}")

# the amnesia attack the flag exists for: delete the memory, try again
os.unlink(state)
r = cosign(ap, "--strict")
finding("H1d", r.returncode != 0,
        "deleting the state file does NOT launder a first contact"
        if r.returncode != 0 else "amnesia still buys a co-signature under --strict")

# ...and the must-not-brick control: without --strict, an unknown store is fine
r = cosign(ap)
finding("H1e", r.returncode == 0,
        "the default is unchanged: a new store is co-signed"
        if r.returncode == 0 else f"non-strict cosign broke: {(r.stdout + r.stderr)[:120]}")

# a rollback is still refused after all this
roll = os.path.join(d, "roll.json")
_a = json.load(open(ap, encoding="utf-8"))
_a["n_writes"] = 1
json.dump(_a, open(roll, "w", encoding="utf-8"))
r = cosign(roll)
finding("H1f", r.returncode != 0,
        "a rollback is still refused (the guard the whole feature exists for)"
        if r.returncode != 0 else "a rollback was co-signed")


# ══════════════════════════════════════════ H2: the HTTP route, and its authentication
print("\nH2  POST /bootstrap on the server")
import inspeximus.witness_server as wsrv
from inspeximus.witness_pool import Witness

d2 = tempfile.mkdtemp()
sp = os.path.join(d2, "w.json")
w0 = Witness(state_path=sp)
TOKEN = "s3cret-token"
PORT = 9762
threading.Thread(target=wsrv.serve,
                 kwargs={"port": PORT, "state_path": sp, "secret_hex": w0._secret,
                         "strict": True, "bootstrap_token": TOKEN}, daemon=True).start()
time.sleep(1.2)


def post(path, body, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"X-Bootstrap-Token": token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


ix2 = Inspeximus(path=os.path.join(d2, "s.json"), receipts=True)
for i in range(3):
    ix2.remember(f"r{i}", key=f"k{i}", object=str(i))
ix2.flush()
SID2 = _derived_store_id(ix2)

code, _body = post("/cosign", {"store_id": SID2, "anchor": ix2.anchor()})
finding("H2a", code == 409, f"strict server refuses an undeclared store (HTTP {code})")

code, body = post("/bootstrap", {"store_id": SID2})
finding("H2b", code == 403, f"no token -> HTTP {code} {str(body)[:60]}")

code, body = post("/bootstrap", {"store_id": SID2}, token="wrong")
finding("H2c", code == 403, f"wrong token -> HTTP {code}")

code, body = post("/bootstrap", {"store_id": SID2}, token=TOKEN)
finding("H2d", code == 200, f"right token -> HTTP {code} {str(body)[:50]}")

code, body = post("/cosign", {"store_id": SID2, "anchor": ix2.anchor()})
finding("H2e", code == 200, f"and now the store co-signs (HTTP {code})")

# the declaration must survive a restart of the witness, not just the request
reborn = Witness(w0._secret, state_path=sp)
finding("H2f", SID2 in reborn._bootstrapped,
        "the bootstrap is in the persisted state, so a restart does not lose it"
        if SID2 in reborn._bootstrapped else "a restart forgot the bootstrap")

print("\n" + "=" * 78)
bad = [f for f in FINDINGS if not f[1]]
print(f"ROUND 4: {len(bad)} real finding(s) of {len(FINDINGS)} probes")
for tag, _ok, text in bad:
    print(f"  * {tag}: {text}")
