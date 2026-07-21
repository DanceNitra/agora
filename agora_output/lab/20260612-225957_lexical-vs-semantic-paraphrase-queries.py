# Paraphrase-query benchmark: does semantic still beat lexical when the query is NOT the title?
# For ~50 content-rich notes, the LLM writes a natural query the note answers WITHOUT reusing title
# words. Then measure recall over the full 5959-note corpus, lexical vs semantic. This removes the
# title-leakage that favours semantic in known-item. Source: simulation on real data.
import json, re, sys, time
import numpy as np
from pathlib import Path
sys.path.insert(0, "C:/Users/Danculus/agora/server")
sys.path.insert(0, "C:/Users/Danculus/agora/mnemo")
from agora.execution.semantic_index import _embed_batch
from inspeximus import _tokens
import urllib.request

def call_llm(SYS, up, tier="cheap", temperature=0.3, max_tokens=40):
    body=json.dumps({"model":"qwen2.5:7b","prompt":up,"system":SYS,"stream":False,
                     "options":{"temperature":temperature,"num_predict":max_tokens}}).encode()
    req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=body,
                               headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r:
        return json.loads(r.read()).get("response","")

cdir = Path("C:/Users/Danculus/agora/server/.semantic_cache")
VAULT = Path("C:/Users/Danculus/my-second-brain")
V = np.load(cdir / "vectors.npy").astype(np.float32); V /= (np.linalg.norm(V,axis=1,keepdims=True)+1e-9)
meta = json.loads((cdir / "meta.json").read_text(encoding="utf-8")); N = len(meta)
_WL = re.compile(r"\[\[([^\]\|#]+)")
title=[]; toks=[]; value=np.zeros(N); body=[]
for i,m in enumerate(meta):
    try: txt=(VAULT/m.get("path","")).read_text(encoding="utf-8",errors="replace")
    except Exception: txt=""
    title.append(m.get("title","") or Path(m.get("path","")).stem); toks.append(_tokens(txt))
    b=txt.split('---',2)[-1] if txt.startswith('---') else txt
    body.append(re.sub(r"\s+"," ",b).strip())
    nlink=len(set(_WL.findall(txt)))
    value[i]=(2 if len(txt)>=900 else 1)+(2 if nlink>=3 else (1 if nlink else 0))+(2 if "status: evergreen" in txt[:900] else 0)
logv=1.0+np.log1p(np.maximum(0.0,value))

rng=np.random.default_rng(13)
# content-rich notes with a real multi-word title, avoid agent/autolinker/meta noise
cand=[i for i in range(N) if len(body[i])>=600 and len(title[i].split())>=2
      and not any(s in (meta[i].get('path','')) for s in ('Agora Agents','autolinker','Daily','Sessions'))]
rng.shuffle(cand); sample=cand[:50]
print(f"generating paraphrase queries for {len(sample)} notes via local LLM...")

SYS=("You write ONE short natural search query (a question or phrase, <=12 words) that the given "
     "note answers. Do NOT reuse any distinctive word from the note's TITLE. Output ONLY the query.")
queries=[]
t0=time.time()
for n,i in enumerate(sample):
    up=f"TITLE: {title[i]}\nNOTE: {body[i][:700]}\n\nQuery (no title words):"
    try:
        q=call_llm(SYS,up,tier="cheap",temperature=0.3,max_tokens=40).strip().strip('"').splitlines()[0][:120]
    except Exception as e:
        q=""
    queries.append(q)
    if n%10==0: print(f"  {n}/{len(sample)}  e.g. '{q[:60]}'")
print(f"generated in {time.time()-t0:.0f}s")

# keep only valid queries that don't trivially leak title tokens
pairs=[(i,q) for i,q in zip(sample,queries) if q and len(_tokens(q))>=2]
qembs=[]
for j in range(0,len(pairs),64): qembs.extend(_embed_batch([q for _,q in pairs[j:j+64]]))
QV=[np.array(e,dtype=np.float32)/(np.linalg.norm(e)+1e-9) for e in qembs]
print(f"\nvalid paraphrase queries: {len(pairs)}")

def rank_of(tgt, mode, qv, qtok):
    if mode=="lexical":
        lq=len(qtok)
        sims=np.array([(len(qtok&toks[i])/min(lq,len(toks[i]))) if (toks[i] and lq) else 0.0 for i in range(N)])
    else:
        sims=np.maximum(0.0, V@qv)
    order=np.argsort(-(sims*logv))[:10]
    for pos,gi in enumerate(order):
        if gi==tgt: return pos+1
    return None

def metr(mode):
    r5=r10=mrr=0
    for (tgt,q),qv in zip(pairs,QV):
        r=rank_of(tgt,mode,qv,_tokens(q))
        if r:
            if r<=5: r5+=1
            r10+=1; mrr+=1.0/r
    n=len(pairs)
    return r5/n,r10/n,mrr/n

print(f"\n{'mode':>10}  recall@5  recall@10   MRR")
for mode in ("lexical","semantic"):
    r5,r10,mrr=metr(mode)
    print(f"{mode:>10}    {r5:.3f}     {r10:.3f}    {mrr:.3f}")
print("\nsample queries:")
for (i,q) in pairs[:6]: print(f"  [{title[i][:32]}] -> '{q}'")
