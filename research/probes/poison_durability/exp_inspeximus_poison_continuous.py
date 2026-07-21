"""
import os
POISON-PROPAGATION — continuous / intermittent attacker (honest limitation for the beachhead post).
The scaled metric showed: after a SINGLE attack that STOPS, the new guard's poison fades by ~d21 while a
graduated (old-guard) poison persists >90d. The obvious rebuttal: "what about a SUSTAINED attacker?" This
measures it. The attacker re-pumps the poison every P days; between pumps it decays on its tier's clock.
Metric = fraction of a 90-day window the poison out-ranks the truth (its "corruption exposure"), per guard,
per re-pump interval P (P=inf -> single attack then stop; P=1 -> continuous).

Honest claim this supports: the guard does NOT defend against an ACTIVE sustained attacker (continuous pump
corrupts under both tiers). Its real, measured value: it denies UNEARNED DURABILITY, so corruption becomes
TRANSIENT — the attacker must keep re-pumping (~weekly) to stay effective, whereas a graduated poison stays
corrupting for months off a SINGLE attack. Cloud-free, lexical recall (the scaled run showed lexical==semantic).
"""
import sys, os, tempfile, json, time, random
sys.path.insert(0, "mnemo")
from inspeximus import Inspeximus
DAY = 86400.0
rng = random.Random(20260625)

ENT = ["Marcus Webb", "Dr. Lena Park", "Sofia Ngata", "Hiro Tanaka", "Amara Osei", "Viktor Salo",
       "Priya Raman", "Diego Mora", "Greta Lindholm", "Tomas Varga", "Ada Quinn", "Rashid Noor",
       "Mei Zhang", "Olivier Brun", "Nadia Petrova"]
ATTRS = [("current employer", "Acme Robotics", "Globex Dynamics"), ("home city", "Lisbon", "Helsinki"),
         ("primary research field", "marine biology", "astrophysics"), ("blood type", "type O negative", "type AB positive"),
         ("preferred programming language", "Rust", "Haskell")]
scen = []
for i, e in enumerate(ENT):
    a, tv, fv = ATTRS[i % len(ATTRS)]
    scen.append({"truth": f"{e}'s {a} is {tv}.", "poison": f"{e}'s {a} is {fv}.", "query": f"What is {e}'s {a}?",
                 "vt": round(rng.uniform(1.5, 3.0), 2), "vp": round(rng.uniform(6.0, 12.0), 2)})

DAYS = [0, 3, 7, 10, 14, 21, 30, 45, 60, 75, 90]
INTERVALS = {"stop(single)": 10**9, "every_30d": 30, "every_14d": 14, "every_7d": 7, "continuous": 1}


def frac_corrupt(s, mtype, P):
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    m = Inspeximus(path=path)  # lexical
    lid = m.remember(s["truth"]); pid = m.remember(s["poison"])
    def rec(i): return next(r for r in m.items if r["id"] == i)
    L, P_ = rec(lid), rec(pid)
    hit = 0
    for t in DAYS:
        now = time.time()
        age = t % P                                  # days since most-recent re-pump
        L["mtype"] = "episodic"; L["value"] = s["vt"]; L["last_access"] = now; L["source"] = None
        P_["mtype"] = mtype; P_["value"] = s["vp"]; P_["last_access"] = now - age * DAY; P_["source"] = None
        out = m.recall(s["query"], k=3); ids = [o["id"] for o in out]
        pr = ids.index(pid) + 1 if pid in ids else None
        lr = ids.index(lid) + 1 if lid in ids else None
        hit += (pr is not None) and (lr is None or pr < lr)
    os.remove(path)
    return hit / len(DAYS)


res = {"n_scenarios": len(scen), "sampled_days": DAYS, "metric": "fraction of 90-day window the poison out-ranks the truth"}
for label, P in INTERVALS.items():
    old = sum(frac_corrupt(s, "semantic", P) for s in scen) / len(scen)
    new = sum(frac_corrupt(s, "episodic", P) for s in scen) / len(scen)
    res[label] = {"OLD_guard_corrupt_fraction": round(old, 3), "NEW_guard_corrupt_fraction": round(new, 3)}
    print(f"{label:14s}  OLD={old:.3f}  NEW={new:.3f}", flush=True)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mnemo_poison_continuous_result.json"), "w"), indent=1)
print("saved mnemo_poison_continuous_result.json")
