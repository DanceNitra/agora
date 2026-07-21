"""Confidence-weighted soft metadata pre-filter on LoCoMo (extends locomo_metadata_prefilter.py).

Prompted by u/jacksonxly on r/Rag, following up on the hard-vs-soft filter result (that post: hard
+0.146 recall@20 overall but craters the ~5% harm subset 0.56->0.15; soft +0.129 overall, harm subset
0.56->0.27, mitigates but doesn't eliminate). His proposal: don't treat the soft boost as a constant -
weight it by (extractor confidence) x (filter selectivity), "IDF for filters plus a trust term". It
should collapse gracefully to plain hybrid when the extractor is unsure or the filter barely narrows
the pool. His open question: does confidence-weighting pull the harm-subset recall back toward the
no-filter baseline (0.56), on a filter that's PREDICTED rather than gold (i.e. noisier)?

This probe builds exactly that and answers it:
  - selectivity(filter) = 1 - |candidates after filter| / |total pool>|  (how much it narrowed the set)
  - confidence: two extractor qualities simulated -
      "gold"  = our exact-name-match heuristic (as in the prior probe), confidence=1.0 always
      "noisy" = the SAME heuristic but with a p_noise=0.25 chance the detected speaker is WRONG
                (simulating a real predicted/fuzzy extractor's error rate), confidence=0.75 for all
                its firings (a simple scalar reflecting ~75% average correctness - a real system
                would have per-instance confidence; this is the honest minimal version)
  - confidence-weighted soft: RRF-fuse the plain-hybrid rank with the filter-preferred rank, but scale
    the filter list's contribution by w = confidence * selectivity. w=0 -> pure hybrid (graceful
    fallback); w large -> filter dominates (approaches hard-filter-like behavior). This is compared
    against a FLAT soft boost (current design, w implicitly = 1 always) on the SAME noisy extractor,
    to isolate what confidence-weighting buys you specifically when the filter can be wrong.

Metrics: overall recall@20 (all 4 methods) AND the harm subset (heuristic fires on the wrong speaker -
both the natural LoCoMo case and cases we've synthetically flipped). This directly answers "does
confidence-weighting pull 0.27 back toward 0.56 on the wrong-fire cases."

Needs: numpy + local Ollama nomic-embed-text. Zero-dependency otherwise. MIT. Run:
  LOCOMO_PATH=<path to locomo10.json> python research/probes/locomo_confweighted_prefilter.py
"""
import json, re, ast, time, math, hashlib, os, urllib.request, collections, random

DATA = os.environ.get("LOCOMO_PATH", "locomo10.json")
CACHE = os.environ.get("LOCOMO_CACHE", "locomo_metadata_prefilter_cache.json")
EMB_URL = "http://localhost:11434/api/embed"
K = 20
ANSWERABLE = ("1", "2", "3", "4")
P_NOISE = 0.25          # simulated predicted-extractor error rate
NOISE_CONF = 0.75       # the noisy extractor's self-reported confidence (honest: ~= 1-P_NOISE)
GOLD_CONF = 1.0
RNG_SEED = 42

_t0 = time.time()
_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def _key(t): return hashlib.sha1(t[:2000].encode("utf-8")).hexdigest()
def _post(payload):
    r = urllib.request.urlopen(urllib.request.Request(
        EMB_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}), timeout=120)
    return json.loads(r.read())["embeddings"]
def warmup(texts, batch=128, flush_every=10):
    miss, seen = [], set()
    for t in texts:
        k = _key(t)
        if k not in _cache and k not in seen:
            seen.add(k); miss.append(t)
    if not miss:
        print("warmup: all cached", flush=True); return
    print(f"warmup: {len(miss)} uncached / {len(texts)}", flush=True)
    n_batches = (len(miss) + batch - 1) // batch
    for bi, i in enumerate(range(0, len(miss), batch)):
        chunk = miss[i:i+batch]
        for c, v in zip(chunk, _post({"model": "nomic-embed-text", "input": [c[:2000] for c in chunk]})):
            _cache[_key(c)] = v
        # dumping the WHOLE cache dict after every batch is O(n^2) I/O on a large shared cache file
        # (this once left a shared cache mid-write when killed) - flush periodically + always at the end.
        if (bi + 1) % flush_every == 0 or (bi + 1) == n_batches:
            json.dump(_cache, open(CACHE, "w"))
            print(f"  warmup batch {bi+1}/{n_batches} (t+{time.time()-_t0:.0f}s)", flush=True)
