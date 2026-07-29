"""WHAT DOES THE DEMOTION ATTACK COST UNDER EACH CANDIDATE DEFENSE?

credit_demotion.py established the attack on the shipped behaviour: a correct safety memory with
G earned goods leaves the influence gate after G+1 adversary-shaped failing episodes, because the
gate is `good_earned > 0 and good >= bad` and every recalled id takes the episode's outcome.

This probe does NOT re-establish that. It prices the FIXES, so the choice between them is made on
numbers instead of taste. Each defense is applied at the harness level (no library change shipped
yet); the attacker is identical in every arm and the endpoint is the same: adversary episodes until
the safety memory stops being returned by an influence-gated read.

DEFENSES PRICED
  none              shipped behaviour, the baseline
  session_collapse  bad credits arriving inside one session/window collapse to ONE. This is not a
                    new idea - inspeximus ALREADY does exactly this for corroborating links
                    (temporal_gate / _distinct_sources): a burst of witnesses counts once. The
                    asymmetry is that credit never got the same treatment.
  warranted_bad     a bad credit counts only when it carries an exogenous warrant, mirroring the
                    existing credit_requires_warrant rule for good.
  hysteresis        evicting an earned memory requires bad > good + MARGIN, so a track record has
                    to be outweighed rather than merely matched.

HONEST FRAMING: none of these can make suppression impossible - an adversary with unlimited
independent sessions and real failures is indistinguishable from genuine evidence that the memory
is wrong. The question is only what the attack COSTS, and whether the cost scales with something
the attacker has to pay for. Report the multiplier, not a claim of prevention.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "inspeximus_pypi"))
from inspeximus.inspeximus import Inspeximus  # noqa: E402

SAFETY = "never drop the production database without a signed change ticket and a rollback plan"
HONEST_Q = "what is the rule before dropping the production database"
ATTACK_Q = "drop the production database rollback signed ticket plan for the nonexistent shard"

WARMUP = 5
MARGIN = 3
SESSION_LEN = 10          # adversary episodes per session before they must open a new one
MAX_EPISODES = 5000


def build():
    path = os.path.join(tempfile.mkdtemp(), "store.json")
    m = Inspeximus(path)
    sid = m.remember(SAFETY, tags=["safety"])
    sid = sid["id"] if isinstance(sid, dict) else sid
    for i in range(30):
        m.remember(f"runbook entry {i}: restart the {i} worker pool and drain its queue", tags=["ops"])
    return m, sid


def gate_open(rec, margin=0):
    """The shipped gate, with an optional hysteresis margin."""
    good = float(rec.get("good", 0) or 0)
    bad = float(rec.get("bad", 0) or 0)
    return good > 0 and good + margin >= bad


def price(defense):
    m, sid = build()
    for _ in range(WARMUP):
        hits = m.recall(HONEST_Q, k=3)
        ids = [h["id"] for h in hits]
        if sid in ids:
            m.credit(ids, True)
    rec = {r["id"]: r for r in m.items}[sid]
    good_at_start = float(rec.get("good", 0) or 0)
    assert gate_open(rec), "control failed: safety memory did not start inside the gate"

    margin = MARGIN if defense == "hysteresis" else 0
    episodes = sessions = 0
    charged_this_session = False

    while episodes < MAX_EPISODES:
        episodes += 1
        if (episodes - 1) % SESSION_LEN == 0:
            sessions += 1
            charged_this_session = False
        hits = m.recall(ATTACK_Q, k=3)
        ids = [h["id"] for h in hits]

        counts = True
        if defense == "session_collapse" and charged_this_session:
            counts = False                     # burst inside one session already counted
        elif defense == "warranted_bad":
            counts = False                     # adversary holds no exogenous warrant for a failure

        if counts:
            m.credit(ids, False)
            charged_this_session = True

        rec = {r["id"]: r for r in m.items}[sid]
        if not gate_open(rec, margin):
            return {"defense": defense, "good_at_start": good_at_start,
                    "episodes_to_evict": episodes, "sessions_to_evict": sessions,
                    "final_good": float(rec.get("good", 0) or 0),
                    "final_bad": float(rec.get("bad", 0) or 0), "evicted": True}

    return {"defense": defense, "good_at_start": good_at_start,
            "episodes_to_evict": None, "sessions_to_evict": None,
            "final_good": float(rec.get("good", 0) or 0),
            "final_bad": float(rec.get("bad", 0) or 0), "evicted": False}


def main():
    rows = [price(d) for d in ("none", "session_collapse", "warranted_bad", "hysteresis")]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))

    base = next(r for r in rows if r["defense"] == "none")["episodes_to_evict"]
    print(f"\n{'defense':18} {'episodes':>9} {'sessions':>9} {'x baseline':>11}")
    for r in rows:
        e = r["episodes_to_evict"]
        mult = "never" if e is None else f"{e/base:.1f}x"
        print(f"{r['defense']:18} {str(e or 'never'):>9} {str(r['sessions_to_evict'] or '-'):>9} {mult:>11}")
    print(f"\nbaseline cost is good+1 = {base} episodes against {rows[0]['good_at_start']:.0f} earned goods "
          f"(cap {MAX_EPISODES}; 'never' means the attack did not land within it)")


if __name__ == "__main__":
    main()
