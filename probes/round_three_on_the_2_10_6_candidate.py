"""Round three, against the UNRELEASED 2.10.6 candidate.

Round one produced eleven fixes. Round two attacked those fixes and produced eleven more, three of
which were FALSE CLAIMS I had written into comments while fixing round one. This round attacks
round two's fixes.

Everything here is MEASURED. Round two's three false claims were all produced by reading code and
believing what its comment said, so nothing below is asserted from a reading.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")

from inspeximus import Inspeximus
from inspeximus.audit_bundle import _derived_store_id, build_bundle, verify_bundle
from inspeximus.core import new_ed25519_keypair
from inspeximus.witness_pool import Witness, verify_attestation

SK, PK = new_ed25519_keypair()
FINDINGS: list[tuple[str, str, str]] = []


def finding(tag, verdict, text):
    FINDINGS.append((tag, verdict, text))
    print(f"  [{verdict}] {tag}: {text}")


def store(d, sub, n, prefix="rec", **kw):
    os.makedirs(os.path.join(d, sub), exist_ok=True)
    ix = Inspeximus(path=os.path.join(d, sub, "s.json"), **kw)
    for i in range(n):
        ix.remember(f"{prefix} {i}", key=f"k{i}", object=str(i))
    ix.flush()
    return ix


# ══════════════════════════════════════════════════ G1: is the hardening reachable at all?
print("\nG1  the two witness hardening switches, from a shipped interface")
h = subprocess.run([sys.executable, "-m", "inspeximus.cli", "witness", "serve", "--help"],
                   capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"}).stdout
c = subprocess.run([sys.executable, "-m", "inspeximus.cli", "witness", "cosign", "--help"],
                   capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"}).stdout
import inspect

import inspeximus.witness_server as wsrv
srv = inspect.signature(wsrv.serve).parameters
missing = []
for flag, where, present in (("--strict", "witness serve", "--strict" in h),
                             ("--strict", "witness cosign", "--strict" in c),
                             ("strict", "witness_server.serve()", "strict" in srv),
                             ("--require-authenticated-state", "witness serve",
                              "require-authenticated-state" in h),
                             ("require_authenticated_state", "witness_server.serve()",
                              "require_authenticated_state" in srv)):
    if not present:
        missing.append(f"{flag} on {where}")
if missing:
    finding("G1", "REAL", f"{len(missing)} unreachable: {missing}. `strict` is the amnesia defence "
                          f"the code argues for at length, and require_authenticated_state is the "
                          f"one that closes F1 outright -- both available only to a caller who "
                          f"builds a Witness in Python. Same class as attest() in round 2.")
else:
    finding("G1", "clean", "both switches reachable from the CLI and the server")


# ══════════════════════════════════════════════════ G2: can the F1 taint be suppressed?
print("\nG2  suppressing the unauthenticated-load taint from the state file")
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w = Witness(state_path=sp)
ix = store(d, "a", 2, receipts=True, receipt_key=SK)
wid = build_bundle(ix, witnesses=[w])["store_id_derived"]

st = json.load(open(sp, encoding="utf-8"))
st.pop("mac", None)
st["unauthenticated_loads"] = []                    # the attacker tidies up after itself
st["heads"][wid]["n_writes"] = 1                    # ...and rolls the remembered head back
json.dump(st, open(sp, "w", encoding="utf-8"))
a = Witness(w._secret, state_path=sp).attest(wid)
if a["memory_authenticated"] is False:
    finding("G2", "clean", f"the taint survives a self-clearing attacker "
                           f"(loads={a['unauthenticated_loads']})")
else:
    finding("G2", "REAL", "clearing `unauthenticated_loads` in the file suppressed the taint")

# and with 20 planted entries, does OUR append still make the window?
st["unauthenticated_loads"] = [1.0] * 20
json.dump(st, open(sp, "w", encoding="utf-8"))
a2 = Witness(w._secret, state_path=sp).attest(wid)
finding("G2b", "clean" if a2["memory_authenticated"] is False else "REAL",
        f"with the 20-slot window pre-filled: memory_authenticated={a2['memory_authenticated']}")


# ══════════════════════════════════════════════════ G3: the derived identity of odd stores
#
# THE FIRST VERSION OF THIS PROBE ASKED THE WRONG QUESTION and reported clean. It checked whether
# two stores COLLIDE on one identity; the property that actually failed is whether an identity
# SURVIVES A COPY, which is the entire reason the derived id replaced the filename. Receipt-less
# stores did not collide -- they each got their own path -- and every one of them was `cp`-able to a
# fresh witness contact. A criterion narrower than the property is how a green suite measures
# nothing, and I wrote one here while holding the note that says so.
print("\nG3  does the identity survive a copy, for every kind of store?")
d = tempfile.mkdtemp()
for name, kw in (("no-receipts", {}), ("receipts", {"receipts": True, "receipt_key": SK})):
    ix = store(d, name, 3, prefix=name, **kw)
    wid = _derived_store_id(ix)
    shutil.copytree(os.path.join(d, name), os.path.join(d, name + "-copy"))
    moved = Inspeximus(path=os.path.join(d, name + "-copy", "s.json"), **kw)
    same = _derived_store_id(moved) == wid
    print(f"     {name:12} id={wid[:52]:52} survives cp: {same}")

    w = Witness(state_path=os.path.join(d, f"w-{name}.json"))
    try:
        build_bundle(ix, witnesses=[w])
        witnessed, why = True, ""
    except ValueError as e:
        witnessed, why = False, str(e)[:70]

    if kw:                                            # receipts on: must be stable AND witnessable
        finding(f"G3-{name}", "clean" if (same and witnessed) else "REAL",
                f"survives cp={same}, witnessable={witnessed}")
    else:                                             # receipts off: must NOT be witnessable at all
        finding(f"G3-{name}", "clean" if (not witnessed and wid.startswith("unkeyed:")) else "REAL",
                f"marked unkeyed={wid.startswith('unkeyed:')}, refused={not witnessed} ({why})"
                if not witnessed else
                f"a receipts-disabled store was witnessed under a FILENAME identity that `cp` "
                f"changes (survives cp={same}) -- the exact bypass the derived id exists to close")

# and a bundle that CLAIMS co-signatures over an unkeyed store, since anyone can write a file
ix = store(d, "handmade", 2)
b = build_bundle(ix)
b["anchor"]["cosignatures"] = [["aa" * 32, "bb" * 64]]
_o = verify_bundle(b)
finding("G3-handmade", "clean" if any("vouch for nothing" in p for p in _o["problems"]) else "REAL",
        "a hand-built bundle claiming co-signatures over an unkeyed store is refused"
        if any("vouch for nothing" in p for p in _o["problems"])
        else f"accepted: {_o['problems']}")


# ══════════════════════════════════════════════════ G4: is clear_poison reachable unauthenticated?
print("\nG4  what an unauthenticated HTTP caller can reach on the witness server")
src = open("C:/Users/Danculus/inspeximus-repo/inspeximus/witness_server.py", encoding="utf-8").read()
routes = sorted(set(__import__("re").findall(r'== "(/[a-z_\-]+)"|startswith\("(/[a-z_\-]+)', src)))
flat = sorted({x for pair in routes for x in pair if x})
print(f"     routes: {flat}")
dangerous = [r for r in flat if "clear" in r or "poison" in r or "bootstrap" in r]
finding("G4", "REAL" if dangerous else "clean",
        f"state-mutating admin routes exposed: {dangerous}" if dangerous else
        f"no admin route is exposed; {flat} are read/co-sign only")


# ══════════════════════════════════════════════════ G5: does the HTTP attest carry the new fields?
print("\nG5  the new attestation fields over the wire")
import threading
import time
d = tempfile.mkdtemp()
sp = os.path.join(d, "w.json")
w = Witness(state_path=sp)
PORT = 9758
threading.Thread(target=wsrv.serve, kwargs={"port": PORT, "state_path": sp,
                                            "secret_hex": w._secret}, daemon=True).start()
time.sleep(1.2)


def get(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10) as r:
        return json.load(r)


pub = get("/pubkey")["pubkey"]
ix = store(d, "m", 3, receipts=True, receipt_key=SK)
from inspeximus.witness_pool import http_witness
http_witness(f"http://127.0.0.1:{PORT}")("prod", ix.anchor())
a = get("/attest?store_id=prod")
v = verify_attestation(a, witness_pubkey=pub)
if "memory_authenticated" in a and v["signed"] and v["ok"]:
    finding("G5", "clean", "the new fields survive the JSON round-trip and the signature still "
                           "verifies over HTTP")
else:
    finding("G5", "REAL", f"has_field={'memory_authenticated' in a} signed={v['signed']} "
                          f"ok={v['ok']} problems={v['problems']}")


# ══════════════════════════════════════════════════ G6: F7's caveat vs a forged attestation
print("\nG6  an attestation forged end-to-end, with no allowlist")
d = tempfile.mkdtemp()
real = Witness(state_path=os.path.join(d, "r.json"))
evil = Witness(state_path=os.path.join(d, "e.json"))
ix = store(d, "s", 3, receipts=True, receipt_key=SK)
wid = build_bundle(ix, witnesses=[real])["store_id_derived"]
ix.remember("the operator rewrites nothing; they just add a friendly witness", key="z", object="9")
ix.flush()
evil.cosign(wid, ix.anchor())                       # the operator's own "witness" sees the new head
b = build_bundle(ix)
out = verify_bundle(b, attestations=[evil.attest(wid)])
unpinned = [x for x in out["limits"] if "UNPINNED" in x]
finding("G6", "clean" if unpinned else "REAL",
        f"ok={out['ok']} and the auditor IS told it is unpinned" if unpinned else
        f"ok={out['ok']} with no unpinned caveat: limits={out['limits']}")


# ══════════════════════════════════════════════════ G7: the real witness is silent and nobody says
print("\nG7  the operator submits to a friendly witness and simply stops asking the real one")
out2 = verify_bundle(b, witnesses=[real.public, evil.public], threshold=1,
                     attestations=[evil.attest(wid)])
missing = [x for x in out2["problems"] + out2["limits"] if "produced no attestation" in x]
finding("G7", "clean" if missing else "REAL",
        f"the silent allowlisted witness is reported: {missing[0][:90]}" if missing else
        f"a witness on the allowlist produced nothing and nothing said so: {out2['problems']}")


print("\n" + "=" * 78)
real_findings = [f for f in FINDINGS if f[1] == "REAL"]
print(f"ROUND 3: {len(real_findings)} real finding(s) of {len(FINDINGS)} probes")
for tag, _v, text in real_findings:
    print(f"  * {tag}: {text}")
if not real_findings:
    print("  (nothing -- and a round that finds nothing is only meaningful if the probes could "
          "have found something; G2/G5/G6/G7 all have a failing shape reachable from one edit)")
