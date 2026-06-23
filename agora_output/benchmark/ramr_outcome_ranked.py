"""RAMR OUTCOME-RANKED-RECALL task family (mnemo's differentiator). Every shipped memory layer ranks recall by
relevance x recency/value; NONE rank by whether a recalled memory actually LED TO A CORRECT OUTCOME. mnemo ships
that channel (recall score x cal; cal=0.5+Beta(good,bad) reliability; fed by credit(ids, outcome)). The lab
already validated the core lift (0.37->0.66) and its robustness to a noisy credit signal. This turns it into a
benchmark family and adds the decisive new dimension: HOW DOES THE LIFT SCALE WITH RETRIEVAL AMBIGUITY?

Setup: M recurring topics; each topic has a FIXED pool of (1+MAXD) memories phrased near-identically (so embedding
similarity ~equal -> relevance ranking is ~chance among them). For each ambiguity level D we use the first 1+D of
them and randomly designate ONE as CORRECT (per set). Over T sessions, for each topic: recall top-1, score hit
(top-1 == correct), then credit([top-1], outcome=hit). Three arms over identical stores:
  NONE    : never credit -> reliability neutral -> rank by relevance only (the field's status quo)
  OUTCOME : credit with the TRUE outcome -> was-it-right reranking (mnemo)
  RANDOM  : credit with a RANDOM outcome (control) -> if this lifts too, the gain is reranking noise, not signal
Sweep D in {1,2,4,8} (ambiguity rises; relevance chance = 1/(1+D)). Metric: OUTCOME-RANKED LIFT = final-session
accuracy(OUTCOME) - accuracy(NONE), per D, bootstrap CI over N_SETS. FALSIFIER (pre-registered): if the OUTCOME
lift CI overlaps 0, the was-it-right channel is decorative; if RANDOM lifts comparably, it's not the outcome
signal. Prediction: lift GROWS with D and RANDOM stays ~0.

EMBED-ONCE design: memory texts are a FIXED pool -> every text is embedded ONCE (cached); only the correctness
label and ambiguity window vary across conditions. This keeps embeddings identical across all conditions (cleaner)
and avoids re-embedding under GPU contention. Cloud-free (local nomic-embed-text). ASCII prints."""
import os, sys, json, time, urllib.request
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mnemo"))
from mnemo import Mnemo

OLL = "http://localhost:11434/api/embeddings"
M_TOPICS = int(os.getenv("RAMR_M", "24"))
MAXD = 8
D_LEVELS = [1, 2, 4, 8]
T_SESS = int(os.getenv("RAMR_T", "8"))
N_SETS = int(os.getenv("RAMR_SETS", "4"))

_emb_cache = {}
def embed(text):
    if text in _emb_cache: return _emb_cache[text]
    body = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    for _ in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                OLL, data=body, headers={"Content-Type": "application/json"}), timeout=90).read())
            v = r.get("embedding")
            if v: _emb_cache[text] = v; return v
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("embed failed")

ENTITIES = ["payment API","auth service","search index","billing job","cache layer","upload queue","report engine",
            "email worker","session store","rate limiter","image CDN","audit log","webhook relay","config loader",
            "metrics sink","backup task","login flow","export tool","notification bus","schema migrator","token vault",
            "feature flag svc","data lake","shard router","pdf renderer","geo lookup","fraud check","recommend svc",
            "chat gateway","trace collector"]
ATTRS = ["retry limit","timeout seconds","max batch size","cache TTL minutes","concurrency cap"]


def build_pool():
    """FIXED pool: M topics, each with 1+MAXD near-identical memory texts (distinct values) + a query."""
    r = np.random.default_rng(99); ents = list(ENTITIES); r.shuffle(ents); pool = []
    for i in range(M_TOPICS):
        ent, attr = ents[i % len(ents)], ATTRS[i % len(ATTRS)]
        vals = list(range(2, 2 + 1 + MAXD)); r2 = np.random.default_rng(500 + i); r2.shuffle(vals)
        mems = [f"The {attr} of the {ent} is {v}." for v in vals[:1 + MAXD]]
        pool.append({"q": f"What is the {attr} of the {ent}?", "mems": mems})
    return pool


def run_arm(pool, D, correct_idx, mode, seed):
    rr = np.random.default_rng(seed)
    store = Mnemo(path=None, embed=embed); store.semantic_threshold = 1
    correct = []
    for ti, tp in enumerate(pool):
        cs = set()
        for j in range(1 + D):
            mid = store.remember(tp["mems"][j], tags=["cfg"], value=1.0, mtype="semantic")
            if j == correct_idx[ti]: cs.add(mid)
        correct.append(cs)
    acc = []
    for _ in range(T_SESS):
        hits = 0
        for tp, cs in zip(pool, correct):
            res = store.recall(tp["q"], k=1 + D, mode="semantic")
            if not res: continue
            top = res[0]; ok = top["id"] in cs; hits += int(ok)
            if mode == "outcome":
                store.credit([top["id"]], outcome=ok)
            elif mode == "random":
                store.credit([top["id"]], outcome=bool(rr.integers(2)))
        acc.append(hits / len(pool))
    return acc


