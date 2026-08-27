"""Round K: attacking round J's fixes, and the tenant work that fell out of them.

Round J found nothing in the feature and two stated limits. But the round itself produced fixes --
the tenant rebinding, the shared-chain concession, the write-time/observed split -- and those are
new places to be wrong. The concession is the one to hunt: I deliberately made a mismatch NOT fail a
verdict, which is exactly the shape of a hole.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus

F = []


def finding(tag, ok, text):
    F.append((tag, ok))
    print(f"  [{'clean' if ok else 'REAL '}] {tag}: {text}")


def tenants():
    d = tempfile.mkdtemp()
    root = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
    paths = {}
    for t in ("acme", "globex"):
        p = os.path.join(d, f"{t}.txt")
        b = f"{t} needs two approvers".encode()
        open(p, "wb").write(b)
        paths[t] = p
        root.for_tenant(t).remember(f"{t} policy", key="pol", object="two",
                                    source={"doc": p, "observed_sha256": hashlib.sha256(b).hexdigest()})
    root.flush()
    return d, root, paths


# ══════════════ K1 the concession: does it swallow something that IS the tenant's business?
print("\nK1  what the shared-chain concession must NOT hide")
d, root, paths = tenants()
acme = root.for_tenant("acme")
w = acme.witness(bind_sources=True)
root.forget(next(r["id"] for r in root.items if r.get("tenant") == "acme"))   # admin erases ACME's row
root.flush()
out = acme.verify_witness(w)
finding("K1a", out["valid"] is False,
        f"an admin erasing THIS tenant's record still invalidates (valid={out['valid']}, "
        f"digest_match={out['digest_match']}) -- the concession is scoped to the shared TIP only")

d, root, paths = tenants()
acme = root.for_tenant("acme")
w = acme.witness(bind_sources=True)
open(paths["acme"], "wb").write(b"acme needs ONE approver")            # acme's own source moves
out = acme.verify_witness(w)
finding("K1b", out["stale_at_use"] is True and out["valid"] is False,
        "and a moved source of this tenant's own still fails")


# ══════════════ K2 can one tenant learn about another through the verdict?
print("\nK2  cross-tenant verification")
d, root, paths = tenants()
w_acme = root.for_tenant("acme").witness(bind_sources=True)
out = root.for_tenant("globex").verify_witness(w_acme)
finding("K2", out["valid"] is False and out["digest_match"] is False,
        "globex verifying acme's witness gets a plain mismatch, not a clean pass")


# ══════════════ K3 can a caller forge observation_bound through meta=?
print("\nK3  forging the binding KIND")
d2 = tempfile.mkdtemp()
src = os.path.join(d2, "p.txt")
open(src, "wb").write(b"policy")
ix = Inspeximus(path=os.path.join(d2, "s.json"), receipts=True)
try:
    ix.remember("policy", key="pol", object="two", source={"doc": src},
                meta={"observation_bound": True, "source_sha256": "aa" * 32})
    forged = True
except Exception as e:
    forged = f"REFUSED: {type(e).__name__}"
ix.flush()
w = ix.witness(ix.recall("policy"), bind_sources=True)
finding("K3", w["sources_observation_bound"] == "0/1",
        f"the reserved keyspace holds: meta= could not claim an observed binding "
        f"({w['sources_observation_bound']}, remember() -> {forged})")


# ══════════════ K4 a RELATIVE source path, re-resolved from a different working directory
print("\nK4  a relative locator verified from elsewhere")
d3 = tempfile.mkdtemp()
os.makedirs(os.path.join(d3, "work"), exist_ok=True)
rel = "policy.txt"
cwd0 = os.getcwd()
os.chdir(os.path.join(d3, "work"))
try:
    open(rel, "wb").write(b"two approvers")
    ix = Inspeximus(path=os.path.join(d3, "s.json"), receipts=True)
    ix.remember("policy", key="pol", object="two",
                source={"doc": rel, "observed_sha256": hashlib.sha256(b"two approvers").hexdigest()})
    ix.flush()
    w = ix.witness(ix.recall("policy"), bind_sources=True)
    here = ix.verify_witness(w)
    os.chdir(d3)                                             # the agent moves; a decoy is planted
    open(os.path.join(d3, rel), "wb").write(b"ONE approver")
    there = ix.verify_witness(w)
finally:
    os.chdir(cwd0)
finding("K4", here["sources_match"] is True and there["sources_match"] is False,
        f"from the original cwd it matches ({here['sources_match']}); from elsewhere the SAME "
        f"relative name resolves to a different file and is reported "
        f"({'moved' if there['sources_moved'] else 'orphaned'}), not passed")


# ══════════════ K5 duplicate ids must not inflate the denominator
print("\nK5  the same record named twice")
d4 = tempfile.mkdtemp()
p4 = os.path.join(d4, "p.txt")
open(p4, "wb").write(b"x")
ix = Inspeximus(path=os.path.join(d4, "s.json"), receipts=True)
ix.remember("policy", key="pol", object="two",
            source={"doc": p4, "observed_sha256": hashlib.sha256(b"x").hexdigest()})
ix.flush()
rid = ix.items[0]["id"]
w = ix.witness([rid, rid, rid], bind_sources=True)
finding("K5", w["sources_bound"] == "1/1" and len(w["sources"]) == 1,
        f"three mentions of one record count once ({w['sources_bound']})")


# ══════════════ K6 a record superseded between the witness and the use
print("\nK6  supersession between verify and use")
d5 = tempfile.mkdtemp()
p5 = os.path.join(d5, "p.txt")
open(p5, "wb").write(b"two approvers")
ix = Inspeximus(path=os.path.join(d5, "s.json"), receipts=True)
ix.remember("needs two approvers", key="pol", object="two",
            source={"doc": p5, "observed_sha256": hashlib.sha256(b"two approvers").hexdigest()})
ix.flush()
w = ix.witness(ix.recall("approvers"), bind_sources=True)
ix.remember("needs ONE approver", key="pol", object="one")           # supersedes on the same key
ix.flush()
out = ix.verify_witness(w)
finding("K6", out["valid"] is False and out["digest_match"] is False,
        "the memory itself was superseded, and the STORE half catches that -- the source never moved")


# ══════════════ K7 the must-fail control for this whole round
print("\nK7  the control")
d6, root6, paths6 = tenants()
a6 = root6.for_tenant("acme")
w6 = a6.witness(bind_sources=True)
clean = a6.verify_witness(w6)["valid"]
root6.for_tenant("globex").remember("noise", key="n", object="1")
root6.flush()
still = a6.verify_witness(w6)["valid"]
open(paths6["acme"], "wb").write(b"acme needs ONE approver")
broken = a6.verify_witness(w6)["valid"]
finding("K7", clean is True and still is True and broken is False,
        f"clean={clean} -> neighbour writes {still} -> own source moves {broken}; if all three "
        f"matched, every probe above would be measuring a constant")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"ROUND K: {len(bad)} real finding(s) of {len(F)} probes" + (f"  -> {bad}" if bad else ""))
