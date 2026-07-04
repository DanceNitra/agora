"""
Reranker stage, PHASE C (deterministic): score the LLM reranker.
final-50 = [LLM-selected pool turns, in pool/RRF order] then fill from the rest of the pool (RRF order) to 50.
The reranker's value = promoting gold turns that retrieval buried at pool-rank 51-100 into the top-50.
"""
import json, glob, pickle
st = pickle.load(open("agora_output/lab/locomo_rerank_pool.pkl", "rb"))
pool = {int(k): v for k, v in st["pool"].items()}
gold = {it["idx"]: set(it["gold_ids"]) for it in pickle.load(open("agora_output/lab/locomo_iter_state.pkl", "rb"))["items"]}

sel = {}
for f in sorted(glob.glob("agora_output/lab/locomo_rerank_out/block_*.json")):
    try:
        for o in json.load(open(f)):
            if "idx" in o and "cids" in o:
                sel[o["idx"]] = [c for c in o["cids"] if isinstance(c, int)]
    except Exception as e:
        print("BAD", f, e)

BUDGET = 50
hit_rerank = hit_pool50 = hit_pool100 = n = 0
promoted_questions = 0   # questions where rerank recovered gold that plain top-50 missed
missing_idx = []
for idx, p in pool.items():
    g = gold[idx]
    if idx not in sel:
        missing_idx.append(idx)
    cids = sel.get(idx, [])
    chosen = [p[c] for c in cids if 0 <= c < len(p)]
    final = list(dict.fromkeys(chosen))                      # selected first, dedup, pool order not enforced on chosen
    for t in p:                                              # fill from RRF order
        if len(final) >= BUDGET:
            break
        if t not in final:
            final.append(t)
    final = final[:BUDGET]
    r = g.issubset(set(final))
    hit_rerank += r
    p50 = g.issubset(set(p[:50])); p100 = g.issubset(set(p[:100]))
    hit_pool50 += p50; hit_pool100 += p100
    if r and not p50:
        promoted_questions += 1
    n += 1

res = {
    "n": n,
    "flat": 0.145,
    "rrf_fonly_top50 (pool@50)": round(hit_pool50 / n, 3),
    "pool_ceiling@100": round(hit_pool100 / n, 3),
    "RERANKED_recall@50": round(hit_rerank / n, 3),
    "questions_rerank_recovered": promoted_questions,
    "questions_missing_rerank_output": len(missing_idx),
}
print(json.dumps(res, indent=1))
json.dump(res, open("agora_output/lab/locomo_rerank_result.json", "w"), indent=1)