if __name__ == "__main__":
    print(f"compile OK - RAMR OUTCOME-RANKED-RECALL (M={M_TOPICS}, T={T_SESS}, sets={N_SETS}, D={D_LEVELS}; embed-once)", flush=True)
    pool = build_pool()
    # pre-embed the whole fixed pool + queries ONCE (progress) so all later conditions hit the cache
    texts = [t for tp in pool for t in tp["mems"]] + [tp["q"] for tp in pool]
    t0 = time.time()
    try:
        for n, t in enumerate(texts):
            embed(t)
            if (n + 1) % 30 == 0: print(f"  pre-embed {n+1}/{len(texts)} ({time.time()-t0:.0f}s)", flush=True)
    except Exception as e:
        print("EMBED UNAVAILABLE:", str(e)[:80]); sys.exit(1)
    print(f"  pre-embed DONE {len(texts)} texts in {time.time()-t0:.0f}s (rest is cache-only)", flush=True)

    fin = {D: {"none": [], "outcome": [], "random": []} for D in D_LEVELS}
    for si in range(N_SETS):
        rs = np.random.default_rng(300 + si)
        for D in D_LEVELS:
            correct_idx = [int(rs.integers(1 + D)) for _ in range(M_TOPICS)]
            for mi, mode in enumerate(("none", "outcome", "random")):
                c = run_arm(pool, D, correct_idx, mode, seed=si * 100 + D * 7 + mi * 31)
                fin[D][mode].append(c[-1])
            print(f"  set {si} D={D}: none {fin[D]['none'][-1]:.2f} | outcome {fin[D]['outcome'][-1]:.2f} | "
                  f"random {fin[D]['random'][-1]:.2f}", flush=True)
    print(f"\n  === OUTCOME-RANKED-RECALL: lift vs retrieval ambiguity (final-session top-1 accuracy, n={N_SETS}) ===", flush=True)
    print(f"  D (chance)   | NONE  | OUTCOME | RANDOM | OUTCOME-LIFT (CI)         | RANDOM-LIFT", flush=True)
    brng = np.random.default_rng(7); any_sig = False; lift_by_D = {}
    for D in D_LEVELS:
        none_f = np.array(fin[D]["none"]); out_f = np.array(fin[D]["outcome"]); rnd_f = np.array(fin[D]["random"])
        d = out_f - none_f; bs = [d[brng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
        lo, hi = np.percentile(bs, [2.5, 97.5]); rlift = float((rnd_f - none_f).mean())
        sig = lo > 0; any_sig = any_sig or sig; lift_by_D[D] = (float(d.mean()), float(lo), float(hi), bool(sig))
        print(f"   {D} ({1/(1+D):.2f})    | {none_f.mean():.2f}  |  {out_f.mean():.2f}   |  {rnd_f.mean():.2f}  | "
              f"{d.mean():+.2f} [{lo:+.2f},{hi:+.2f}] {'SIG' if sig else '   '} | {rlift:+.2f}", flush=True)
    lifts = [lift_by_D[D][0] for D in D_LEVELS]
    grows = lifts[-1] - lifts[0] >= 0.05
    # control check: does RANDOM credit produce a comparable POSITIVE lift? (a NEGATIVE random-lift is the ideal
    # control outcome -- random reranking should HURT. Use the signed max, not abs.)
    rnd_max = max(float((np.array(fin[D]["random"]) - np.array(fin[D]["none"])).mean()) for D in D_LEVELS)
    print(f"\n  === VERDICT (pre-registered) ===", flush=True)
    if any_sig and rnd_max < 0.05:
        msg = (f"WAS-IT-RIGHT BEATS WAS-IT-RECALLED: outcome-credit reranking lifts top-1 recall over relevance-only "
               f"with CI excluding 0, while RANDOM credit does not (max |random-lift| {rnd_max:.2f}) -> the gain is the "
               f"OUTCOME signal, not reranking noise. ")
        msg += (f"The lift GROWS with retrieval ambiguity (D=1 -> {lifts[0]:+.2f}, D={D_LEVELS[-1]} -> {lifts[-1]:+.2f}): "
                f"when relevance can't disambiguate near-identical memories, outcome feedback is the only signal -- "
                f"exactly where mnemo's differentiator pays off." if grows else
                f"The lift does not clearly grow with ambiguity over the tested range.")
        print("  " + msg, flush=True)
    elif any_sig:
        print(f"  outcome-credit lifts recall (CI>0) BUT random credit lifts comparably (max {rnd_max:.2f}) -> the gain "
              f"may be reranking dynamics, not the outcome signal. Needs a cleaner control.", flush=True)
    else:
        print(f"  DECORATIVE: the outcome-ranked lift CI overlaps 0 at every ambiguity level -> on this task mnemo's "
              f"was-it-right channel does not measurably beat relevance ranking. Honest negative.", flush=True)
    json.dump({"final": {str(D): fin[D] for D in D_LEVELS}, "lift_by_D": {str(D): lift_by_D[D] for D in D_LEVELS},
               "M": M_TOPICS, "T": T_SESS, "sets": N_SETS},
              open("agora_output/benchmark/ramr_outcome_ranked_result.json", "w"))
    print("DONE", flush=True)
