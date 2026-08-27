"""Does inspeximus write an identifier one way and look it up another?

@Stratogain's proposed fixture case on anthropics/claude-code#34556, after finding it in their own
ledger: the hook stored `session_id.slice(0, 8)` and the lookup compared the full id, so a session
could not find its own observations and every honest capture silently degraded to a write-time hash.
It "passes every test that only checks whether a verdict was produced."

We already shipped one instance of this class TODAY -- witness fork-memory keyed on the caller's
`store_id` label while the identity that mattered was the derived one -- so the right response is a
round-trip on every identifier-keyed surface we have, not a claim that we are clean.

THE ROUND TRIP IS THE TEST: write under an id, read back under the SAME id, and require the record
to come back. A near-miss id must NOT come back, or the lookup is too loose and the round trip
proves nothing. Both halves, or this probe is the disease it is looking for.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus

F = []


def check(tag, ok, text):
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {text}")


def store(**kw):
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), **kw)


# identifiers chosen to break a naive transform: long enough to be truncated, mixed case, and a
# near-miss that differs only past the 8th character (exactly what slice(0,8) would collapse).
LONG = "session-abcdefgh-0000000000000000-alpha"
NEAR = "session-abcdefgh-0000000000000000-omega"
MIXED = "Acme-Tenant-ID"

# ── the supersession key ─────────────────────────────────────────────────────────────────────
ix = store()
ix.remember("first value", key=LONG, object="1")
ix.remember("second value", key=LONG, object="2")          # must SUPERSEDE, not sit beside
ix.remember("a different key", key=NEAR, object="3")
ix.flush()
live = [r for r in ix.items if r.get("status") == "active"]
by_key = {}
for r in live:
    by_key.setdefault(r.get("key"), []).append(r)
check("supersession key", len(by_key.get(LONG, [])) == 1 and len(by_key.get(NEAR, [])) == 1,
      f"{len(by_key.get(LONG, []))} live under the long key, {len(by_key.get(NEAR, []))} under the "
      f"near-miss (1 and 1 = write and read agree, and the two are not collapsed)")

# ── decision topics ──────────────────────────────────────────────────────────────────────────
ix = store()
ix.remember_decision("we chose A", topic=LONG, because="x")
ix.remember_decision("we chose B", topic=LONG, because="y")
ix.remember_decision("unrelated", topic=NEAR, because="z")
ix.flush()
dec = [r for r in ix.items if r.get("status") == "active" and str(r.get("key", "")).startswith("decision::")]
keys = {r["key"] for r in dec}
check("decision topic", len(dec) == 2 and f"decision::{LONG}" in keys and f"decision::{NEAR}" in keys,
      f"{len(dec)} live decisions, keys {sorted(k[-6:] for k in keys)} -- the topic survives whole")

# ── tenant ───────────────────────────────────────────────────────────────────────────────────
root = store(receipts=True)
root.for_tenant(MIXED).remember("mixed-case tenant", key="a", object="1")
root.for_tenant(MIXED.lower()).remember("lowercase tenant", key="b", object="2")
root.flush()
check("tenant is not case-folded",
      len(root.for_tenant(MIXED).items) == 1 and len(root.for_tenant(MIXED.lower()).items) == 1,
      f"{len(root.for_tenant(MIXED).items)} for {MIXED!r}, "
      f"{len(root.for_tenant(MIXED.lower()).items)} for its lowercase -- two tenants, not one")

# ── the witness identity we fixed today ──────────────────────────────────────────────────────
from inspeximus.audit_bundle import _derived_store_id, build_bundle
ix = store(receipts=True)
ix.remember("x", key="k", object="v")
ix.flush()
wid = build_bundle(ix)["store_id_derived"]
check("derived store id round-trips", wid == _derived_store_id(ix) and wid.startswith("insp1:"),
      f"the bundle publishes exactly what the witness keys on ({wid[:22]}...)")

# ── the id a record is given, vs the id history/provenance is asked for ──────────────────────
ix = store(receipts=True)
rid = ix.remember("a record with a long life", key="k", object="v")
ix.flush()
rid = rid if isinstance(rid, str) else ix.items[0]["id"]
h = ix.history("k")
prov = ix.provenance(rid) if hasattr(ix, "provenance") else None
check("record id round-trips into provenance",
      bool(prov) and (prov.get("id") == rid or prov.get("memory_id") == rid),
      f"provenance({rid}) answered about {(prov or {}).get('id') or (prov or {}).get('memory_id')}")

# ── session / user / agent scoping, the exact shape Stratogain hit ───────────────────────────
ix = store(receipts=True)
ix.remember("in the long session", key="a", object="1", session_id=LONG)
ix.remember("in the near session", key="b", object="2", session_id=NEAR)
ix.flush()
stored = {r.get("session_id") for r in ix.items if r.get("session_id")}
check("session_id is stored whole", stored == {LONG, NEAR},
      f"stored {sorted(s[-6:] for s in stored)} -- not truncated, and the two do not collapse"
      if stored == {LONG, NEAR} else f"stored {stored!r}")

# ── the must-fail control: a near-miss must NOT resolve ──────────────────────────────────────
ix = store()
ix.remember("only under the long key", key=LONG, object="1")
ix.flush()
wrong = [r for r in ix.items if r.get("key") == NEAR]
check("control: a near-miss id does not resolve", wrong == [],
      "an id differing only after the 8th character finds nothing, so the checks above are not "
      "passing on a lookup that matches everything")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"IDENTIFIER ROUND-TRIP: {len(bad)} failure(s) of {len(F)}" + (f"  -> {bad}" if bad else ""))
