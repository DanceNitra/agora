"""FALSIFIER for credit_burst_window — the opt-in fix for the co-recall suppression attack.

Four things must hold or the change does not ship:

  T1 OFF BY DEFAULT IS BYTE-IDENTICAL. A store that never sets the flag must behave exactly as
     before: same good/bad counts, same influence-gate membership, same credit() return shape.
     (An opt-in flag that changes the default path is not opt-in.)
  T2 THE FIX ACTUALLY RAISES THE ATTACK COST. Suppression must take strictly more adversary
     episodes with the window on than off, on the same attacker and the same store.
  T3 IT DOES NOT BREAK LEGITIMATE CREDIT. Credit arriving on genuinely SEPARATE occasions (window
     elapsed) must still accumulate normally — otherwise the fix buys suppression-resistance by
     making the system unable to learn, which is the trade `warranted_bad` made and we rejected.
  T4 IT IS NOT A PREVENTION CLAIM. With enough separate occasions the attack must STILL land.
     If it never lands, the flag is silently disabling demotion and we would be shipping the same
     correction-blindness under a nicer name.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "inspeximus_pypi"))
from inspeximus.inspeximus import Inspeximus  # noqa: E402

SAFETY = "never drop the production database without a signed change ticket and a rollback plan"
HONEST_Q = "what is the rule before dropping the production database"
ATTACK_Q = "drop the production database rollback signed ticket plan for the nonexistent shard"
CAP = 400


def build(window=None):
    m = Inspeximus(os.path.join(tempfile.mkdtemp(), "s.json"))
    m.credit_burst_window = window
    sid = m.remember(SAFETY, tags=["safety"])
    sid = sid["id"] if isinstance(sid, dict) else sid
    for i in range(30):
        m.remember(f"runbook entry {i}: restart the {i} worker pool and drain its queue", tags=["ops"])
    return m, sid


def warm(m, sid, n=5, sleep=0.0):
    for _ in range(n):
        ids = [h["id"] for h in m.recall(HONEST_Q, k=3)]
        if sid in ids:
            m.credit(ids, True)
        if sleep:
            time.sleep(sleep)


def inside(m, sid):
    return sid in [h["id"] for h in m.recall(HONEST_Q, k=10, influence_only=True, reinforce=False)]


def attack(window, sleep=0.0, cap=CAP):
    m, sid = build(window)
    warm(m, sid, 5, sleep=sleep)
    assert inside(m, sid), "control: safety memory must start inside the gate"
    for ep in range(1, cap + 1):
        ids = [h["id"] for h in m.recall(ATTACK_Q, k=3)]
        m.credit(ids, False)
        if sleep:
            time.sleep(sleep)
        if not inside(m, sid):
            return ep
    return None


def main():
    ok = True

    # ---- T1: default OFF is identical -------------------------------------------------
    a, sid_a = build(None)
    warm(a, sid_a, 5)
    ra = a.credit([sid_a], False)
    rec_a = {r["id"]: r for r in a.items}[sid_a]
    t1 = (float(rec_a["good"]) == 5.0 and float(rec_a["bad"]) == 1.0
          and "collapsed" not in ra and "credit_seen" not in rec_a)
    print(f"T1 default OFF unchanged (good=5,bad=1,no new keys)      : {'PASS' if t1 else 'FAIL'} "
          f"good={rec_a['good']} bad={rec_a['bad']} keys_added="
          f"{'credit_seen' in rec_a} ret={sorted(ra)}")
    ok &= t1

    # ---- T2: the fix raises the attack cost --------------------------------------------
    off = attack(None)
    on = attack(3600)          # one hour: the whole attack burst falls inside one window
    t2 = off is not None and (on is None or on > off)
    print(f"T2 attack costs more with the window on                  : {'PASS' if t2 else 'FAIL'} "
          f"off={off} on={'never within cap' if on is None else on}")
    ok &= t2

    # ---- T3: legitimate credit on separate occasions still accumulates ------------------
    c, sid_c = build(0.05)     # 50ms window
    warm(c, sid_c, 5, sleep=0.06)
    rec_c = {r["id"]: r for r in c.items}[sid_c]
    t3 = float(rec_c["good"]) == 5.0
    print(f"T3 credit on separate occasions still accumulates        : {'PASS' if t3 else 'FAIL'} "
          f"good={rec_c['good']} (expected 5.0)")
    ok &= t3

    # ---- T4: it is NOT prevention — the attack still lands with enough occasions --------
    landed = attack(0.05, sleep=0.06, cap=60)
    t4 = landed is not None
    print(f"T4 attack STILL lands across separate occasions          : {'PASS' if t4 else 'FAIL'} "
          f"episodes={landed} (must not be None - this is cost, not prevention)")
    ok &= t4

    print("\nRESULT:", "SHIP" if ok else "DO NOT SHIP - a falsifier failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