def embed(t):
    v = _cache.get(_key(t))
    if v is None:
        v = _post({"model": "nomic-embed-text", "input": [t[:2000]]})[0]; _cache[_key(t)] = v
    return v
def cos(a, b):
    d = sum(x*y for x, y in zip(a, b)); na = sum(x*x for x in a)**.5; nb = sum(x*x for x in b)**.5
    return d / ((na*nb) or 1)

_tok = re.compile(r"[a-z0-9]+")
def toks(s): return _tok.findall(s.lower())
class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [toks(d) for d in docs]; self.N = len(self.docs)
        self.dl = [len(d) for d in self.docs]; self.avgdl = (sum(self.dl)/self.N) if self.N else 0
        df = collections.Counter(); self.tf = []
        for d in self.docs:
            c = collections.Counter(d); self.tf.append(c)
            for t in c: df[t] += 1
        self.idf = {t: math.log(1 + (self.N - n + 0.5)/(n + 0.5)) for t, n in df.items()}
    def scores(self, query, idxs):
        q = toks(query); out = {}
        for i in idxs:
            c = self.tf[i]; dl = self.dl[i]; s = 0.0
            for t in q:
                f = c.get(t, 0)
                if not f: continue
                s += self.idf.get(t, 0.0) * (f*(self.k1+1)) / (f + self.k1*(1 - self.b + self.b*dl/(self.avgdl or 1)))
            out[i] = s
        return out

def gold_of(q, tset):
    e = q.get("evidence")
    try: ids = ast.literal_eval(e) if isinstance(e, str) else e
    except Exception: ids = []
    return [i for i in (ids or []) if i in tset]

def rrf(rank_a, rank_b, ids, c=60):
    ra = {i: r for r, i in enumerate(rank_a)}; rb = {i: r for r, i in enumerate(rank_b)}
    return sorted(ids, key=lambda i: -(1.0/(c+ra[i]) + 1.0/(c+rb[i])))

def weighted_rrf(rank_a, rank_b, ids, w, c=60):
    """RRF where rank_b's contribution is scaled by w in [0, inf). w=0 -> pure rank_a (graceful
    fallback to plain hybrid); w=1 -> the classic flat-soft RRF; w>1 -> filter list dominates more."""
    ra = {i: r for r, i in enumerate(rank_a)}; rb = {i: r for r, i in enumerate(rank_b)}
    return sorted(ids, key=lambda i: -(1.0/(c+ra[i]) + w * 1.0/(c+rb[i])))

def hybrid_over(cand_ids, order_index, bm, tvec, qv, question):
    idxs = [order_index[i] for i in cand_ids]
    bm_s = bm.scores(question, idxs)
    bm_rank = sorted(cand_ids, key=lambda i: -bm_s[order_index[i]])
    vec_rank = sorted(cand_ids, key=lambda i: -cos(qv, tvec[i]))
    return rrf(bm_rank, vec_rank, list(cand_ids))

def session_of(dia_id):
    m = re.match(r"D(\d+):", dia_id)
    return m.group(1) if m else None

# ---------- run ----------
D = json.load(open(DATA))
_all = []
for D0 in D:
    conv = D0["conversation"]; tset = set()
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]:
            _all.append(t["text"]); tset.add(t["dia_id"])
    for q in D0["qa"]:
        if str(q.get("category")) in ANSWERABLE and gold_of(q, tset):
            _all.append(q["question"])
warmup(_all)

rng = random.Random(RNG_SEED)

