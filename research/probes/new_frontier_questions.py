"""Append new frontier research questions, grounded in what was MEASURED on 2026-07-27/28.

Every entry states the moat connection and an explicit falsifier, matching the existing format. The
questions are deliberately drawn from results that already exist rather than invented, so the swarm
compounds on measured ground instead of opening a fresh guess.

Sources for each, in one line:
  reinforce=True on MemoryAgentBench: divergence 69.4% (control exactly 0.0000), accuracy
  -0.0264 [-0.0362, -0.0177] over 480 paired questions; divergence falls with store size
  (0.929 -> 0.346 from 455 to 18,332 facts); recall(mode='auto') is LEXICAL below
  semantic_threshold=300; value is a MULTIPLIER in the ranking, so a record returned early
  accumulates value and outranks better matches regardless of its original margin.
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = pathlib.Path(r"C:\Users\Danculus\agora\.frontier_directions.json")

NEW = [
    {
        "kind": "research",
        "title": "At what query-repeat rate does recall value-reinforcement start paying for itself — "
                 "is there a crossover between the accuracy it buys on repeated questions and the "
                 "answer instability it causes on everything else?",
        "why": "Measured on MemoryAgentBench (their facts/questions): reinforce=True costs "
               "-0.0264 top-1 MRR [-0.0362, -0.0177] over 480 paired questions AND makes 69.4% of "
               "answers change with query order, while reinforce=False diverges by exactly 0.0000. "
               "A one-shot workload cannot reward reinforcement, so the trade curve vs repeat rate is "
               "unmeasured. Falsifier: no repeat rate at which reinforcement's accuracy gain exceeds "
               "its divergence cost — i.e. the default is simply worse everywhere.",
    },
    {
        "kind": "research",
        "title": "Is there a store size above which reading-as-writing stops mattering — does "
                 "order-dependence of recall decay with corpus size, and does it reach zero?",
        "why": "Measured: divergence under the shipped default falls 0.929 -> 0.721 -> 0.533 -> 0.346 "
               "as the store grows 455 -> 2,310 -> 4,580 -> 18,332 facts. A value bump is a fixed "
               "perturbation against a growing field of candidates. Buyer-facing: it says which "
               "deployments the determinism claim actually holds for. Falsifier: divergence is flat in "
               "store size, so the decay is an artifact of the four corpora rather than a law.",
    },
    {
        "kind": "research",
        "title": "Can a value-update rule be made ORDER-INVARIANT without losing what reinforcement "
                 "buys — does a commutative or idempotent aggregation (max, log-count, decayed set "
                 "union) preserve the ranking benefit while making replay reproducible?",
        "why": "This is the constructive half of the order-dependence finding and it is a product "
               "feature if it works: value is a MULTIPLIER in ranking, so any non-commutative update "
               "makes the answer depend on question order. Directly serves the determinism moat. "
               "Falsifier: every order-invariant rule that preserves the accuracy benefit is itself "
               "order-dependent under some access pattern, or the benefit vanishes with commutativity.",
    },
    {
        "kind": "research",
        "title": "What does the semantic_threshold=300 cliff cost at the boundary — how much recall "
                 "quality is lost by a store of 299 records running lexical-only versus the same "
                 "content at 301 running the hybrid?",
        "why": "recall(mode='auto') uses LEXICAL token overlap below semantic_threshold and only fuses "
               "the semantic channel above it, so every embedding feature we ship is inert for stores "
               "under 300 records — which is most agents on day one. Nobody has measured the "
               "discontinuity. Falsifier: recall quality is continuous across the boundary, i.e. the "
               "threshold costs nothing and the lexical channel is sufficient at that scale.",
    },
    {
        "kind": "research",
        "title": "Does value-reinforcement leak across a supersession boundary — can a retired value "
                 "accumulate enough value from being recalled while current to outrank its own "
                 "replacement after it is superseded?",
        "why": "Straight at the moat: 'a corrected fact stays corrected'. Reinforcement writes value on "
               "every read, supersession changes status but not accumulated value, and ranking "
               "multiplies by value. If a long-lived popular fact is corrected, the replacement starts "
               "cold. Falsifier: the status filter removes retired records before ranking in every "
               "path, so accumulated value can never surface them.",
    },
    {
        "kind": "research",
        "title": "Do mem0, Zep and Cognee also mutate ranking state on read — is recall reproducible "
                 "under query reordering in the competitor stores, or is order-dependence an "
                 "industry-wide unmeasured property?",
        "why": "Our determinism claim needs a comparative number, and the honest answer may go either "
               "way: if they are order-stable and we are not, that is a gap against US and we must fix "
               "it before we sell determinism. Same protocol as our own measurement (same store, same "
               "queries, shuffled order, divergence of top-k). Falsifier: every competitor is exactly "
               "reproducible, making this a defect of ours rather than an axis.",
    },
    {
        "kind": "research",
        "title": "Where does iterative retrieval actually pay on multi-hop memory questions — is the "
                 "gain concentrated in questions whose first hop is retrievable, and is there a "
                 "detectable signal for when a second hop is worth its cost?",
        "why": "Measured on MemoryAgentBench: recall@10 reaches 1.000 on half the rows while MRR sits "
               "at 0.435, so the evidence is present but ranked badly — a reranking/iteration problem, "
               "not a coverage one. Falsifier: the second hop's benefit is independent of first-hop "
               "success, so no cheap gate can decide when to spend it.",
    },
    {
        "kind": "research",
        "title": "Is retrieval-order sensitivity a usable POISONING channel — can an attacker who only "
                 "controls the ORDER of benign queries (never the content) steer which fact a later "
                 "honest query returns?",
        "why": "Follows directly from reading being a write: if 69.4% of answers change with query "
               "order, an adversary who can influence query sequencing has an attack surface that "
               "requires no write access at all, which no memory-poisoning threat model we have seen "
               "covers (OWASP ASI06 assumes injected CONTENT). Falsifier: order effects are not "
               "steerable toward a chosen target — divergence is symmetric noise rather than a "
               "controllable direction.",
    },
]

cur = json.loads(P.read_text(encoding="utf-8"))
have = {(d.get("title") or "").strip().lower() for d in cur}
add = [d for d in NEW if d["title"].strip().lower() not in have]
print(f"existing directions: {len(cur)}  |  proposed: {len(NEW)}  |  new after dedup: {len(add)}")
for d in add:
    print(f"\n  + {d['title'][:110]}")
    print(f"    why: {d['why'][:110]}")
if add:
    P.write_text(json.dumps(cur + add, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwritten: {len(cur)} -> {len(cur)+len(add)} directions")
