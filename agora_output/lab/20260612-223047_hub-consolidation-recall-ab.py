# Consolidate the top-56 hubs and measure RECALL before/after — faithful to inspeximus's real lexical
# recall (overlap-coefficient similarity x curation value). Known-item benchmark: query = a note's
# title, ground-truth target = that note. If hub notes (autolinker reports that contain ~every
# concept token) capture top-k slots and bury the true note, removing them should raise recall.
# Source: simulation on the real vault.
import json, re, math
import numpy as np
from pathlib import Path
from collections import defaultdict

cdir = Path("C:/Users/Danculus/agora/server/.semantic_cache")
VAULT = Path("C:/Users/Danculus/my-second-brain")
meta = json.loads((cdir / "meta.json").read_text(encoding="utf-8"))
N = len(meta)

# --- inspeximus's exact tokenizer / similarity ---
_WORD = re.compile(r"[a-z0-9][a-z0-9\-']{2,}")
_STOP = frozenset("the a an of for to in on and or is are was were be been with this that it its as "
                  "by at from into our we us you your he she they them his her their not no".split())
def _stem(w): return w[:-1] if (w.endswith("s") and len(w) > 4) else w
def _tokens(text): return {_stem(w) for w in _WORD.findall((text or "").lower()) if w not in _STOP}
def sim(qtok, ttok):
    if not qtok or not ttok: return 0.0
    return len(qtok & ttok) / min(len(qtok), len(ttok))   # overlap coefficient

# --- load note text, tokens, value (recall.py _note_value), wikilink degree ---
_WL = re.compile(r"\[\[([^\]\|#]+)")
texts = [""] * N; toks = [None] * N; value = np.zeros(N); title = [""] * N
adj = defaultdict(set)
def base(p): return Path(p).stem.lower().strip()
by_base, by_title = {}, {}
for i, m in enumerate(meta):
    by_base.setdefault(base(m.get("path", "")), i)
    t = (m.get("title", "") or "").lower().strip()
    if t: by_title.setdefault(t, i)
for i, m in enumerate(meta):
    title[i] = m.get("title", "") or Path(m.get("path", "")).stem
    try:
        txt = (VAULT / m.get("path", "")).read_text(encoding="utf-8", errors="replace")
    except Exception:
        txt = ""
    texts[i] = txt
    toks[i] = _tokens(txt)
    links = set(_WL.findall(txt))
    evergreen = "status: evergreen" in txt[:900]
    nlink = len(links)
    value[i] = (2 if len(txt) >= 900 else 1) + (2 if nlink >= 3 else (1 if nlink else 0)) + (2 if evergreen else 0)
    for tgt in links:
        key = tgt.strip().lower()
        j = by_base.get(key) or by_title.get(key) or by_base.get(key.split("/")[-1])
        if j is not None and j != i:
            adj[i].add(j); adj[j].add(i)

deg = np.array([len(adj[i]) for i in range(N)])
HUBS = set(np.argsort(-deg)[:56].tolist())
print(f"notes={N}  hubs=56 (top by wikilink degree)  top hub deg={deg.max()}")
print("hub examples:", [title[i][:30] for i in list(HUBS)[:5]])

# --- known-item recall benchmark: query = title, target = that note ---
rng = np.random.default_rng(5)
cands = [i for i in range(N) if i not in HUBS and len(toks[i]) >= 4 and len(title[i].split()) >= 2]
rng.shuffle(cands)
queries = cands[:350]
logv = 1.0 + np.log1p(np.maximum(0.0, value))   # value multiplier, precomputed

def evaluate(exclude_hubs):
    pool = [i for i in range(N) if not (exclude_hubs and i in HUBS)]
    pool_arr = np.array(pool)
    r5 = r10 = mrr = hub_in_top10 = hub_rank1 = 0
    for q in queries:
        qt = _tokens(title[q])
        scores = np.array([sim(qt, toks[i]) * logv[i] for i in pool])
        # rank: indices into pool sorted by score desc
        order = np.argsort(-scores)
        topN = pool_arr[order[:10]]
        # rank of the true note q
        rank = None
        for pos, gi in enumerate(topN):
            if gi == q: rank = pos + 1; break
        if rank:
            if rank <= 5: r5 += 1
            r10 += 1
            mrr += 1.0 / rank
        if not exclude_hubs:
            if any(gi in HUBS for gi in topN): hub_in_top10 += 1
            if topN[0] in HUBS: hub_rank1 += 1
    n = len(queries)
    return dict(recall5=r5/n, recall10=r10/n, mrr=mrr/n,
                hub_in_top10=hub_in_top10/n, hub_rank1=hub_rank1/n, n=n)

before = evaluate(exclude_hubs=False)
after = evaluate(exclude_hubs=True)
print(f"\nKnown-item recall over {before['n']} queries (inspeximus lexical x value):")
print(f"  metric        BEFORE (with hubs)   AFTER (hubs consolidated)")
print(f"  recall@5         {before['recall5']:.3f}              {after['recall5']:.3f}")
print(f"  recall@10        {before['recall10']:.3f}              {after['recall10']:.3f}")
print(f"  MRR              {before['mrr']:.3f}              {after['mrr']:.3f}")
print(f"\nHub noise in the BEFORE corpus:")
print(f"  queries with >=1 hub in top-10: {before['hub_in_top10']*100:.1f}%")
print(f"  queries where a hub took rank-1: {before['hub_rank1']*100:.1f}%")
d5 = (after['recall5']-before['recall5'])
print(f"\n=> consolidating 56 notes (<1%) changes recall@5 by {d5:+.3f} "
      f"({100*d5/max(before['recall5'],1e-9):+.0f}%), MRR {after['mrr']-before['mrr']:+.3f}")
