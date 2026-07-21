"""
Headroom probe (FREE, cached) before building the reranker + multi-round.
For the best fusion (RRF over v1 follow-up queries), report full-evidence recall@K for K in {50..300}.
recall@K is the CEILING of a 'rerank a top-K pool down to 50' stage (a perfect reranker keeps all gold if
gold is within top-K and |gold|<=50). Also report the gold-size distribution (multi-hop evidence count).
"""
import json, time, urllib.request, pickle, re
import numpy as np

st = pickle.load(open("agora_output/lab/locomo_iter_state.pkl", "rb"))
vecs = {t: np.asarray(v, dtype=np.float32) for t, v in st["vecs"].items()}
items = {it["idx"]: it for it in st["items"]}
question_of = {q["idx"]: q["question"] for q in json.load(open("agora_output/lab/locomo_iter_input.json"))}
fup_v1 = {}
for o in json.load(open("agora_output/lab/locomo_iter_followups.json")):
    fup_v1[o["idx"]] = [q for q in o.get("queries", []) if isinstance(q, str) and q.strip()]

D = json.load(open("agora_output/lab/data/locomo10.json"))
sample_turns = []
for s in D:
    conv = s["conversation"]; turns = {}
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]:
            turns[t["dia_id"]] = t["text"]
    sample_turns.append(turns)


def unit(v):
    return v / (np.linalg.norm(v) + 1e-9)


def embed_batch(texts):
    for _ in range(3):
        try:
            body = json.dumps({"model": "nomic-embed-text", "input": [t[:2000] for t in texts]}).encode()
            r = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/embed",
                data=body, headers={"Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["embeddings"]
        except Exception:
            time.sleep(3)
    raise RuntimeError("embed failed")


allq = sorted({q for qs in fup_v1.values() for q in qs})
qvec = {}
for i in range(0, len(allq), 64):
    chunk = allq[i:i + 64]
    for t, v in zip(chunk, embed_batch(chunk)):
        qvec[t] = unit(np.asarray(v, dtype=np.float32))


def rrf(rankings, k0=60):
    score = {}
    for r in rankings:
        for rank, tid in enumerate(r):
            score[tid] = score.get(tid, 0.0) + 1.0 / (k0 + rank + 1)
    return score


KS = [50, 80, 100, 150, 200, 300]
hit = {k: 0 for k in KS}
goldsizes = []
poolsizes = []
n = 0
for idx, it in items.items():
    turns = sample_turns[it["sample_i"]]; tids = it["turn_ids"]; g = set(it["gold_ids"])
    goldsizes.append(len(g)); poolsizes.append(len(tids))
    TM = np.stack([unit(vecs[turns[i]]) for i in tids])
    fq = fup_v1.get(idx, [])
    ranks = [[tids[j] for j in np.argsort(-(TM @ qvec[q]))] for q in fq]
    if not ranks:
        qv = unit(vecs[question_of[idx]]); ranks = [[tids[j] for j in np.argsort(-(TM @ qv))]]
    ranked = [t for t, _ in sorted(rrf(ranks).items(), key=lambda x: -x[1])]
    for k in KS:
        hit[k] += g.issubset(set(ranked[:k]))
    n += 1

res = {"n": n,
       "recall_at_K": {str(k): round(hit[k] / n, 3) for k in KS},
       "gold_size": {"mean": round(float(np.mean(goldsizes)), 2), "max": int(max(goldsizes)),
                     "p90": int(np.percentile(goldsizes, 90)),
                     "frac_gt_10": round(float(np.mean([s > 10 for s in goldsizes])), 3)},
       "avg_turns_per_conv": round(float(np.mean(poolsizes)), 0)}
print(json.dumps(res, indent=1))
json.dump(res, open("agora_output/lab/locomo_headroom_result.json", "w"), indent=1)
