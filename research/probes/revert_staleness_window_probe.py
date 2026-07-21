"""revert_staleness_window_probe.py — does a bounded staleness allowance N ESCAPE the replay horn, or just widen it? (jacksonxly, r/RAG 2026-07-11)

jacksonxly's first point:

  "the staleness-counter version worries me: a bounded allowance of N just makes the replay window N states
   instead of one. accept version >= current - N and a captured cap is live for N moves, so you'd be tuning
   the exact horn you closed, not escaping it."

He is arguing against a *tempting* relaxation: to cut the liveness cost of tight binding (a legit revert
fails when a write races it), let the verifier accept a capability whose bound state is within N supersessions
of the current one. This probe MEASURES what that costs. inspeximus ships tight (N=0); we simulate the bounded-N
verifier and count, for a capability an attacker captured once, how many DIFFERENT later current-values it
could still revert as N grows. If jacksonxly is right, the replay window is exactly N+1 (the minted state plus
N moves), i.e. relaxing liveness re-opens replay linearly. That is "tuning the horn, not escaping it."

Deterministic, no LLM, no network. RUN: python research/probes/revert_staleness_window_probe.py
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "inspeximus_pypi"))
from inspeximus import Inspeximus, new_receipt_keypair, sign_revert

sk, pk = new_receipt_keypair()


def build_chain(depth):
    """A store where `region` is corrected `depth` times: v0 -> v1 -> ... -> v{depth}. Returns the store and
    the ordered list of active-record ids as each version became current (the 'states' a cap could bind to)."""
    m = Inspeximus(path=None, revert_pubkey=pk); m.echo_guard = True
    ids = []
    m.remember("region is v0", key="region", object="v0")
    ids.append(m._current_active_id("region"))
    for v in range(1, depth + 1):
        m.remember(f"correction: region is now v{v}", key="region", object=f"v{v}")
        ids.append(m._current_active_id("region"))
    return m, ids


def bounded_N_accepts(state_ids, minted_idx, current_idx, N):
    """Simulate a bounded-staleness verifier: it accepts a capability minted for state `minted_idx` while the
    live state is `current_idx` iff current is within N supersessions ahead of the minted one
    (0 <= current_idx - minted_idx <= N). N=0 is inspeximus's actual tight binding."""
    return 0 <= (current_idx - minted_idx) <= N


R = {"replay_window_by_N": {}, "note": "window = number of distinct later current-states one captured cap can still revert"}
DEPTH = 8
m, state_ids = build_chain(DEPTH)

for N in (0, 1, 2, 3, 4):
    # attacker captures a cap minted for an early state (index 1), then the value keeps moving forward.
    minted_idx = 1
    window = 0
    for current_idx in range(minted_idx, len(state_ids)):
        if bounded_N_accepts(state_ids, minted_idx, current_idx, N):
            window += 1        # a captured cap would be honored against this current-state
    R["replay_window_by_N"][f"N={N}"] = window

# inspeximus's real binding is N=0. Confirm it against the live store: a captured cap dies after exactly one move.
captured = sign_revert(sk, m.revert_challenge("region"))   # cap for the CURRENT state (v8)
first = m.revert("region", capability=captured)            # v8 -> v7, succeeds once
replay = m.revert("region", capability=captured)           # state moved to v7, same cap now refused
R["inspeximus_tight_binding_single_use"] = first["ok"] and (not replay["ok"])

print(json.dumps(R, indent=2))
win = R["replay_window_by_N"]
linear = all(win[f"N={n}"] == n + 1 for n in (0, 1, 2, 3, 4))
print("\nREADING: the replay window grows EXACTLY as N+1 (N=0 -> 1 state, N=3 -> 4 states). A bounded staleness")
print("allowance does not escape the replay horn; it widens it one state per unit of tolerance, precisely as")
print("jacksonxly said. inspeximus keeps N=0 (window = 1, single-use), paying the liveness cost instead of buying")
print("it back with replay surface.")
print("\nALL PASS" if (linear and R["inspeximus_tight_binding_single_use"]) else "\nFAIL")
sys.exit(0 if (linear and R["inspeximus_tight_binding_single_use"]) else 1)
