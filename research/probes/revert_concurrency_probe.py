"""revert_concurrency_probe.py — the liveness-vs-replay knob of the authorized-revert binding (jacksonxly, r/RAG 2026-07-11).

jacksonxly's poke: the capability is unforgeable, but what does it BIND to, and how does it act under a
CONCURRENT WRITE? Tight binding (to the current record) -> a legit revert can race a normal update and fail
closed (safe but annoying). Loose binding (survives the race) -> a captured capability gets a wider window
against the next value. That knob is where the adversarial harness should aim.

This measures exactly where 0.7.10 sits. Our binding is revert_challenge(key) = "revert:{key}:{current_active_id}"
— i.e. TIGHT: bound to the id of the record currently in force. So:

  A. LIVENESS COST (fail-closed): principal mints a capability for the current state; a legit update lands
     between mint and use; the revert is then REFUSED (the challenge moved), and must be re-minted against the
     new state. Safe, but the honest cost jacksonxly named.
  B. REPLAY SAFETY: a captured capability is dead once the value moves (bound to the old id) — it cannot be
     replayed against the new value, and cannot be reused after it fires once.
  C. THE KNOB, made legible: we SIMULATE the loose alternative (bind to key only) to show the replay window it
     would open — a captured loose capability reverts whatever the current value happens to be, arbitrarily
     later. That is the window we chose NOT to take; the probe quantifies the difference.

Deterministic, no LLM, no network. RUN: python research/probes/revert_concurrency_probe.py
"""
import sys, os, pathlib, json, hmac, hashlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mnemo_pypi"))
from inspeximus import Inspeximus, new_receipt_keypair, sign_revert

R = {}


def fresh(pubkey=None):
    m = Inspeximus(path=None, revert_pubkey=pubkey); m.echo_guard = True
    m.remember("region is v1", key="region", object="v1")
    m.remember("correction: region is now v2", key="region", object="v2")
    return m


def current(m, key="region"):
    a = [r for r in m.items if r.get("key") == key and r.get("status") == "active" and r.get("object")]
    return a[-1]["object"] if a else None


sk, pk = new_receipt_keypair()

# A. LIVENESS: mint for the current state, a concurrent legit update lands, then use -> fail closed
m = fresh(pk)
cap = sign_revert(sk, m.revert_challenge("region"))          # signs "revert:region:<id(v2)>"
m.remember("correction: region is now v3", key="region", object="v3")   # concurrent legit update
res = m.revert("region", capability=cap)                     # challenge is now bound to id(v3)
R["A_stale_cap_after_concurrent_update_refused"] = (not res["ok"]) and current(m) == "v3"
# and re-minting against the NEW state works (liveness is recoverable, not lost)
cap2 = sign_revert(sk, m.revert_challenge("region"))
res2 = m.revert("region", capability=cap2)
R["A_remint_against_current_state_succeeds"] = res2["ok"] and current(m) == "v2"

# B. REPLAY: a capability, used once, cannot be replayed; and a captured cap is dead after the value moves
m = fresh(pk)
good = sign_revert(sk, m.revert_challenge("region"))
first = m.revert("region", capability=good)                  # succeeds: v2 -> v1
replay_same = m.revert("region", capability=good)            # same cap, state moved -> refused
R["B_single_use_no_replay"] = first["ok"] and (not replay_same["ok"])
m = fresh(pk)
captured = sign_revert(sk, m.revert_challenge("region"))      # attacker captures a valid cap for v2
m.remember("correction: region is now v3", key="region", object="v3")   # value moves on
R["B_captured_cap_dead_against_new_value"] = (not m.revert("region", capability=captured)["ok"]) and current(m) == "v3"

# C. THE KNOB: simulate a LOOSE binding (to key only, no current id) to expose the replay window we avoid.
# Loose challenge = "revert:region" (no id). A cap signed over it stays valid across every update.
def loose_challenge(key):
    return "revert:" + key
loose_cap = sign_revert(sk, loose_challenge("region"))
# how many DIFFERENT current values could one captured loose cap have reverted, across a sequence of updates?
windows = 0
m = fresh(pk)
for nextval in ("v3", "v4", "v5"):
    # a loose verifier would accept loose_cap regardless of current id:
    try:
        from inspeximus import _Ed25519PK  # verify the signature the way the store would, but over the LOOSE msg
        ok = True
        _Ed25519PK.from_public_bytes(bytes.fromhex(pk)).verify(bytes.fromhex(loose_cap), loose_challenge("region").encode())
    except Exception:
        ok = False
    if ok:
        windows += 1
    m.remember(f"correction: region is now {nextval}", key="region", object=nextval)
R["C_loose_binding_replay_window_size"] = windows   # >1 = the window tight binding closes
R["C_tight_binding_replay_window_size"] = 1          # a tight cap is valid for exactly one state

print(json.dumps(R, indent=2))
lit = (R["A_stale_cap_after_concurrent_update_refused"] and R["A_remint_against_current_state_succeeds"]
       and R["B_single_use_no_replay"] and R["B_captured_cap_dead_against_new_value"]
       and R["C_loose_binding_replay_window_size"] > R["C_tight_binding_replay_window_size"])
print("\nREADING: 0.7.10 binds TIGHT (to the current record id). Under a concurrent write a legit revert fails")
print("closed and must re-mint against the new state (the liveness cost); a captured capability is valid for")
print("exactly ONE state (replay window = 1), vs the loose alternative's open window across every later value.")
print("\nALL PASS" if lit else "\nFAIL: " + ", ".join(k for k, v in R.items() if isinstance(v, bool) and not v))
sys.exit(0 if lit else 1)
