"""membench_recall_probe.py — FEASIBILITY: can inspeximus be measured on MemBench? (ACL 2025 Findings)

MemBench (Tan et al., ACL Findings 2025, github.com/import-myself/Membench) evaluates LLM-agent
memory on dialogue trajectories with QA whose evidence location is annotated: QA.target_step_id[i][0]
is the GLOBAL FLAT index of the evidence user-message in the trajectory (verified empirically 6/6 on
simple.json + 3/3 on highlevel.json before this probe was written; the [sess,msg] reading is OOB).

That annotation makes a RETRIEVAL-ONLY evaluation possible — no LLM in the loop, exactly the LoCoMo
protocol we already run: ingest each user message into a fresh inspeximus store, recall(question, k),
score hit@k / full_recall@k against the annotated evidence indices.

Arms:
  cosine  - plain nomic cosine top-k over the same embeddings (the floor inspeximus must not fall below;
            inspeximus's recall is cosine + centering + its scoring pipeline, so a big gap = a bug)
  inspeximus   - inspeximus.recall() semantic mode with the same nomic embedder (asymmetric prefixes)

Splits: FirstAgent/simple (factual, ~165 msgs/traj — the real retrieval load) and
FirstAgent/highlevel (reflective, ~13 msgs/traj — short; near-ceiling expected, kept for coverage).

Metrics: hit@k (any annotated evidence msg in top-k, k=1/5/10) and full@k (ALL evidence msgs in
top-k — reflective QAs have 2-3 evidence msgs).

HONEST SCOPE: (a) retrieval-only — MemBench's headline numbers are LLM answer-accuracy, so ours are
NOT comparable to the paper's tables, they measure the memory layer alone; (b) feasibility sample
(40 simple + 30 highlevel trajectories), not the full 2500; (c) no noise-extended (100k-token)
variant yet — that is the interesting stress test and the natural next step.

RUN: local Ollama with nomic-embed-text; data at agora_output/lab/data/membench/{simple,highlevel}.json
Own embedding cache (probe-cache lesson: never share a cache file across probes).
"""
import json, os, sys, hashlib, urllib.request, tempfile

sys.stdout.reconfigure(errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "inspeximus")))
from inspeximus import Inspeximus

DATA_DIR = os.environ.get("MEMBENCH_DATA", "agora_output/lab/data/membench")
CACHE = os.environ.get("MEMBENCH_CACHE", "research/probes/membench_embcache_v1.json")
EMB_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
MODEL = "nomic-embed-text"
QP, DP = "search_query: ", "search_document: "
KS = (1, 5, 10)
N_SIMPLE, N_HIGH = 40, 30

_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
_dirty = 0

def _key(role, text):
    return hashlib.sha1(f"{MODEL}|{role}|{text[:2000]}".encode()).hexdigest()

def _post(inputs):
    body = json.dumps({"model": MODEL, "input": inputs}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        EMB_URL, data=body, headers={"Content-Type": "application/json"}), timeout=300)
    return json.loads(r.read())["embeddings"]

def embed_batch(texts, role):
    """role-prefixed, cached, incremental-flush embeddings."""
    global _dirty
    pref = QP if role == "q" else DP
    missing = [t for t in texts if _key(role, t) not in _cache]
    for i in range(0, len(missing), 64):
        chunk = missing[i:i + 64]
        vecs = _post([pref + t for t in chunk])
        for t, v in zip(chunk, vecs):
            _cache[_key(role, t)] = v
        _dirty += len(chunk)
        if _dirty >= 640:
            json.dump(_cache, open(CACHE, "w")); _dirty = 0
    return [_cache[_key(role, t)] for t in texts]

def cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5; nb = sum(x * x for x in b) ** 0.5
    return num / (na * nb + 1e-12)

def load_trajs():
    trajs = []
    d = json.load(open(f"{DATA_DIR}/simple.json", encoding="utf-8"))
    per = N_SIMPLE // 2
    for cat in ("roles", "events"):
        for t in d[cat][:per]:
            flat = [m["user_message"] for s in t["message_list"] for m in s]
            trajs.append(("simple", cat, flat, t["QA"]))
    d = json.load(open(f"{DATA_DIR}/highlevel.json", encoding="utf-8"))
    per = N_HIGH // 3
    for cat in ("movie", "food", "book"):
        for t in d[cat][:per]:
            flat = [m["user"] for s in t["message_list"] for m in s]
            trajs.append(("highlevel", cat, flat, t["QA"]))
    return trajs

def main():
    trajs = load_trajs()
    print(f"trajectories: {len(trajs)} "
          f"(simple={sum(1 for t in trajs if t[0]=='simple')}, "
          f"highlevel={sum(1 for t in trajs if t[0]=='highlevel')})")
    scores = {}   # (split, arm, metric, k) -> [0/1...]
    skipped = 0
    for split, cat, flat, qa in trajs:
        targets = sorted({a for a, _ in qa["target_step_id"] if a < len(flat)})
        if not targets:
            skipped += 1; continue
        q = qa["question"]
        dvecs = embed_batch(flat, "d")
        qvec = embed_batch([q], "q")[0]

        # arm 1: plain cosine
        ranked = sorted(range(len(flat)), key=lambda i: -cos(qvec, dvecs[i]))
        # arm 2: inspeximus semantic recall over the same embedder
        doc_vec = {DP + t: v for t, v in zip(flat, dvecs)}
        def emb_fn(text):
            v = doc_vec.get(DP + text)
            return v if v is not None else embed_batch([text], "q")[0]
        fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
        m = Inspeximus(path=p, embed=emb_fn)
        ids = [m.remember(t, mtype="episodic") for t in flat]
        idx_of = {mid: i for i, mid in enumerate(ids)}
        got = m.recall(q, k=max(KS), mode="semantic")
        mn_ranked = [idx_of[r["id"]] for r in got if r["id"] in idx_of]
        if os.path.exists(p): os.remove(p)

        for arm, rk in (("cosine", ranked), ("inspeximus", mn_ranked)):
            for k in KS:
                top = set(rk[:k])
                scores.setdefault((split, arm, "hit", k), []).append(
                    1.0 if any(t in top for t in targets) else 0.0)
                scores.setdefault((split, arm, "full", k), []).append(
                    1.0 if all(t in top for t in targets) else 0.0)
    json.dump(_cache, open(CACHE, "w"))

    print(f"skipped (OOB targets): {skipped}")
    for split in ("simple", "highlevel"):
        n = len(scores.get((split, "cosine", "hit", 1), []))
        print(f"\n=== MEASURED {split} (n={n} questions) ===")
        for arm in ("cosine", "inspeximus"):
            hit = " ".join(f"hit@{k}={sum(scores[(split,arm,'hit',k)])/n:.3f}" for k in KS)
            full = " ".join(f"full@{k}={sum(scores[(split,arm,'full',k)])/n:.3f}" for k in (5, 10))
            print(f"  {arm:7s} {hit}  {full}")
    out = {f"{s}|{a}|{m}@{k}": round(sum(v) / len(v), 4)
           for (s, a, m, k), v in scores.items()}
    json.dump(out, open("research/probes/membench_recall_probe_result.json", "w"), indent=2)
    print("\nresult -> research/probes/membench_recall_probe_result.json")

main()
