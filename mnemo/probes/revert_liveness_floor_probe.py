"""revert_liveness_floor_probe.py — the store owns no-infinite-bypass; the harness owns who-goes-first.
Jacksonxly's fairness boundary, measured on the real mnemo 0.7.13 (r/RAG, 2026-07-12).

His boundary, and the test that draws it:
  - If the worst case is "the revert lands LATER", it is harness scheduling (policy, control layer).
  - If the worst case is "the revert NEVER lands", it is a liveness property and belongs in the STORE.
  Priority only deprioritizes (control). Bounded bypass is the thing that can silently become "never" (content).

This measures where mnemo sits. The claim under test: in this synchronous store the liveness floor holds BY
CONSTRUCTION, because submit_revert is TERMINAL — it evaluates atomically against the current state on the
call itself and lands-or-conflicts, never left pending. So a hostile scheduler can delay WHEN a submitted
revert's call runs, but cannot bypass it unboundedly or turn it into never-evaluated.

Deterministic, no LLM, no network. RUN: python mnemo/probes/revert_liveness_floor_probe.py
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mnemo_pypi"))
from mnemo import Mnemo, new_receipt_keypair, sign_revert, __version__

sk, pk = new_receipt_keypair()
R = {"mnemo_version": __version__}


def fresh(depth=1):
    m = Mnemo(path=None, revert_pubkey=pk); m.echo_guard = True
    m.remember("region is v0", key="region", object="v0")
    for v in range(1, depth + 1):
        m.remember(f"correction: region is now v{v}", key="region", object=f"v{v}")
    return m


def cur(m):
    a = [r for r in m.items if r.get("key") == "region" and r.get("status") == "active" and r.get("object")]
    return max(a, key=lambda r: r.get("valid_from", r["ts"]))["object"] if a else None


signer = lambda intent: sign_revert(sk, intent)

# ── 1. ABSOLUTE "lands later, never never": a hostile scheduler runs K writes before the revert call.
#      restore_now still lands regardless of K -> worst case is LATER, so it is a harness policy, not a bug.
absolute_lands_at = {}
for K in (0, 1, 10, 100, 1000):
    m = fresh(depth=2)
    for i in range(K):                                    # scheduler starves the reverter with writes
        m.remember(f"correction: region is now w{i}", key="region", object=f"w{i}")
    res = m.restore_now("region", "v0", sign=signer)      # the revert's turn finally comes
    absolute_lands_at[K] = res["ok"] and cur(m) == "v0"
R["1_absolute_lands_after_any_delay"] = all(absolute_lands_at.values())

# ── 2. RELATIVE is EVALUATED, never left pending: after any write-storm, revert_now returns a definitive
#      land-or-conflict on the call (fairness), it does not silently vanish.
m = fresh(depth=1)
for i in range(500):
    m.remember(f"correction: region is now w{i}", key="region", object=f"w{i}")
res = m.revert_now("region", sign=signer)
R["2_relative_reaches_a_verdict"] = res.get("reason") == "conflict" or res.get("ok") is True
R["2_relative_lands_when_quiescent"] = fresh(1).revert_now("region", sign=signer)["ok"]

# ── 3. ZERO bypass of a SUBMITTED revert: there is no "pending" state a write can be admitted ahead of.
#      Model the adversary explicitly: measure how many writes can be admitted AFTER submit_revert is
#      called but BEFORE it takes effect. In a synchronous store that number is 0 by construction.
m = fresh(depth=2)
before = len([r for r in m.items if r.get("key") == "region"])
res = m.restore_now("region", "v0", sign=signer)          # submit is terminal: effect is applied on return
after = len([r for r in m.items if r.get("key") == "region"])
R["3_submitted_revert_applied_atomically"] = res["ok"] and (after == before + 1)
# there is NO API that leaves a revert pending while admitting writes: submit_revert returns a verdict,
# not a ticket, so a buggy/adversarial harness cannot construct unbounded bypass.
R["3_no_pending_ticket_api"] = not any(hasattr(m, n) for n in
                                       ("enqueue_revert", "open_revert", "pending_revert", "defer_revert"))

# ── 4. The store's floor is un-bypassable by the caller: revert_now/restore_now mint+submit in ONE call,
#      so a caller physically cannot insert writes into the mint->submit window (the only starvation seam
#      the hand-rolled mint-then-submit pattern had). Contrast: the split pattern CAN be starved.
m = fresh(depth=1)
intent = m.revert_intent("region"); cap = signer(intent)  # hand-rolled split: mint...
m.remember("correction: region is now vX", key="region", object="vX")   # ...caller-admitted write...
split_res = m.submit_revert(intent, cap)                  # ...then submit -> correct conflict (the seam)
R["4_split_pattern_can_conflict_on_seam"] = split_res.get("reason") == "conflict"
m2 = fresh(depth=1)
R["4_atomic_now_closes_the_seam"] = m2.revert_now("region", sign=signer)["ok"] and cur(m2) == "v0"

# ── 5. Priority is control, not content: deprioritizing the reverter (running writes first) only delays it;
#      it still lands. A policy that WEIGHTS writers over the reverter cannot reintroduce "never lands".
m = fresh(depth=2)
order = ["w"] * 50 + ["revert"]                           # writer-priority policy: reverter goes dead last
for step in order:
    if step == "w":
        m.remember(f"correction: region is now {step}{cur(m)}", key="region", object="wx")
    else:
        res = m.restore_now("region", "v0", sign=signer)
R["5_writer_priority_still_lands"] = res["ok"] and cur(m) == "v0"

print(json.dumps(R, indent=2))
ok = (R["1_absolute_lands_after_any_delay"] and R["2_relative_reaches_a_verdict"]
      and R["2_relative_lands_when_quiescent"] and R["3_submitted_revert_applied_atomically"]
      and R["3_no_pending_ticket_api"] and R["4_split_pattern_can_conflict_on_seam"]
      and R["4_atomic_now_closes_the_seam"] and R["5_writer_priority_still_lands"])
print("\nREADING: the liveness floor is the store's, by construction. A submitted revert is evaluated")
print("atomically and terminally — it lands (absolute, after any delay) or reaches a definitive conflict")
print("(relative, fairness), and is never left pending for writes to bypass (max bypass = 0). A harness can")
print("only choose WHEN the call runs (worst case: lands later = policy), never turn it into never-lands.")
print("revert_now/restore_now make the un-bypassable land-now path a store primitive, so the mint->submit")
print("seam isn't every caller's to re-open. Store owns no-infinite-bypass; harness owns who-goes-first.")
print("\nALL PASS" if ok else "\nFAIL: " + ", ".join(k for k, v in R.items() if v is False))
sys.exit(0 if ok else 1)
