"""RAMR point-4 hardening: an INDEPENDENT external baseline (kills the 'you benchmarked your own NONE arm = a
strawman' attack). The OUTCOME-RANKED result compared inspeximus-with-credit (OUTCOME) vs inspeximus-without-credit (NONE).
A skeptic: 'maybe your NONE arm is artificially weak.' This adds a standard, INDEPENDENT vector retriever -- NOT
our code -- on the SAME task + SAME embeddings:
  EXT-SKLEARN : sklearn.neighbors.NearestNeighbors(metric=cosine) top-1 (the textbook RAG retrieval baseline)
  EXT-NUMPY   : plain numpy cosine argmax top-1 (a second independent implementation, sanity cross-check)
  INSPEXIMUS-NONE  : inspeximus recall, no outcome credit (relevance-only)  -> should MATCH the external baselines
  INSPEXIMUS-OUTCOME: inspeximus recall + was-it-right credit               -> should BEAT all of them
If EXT ~= INSPEXIMUS-NONE, the NONE arm is a faithful standard retriever (not a strawman); the outcome lift is then a
lift over an INDEPENDENT baseline, not just over our own switch. Disk-persisted embeddings (cloud-free, embed-once
ever). ASCII prints."""
import os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_outcome_ranked as oro
from sklearn.neighbors import NearestNeighbors

D_LEVELS = oro.D_LEVELS
N_SETS = int(os.getenv("RAMR_SETS", "4"))
T_SESS = oro.T_SESS
EMB_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "emb_cache.json")


def load_disk_cache():
    if os.path.exists(EMB_CACHE):
        try:
            oro._emb_cache.update(json.load(open(EMB_CACHE)))
            print(f"  loaded {len(oro._emb_cache)} cached embeddings from disk", flush=True)
        except Exception:
            pass


def save_disk_cache():
    json.dump(oro._emb_cache, open(EMB_CACHE, "w"))


def cos_top1(qv, mvs):
    """independent numpy cosine top-1 index."""
    q = np.array(qv, float); M = np.array(mvs, float)
    qn = q / (np.linalg.norm(q) + 1e-9); Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return int(np.argmax(Mn @ qn))


def sklearn_top1(qv, mvs):
    """independent sklearn NearestNeighbors (cosine) top-1 index -- a real, standard library."""
    nn = NearestNeighbors(n_neighbors=1, metric="cosine").fit(np.array(mvs, float))
    return int(nn.kneighbors([np.array(qv, float)], return_distance=False)[0][0])