METHODS = ("hybrid", "hard_gold", "soft_flat_gold", "hard_noisy", "soft_flat_noisy", "soft_confweighted_noisy")
# harm subset: split by WHICH condition actually mis-identifies the speaker (gold heuristic wrong,
# or the injected noise flipped a correct gold detection) - track both together as "any wrong-fire".
harm = {m: [] for m in METHODS}
harm["hybrid_noisy"] = []   # no-filter baseline measured on the SAME wrong_noisy subset (not wrong_gold)
per_conv = {m: [] for m in METHODS}
fire = noisy_flips = 0
n_q = 0
t0 = time.time()
for ci, D0 in enumerate(D):
    conv = D0["conversation"]; sa = conv["speaker_a"]; sb = conv["speaker_b"]
    order, text, spk = [], {}, {}
    for sk in sorted([k for k in conv if re.fullmatch(r"session_\d+", k)], key=lambda s: int(s.split("_")[1])):
        for t in conv[sk]:
            order.append(t["dia_id"]); text[t["dia_id"]] = t["text"]; spk[t["dia_id"]] = t["speaker"]
    turnset = set(order); oidx = {i: j for j, i in enumerate(order)}
    N = len(order)
    bm = BM25([text[i] for i in order])
    tvec = {i: embed(text[i]) for i in order}
    qs = [q for q in D0["qa"] if str(q.get("category")) in ANSWERABLE and gold_of(q, turnset)]
    conv_acc = {m: [] for m in METHODS}
    for q in qs:
        n_q += 1; g = set(gold_of(q, turnset)); ng = len(g); qv = embed(q["question"])
        rk = hybrid_over(order, oidx, bm, tvec, qv, q["question"])
        conv_acc["hybrid"].append(len(g & set(rk[:K])) / ng)

        qn = q["question"].lower(); na = sa.lower() in qn; nb = sb.lower() in qn
        wrong_gold = wrong_noisy = None
        if na ^ nb:
            fire += 1
            named_gold = sa if na else sb
            wrong_gold = not all(spk[gi] == named_gold for gi in g)

            # GOLD arm (exact heuristic, as before)
            cand_gold = [i for i in order if spk[i] == named_gold]
            rk_hard_gold = hybrid_over(cand_gold, oidx, bm, tvec, qv, q["question"]) if cand_gold else []
            prior_gold = [i for i in rk if spk[i] == named_gold] + [i for i in rk if spk[i] != named_gold]
            rk_soft_gold = rrf(rk, prior_gold, order)

            # NOISY arm: simulate a predicted extractor - flip the named speaker w.p. P_NOISE
            named_noisy = named_gold
            if rng.random() < P_NOISE:
                named_noisy = sb if named_gold == sa else sa
                noisy_flips += 1
            wrong_noisy = not all(spk[gi] == named_noisy for gi in g)
            cand_noisy = [i for i in order if spk[i] == named_noisy]
            selectivity = 1.0 - (len(cand_noisy) / N if N else 0.0)
            rk_hard_noisy = hybrid_over(cand_noisy, oidx, bm, tvec, qv, q["question"]) if cand_noisy else []
            prior_noisy = [i for i in rk if spk[i] == named_noisy] + [i for i in rk if spk[i] != named_noisy]
            rk_soft_flat_noisy = rrf(rk, prior_noisy, order)                     # flat boost (w implicitly 1)
            w = NOISE_CONF * selectivity                                        # jacksonxly's confidence-weighted boost
            rk_soft_confw_noisy = weighted_rrf(rk, prior_noisy, order, w)
        else:
            rk_hard_gold = rk_soft_gold = rk
            rk_hard_noisy = rk_soft_flat_noisy = rk_soft_confw_noisy = rk

        conv_acc["hard_gold"].append(len(g & set(rk_hard_gold[:K])) / ng)
        conv_acc["soft_flat_gold"].append(len(g & set(rk_soft_gold[:K])) / ng)
        conv_acc["hard_noisy"].append(len(g & set(rk_hard_noisy[:K])) / ng)
        conv_acc["soft_flat_noisy"].append(len(g & set(rk_soft_flat_noisy[:K])) / ng)
        conv_acc["soft_confweighted_noisy"].append(len(g & set(rk_soft_confw_noisy[:K])) / ng)

        if wrong_gold:
            harm["hybrid"].append(len(g & set(rk[:K])) / ng)
            harm["hard_gold"].append(len(g & set(rk_hard_gold[:K])) / ng)
            harm["soft_flat_gold"].append(len(g & set(rk_soft_gold[:K])) / ng)
        if wrong_noisy:
            harm["hybrid_noisy"].append(len(g & set(rk[:K])) / ng)
            harm["hard_noisy"].append(len(g & set(rk_hard_noisy[:K])) / ng)
            harm["soft_flat_noisy"].append(len(g & set(rk_soft_flat_noisy[:K])) / ng)
            harm["soft_confweighted_noisy"].append(len(g & set(rk_soft_confw_noisy[:K])) / ng)
    for m in METHODS:
        per_conv[m].append(sum(conv_acc[m]) / len(conv_acc[m]))
    print(f"  conv {ci}: {len(order)} turns, {len(qs)} Q (t+{time.time()-t0:.0f}s)", flush=True)
