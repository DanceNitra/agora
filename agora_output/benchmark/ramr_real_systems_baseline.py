"""RAMR external REAL-SYSTEM baseline: benchmark the retrieval ENGINES that shipped Claude-Code memory systems
actually use, on RAMR's near-duplicate disambiguation task -- the honest way to fill the 'external real-system
baseline' gap without fragile end-to-end installs (several are hosted/paid or need the Claude Code runtime).
We reproduce the actual retrieval primitives faithfully:
  KEYWORD (SQLite FTS5 / BM25)  -- claude-brain's keyword search mode; the engine grep/FTS file-memory tools use.
  VECTOR  (dense cosine over a real sentence-embedding model, local nomic-embed-text) -- claude-brain's semantic
           mode, mem0's vector recall, mnemo's relevance ranking.
  mnemo NONE (relevance-only) and mnemo OUTCOME (was-it-right reranking) for reference.
Task: M topics, each 1 correct + D distractor memories that are NEAR-IDENTICAL (share all query tokens, differ
only in the stored value) -- the realistic 'which of several similar remembered facts is the right one' case.
Top-1 retrieval accuracy. Same fixed pool + cached embeddings as ramr_external_baseline (seed 99). Cloud-free.
ASCII prints."""
import os, sys, json, re, sqlite3, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_outcome_ranked as oro

D_LEVELS = oro.D_LEVELS
N_SEEDS = int(os.getenv("RAMR_SETS", "4"))
EMB_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "emb_cache.json")


def load_cache():
    if os.path.exists(EMB_CACHE):
        oro._emb_cache.update(json.load(open(EMB_CACHE)))


def fts5_top1(query, cand_texts):
    """claude-brain's keyword engine: SQLite FTS5 BM25. Returns index of the top-ranked candidate."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE VIRTUAL TABLE m USING fts5(body)")
    con.executemany("INSERT INTO m(rowid, body) VALUES (?,?)", [(i, t) for i, t in enumerate(cand_texts)])
    toks = [w for w in re.findall(r"[A-Za-z0-9]+", query) if len(w) > 1]
    match = " OR ".join(toks)
    rows = con.execute("SELECT rowid FROM m WHERE m MATCH ? ORDER BY bm25(m)", (match,)).fetchall()
    con.close()
    return rows[0][0] if rows else 0


def cos_top1(qv, mvs):
    q = np.array(qv, float); M = np.array(mvs, float)
    qn = q / (np.linalg.norm(q) + 1e-9); Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return int(np.argmax(Mn @ qn))


if __name__ == "__main__":
    print(f"compile OK - RAMR REAL-SYSTEM retrieval-engine baseline (FTS5/BM25 keyword + dense vector vs mnemo; "
          f"sets={N_SEEDS})", flush=True)
    load_cache()
    pool = oro.build_pool()
    # ensure embeddings for the vector arm are present (cache-first; only embeds misses)
    texts = [t for tp in pool for t in tp["mems"]] + [tp["q"] for tp in pool]
    miss = [t for t in texts if t not in oro._emb_cache]
    if miss:
        print(f"  embedding {len(miss)} uncached texts...", flush=True)
        for t in texts:
            oro.embed(t)
        json.dump(oro._emb_cache, open(EMB_CACHE, "w"))
    acc = {D: {"keyword_fts5": [], "vector_nomic": [], "mnemo_none": [], "mnemo_outcome": []} for D in D_LEVELS}
    for si in range(N_SEEDS):
        rs = np.random.default_rng(300 + si)
        for D in D_LEVELS:
            correct_idx = [int(rs.integers(1 + D)) for _ in range(oro.M_TOPICS)]
            kw = vec = 0
            for ti, tp in enumerate(pool):
                cand_texts = [tp["mems"][j] for j in range(1 + D)]
                if fts5_top1(tp["q"], cand_texts) == correct_idx[ti]:
                    kw += 1
                qv = oro._emb_cache[tp["q"]]; mvs = [oro._emb_cache[tp["mems"][j]] for j in range(1 + D)]
                if cos_top1(qv, mvs) == correct_idx[ti]:
                    vec += 1
            acc[D]["keyword_fts5"].append(kw / oro.M_TOPICS)
            acc[D]["vector_nomic"].append(vec / oro.M_TOPICS)
            acc[D]["mnemo_none"].append(oro.run_arm(pool, D, correct_idx, "none", seed=si * 100 + D * 7)[-1])
            acc[D]["mnemo_outcome"].append(oro.run_arm(pool, D, correct_idx, "outcome", seed=si * 100 + D * 7 + 31)[-1])
        print(f"  set {si} done", flush=True)

    print(f"\n  === REAL-SYSTEM RETRIEVAL ENGINES on near-duplicate disambiguation (top-1 acc, n={N_SEEDS}) ===", flush=True)
    print(f"  D (chance)  | KEYWORD FTS5/BM25 | VECTOR (nomic) | mnemo-NONE | mnemo-OUTCOME", flush=True)
    for D in D_LEVELS:
        a = {k: float(np.mean(v)) for k, v in acc[D].items()}
        print(f"   {D} ({1/(1+D):.2f})   |      {a['keyword_fts5']:.3f}       |    {a['vector_nomic']:.3f}     |   "
              f"{a['mnemo_none']:.3f}    |   {a['mnemo_outcome']:.3f}", flush=True)
    Dh = D_LEVELS[-1]; ch = 1 / (1 + Dh)
    kw_h = float(np.mean(acc[Dh]["keyword_fts5"])); vec_h = float(np.mean(acc[Dh]["vector_nomic"]))
    out_h = float(np.mean(acc[Dh]["mnemo_outcome"]))
    # CI of outcome vs the BEST real-system engine at hardest D
    best_rs = np.maximum(np.array(acc[Dh]["keyword_fts5"]), np.array(acc[Dh]["vector_nomic"]))
    d = np.array(acc[Dh]["mnemo_outcome"]) - best_rs
    rng = np.random.default_rng(7); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"\n  === VERDICT ===", flush=True)
    kw_chance = abs(kw_h - ch) < 0.10; vec_chance = abs(vec_h - ch) < 0.10
    if kw_chance and vec_chance and lo > 0:
        print(f"  BOTH shipped-system retrieval engines hit the SAME WALL: at D={Dh} (chance {ch:.2f}), SQLite "
              f"FTS5/BM25 keyword = {kw_h:.2f} and dense-vector semantic = {vec_h:.2f} -- both ~chance, because "
              f"near-duplicate memories share query tokens (keyword) and embed near-identically (vector). The "
              f"outcome (was-it-right) signal beats the best of them by {d.mean():+.2f} (95% CI [{lo:+.2f},{hi:+.2f}], "
              f"excludes 0). So the disambiguation gap is NOT a weakness of our baseline -- the entire relevance-"
              f"based retrieval class that real systems (claude-brain keyword+semantic, mem0, grep-memory) ship on "
              f"fails this case identically; an outcome signal is what breaks the tie. Strong external real-system "
              f"baseline.", flush=True)
    else:
        print(f"  MIXED: keyword {kw_h:.2f}, vector {vec_h:.2f} vs chance {ch:.2f}; outcome-vs-best lift {d.mean():+.2f} "
              f"CI [{lo:+.2f},{hi:+.2f}]. Inspect per engine.", flush=True)
    json.dump({"acc": {str(D): {k: list(map(float, v)) for k, v in acc[D].items()} for D in D_LEVELS},
               "outcome_vs_best_realsystem_ci": [float(lo), float(hi)], "sets": N_SEEDS},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ramr_real_systems_result.json"), "w"))
    print("DONE", flush=True)
