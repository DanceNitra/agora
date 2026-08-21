"""Adversarial pass on the VERIFY -> USE window, before it ships.

The rule the owner set: attack the CANDIDATE, fold every finding into the same version, release
once. This feature is a guarantee an agent will act on, so the question is not "does it work" but
"what makes it say SAFE when it is not".

Each probe names what it would take to be REFUTED, because a probe that cannot fail measures
nothing -- and I wrote one of those against this very feature two hours ago.
"""
from __future__ import annotations

import copy
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


def scene(bind=True, text=b"deployment needs two approvers"):
    d = tempfile.mkdtemp()
    src = os.path.join(d, "policy.txt")
    open(src, "wb").write(text)
    ix = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
    kw = {"doc": src}
    if bind:
        kw["observed_sha256"] = hashlib.sha256(text).hexdigest()
    ix.remember("deployment needs two approvers", key="pol", object="two", source=kw)
    ix.flush()
    return d, src, ix


# ══════════════════════ J1 the witness is a dict the caller carries; can they edit it clean?
print("\nJ1  the courier edits the witness")
_d, src, ix = scene()
w = ix.witness(ix.recall("approvers"), bind_sources=True)
open(src, "wb").write(b"deployment needs ONE approver")
tampered = copy.deepcopy(w)
tampered["sources"] = {}                                  # "nothing to check here"
out = ix.verify_witness(tampered)
finding("J1a", out["sources_match"] is False and not out["valid"],
        f"emptying `sources` does not buy a pass (sources_match={out['sources_match']})")

tampered2 = copy.deepcopy(w)
tampered2.pop("sources", None)                            # drop the key entirely
out2 = ix.verify_witness(tampered2)
finding("J1b", "sources_match" not in out2,
        "dropping the key downgrades to a store-only witness -- REPORTED as such, not claimed clean"
        if "sources_match" not in out2 else f"still claims {out2.get('sources_match')}")
# ...but does anything tell the auditor the witness was downgraded? That is the honest question.
finding("J1c", out2.get("valid") is True,
        "NOTE: a stripped witness verifies as the store-only kind. The hydration witness is "
        "unsigned by design, so this is a stated limit, not a new hole -- see J2")

# ══════════════════════ J2 rewrite the pinned digest to the CURRENT bytes
print("\nJ2  the courier re-pins to whatever the file says now")
_d, src, ix = scene()
w = ix.witness(ix.recall("approvers"), bind_sources=True)
open(src, "wb").write(b"deployment needs ONE approver")
forged = copy.deepcopy(w)
for v in forged["sources"].values():
    v["sha256"] = hashlib.sha256(open(src, "rb").read()).hexdigest()
out = ix.verify_witness(forged)
finding("J2", out["sources_match"] is True,
        "EXPECTED and it is the honest limit: the witness is an unsigned receipt the caller holds, "
        "so a caller who edits it can always make it agree. It binds an HONEST caller's "
        "verification to their use; it is not an operator-adversarial artifact (that is attest())")

# ══════════════════════ J3 a source that changes and changes BACK
print("\nJ3  the source changes and is restored before use")
_d, src, ix = scene()
w = ix.witness(ix.recall("approvers"), bind_sources=True)
orig = open(src, "rb").read()
open(src, "wb").write(b"transient nonsense")
open(src, "wb").write(orig)
out = ix.verify_witness(w)
finding("J3", out["sources_match"] is True,
        "a restored source reads fresh -- correct for a CONTENT digest, and the honest scope: this "
        "answers 'are the bytes the same', not 'was there a window'")

# ══════════════════════ J4 does binding sources slow a big answer to a crawl?
print("\nJ4  cost on a realistic answer")
import time
d = tempfile.mkdtemp()
ix = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
srcs = []
for i in range(200):
    p = os.path.join(d, f"doc{i}.txt")
    b = f"policy fragment {i}".encode()
    open(p, "wb").write(b)
    srcs.append(p)
    ix.remember(f"fragment {i}", key=f"k{i}", object=str(i),
                source={"doc": p, "observed_sha256": hashlib.sha256(b).hexdigest()})
ix.flush()
hits = ix.recall("fragment", k=20)
t0 = time.time(); w = ix.witness(hits, bind_sources=True); t_w = time.time() - t0
t0 = time.time(); out = ix.verify_witness(w); t_v = time.time() - t0
t0 = time.time(); wall = ix.witness(bind_sources=True); t_all = time.time() - t0
finding("J4", t_w < 0.5 and t_v < 1.0,
        f"witness over {len(hits)} hits {t_w*1000:.1f}ms, verify {t_v*1000:.1f}ms "
        f"(whole store, 200 records: {t_all*1000:.1f}ms) -- bounded by what the answer used")

# ══════════════════════ J5 the JSON round-trip an agent will actually do
print("\nJ5  the witness survives being carried as JSON")
_d, src, ix = scene()
w = json.loads(json.dumps(ix.witness(ix.recall("approvers"), bind_sources=True)))
finding("J5a", ix.verify_witness(w)["sources_match"] is True, "round-trips clean")
open(src, "wb").write(b"deployment needs ONE approver")
finding("J5b", ix.verify_witness(w)["stale_at_use"] is True, "and still catches the move")

# ══════════════════════ J6 a resolver that throws, and one that lies by returning b""
print("\nJ6  a hostile resolver")
_d, _src, ix = scene()
w = ix.witness(ix.recall("approvers"), bind_sources=True)


def boom(_doc):
    raise RuntimeError("network down")


o1 = ix.verify_witness(w, resolver=boom)
finding("J6a", o1["sources_orphaned"] and o1["sources_match"] is False,
        "a throwing resolver is ORPHANED, not a pass")
o2 = ix.verify_witness(w, resolver=lambda _d: b"")
finding("J6b", o2["sources_match"] is False and o2["stale_at_use"] is True,
        "an empty body is a MISMATCH, not a missing source -- b'' is not None")

# ══════════════════════ J7 the must-fail control
print("\nJ7  the control that fails if the fixture stops reproducing the defect")
_d, src, ix = scene()
w = ix.witness(ix.recall("approvers"), bind_sources=True)
before = ix.verify_witness(w)["sources_match"]
open(src, "wb").write(b"deployment needs ONE approver")
after = ix.verify_witness(w)["sources_match"]
finding("J7", before is True and after is False,
        f"the probe can distinguish moved from unmoved ({before} -> {after}); if these ever "
        f"matched, every J above would be measuring a constant")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"ROUND J: {len(bad)} real finding(s) of {len(F)} probes"
      + (f"  -> {bad}" if bad else ""))
