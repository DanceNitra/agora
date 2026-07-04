"""
Re-rerank PHASE C: score the LLM reranker over the MERGED top-150 pool.
final-50 = [LLM-selected, dedup] then fill from merged-RRF order to 50. Compare to flat/rrf_fonly/prev-rerank.
"""
import json, glob, pickle
mr = pickle.load(open("agora_output/lab/locomo_mr_pool.pkl", "rb"))["pool"]
pool = {int(k): v for k, v in mr.items()}
gold = {it["idx"]: set(it["gold_ids"]) for it in pickle.load(open("agora_output/lab/locomo_iter_state.pkl", "rb"))["items"]}

sel = {}
for f in sorted(glob.glob("agora_output/lab/locomo_rerank2_out/block_*.json")):
    try:
        for o in json.load(open(f)):
            if "idx" in o and "cids" in o:
                sel[o["idx"]] = [c for c in o["cids"] if isinstance(c, int)]
    except Exception as e:
        print("BAD", f, e)

BUDGET = 50
hit = miss = n = 0
for idx, p in pool.items():
    g = gold[idx]
    chosen = [p[c] for c in sel.get(idx, []) if 0 <= c < len(p)]
    final = list(dict.fromkeys(chosen))
    for t in p:
        if len(final) >= BUDGET:
            break
        if t not in final:
            final.append(t)
    hit += g.issubset(set(final[:BUDGET]))
    if idx not in sel:
        miss += 1
    n += 1

res = {"n": n, "flat": 0.145, "rrf_fonly@50": 0.326, "prev_rerank_top100@50": 0.482,
       "merged_pool_ceiling@150": 0.656,
       "RERANK2_merged150_recall@50": round(hit / n, 3),
       "questions_missing_output": miss}
print(json.dumps(res, indent=1))
json.dump(res, open("agora_output/lab/locomo_rerank2_result.json", "w"), indent=1)
