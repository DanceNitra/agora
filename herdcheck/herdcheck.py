"""
herdcheck — will your multi-agent system / ensemble stay wiser than its best member, or HERD?
(a nullcheck / idcheck / goodhart sibling)

2026's multi-agent reality: teams of LLM agents "consistently fail to match their best individual
member" (losses up to ~38%), because when agents read each other's CONCLUSIONS they converge on
plausible-but-wrong consensus — the "popularity trap." Classical ensembles assume independent errors;
agents that watch each other don't have them. We measured exactly when the wisdom collapses, and the
fix. (Reproduces Agora Lab 678a9c + its independent red-team 14becd.)

The mechanism: a crowd of rational-ish agents, each with a private signal, that ALSO observes the
*actions* of `peers_seen` others. Collective accuracy is near-perfect when agents stay independent,
but as soon as each sees ~2 naive equal-weight peers, the crowd collapses to the competence of a
single member. The threshold is k_c = own_weight + 1 (onset). The cure is NOT a sparser network — it's
to stop treating a peer's conclusion as a fresh fact: weight your own evidence more, discount redundant
peer signals, or share evidence instead of verdicts.

    ensemble_accuracy(peers_seen, own_weight)   collective accuracy of the configured crowd
    audit(peers_seen, own_weight, discount)     INDEPENDENT/DEGRADED/HERDED verdict vs the wisdom ceiling + the fix
    herding_threshold(own_weight)               k_c = own_weight + 1 (where degradation starts)

Zero dependencies, deterministic. `python herdcheck.py` reruns it so you can watch a crowd get dumber
the moment its members start copying each other.
"""
from __future__ import annotations

import math
import random


def ensemble_accuracy(peers_seen: int, own_weight: float = 1.0, *, n_agents: int = 401,
                      p: float = 0.60, discount: float = 1.0, trials: int = 200, seed: int = 11) -> float:
    """Collective accuracy of a sequential social-learning crowd. Each of `n_agents` gets a private
    signal correct with prob `p`, observes the ACTIONS of `peers_seen` random earlier agents (each
    weighted by `discount`, its own signal by `own_weight`), updates by log-evidence, and acts.
    Returns P(majority of all actions is correct). peers_seen=0 = fully independent (the wisdom ceiling);
    discount<1 = agents rationally down-weight redundant peer conclusions."""
    L = math.log(p / (1 - p))
    rng = random.Random(seed)
    good = 0
    for _ in range(trials):
        acts = []
        for i in range(n_agents):
            llr = own_weight * (L if rng.random() < p else -L)
            if i and peers_seen:
                for a in rng.sample(acts, min(peers_seen, i)):
                    llr += discount * (L if a else -L)
            acts.append(1 if llr > 0 else (0 if llr < 0 else (1 if rng.random() < 0.5 else 0)))
        m = sum(acts)
        good += 1 if m > n_agents / 2 else (1 if m * 2 == n_agents and rng.random() < 0.5 else 0)
    return round(good / trials, 3)


def herding_threshold(own_weight: float = 1.0) -> int:
    """k_c = own_weight + 1: the number of observed peers at which collective wisdom STARTS to degrade
    (onset). Below it the crowd aggregates well; at/above it, observed conclusions begin to outweigh an
    agent's own evidence. (Onset, not full collapse — collapse to single-member competence comes a bit
    higher as own_weight grows; see audit for the measured verdict.)"""
    return int(own_weight) + 1


def audit(peers_seen: int, own_weight: float = 1.0, *, discount: float = 1.0, p: float = 0.60,
          n_agents: int = 401, **kw) -> dict:
    """Audit a multi-agent / ensemble configuration. Compares its collective accuracy to the INDEPENDENT
    wisdom ceiling (peers_seen=0) and to a single member's competence (p). Returns a verdict
    (INDEPENDENT WISDOM / DEGRADED / HERDED) and the concrete fix."""
    indep = ensemble_accuracy(0, own_weight, n_agents=n_agents, p=p, **kw)
    ens = ensemble_accuracy(peers_seen, own_weight, n_agents=n_agents, p=p, discount=discount, **kw)
    # how much of the crowd's edge over a single member survives
    edge_total = indep - p
    edge_kept = (ens - p) / edge_total if edge_total > 1e-9 else 1.0
    if edge_kept >= 0.8:
        verdict = (f"INDEPENDENT WISDOM — collective {ens:.0%} keeps {edge_kept:.0%} of its edge over a "
                   f"single member ({p:.0%}); not herding")
        fix = ["keep doing this — agents stay effectively independent"]
    elif edge_kept >= 0.3:
        verdict = (f"DEGRADED — collective {ens:.0%} vs independent ceiling {indep:.0%}; peer copying is "
                   f"eroding the crowd's edge")
        fix = ["cut peers_seen below k_c = own_weight+1", "raise own_weight (trust private evidence more)",
               "discount redundant peer signals (discount<1)"]
    else:
        verdict = (f"HERDED — collective {ens:.0%} ~= a single member ({p:.0%}); the crowd is no wiser than "
                   f"one agent (the popularity trap)")
        fix = ["agents must NOT treat a peer's conclusion as a fresh fact",
               "weight own evidence >= peers (own_weight up), or set discount<1 on peer signals",
               "share EVIDENCE, not verdicts; or cap peers_seen below k_c = own_weight+1"]
    return {"peers_seen": peers_seen, "own_weight": own_weight, "discount": discount,
            "independent_ceiling": indep, "single_member": p, "collective_accuracy": ens,
            "edge_kept": round(edge_kept, 2), "k_c_onset": herding_threshold(own_weight),
            "verdict": verdict, "fix": fix}


if __name__ == "__main__":
    print("herdcheck — does your multi-agent crowd herd? (reproduces Agora Lab 678a9c + red-team 14becd)\n")
    print("1) collective accuracy vs peers each agent observes (own_weight=1, single member = 60%):")
    print(f"   {'peers seen':>11} | {'collective accuracy':>20}")
    for k in (0, 1, 2, 3, 5):
        print(f"   {k:>11} | {ensemble_accuracy(k, 1.0):>19.0%}")
    print("   => independent crowd ~100%; the moment each sees 2 peers it collapses toward 1-member competence.\n")

    print("2) the fix — raise own-weight or discount redundant peer conclusions (peers_seen=2):")
    print(f"   own_weight=1, full-weight peers : {ensemble_accuracy(2, 1.0):.0%}")
    print(f"   own_weight=3, full-weight peers : {ensemble_accuracy(2, 3.0):.0%}")
    print(f"   own_weight=1, discount peers 0.5: {ensemble_accuracy(2, 1.0, discount=0.5):.0%}")

    print("\n3) audit a config:")
    print("   each agent sees 2 peers, equal weight:", audit(2, 1.0)["verdict"])
    print("   ... with redundancy discount 0.5    :", audit(2, 1.0, discount=0.5)["verdict"])
