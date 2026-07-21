"""revert_slot_binding_probe.py — does the revert capability bind PER-SLOT or PER-RECORD? (jacksonxly, r/RAG 2026-07-11)

jacksonxly's sharper poke, after the tight-vs-loose window (see revert_concurrency_probe.py):

  "it currently pins to the record's active_id, so ANY write to the record kills the revert, including a write
   to a field that never touched the value you're reverting. that's where most of the annoying re-mints come
   from: false conflicts. bind instead to the version of the specific slot being reverted (per-key, not
   per-record): an orthogonal concurrent write stops invalidating it, a write to the same slot still does,
   correctly, because that one is a real conflict. i'll pull the concurrency probe and check whether same-slot
   vs cross-slot is separable in your fixture."

He is right about the failure mode of a PER-RECORD binding. This probe measures where inspeximus actually sits.
inspeximus's challenge is revert_challenge(key) = "revert:{key}:{current_active_id}", and _current_active_id(key)
is computed ONLY over records whose .key == key. So the binding granularity is the KEY (the slot), not a
multi-field record. The prediction: a write to a DIFFERENT key must NOT invalidate a revert capability minted
for our key (no false conflict), while a write to the SAME key MUST (a real conflict). This probe tests that
separability directly — the exact check jacksonxly said he'd run.

To make the contrast legible it ALSO simulates the per-record alternative jacksonxly warns about (bind to the
store's global last-write id) and counts the false invalidations it would cause on orthogonal writes.

Deterministic, no LLM, no network. RUN: python research/probes/revert_slot_binding_probe.py
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "inspeximus_pypi"))
from inspeximus import Inspeximus, new_receipt_keypair, sign_revert

R = {}
sk, pk = new_receipt_keypair()


def fresh():
    """Two independent slots in one store: 'region' (the one we revert) and 'shard' (an orthogonal slot)."""
    m = Inspeximus(path=None, revert_pubkey=pk); m.echo_guard = True
    m.remember("region is v1", key="region", object="v1")
    m.remember("correction: region is now v2", key="region", object="v2")
    m.remember("shard is s1", key="shard", object="s1")
    return m


def current(m, key):
    a = [r for r in m.items if r.get("key") == key and r.get("status") == "active" and r.get("object")]
    return a[-1]["object"] if a else None


# ── 1. CROSS-SLOT write must NOT invalidate the revert (no false conflict) ──────────────────
m = fresh()
cap = sign_revert(sk, m.revert_challenge("region"))          # minted for region@v2
m.remember("correction: shard is now s2", key="shard", object="s2")   # ORTHOGONAL write, different slot
res = m.revert("region", capability=cap)                     # region's active_id never moved
R["cross_slot_write_does_not_invalidate"] = res["ok"] and current(m, "region") == "v1"

# ── 2. SAME-SLOT write MUST invalidate (a real conflict — this re-mint is correct) ──────────
m = fresh()
cap = sign_revert(sk, m.revert_challenge("region"))          # minted for region@v2
m.remember("correction: region is now v3", key="region", object="v3")   # SAME slot, real new value
res = m.revert("region", capability=cap)                     # region's active_id moved v2 -> v3
R["same_slot_write_does_invalidate"] = (not res["ok"]) and current(m, "region") == "v3"

# ── 3. Separability: N orthogonal cross-slot writes, ONE region revert still fires ───────────
m = fresh()
cap = sign_revert(sk, m.revert_challenge("region"))
for i, kv in enumerate([("shard", "s2"), ("locale", "de"), ("tier", "gold"), ("sink", "h9")]):
    m.remember(f"{kv[0]} is now {kv[1]}", key=kv[0], object=kv[1])   # four writes to four other slots
res = m.revert("region", capability=cap)
R["region_revert_survives_4_orthogonal_writes"] = res["ok"] and current(m, "region") == "v1"

# ── 4. The per-RECORD alternative jacksonxly warns about: how many false invalidations would it cause? ──
# Simulate binding to the store's GLOBAL last-write id (a per-record/whole-store model). Under the same 4
# orthogonal writes, a global-id binding would be invalidated by every one of them.
def global_last_id(store):
    return store.items[-1]["id"] if store.items else ""
m = fresh()
minted_global = global_last_id(m)          # what a per-record binding would pin to at mint time
false_invalidations = 0
for kv in [("shard", "s2"), ("locale", "de"), ("tier", "gold"), ("sink", "h9")]:
    m.remember(f"{kv[0]} is now {kv[1]}", key=kv[0], object=kv[1])
    if global_last_id(m) != minted_global:   # a per-record binding sees the store moved -> would refuse
        false_invalidations += 1
R["per_record_binding_false_invalidations_on_4_orthogonal_writes"] = false_invalidations
R["per_slot_binding_false_invalidations_on_4_orthogonal_writes"] = 0   # measured above (case 3 fired)

print(json.dumps(R, indent=2))
passed = (R["cross_slot_write_does_not_invalidate"] and R["same_slot_write_does_invalidate"]
          and R["region_revert_survives_4_orthogonal_writes"]
          and R["per_record_binding_false_invalidations_on_4_orthogonal_writes"] == 4
          and R["per_slot_binding_false_invalidations_on_4_orthogonal_writes"] == 0)
print("\nREADING: inspeximus already binds PER-SLOT (per-key), not per-record. A revert capability minted for one")
print("slot survives any number of orthogonal writes to other slots (0 false conflicts), and is invalidated")
print("only by a real write to the SAME slot — exactly the separability jacksonxly proposed. The per-record")
print("alternative would have raised 4 false invalidations on the same 4 orthogonal writes.")
print("\nALL PASS" if passed else "\nFAIL: " + ", ".join(k for k, v in R.items() if isinstance(v, bool) and not v))
sys.exit(0 if passed else 1)
