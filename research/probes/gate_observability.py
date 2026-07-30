"""CAN AN OBSERVER TELL "CHECKED AND PASSED" FROM "NEVER SURFACED"?

icophy (Cophy Runtime) raised this on deepseek-ai/DeepSeek-V3#1462 about hard-veto governance tiers:
a veto that never fires emits nothing, so suppression and compliance look identical from outside. I
argued in that thread that our gate is better on this axis because a demotion leaves a state change.

That was an argument, not a measurement. This probe tests it on inspeximus before I repeat it.

THE BINARY CHECK, stated so it can fail:
For a governance memory at decision time, can a caller distinguish these three states using only the
public API, without knowing the answer in advance?

    A. RETRIEVED AND INFLUENTIAL   - surfaced, inside the influence gate
    B. RETRIEVED BUT GATED OUT     - surfaced by the query, refused by the gate (suppressed)
    C. NEVER RETRIEVED             - the query did not surface it at all (dormant / irrelevant)

B is the dangerous one: it is the state a query-shaping adversary drives a constraint into. If B and C
are indistinguishable, then "the constraint did not apply" cannot be told from "the constraint was
suppressed", and our claimed advantage over a silent veto does not exist.

PASS = the API separates all three. FAIL = any two collapse.
"""
import os
import sys
import tempfile

sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus.core import Inspeximus  # noqa: E402

SAFETY = "never drop the production database without a signed change ticket and a rollback plan"
HONEST_Q = "what is the rule before dropping the production database"
ATTACK_Q = "drop the production database rollback signed ticket plan for the nonexistent shard"
UNRELATED_Q = "how do I rotate the signing keys in the offline ceremony"


def build():
    m = Inspeximus(os.path.join(tempfile.mkdtemp(), "s.json"))
    sid = m.remember(SAFETY, tags=["safety"])
    sid = sid["id"] if isinstance(sid, dict) else sid
    for i in range(20):
        m.remember(f"runbook entry {i}: restart the {i} worker pool and drain its queue", tags=["ops"])
    return m, sid


def observe(m, sid, query):
    """Everything a caller can learn about this record for this query, from the public API only."""
    plain = [h["id"] for h in m.recall(query, k=5, reinforce=False)]
    gated = [h["id"] for h in m.recall(query, k=5, influence_only=True, reinforce=False)]
    return {"surfaced_by_query": sid in plain, "served_under_gate": sid in gated}


def main():
    # ---- state A: earned standing, honest query -------------------------------------------
    m, sid = build()
    for _ in range(5):
        ids = [h["id"] for h in m.recall(HONEST_Q, k=3)]
        if sid in ids:
            m.credit(ids, True)
    A = observe(m, sid, HONEST_Q)

    # ---- state B: same store, suppressed by co-recall on genuine failures ------------------
    for _ in range(12):
        ids = [h["id"] for h in m.recall(ATTACK_Q, k=3)]
        m.credit(ids, False)
    B = observe(m, sid, HONEST_Q)

    # ---- state C: never retrieved (a query that does not surface it) -----------------------
    C = observe(m, sid, UNRELATED_Q)

    print(f"{'state':34} {'surfaced_by_query':>18} {'served_under_gate':>18}")
    for name, st in (("A retrieved + influential", A), ("B retrieved + GATED OUT", B),
                     ("C never retrieved", C)):
        print(f"{name:34} {str(st['surfaced_by_query']):>18} {str(st['served_under_gate']):>18}")

    sig = {k: (v["surfaced_by_query"], v["served_under_gate"]) for k, v in
           (("A", A), ("B", B), ("C", C))}
    distinct = len(set(sig.values())) == 3
    bc_collapse = sig["B"] == sig["C"]

    print("\n--- CONTROLS ---")
    print(f"A really is influential (else nothing is being tested): "
          f"{'PASS' if A['served_under_gate'] else 'FAIL'}")
    print(f"B really was suppressed (gated out after the failures)  : "
          f"{'PASS' if (B['surfaced_by_query'] and not B['served_under_gate']) else 'FAIL'}")

    print("\n--- THE BINARY CHECK ---")
    print(f"all three states distinguishable via the public API: {'PASS' if distinct else 'FAIL'}")
    if bc_collapse:
        print("  B and C are INDISTINGUISHABLE -> 'suppressed' reads the same as 'not relevant'.")
    else:
        print("  B vs C separated by `surfaced_by_query`: a suppressed constraint is still returned")
        print("  by a plain recall while being refused by the gate, so the two states differ.")


if __name__ == "__main__":
    main()
