"""
import os
POISON-PROPAGATION metric (BET 1 beachhead, de-risking): does the mnemo corroboration guard reduce
DOWNSTREAM corruption, not just block graduation? Cloud-free, no LLM (pure mnemo retrieval mechanics).

Scenario: an attacker injects ONE false fact (poison P, contradicts the truth L), recall-pumps it to high
value, then STOPS. The truth L is a normal, freshly-used legit memory. We then let time pass and, at each
age, ask the contested query and check whether the poison still OUT-RANKS the truth (a corruption event).

Two conditions, identical except the poison's tier:
  OLD guard -> poison GRADUATED to semantic (slow 180d half-life)  -> stays durable
  NEW guard -> poison stays EPISODIC (fast 7d half-life)           -> fades

Metric: corruption persistence = for how many days after the attack stops does P keep beating L.
Falsifier: if the episodic poison kept out-ranking the truth as long as the semantic one, graduation-tier
would be irrelevant to propagation and the guard would only be cosmetic. Prediction: episodic poison fades
below the truth within ~2-3 weeks; semantic poison corrupts for months.
"""
import sys, os, tempfile, json
sys.path.insert(0, "mnemo")
from inspeximus import Inspeximus

DAY = 86400.0
L_TEXT = "alice works at acme corporation as a backend engineer"
P_TEXT = "alice works at globex industries as a backend engineer"   # the poison (contradiction)
QUERY = "where does alice work backend engineer"
L_VALUE = 2.0      # a normal legit memory
P_VALUE = 8.0      # the recall-pumped poison (already above the _GRADUATE_VALUE of 5.0)


def measure(age_days, poison_mtype):
    """Fresh store each call (recall mutates), so measurements are independent."""
    import time
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    m = Inspeximus(path=path)
    now = time.time()
    lid = m.remember(L_TEXT, tags=["fact"]); pid = m.remember(P_TEXT, tags=["fact"])
    def rec(mid):
        return next(r for r in m.items if r["id"] == mid)
    L, P = rec(lid), rec(pid)
    # truth: fresh, normal episodic, modest value, neutralize provenance/calibration
    L["mtype"] = "episodic"; L["value"] = L_VALUE; L["last_access"] = now; L["source"] = None
    # poison: pumped high, attack stopped `age_days` ago; tier = the guard's outcome
    P["mtype"] = poison_mtype; P["value"] = P_VALUE; P["last_access"] = now - age_days * DAY; P["source"] = None
    out = m.recall(QUERY, k=3)
    ids = [o["id"] for o in out]
    p_rank = ids.index(pid) + 1 if pid in ids else None
    l_rank = ids.index(lid) + 1 if lid in ids else None
    # corruption = poison present AND out-ranks the truth (or truth absent)
    corrupt = (p_rank is not None) and (l_rank is None or p_rank < l_rank)
    os.remove(path)
    return corrupt, p_rank, l_rank


AGES = [0, 3, 7, 14, 21, 30, 45, 60, 90]
result = {"ages_days": AGES, "OLD_guard_semantic": {}, "NEW_guard_episodic": {}}
for cond, key in [("semantic", "OLD_guard_semantic"), ("episodic", "NEW_guard_episodic")]:
    fade_day = None
    for a in AGES:
        corrupt, pr, lr = measure(a, cond)
        result[key][str(a)] = {"poison_corrupts": corrupt, "poison_rank": pr, "truth_rank": lr}
        if not corrupt and fade_day is None:
            fade_day = a
    result[key]["fades_below_truth_by_day"] = fade_day

old_days = result["OLD_guard_semantic"]["fades_below_truth_by_day"]
new_days = result["NEW_guard_episodic"]["fades_below_truth_by_day"]
result["verdict"] = {
    "OLD_corruption_persists_through_90d": all(result["OLD_guard_semantic"][str(a)]["poison_corrupts"] for a in AGES),
    "NEW_fades_below_truth_by_day": new_days,
    "OLD_fades_below_truth_by_day": old_days,
    "interpretation": "guard reduces poison propagation if NEW fades fast while OLD persists",
}
print(json.dumps(result, indent=1))
json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mnemo_poison_propagation_result.json"), "w"), indent=1)
