"""
Full-LoCoMo iterative-retrieval benchmark, PHASE C (deterministic, cloud-free).
Takes the Claude readers' follow-up queries (PHASE B), does round-2 retrieval, combines round-1 + round-2
capped at BUDGET=50, and scores multi-hop full-evidence recall@50 vs the flat baseline.

Inputs:  locomo_iter_state.pkl (phase A), locomo_iter_input.json (phase A), locomo_iter_followups.json (phase B)
Output:  locomo_iter_result.json + printed flat vs iterative headline (n=276)
"""
import json, time, urllib.request, pickle, re
import numpy as np

BUDGET = 50
st = pickle.load(open("agora_output/lab/locomo_iter_state.pkl", "rb"))
vecs = {t: np.asarray(v, dtype=np.float32) for t, v in st["vecs"].items()}
items = {it["idx"]: it for it in st["items"]}
question_of = {q["idx"]: q["question"] for q in json.load(open("agora_output/lab/locomo_iter_input.json"))}
fups = {f["idx"]: (f.get("queries") or [])
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


def flat_rank(it):
    """sample turns ranked by cosine to the QUESTION (the flat baseline ordering)."""
    turns = sample_turns[it["sample_i"]]; tids = it["turn_ids"]
    TM = np.stack([unit(vecs[turns[i]]) for i in tids])
    qv = unit(vecs[question_of[it["idx"]]])
    return [tids[j] for j in np.argsort(-(TM @ qv))]


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


allq = sorted({q for qs in fups.values() for q in qs if isinstance(q, str) and q.strip()})
qvec = {}
for i in range(0, len(allq), 64):
    chunk = allq[i:i + 64]
    for t, v in zip(chunk, embed_batch(chunk)):
        qvec[t] = unit(np.asarray(v, dtype=np.float32))
print(f"embedded {len(qvec)} follow-up queries", flush=True)

iter_hit = flat_hit = n = no_followups = 0
for idx, it in items.items():
    turns = sample_turns[it["sample_i"]]; tids = it["turn_ids"]
    g = set(it["gold_ids"]); round1 = it["round1_ids"]
    flat_ranked = flat_rank(it)
    flat_hit += g.issubset(set(flat_ranked[:BUDGET]))
    qs = [q for q in fups.get(idx, []) if isinstance(q, str) and q.strip()]
    final = list(round1)
    if qs:
        QM = np.stack([qvec[q] for q in qs])
        TM = np.stack([unit(vecs[turns[i]]) for i in tids])
        sim = (TM @ QM.T).max(axis=1)
        for j in np.argsort(-sim):
            if len(final) >= BUDGET:
                break
            tid = tids[j]
            if tid not in final:
                final.append(tid)
    else:
        no_followups += 1
        final = flat_ranked[:BUDGET]
    iter_hit += g.issubset(set(final[:BUDGET]))
    n += 1

result = {
    "n": n,
    "flat_full_recall@50": round(flat_hit / n, 3),
    "iterative_full_recall@50": round(iter_hit / n, 3),
    "delta": round((iter_hit - flat_hit) / n, 3),
    "multiplier": round(iter_hit / flat_hit, 2) if flat_hit else None,
    "questions_with_no_followup": no_followups,
}
print(json.dumps(result, indent=1))
json.dump(result, open("agora_output/lab/locomo_iter_result.json", "w"), indent=1)
