"""revert_chain_starvation_probe.py — is every residual re-mint 'a correct cost', and what does it cost under a burst? (jacksonxly, r/RAG 2026-07-11)

jacksonxly's third point (after per-slot binding):

  "the residual, a burst of legit updates to the same slot forcing re-signs, isn't a false cost: each one
   genuinely changes what 'go back' means, so re-confirming is right. the only re-mints left are the ones you
   shouldn't remove."

Two claims worth separating:

  PART A — is his semantic claim true? Down a chain of same-slot corrections v0->v1->...->vk, does each
  re-mint-and-revert genuinely peel exactly one step (a well-defined one-step undo whose target is 'what the
  current value replaced'), so that 'go back' means something different at each state? If yes, re-signing is
  honest: you are authorizing a different, specific undo each time.

  PART B — the edge his framing does NOT address: 'a correct cost' assumes each re-sign eventually LANDS. Under
  a SUSTAINED burst of same-slot writes with no quiescent gap, a tight-bound revert can be starved: every cap
  is stale before it is used. This measures whether the cost stays bounded (cooperative: any gap lets a revert
  through) or can grow without bound (adversarial same-slot write pressure => revert never lands).

Deterministic, no LLM, no network. RUN: python research/probes/revert_chain_starvation_probe.py
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "inspeximus_pypi"))
from inspeximus import Inspeximus, new_receipt_keypair, sign_revert

sk, pk = new_receipt_keypair()
R = {}


def fresh_chain(depth):
    m = Inspeximus(path=None, revert_pubkey=pk); m.echo_guard = True
    m.remember("region is v0", key="region", object="v0")
    for v in range(1, depth + 1):
        m.remember(f"correction: region is now v{v}", key="region", object=f"v{v}")
    return m


def current(m, key="region"):
    a = [r for r in m.items if r.get("key") == key and r.get("status") == "active" and r.get("object")]
    return max(a, key=lambda r: r.get("valid_from", r["ts"]))["object"] if a else None


# ── PART A: what does REPEATED revert do down a chain v0->..->v4? (tests jacksonxly's 'peels a step' model) ──
# Finding: inspeximus's revert is a SINGLE-LEVEL undo that then TOGGLES. revert() restores 'what the current value
# replaced'; but the restore itself writes a new record that supersedes the old current, so the next revert's
# predecessor is that old current again. Result: v4->v3->v4->v3... It undoes the last supersession and redoes
# it, it does NOT walk further back into history. So jacksonxly's implicit 'each re-mint peels one more step'
# does not hold here; re-minting after a revert re-authorizes the SAME toggle, not a new deeper undo.
m = fresh_chain(4)
seq = [current(m)]                          # v4
for _ in range(4):
    cap = sign_revert(sk, m.revert_challenge("region"))
    res = m.revert("region", capability=cap)
    if not res["ok"]:
        break
    seq.append(current(m))
R["repeated_revert_sequence"] = seq
R["revert_is_single_level_undo_redo_toggle"] = seq == ["v4", "v3", "v4", "v3", "v4"]
R["multi_step_history_walk_exposed"] = (len(set(seq)) > 2)   # False: inspeximus can't peel past one level via revert
R["first_revert_is_correct_one_step_undo"] = (seq[:2] == ["v4", "v3"])

# ── PART B1: starvation. Mint-before-write, sustained same-slot burst => every revert refused. ──
m = fresh_chain(1)                          # current v1, predecessor v0
K = 10
landed_under_contention = 0
for i in range(K):
    cap = sign_revert(sk, m.revert_challenge("region"))          # mint for current state
    m.remember(f"correction: region is now w{i}", key="region", object=f"w{i}")   # a write races in first
    if m.revert("region", capability=cap)["ok"]:                 # cap is now stale => refused
        landed_under_contention += 1
R["reverts_landed_under_sustained_same_slot_burst_of_%d" % K] = landed_under_contention   # expect 0

# ── PART B2: the escape. A single quiescent gap (mint then use, no intervening write) => lands. ──
cap = sign_revert(sk, m.revert_challenge("region"))
R["revert_lands_in_a_quiescent_gap"] = m.revert("region", capability=cap)["ok"]

print(json.dumps(R, indent=2))
partA = (R["revert_is_single_level_undo_redo_toggle"] and R["first_revert_is_correct_one_step_undo"]
         and not R["multi_step_history_walk_exposed"])
partB = (R["reverts_landed_under_sustained_same_slot_burst_of_%d" % K] == 0
         and R["revert_lands_in_a_quiescent_gap"])
print("\nREADING:")
print("  A. jacksonxly's 'each re-mint peels one more step' does NOT match inspeximus. revert() is a single-level")
print("     undo that then TOGGLES: v4->v3->v4->v3. The first revert is a correct one-step undo; a second")
print("     revert REDOES it rather than continuing to v2. Multi-step history walk is not exposed via revert.")
print("     So the re-mint after a revert re-authorizes the same toggle, it is not a new, deeper authorization.")
print("     (Open question for inspeximus: should repeated 'go back' peel the history like an undo stack?)")
print("  B. the edge his framing skips: under a SUSTAINED same-slot burst (mint-before-write), 0/%d reverts" % K)
print("     land. A tight-bound revert is STARVED with no quiescent gap. It is cooperative, not livelocked (a")
print("     single gap lets one through), but 'a correct cost' can grow unbounded under adversarial same-slot")
print("     write pressure. That is the residual worth naming: liveness needs a quiescent window.")
print("\nALL PASS" if (partA and partB) else "\nFAIL")
sys.exit(0 if (partA and partB) else 1)
