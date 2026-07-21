"""
Push absolute recall higher WITHOUT new LLM calls: reuse the cached 276 follow-up queries and try better
ways to FUSE the question ranking with the follow-up-query rankings. Cloud-free, fast (cached embeddings).

Strategies scored at full-evidence recall@50 (n=276), vs flat 0.145 and the current scheme 0.297:
  current     - round-1 top-15 by question, fill to 50 by max follow-up cosine (the shipped number)
  maxpool     - score turn = max(cos(Q), cos(fup_i)); top-50
  sumpool     - score turn = cos(Q) + sum_i cos(fup_i); top-50
  rrf_qf      - Reciprocal Rank Fusion over {question, fup_1, fup_2, ...}; top-50
  rrf_fonly   - RRF over follow-ups only (drop the question ranking)
  reserve_k   - guarantee top-K by question, then RRF(Q,fups) for the remaining 50-K  (sweep K)
"""
import json, time, urllib.request, pickle, re
import numpy as np

BUDGET = 50
st = pickle.load(open("agora_output/lab/locomo_iter_state.pkl", "rb"))
vecs = {t: np.asarray(v, dtype=np.float32) for t, v in st["vecs"].items()}
items = {it["idx"]: it for it in st["items"]}
question_of = {q["idx"]: q["question"] for q in json.load(open("agora_output/lab/locomo_iter_input.json"))}
fups = {f["idx"]: [q for q in (f.get("queries") or []) if isinstance(q, str) and q.strip()]
        for f in json.load(open("agora_output/lab/locomo_iter_followups.json"))}

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


allq = sorted({q for qs in fups.values() for q in qs})
qvec = {}
for i in range(0, len(allq), 64):
    chunk = allq[i:i + 64]
    for t, v in zip(chunk, embed_batch(chunk)):
        qvec[t] = unit(np.asarray(v, dtype=np.float32))
print(f"embedded {len(qvec)} follow-up queries", flush=True)


def rrf(rankings, k0=60):
    """rankings: list of lists of tids (best first). returns dict tid->rrf score."""
    score = {}
    for r in rankings:
        for rank, tid in enumerate(r):
            score[tid] = score.get(tid, 0.0) + 1.0 / (k0 + rank + 1)
    return score


def topset(scoremap, n):
    return set(t for t, _ in sorted(scoremap.items(), key=lambda x: -x[1])[:n])


strategies = ["flat", "current", "maxpool", "sumpool", "rrf_qf", "rrf_fonly",
              "reserve5", "reserve10"]
hits = {s: 0 for s in strategies}
n = 0
for idx, it in items.items():
    turns = sample_turns[it["sample_i"]]; tids = it["turn_ids"]
    g = set(it["gold_ids"])
    TM = np.stack([unit(vecs[turns[i]]) for i in tids])
    qv = unit(vecs[question_of[idx]])
    qsim = TM @ qv
    q_rank = [tids[j] for j in np.argsort(-qsim)]
    fq = fups.get(idx, [])
    fsims = [TM @ qvec[q] for q in fq] if fq else []
    f_ranks = [[tids[j] for j in np.argsort(-fs)] for fs in fsims]

    # flat
    hits["flat"] += g.issubset(set(q_rank[:BUDGET]))
    # current: round1 top15 by Q + fill by max fup sim
    final = list(q_rank[:15])
    if fsims:
        msim = np.max(np.stack(fsims), axis=0)
        for j in np.argsort(-msim):
            if len(final) >= BUDGET: break
            if tids[j] not in final: final.append(tids[j])
    else:
        final = q_rank[:BUDGET]
    hits["current"] += g.issubset(set(final[:BUDGET]))
    # maxpool
    if fsims:
        mp = np.maximum(qsim, np.max(np.stack(fsims), axis=0))
    else:
        mp = qsim
    hits["maxpool"] += g.issubset(set(tids[j] for j in np.argsort(-mp)[:BUDGET]))
    # sumpool
    sp = qsim + (np.sum(np.stack(fsims), axis=0) if fsims else 0.0)
    hits["sumpool"] += g.issubset(set(tids[j] for j in np.argsort(-sp)[:BUDGET]))
    # rrf over question + fups
    hits["rrf_qf"] += g.issubset(topset(rrf([q_rank] + f_ranks), BUDGET))
    # rrf fups only (fallback to q if no fups)
    hits["rrf_fonly"] += g.issubset(topset(rrf(f_ranks if f_ranks else [q_rank]), BUDGET))
    # reserve K by question, RRF(Q,fups) for the rest
    for K, name in [(5, "reserve5"), (10, "reserve10")]:
        reserved = q_rank[:K]
        rest = [t for t, _ in sorted(rrf([q_rank] + f_ranks).items(), key=lambda x: -x[1]) if t not in reserved]
        final2 = reserved + rest[:BUDGET - K]
        hits[name] += g.issubset(set(final2[:BUDGET]))
    n += 1

res = {s: round(hits[s] / n, 3) for s in strategies}
res["n"] = n
best = max(strategies, key=lambda s: hits[s])
res["best"] = best
print(json.dumps(res, indent=1))
print(f"BEST: {best} = {hits[best]/n:.3f}  (flat {hits['flat']/n:.3f}, current {hits['current']/n:.3f})")
json.dump(res, open("agora_output/lab/locomo_iter_fuse_result.json", "w"), indent=1)
