"""
mnemo recall-quality benchmark: LEXICAL (token overlap, the zero-dep default) vs SEMANTIC
(nomic-embed-text via local Ollama :11434). Severe-test on our own product: does lexical recall
miss relevant memories that semantic catches? Decides whether the embedder upgrade is justified.

Fair design: 24 memories across 6 domains; 12 labelled queries mixing exact-term, abbreviation,
synonym and paraphrase phrasings, with hand-set ground-truth relevant memories. Metrics: hit@3
(>=1 relevant in top 3), MRR, and "semantic-only rescues" (lexical missed, semantic found).
"""
import json, sys, urllib.request
sys.path.insert(0, r"C:/Users/Danculus/agora/mnemo")
from mnemo import Mnemo

MEMS = [
    "Difference-in-differences estimates causal effects from parallel pre-treatment trends",   # 0
    "A pre-trends test catches only about 31% of fatal DiD bias",                               # 1
    "Synthetic control builds a weighted donor pool to match the treated unit's pre-period",   # 2
    "Randomized controlled trials remove confounding by random assignment",                     # 3
    "Instrumental variables identify effects when an instrument shifts treatment not outcome",  # 4
    "Stock returns show fat tails and volatility clustering, unlike Gaussian models",           # 5
    "Geometric Brownian motion assumes lognormal prices and normal returns",                    # 6
    "A crash-prone market has heavy-tailed return distributions and correlated drawdowns",      # 7
    "GARCH models capture time-varying volatility and excess kurtosis",                         # 8
    "Value-at-Risk underestimates tail losses when returns are non-normal",                     # 9
    "Critical systems show power-law scaling and long-range correlations",                      # 10
    "Near a phase transition, susceptibility diverges and fluctuations grow",                   # 11
    "Neuronal avalanches follow a power law at the critical branching ratio",                   # 12
    "Self-organized criticality produces scale-free event-size distributions",                  # 13
    "The vagus nerve suppresses inflammation via the cholinergic anti-inflammatory pathway",    # 14
    "Acetylcholine from efferent vagal fibers reduces macrophage TNF release",                  # 15
    "Memory consolidation during sleep strengthens important traces and prunes weak ones",      # 16
    "Value-ranked retention beats FIFO eviction super-linearly as the budget shrinks",          # 17
    "Append-only storage prevents silent accuracy drift from rewritten records",                # 18
    "Spaced repetition schedules reviews at expanding intervals for durable recall",            # 19
    "Mixture-of-experts activates a sparse subset of parameters per token",                     # 20
    "Gradient descent with a constant step size stalls at a variance floor",                    # 21
    "Transformer attention scales quadratically with sequence length",                          # 22
    "Overfitting rises when model capacity exceeds the information in the data",                 # 23
]
# (query, set-of-relevant-indices, phrasing-type)
QUERIES = [
    ("DiD",                                               {0, 1}, "abbrev"),
    ("estimating causal effects without randomization",   {0, 2, 4}, "paraphrase"),
    ("market crashes and heavy tails",                    {5, 7, 9}, "synonym"),
    ("time-varying volatility model",                     {8}, "exact-ish"),
    ("scale-free distributions at criticality",           {10, 12, 13}, "synonym"),
    ("controlling brain inflammation through nerves",     {14, 15}, "paraphrase"),
    ("the dream pass that prunes weak memories",          {16, 17}, "jargon"),
    ("why a constant learning rate makes SGD plateau",    {21}, "synonym"),
    ("sparse parameter activation in large models",       {20}, "exact-ish"),
    ("keeping memory immutable to avoid drift",           {18}, "synonym"),
    ("predicting tail risk with non-Gaussian returns",    {5, 8, 9}, "paraphrase"),
    ("expanding review intervals for durable retention",  {19}, "exact-ish"),
]


_ecache = {}
_ecalls = [0]
def nomic(text):
    # NOTE: mnemo._similarity re-embeds the query once PER record (O(n) embed calls per recall).
    # We cache here so the benchmark is fast — and to expose that O(n) re-embed as a real fix.
    if text in _ecache:
        return _ecache[text]
    _ecalls[0] += 1
    req = urllib.request.Request("http://localhost:11434/api/embeddings",
        data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode(),
        headers={"Content-Type": "application/json"})
    v = json.loads(urllib.request.urlopen(req, timeout=20).read())["embedding"]
    _ecache[text] = v
    return v


def build(embed):
    m = Mnemo(None, embed=embed)
    for t in MEMS:
        m.remember(t, value=1.0)
    return m


def evaluate(m, k=3):
    hits = 0; rr = 0.0; per = []
    for q, gt, _t in QUERIES:
        got = [MEMS.index(h["text"]) for h in m.recall(q, k=k)]
        hit = any(i in gt for i in got)
        hits += hit
        rank = next((r + 1 for r, i in enumerate(got) if i in gt), 0)
        rr += (1.0 / rank) if rank else 0.0
        per.append(hit)
    return hits / len(QUERIES), rr / len(QUERIES), per


lex_hit, lex_mrr, lex_per = evaluate(build(None))
sem_hit, sem_mrr, sem_per = evaluate(build(nomic))

print(f"{'metric':<26}{'LEXICAL':>10}{'SEMANTIC':>10}")
print(f"{'hit@3 (>=1 relevant)':<26}{lex_hit:>9.0%}{sem_hit:>10.0%}")
print(f"{'MRR':<26}{lex_mrr:>10.2f}{sem_mrr:>10.2f}")
rescues = [QUERIES[i][0] for i in range(len(QUERIES)) if sem_per[i] and not lex_per[i]]
regress = [QUERIES[i][0] for i in range(len(QUERIES)) if lex_per[i] and not sem_per[i]]
print(f"\nsemantic-only rescues (lexical missed, semantic found): {len(rescues)}/{len(QUERIES)}")
for r in rescues:
    print(f"   + {r}")
if regress:
    print(f"lexical-only (semantic regressed): {len(regress)}")
    for r in regress:
        print(f"   - {r}")
print("\nper-query type breakdown (L=lexical hit, S=semantic hit):")
for i, (q, gt, t) in enumerate(QUERIES):
    print(f"  [{t:>10}] L={'Y' if lex_per[i] else '.'} S={'Y' if sem_per[i] else '.'}  {q}")
