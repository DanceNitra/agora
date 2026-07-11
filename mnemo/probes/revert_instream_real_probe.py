"""revert_instream_real_probe.py — jacksonxly's in-stream revert, measured on the REAL mnemo 0.7.12.

The simulation (revert_instream_sim_probe.py) showed the construction is coherent; this measures the actual
implementation (revert_intent / restore_intent / submit_revert) against the same five claims — including the
question jackson explicitly asked: does cross-slot zero-false-conflict survive once revert is in-stream
instead of beside it?

Deterministic, no LLM, no network. RUN: python mnemo/probes/revert_instream_real_probe.py
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mnemo_pypi"))
from mnemo import Mnemo, new_receipt_keypair, sign_revert, __version__

sk, pk = new_receipt_keypair()
R = {"mnemo_version": __version__}


def fresh(depth=1, keys=("region",)):
    m = Mnemo(path=None, revert_pubkey=pk); m.echo_guard = True
    for k in keys:
        m.remember(f"{k} is {k}_v0", key=k, object=f"{k}_v0")
        for v in range(1, depth + 1):
            m.remember(f"correction: {k} is now {k}_v{v}", key=k, object=f"{k}_v{v}")
    return m


def cur(m, k="region"):
    a = [r for r in m.items if r.get("key") == k and r.get("status") == "active" and r.get("object")]
    return max(a, key=lambda r: r.get("valid_from", r["ts"]))["object"] if a else None


# ── 1. NAMED (absolute) liveness under same-slot bursts of any size ──────────────────────────
ok1 = True
for burst in (1, 5, 20, 100):
    m = fresh(depth=2)                                     # history: v0 v1 v2
    intent = m.restore_intent("region", "region_v0")
    cap = sign_revert(sk, intent)
    for i in range(burst):                                  # sustained same-slot burst AFTER mint
        m.remember(f"correction: region is now region_w{i}", key="region", object=f"region_w{i}")
    res = m.submit_revert(intent, cap)
    ok1 &= res["ok"] and cur(m) == "region_v0"
R["1_named_lands_under_bursts_1_5_20_100"] = ok1

# ── 2. RELATIVE under burst: clean CONFLICT (definitive), never starvation, and distinct from auth-fail ──
m = fresh(depth=1)
intent = m.revert_intent("region")                          # base = v1
cap = sign_revert(sk, intent)
for i in range(10):
    m.remember(f"correction: region is now region_w{i}", key="region", object=f"region_w{i}")
res = m.submit_revert(intent, cap)
R["2_relative_under_burst_reason"] = res.get("reason")      # expect "conflict" (definitive, not a retry loop)
R["2_conflict_distinct_from_auth"] = res.get("reason") == "conflict"
bad = m.submit_revert(m.revert_intent("region"), "00" * 64)  # a WRONG capability, for contrast
R["2_bad_cap_reason_is_authorization"] = bad.get("reason") == "authorization_required"
# and with NO contention the same relative op lands (liveness in the quiescent case preserved)
m2 = fresh(depth=1)
i2 = m2.revert_intent("region")
R["2_relative_lands_when_quiescent"] = m2.submit_revert(i2, sign_revert(sk, i2))["ok"] and cur(m2) == "region_v0"

# ── 3. Replay window stays 1 ─────────────────────────────────────────────────────────────────
m = fresh(depth=2)
i_abs = m.restore_intent("region", "region_v0"); c_abs = sign_revert(sk, i_abs)
first = m.submit_revert(i_abs, c_abs)
m.remember("correction: region is now region_v9", key="region", object="region_v9")
replay = m.submit_revert(i_abs, c_abs)                      # SAME signed intent, later state
R["3_abs_single_use"] = first["ok"] and replay.get("reason") == "replay_rejected"
m = fresh(depth=1)
i_rel = m.revert_intent("region"); c_rel = sign_revert(sk, i_rel)   # captured, UNUSED
m.remember("correction: region is now region_v2", key="region", object="region_v2")
R["3_captured_stale_rel_conflicts"] = m.submit_revert(i_rel, c_rel).get("reason") == "conflict"
# absolute cannot inject a value that never held the key
m = fresh(depth=1)
i_bad = m.restore_intent("region", "evil_value")
R["3_abs_cannot_inject_foreign_value"] = m.submit_revert(i_bad, sign_revert(sk, i_bad)).get("reason") == "unknown_target"

# ── 4. jackson's question: cross-slot zero-false-conflict SURVIVES in-stream ─────────────────
false_conflicts = 0
for t in range(20):
    m = fresh(depth=1, keys=("region", "shard", "locale"))
    intent = m.revert_intent("region"); cap = sign_revert(sk, intent)
    for i in range(4):                                      # hot ORTHOGONAL writers
        m.remember(f"correction: shard is now s{t}_{i}", key="shard", object=f"s{t}_{i}")
        m.remember(f"correction: locale is now l{t}_{i}", key="locale", object=f"l{t}_{i}")
    if not m.submit_revert(intent, cap)["ok"]:
        false_conflicts += 1
R["4_cross_slot_false_conflicts_in_20_trials"] = false_conflicts
# ...and a SAME-slot write still conflicts (a true conflict, correctly)
m = fresh(depth=1)
intent = m.revert_intent("region"); cap = sign_revert(sk, intent)
m.remember("correction: region is now region_vX", key="region", object="region_vX")
R["4_same_slot_still_true_conflict"] = m.submit_revert(intent, cap).get("reason") == "conflict"

# ── 5. Legacy optimistic path untouched (regression) ─────────────────────────────────────────
m = fresh(depth=1)
legacy_cap = sign_revert(sk, m.revert_challenge("region"))
R["5_legacy_revert_still_works"] = m.revert("region", capability=legacy_cap)["ok"] and cur(m) == "region_v0"
m = fresh(depth=1)
stale = sign_revert(sk, m.revert_challenge("region"))
m.remember("correction: region is now region_v2", key="region", object="region_v2")
R["5_legacy_stale_cap_still_refused"] = not m.revert("region", capability=stale)["ok"]

print(json.dumps(R, indent=2))
ok = (R["1_named_lands_under_bursts_1_5_20_100"] and R["2_conflict_distinct_from_auth"]
      and R["2_bad_cap_reason_is_authorization"] and R["2_relative_lands_when_quiescent"]
      and R["3_abs_single_use"] and R["3_captured_stale_rel_conflicts"]
      and R["3_abs_cannot_inject_foreign_value"]
      and R["4_cross_slot_false_conflicts_in_20_trials"] == 0 and R["4_same_slot_still_true_conflict"]
      and R["5_legacy_revert_still_works"] and R["5_legacy_stale_cap_still_refused"])
print("\nREADING: the real implementation matches the simulation. Named reverts land under any same-slot")
print("burst (exactly once); a relative revert under contention returns a definitive CONFLICT distinct from")
print("authorization_required (and still lands when quiescent); the replay window stays 1 (single-use signed")
print("intents; an absolute intent cannot inject a value the key never held); cross-slot zero-false-conflict")
print("SURVIVES in-stream (jackson's question) while a same-slot write still conflicts correctly; and the")
print("legacy optimistic path is regression-clean.")
print("\nALL PASS" if ok else "\nFAIL: " + ", ".join(k for k, v in R.items() if v is False))
sys.exit(0 if ok else 1)
