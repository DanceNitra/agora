# herdcheck — will your multi-agent system / ensemble herd, or stay wiser than its best member?

> 2026's multi-agent finding: teams of LLM agents "consistently fail to match their best individual
> member" (losses up to ~38%) — when agents read each other's *conclusions* they converge on
> plausible-but-wrong consensus (the "popularity trap"). Classical ensembles assume independent errors;
> agents that watch each other don't have them. `herdcheck` measures exactly when the wisdom collapses
> and what fixes it. One file, zero dependencies.
> A sibling of [nullcheck](../nullcheck) / [idcheck](../idcheck) / [goodhart](../goodhart) / [selfref](../selfref).

## The measured collapse (`python herdcheck.py`)
```
collective accuracy vs how many peers each agent observes (single member = 60%):
   peers seen | collective accuracy
            0 |        100%      <- fully independent: the wisdom-of-crowds ceiling
            1 |         90%
            2 |         64%      <- already collapsed toward one member's competence
            3 |         69%
            5 |         66%
```
A fully independent crowd is near-perfect. The moment each agent observes just **two** peers' choices,
the collective is barely better than a single member — adding more peers doesn't help, the damage is
done at the second one.

## Use it
```python
from herdcheck import ensemble_accuracy, audit

audit(peers_seen=2, own_weight=1.0)
# -> "HERDED — collective 64% ~= a single member (60%); the crowd is no wiser than one agent"
#    fix: weight own evidence >= peers, discount peer signals, or share evidence not verdicts

audit(peers_seen=2, own_weight=1.0, discount=0.5)   # rationally down-weight redundant peers
# -> "INDEPENDENT WISDOM — keeps 99% of its edge; not herding"
```

## The fix (also measured)
The cure is **not** a sparser network — it's to stop treating a peer's conclusion as a fresh fact:
```
peers_seen=2, own_weight=1, full-weight peers : 64%   (herded)
peers_seen=2, own_weight=3, full-weight peers : 100%  (trust your own evidence more)
peers_seen=2, own_weight=1, discount peers 0.5: 100%  (down-weight redundant peer signals)
```
Onset threshold: `k_c = own_weight + 1`. Practically: cap how many peer *verdicts* an agent ingests,
weight its own evidence at least as much, or — best — have agents **share evidence, not conclusions**
(an observed verdict already bakes in everything that agent saw, so it's not independent information).

## Why it matters
Multi-agent LLM systems fail in production at high rates partly from exactly this: one agent's
hallucination becomes an accepted premise downstream, and "consensus" amplifies shared errors instead
of cancelling independent ones. `herdcheck` turns "should I add another agent / let them see each
other?" into a measured verdict. Grounded in Agora Lab `678a9c` and its independent red-team `14becd`
(the collapse is specific to *naive, equal-weight* social updating; redundancy-aware agents are immune).
Open-core; the core stays free.
