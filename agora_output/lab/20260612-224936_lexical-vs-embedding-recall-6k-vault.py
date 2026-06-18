# Re-open the embedder decision at scale: lexical vs semantic recall on the 6k-note vault, crossed
# with the hub-pass. Known-item benchmark (query=title, target=that note), 350 queries, same value
# ranking (sim x (1+log1p(value))) for both. Semantic = nomic-embed cosine over cached note vectors;
# query titles embedded live via the same Ollama model. Source: simulation on real data.
import json, re, sys, time
import numpy as np
from pathlib import Path
sys.path.insert(0, "C:/Users/Danculus/agora/server")
sys.path.insert(0, "C:/Users/Danculus/agora/mnemo")
from agora.execution.semantic_index import _embed_batch
from mnemo import _tokens

cdir = Path("C:/Users/Danculus/agora/server/.semantic_cache")
VAULT = Path("C:/Users/Danculus/my-second-brain")
V = np.load(cdir / "vectors.npy").astype(np.float32)
V /= (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
meta = json.loads((cdir / "meta.json").read_text(encoding="utf-8"))
N = len(meta)
_WL = re.compile(r"\[\[([^\]\|#]+)")

title = []; toks = []; value = np.zeros(N)
for i, m in enumerate(meta):
    try:
        txt = (VAULT / m.get("path", "")).read_text(encoding="utf-8", errors="replace")
    except Exception:
        txt = ""
    title.append(m.get("title", "") or Path(m.get("path", "")).stem)
    toks.append(_tokens(txt))
    nlink = len(set(_WL.findall(txt)))
    value[i] = (2 if len(txt) >= 900 else 1) + (2 if nlink >= 3 else (1 if nlink else 0)) + (2 if "status: evergreen" in txt[:900] else 0)
logv = 1.0 + np.log1p(np.maximum(0.0, value))

# hubs by vocabulary coverage (what mnemo.consolidate flags), coverage >= 0.12
from collections import Counter
df = Counter()
for tk in toks: df.update(tk)
common = {w for w, c in df.items() if c >= max(3, int(0.002 * N))}
nv = len(common) or 1
cov = np.array([len(tk & common) / nv for tk in toks])
HUBS = set(np.where(cov >= 0.12)[0].tolist())
print(f"N={N}  hubs flagged (cov>=0.12): {len(HUBS)}")

rng = np.random.default_rng(5)
cands = [i for i in range(N) if len(title[i].split()) >= 2 and len(toks[i]) >= 4]
rng.shuffle(cands)
queries = cands[:350]

# embed query titles (live, same nomic model)
qt0 = time.time()
qvecs = []
for s in range(0, len(queries), 64):
    chunk = [title[q] for q in queries[s:s+64]]
    qvecs.extend(_embed_batch(chunk))
QV = np.array(qvecs, dtype=np.float32)
QV /= (np.linalg.norm(QV, axis=1, keepdims=True) + 1e-9)
print(f"embedded {len(queries)} query titles in {time.time()-qt0:.1f}s")

def metrics(rank_of):
    r5 = sum(1 for r in rank_of if r and r <= 5)
    r10 = sum(1 for r in rank_of if r and r <= 10)
    mrr = sum(1.0/r for r in rank_of if r)
    n = len(rank_of)
    return r5/n, r10/n, mrr/n

def run(mode, drop_hubs):
    keep = np.array([i for i in range(N) if not (drop_hubs and i in HUBS)])
    ranks = []
    for qi, q in enumerate(queries):
        if mode == "lexical":
            qtok = _tokens(title[q])
            lq = len(qtok)
            sims = np.array([ (len(qtok & toks[i]) / min(lq, len(toks[i]))) if toks[i] else 0.0 for i in keep ])
        else:  # semantic
            sims = V[keep] @ QV[qi]
            sims = np.maximum(sims, 0.0)
        scores = sims * logv[keep]
        order = np.argsort(-scores)[:10]
        top = keep[order]
        rank = None
        for pos, gi in enumerate(top):
            if gi == q: rank = pos + 1; break
        ranks.append(rank)
    return metrics(ranks)

print("\n cell                         recall@5  recall@10   MRR")
for mode in ("lexical", "semantic"):
    for drop in (False, True):
        r5, r10, mrr = run(mode, drop)
        tag = f"{mode} + {'hub-pass' if drop else 'raw     '}"
        print(f"  {tag:26s}   {r5:.3f}     {r10:.3f}    {mrr:.3f}")