if __name__ == "__main__":
    print(f"compile OK - RAMR EXTERNAL BASELINE (sklearn/numpy cosine vs inspeximus NONE/OUTCOME; sets={N_SETS})", flush=True)
    load_disk_cache()
    pool = oro.build_pool()
    texts = [t for tp in pool for t in tp["mems"]] + [tp["q"] for tp in pool]
    t0 = time.time(); newc = 0
    try:
        for n, t in enumerate(texts):
            if t not in oro._emb_cache: newc += 1
            oro.embed(t)
            if (n + 1) % 40 == 0: print(f"  embed {n+1}/{len(texts)} ({time.time()-t0:.0f}s, {newc} new)", flush=True)
    except Exception as e:
        print("EMBED UNAVAILABLE:", str(e)[:80]); sys.exit(1)
    save_disk_cache()
    print(f"  embeds ready ({newc} new, {len(texts)-newc} from cache) in {time.time()-t0:.0f}s", flush=True)

    # accumulate per-D accuracy for each method over sets
    acc = {D: {"ext_sklearn": [], "ext_numpy": [], "inspeximus_none": [], "inspeximus_outcome": []} for D in D_LEVELS}
    for si in range(N_SETS):
        rs = np.random.default_rng(300 + si)        # SAME correct_idx seed as the outcome experiment
        for D in D_LEVELS:
            correct_idx = [int(rs.integers(1 + D)) for _ in range(oro.M_TOPICS)]
            # independent external baselines (stateless -> one pass over topics)
            sk_hits = nz_hits = 0
            for ti, tp in enumerate(pool):
                qv = oro._emb_cache[tp["q"]]
                mvs = [oro._emb_cache[tp["mems"][j]] for j in range(1 + D)]
                sk_hits += int(sklearn_top1(qv, mvs) == correct_idx[ti])
                nz_hits += int(cos_top1(qv, mvs) == correct_idx[ti])
            acc[D]["ext_sklearn"].append(sk_hits / oro.M_TOPICS)
            acc[D]["ext_numpy"].append(nz_hits / oro.M_TOPICS)
            # inspeximus arms (final-session accuracy), reusing the SAME pool + cached embeddings
            none_c = oro.run_arm(pool, D, correct_idx, "none", seed=si * 100 + D * 7)
            out_c = oro.run_arm(pool, D, correct_idx, "outcome", seed=si * 100 + D * 7 + 31)
            acc[D]["inspeximus_none"].append(none_c[-1]); acc[D]["inspeximus_outcome"].append(out_c[-1])
        print(f"  set {si} done", flush=True)

    print(f"\n  === EXTERNAL-BASELINE COMPARISON (final-session top-1 accuracy, n={N_SETS} sets) ===", flush=True)
    print(f"  D (chance)  | EXT-sklearn | EXT-numpy | INSPEXIMUS-NONE | INSPEXIMUS-OUTCOME", flush=True)
    brng = np.random.default_rng(7)
    gaps_none, gaps_out = [], []
    for D in D_LEVELS:
        a = {k: float(np.mean(v)) for k, v in acc[D].items()}
        print(f"   {D} ({1/(1+D):.2f})   |   {a['ext_sklearn']:.3f}     |  {a['ext_numpy']:.3f}   |   "
              f"{a['inspeximus_none']:.3f}    |   {a['inspeximus_outcome']:.3f}", flush=True)
        gaps_none.append(abs(a["inspeximus_none"] - a["ext_sklearn"]))
        gaps_out.append(a["inspeximus_outcome"] - a["ext_sklearn"])
    # CI of OUTCOME-vs-EXTERNAL gap at the hardest ambiguity
    Dh = D_LEVELS[-1]
    d = np.array(acc[Dh]["inspeximus_outcome"], float) - np.array(acc[Dh]["ext_sklearn"], float)
    bs = [d[brng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"\n  === VERDICT ===", flush=True)
    none_matches = max(gaps_none) < 0.08
    print(f"  NONE-vs-external max |gap| across D: {max(gaps_none):.3f}  -> "
          f"{'NONE arm MATCHES an independent standard retriever (NOT a strawman)' if none_matches else 'NONE arm differs from external baseline -- inspect'}", flush=True)
    print(f"  OUTCOME beats external sklearn baseline at D={Dh}: {d.mean():+.3f}  95% CI [{lo:+.3f},{hi:+.3f}] "
          f"{'(excludes 0)' if lo>0 else '(overlaps 0)'}", flush=True)
    if none_matches and lo > 0:
        print(f"  DEFENSIBLE: an independent sklearn cosine retriever scores ~the same as inspeximus-NONE, so NONE is a "
              f"faithful relevance-only baseline, not a strawman. Outcome-ranked recall beats this INDEPENDENT "
              f"baseline (CI excludes 0). The was-it-right lift is real, not an artifact of comparing our own switch.", flush=True)
    else:
        print(f"  inspect: {'NONE matches but outcome lift CI overlaps 0' if none_matches else 'NONE diverges from external retriever'}.", flush=True)
    json.dump({"acc": {str(D): {k: list(map(float, v)) for k, v in acc[D].items()} for D in D_LEVELS},
               "outcome_vs_ext_ci": [float(lo), float(hi)], "sets": N_SETS},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ramr_external_baseline_result.json"), "w"))
    print("DONE", flush=True)
