"""Can a SEMANTIC check tell a restatement from a different claim in the same topic?

Measured today: prefix equality, token overlap and keyword-family matching all fail to identify the same
proposition across notations. The LinUCB regret bound entered the ledger three times; a fourth wording
("the optimism-based bandit algorithm of Chu et al. attains sublinear cumulative regret") shares no prefix,
scores below the overlap threshold, and contains no family keyword. Adding a fourth keyword would be
another patch on the same blindness.

The stack already has a local embedder. The question this answers is not "is cosine high for
restatements" -- of course it is -- but the one that decides whether a guard can be built on it:

    does it SEPARATE restatements of one proposition from DIFFERENT propositions in the same family?

Because the cost of getting that wrong is asymmetric and known: blocking "real-world networks are
scale-free" (verdict FAILED) because a power-law claim was already replicated would discard the Crucible's
most valuable output. A guard is only shippable if there is a threshold with the restatements above it and
the distinct-but-related pairs below.

SHOULD-MERGE  : the LinUCB family -- one theorem, four notations
SHOULD NOT    : pairs that share a topic but assert different things, including the FAILED that the
                keyword rule would have thrown away
"""
import itertools
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

LINUCB = [
    "LinUCB (Chu et al 2011): linear contextual bandit achieves O(sqrt(Td log^3)) i.e. sublinear ~sqrt(T) regret w.p. 1-delta",
    "LinUCB achieves O~(sqrt(Td)) regret with prob 1-delta for linear-payoff contextual bandits (sublinear in T, sqrt(d) dimension dependence)",
    "For T rounds, K actions, d-dim feature vectors, an O(sqrt(T d ln^3(K T ln(T)/delta))) regret bound holds w.p. 1-delta for the simplest known linear-payoff bandit",
    "Under a linear reward model the optimism-based bandit algorithm of Chu et al. attains sublinear cumulative regret scaling as the square root of the horizon",
]
DISTINCT = [
    ("Real-world networks are scale-free: their degree distributions follow a power law p(k) ~ k^-gamma",
     "Miller (1957): random typing (letters + space) reproduces the POWER-LAW FORM of Zipf's law"),
    ("Systems in the same universality class share the same critical exponents (Lubeck 2004)",
     "Internet AS-level topology follows a power-law degree distribution"),
    ("BA networks N=2000 m=2: removing the top 10% of nodes by degree raises the bond-percolation threshold",
     "The epidemic threshold vanishes in the thermodynamic limit for scale-free contact networks"),
    ("LinUCB (Chu et al 2011): linear contextual bandit achieves O(sqrt(Td log^3)) sublinear regret",
     "Thompson sampling outperforms UCB empirically on Bernoulli bandits despite a weaker regret bound"),
]


def embed(text: str) -> list:
    body = json.dumps({"model": MODEL, "prompt": "search_document: " + text}).encode()
    req = urllib.request.Request(EMBED_URL, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb)


try:
    vecs = {t: embed(t) for t in LINUCB + [x for p in DISTINCT for x in p]}
except Exception as e:
    print(f"embedder unavailable ({type(e).__name__}: {e}) -- cannot answer this question without it.")
    print("This is the measurement the design depends on; do NOT ship a semantic guard on the assumption.")
    raise SystemExit(2)

print("=== SHOULD MERGE: one theorem, four notations ===")
same = []
for a, b in itertools.combinations(LINUCB, 2):
    c = cos(vecs[a], vecs[b])
    same.append(c)
    print(f"   {c:.3f}   {a[:52]}  ||  {b[:52]}")

print("\n=== SHOULD NOT MERGE: different propositions, related topics ===")
diff = []
for a, b in DISTINCT:
    c = cos(vecs[a], vecs[b])
    diff.append(c)
    print(f"   {c:.3f}   {a[:52]}  ||  {b[:52]}")

lo_same, hi_diff = min(same), max(diff)
print(f"\nlowest restatement pair : {lo_same:.3f}")
print(f"highest distinct pair   : {hi_diff:.3f}")
print(f"margin                  : {lo_same - hi_diff:+.3f}")
if lo_same > hi_diff:
    print(f"\nSEPARABLE. Any threshold in ({hi_diff:.3f}, {lo_same:.3f}) merges every restatement and keeps")
    print("every distinct claim -- including the FAILED the keyword rule would have discarded.")
else:
    print("\nNOT SEPARABLE on this fixture: some distinct pair scores at or above the closest restatement.")
    print("A cosine threshold would either miss restatements or eat real claims. Do not ship one on this")
    print("evidence; the honest answer stays 'declare it by hand, with the evidence attached'.")
