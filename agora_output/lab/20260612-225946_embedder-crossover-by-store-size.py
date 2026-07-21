# Where does the lexical->semantic crossover sit? Known-item recall@5 (query=title) on NESTED
# sub-corpora of growing size, lexical vs semantic, averaged over 3 shuffles. The crossover is the
# store size where semantic overtakes lexical. Source: simulation on real data.
import json, re, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, "C:/Users/Danculus/agora/server")
sys.path.insert(0, "C:/Users/Danculus/agora/mnemo")
from agora.execution.semantic_index import _embed_batch
from inspeximus import _tokens

cdir = Path("C:/Users/Danculus/agora/server/.semantic_cache")
VAULT = Path("C:/Users/Danculus/my-second-brain")
V = np.load(cdir / "vectors.npy").astype(np.float32); V /= (np.linalg.norm(V,axis=1,keepdims=True)+1e-9)
meta = json.loads((cdir / "meta.json").read_text(encoding="utf-8")); N = len(meta)
_WL = re.compile(r"\[\[([^\]\|#]+)")
title=[]; toks=[]; value=np.zeros(N)
for i,m in enumerate(meta):
    try: txt=(VAULT/m.get("path","")).read_text(encoding="utf-8",errors="replace")
    except Exception: txt=""
    title.append(m.get("title","") or Path(m.get("path","")).stem); toks.append(_tokens(txt))
    nlink=len(set(_WL.findall(txt)))
    value[i]=(2 if len(txt)>=900 else 1)+(2 if nlink>=3 else (1 if nlink else 0))+(2 if "status: evergreen" in txt[:900] else 0)
logv=1.0+np.log1p(np.maximum(0.0,value))

SIZES=[24,32,48,72,120,200,350,600,1000,1800,3000,5959]
Q=24                       # fixed query set per shuffle (first Q of the shuffle; present at all sizes)
SEEDS=[5,17,29]
def recall5(corpus_idx, qlist, mode, qvec_map):
    arr=np.array(corpus_idx)
    hit=0
    for qi,q in enumerate(qlist):
        if mode=="lexical":
            qt=_tokens(title[q]); lq=len(qt)
            sims=np.array([(len(qt&toks[i])/min(lq,len(toks[i]))) if toks[i] else 0.0 for i in arr])
        else:
            sims=np.maximum(arr.dtype.type(0), V[arr]@qvec_map[q])
        order=np.argsort(-(sims*logv[arr]))[:5]
        if q in arr[order]: hit+=1
    return hit/len(qlist)

# pre-embed the query titles we'll use (union of first Q across seeds)
need=set()
for s in SEEDS:
    rng=np.random.default_rng(s); od=np.arange(N); rng.shuffle(od); need.update(od[:Q].tolist())
need=list(need)
embs=[]
for j in range(0,len(need),64): embs.extend(_embed_batch([title[i] for i in need[j:j+64]]))
qvec_map={i:(np.array(e,dtype=np.float32)/(np.linalg.norm(e)+1e-9)) for i,e in zip(need,embs)}
print(f"embedded {len(need)} query titles\n")

print(f"{'N':>6}  {'lexical@5':>9}  {'semantic@5':>10}  winner")
results=[]
for sz in SIZES:
    lx=[]; sm=[]
    for s in SEEDS:
        rng=np.random.default_rng(s); od=np.arange(N); rng.shuffle(od)
        corpus=od[:sz].tolist(); qlist=od[:Q].tolist()
        lx.append(recall5(corpus,qlist,"lexical",qvec_map))
        sm.append(recall5(corpus,qlist,"semantic",qvec_map))
    L,S=np.mean(lx),np.mean(sm)
    results.append((sz,L,S))
    print(f"{sz:>6}  {L:>9.3f}  {S:>10.3f}  {'semantic' if S>L else 'lexical'}")

cross=None
for i in range(1,len(results)):
    if results[i-1][2]<=results[i-1][1] and results[i][2]>results[i][1]:
        cross=(results[i-1][0],results[i][0]); break
print(f"\ncrossover (semantic overtakes lexical): between N={cross[0]} and N={cross[1]}" if cross
      else "\nno crossover in range (semantic ahead throughout or behind throughout)")