json.dump(_cache, open(CACHE, "w"))

def mean(x): return sum(x) / len(x) if x else float("nan")
def boot_ci(deltas, iters=10000, seed=17):
    rnd = random.Random(seed); n = len(deltas); samp = []
    for _ in range(iters):
        samp.append(mean([deltas[rnd.randrange(n)] for _ in range(n)]))
    samp.sort(); return samp[int(.025*iters)], samp[int(.975*iters)]

base = per_conv["hybrid"]
print(f"\n=== LoCoMo confidence-weighted soft filter (recall@{K}, n_q={n_q}, 10 conversations) ===")
print(f"speaker heuristic fired on {fire}/{n_q} Q; noisy extractor flipped {noisy_flips}/{fire} "
      f"firings ({100*noisy_flips//max(fire,1)}%, target P_NOISE={P_NOISE})")
print(f"\n{'method':<26}{'recall@20':>10}{'delta vs hybrid':>18}{'conv win-rate':>15}")
for m in METHODS:
    r = mean(per_conv[m]); dlt = [per_conv[m][i] - base[i] for i in range(len(base))]
    wins = sum(1 for d in dlt if d > 0)
    if m == "hybrid":
        print(f"{m:<26}{r:>10.3f}{'--':>18}{'--':>15}")
    else:
        lo, hi = boot_ci(dlt)
        print(f"{m:<26}{r:>10.3f}{mean(dlt):>+18.3f}{f'{wins}/10':>15}   CI[{lo:+.3f},{hi:+.3f}]")

print(f"\nHARM SUBSETS (heuristic fires on the WRONG speaker) -- each row's baseline is the no-filter")
print(f"recall on ITS OWN subset (gold-wrong-fire subset != noisy-wrong-fire subset, different questions):")
print(f"  {'[gold subset] no-filter':<26}{mean(harm['hybrid']):.3f}   n={len(harm['hybrid'])}")
print(f"  {'gold: hard':<26}{mean(harm['hard_gold']):.3f}   n={len(harm['hard_gold'])}")
print(f"  {'gold: soft (flat)':<26}{mean(harm['soft_flat_gold']):.3f}   n={len(harm['soft_flat_gold'])}")
print(f"  {'[noisy subset] no-filter':<26}{mean(harm['hybrid_noisy']):.3f}   n={len(harm['hybrid_noisy'])}")
print(f"  {'noisy: hard':<26}{mean(harm['hard_noisy']):.3f}   n={len(harm['hard_noisy'])}")
print(f"  {'noisy: soft (flat)':<26}{mean(harm['soft_flat_noisy']):.3f}   n={len(harm['soft_flat_noisy'])}   <- flat boost, ignores confidence/selectivity")
print(f"  {'noisy: soft (conf-weighted)':<26}{mean(harm['soft_confweighted_noisy']):.3f}   n={len(harm['soft_confweighted_noisy'])}   <- jacksonxly's proposal: w = confidence x selectivity")

print("\nReading: does confidence-weighting (w = extractor_confidence x filter_selectivity) pull the")
print("harm-subset recall further back toward the no-filter baseline than a FLAT soft boost does, on a")
print("filter that can be WRONG (simulated predicted/noisy extraction, not gold)? Compare the last two rows.")

result = {"k": K, "n_q": n_q, "fire": fire, "noisy_flips": noisy_flips, "p_noise": P_NOISE,
          "recall@20": {m: round(mean(per_conv[m]), 4) for m in METHODS},
          "delta_vs_hybrid": {m: round(mean([per_conv[m][i]-base[i] for i in range(len(base))]), 4) for m in METHODS if m != "hybrid"},
          "harm_subset": {m: {"mean": round(mean(harm[m]), 4) if harm[m] else None, "n": len(harm[m])} for m in list(METHODS) + ["hybrid_noisy"]}}
json.dump(result, open("locomo_confweighted_prefilter_result.json", "w"), indent=1)
print("\nsaved: locomo_confweighted_prefilter_result.json")
