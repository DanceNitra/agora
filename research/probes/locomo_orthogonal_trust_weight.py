"""Orthogonal-signal trust weight vs self-reported-confidence trust weight, on LoCoMo (r/Rag follow-up).

u/jacksonxly's point on the confidence-weighted metadata filter (locomo_confweighted_prefilter.py):
using the EXTRACTOR'S OWN confidence as the filter's trust weight is exactly wrong in the failure mode we
care about (overconfident-on-wrong) — a model that reports high confidence precisely when it mis-extracts
just up-weights the filter on the worst cases, rebuilding the hard filter's harm. His fix: derive the
weight from a signal ORTHOGONAL to the extractor's own belief — e.g. AGREEMENT between two independent
extractors ("two independent extractors agreeing is real signal, one model's own belief isn't").

This probe tests exactly that, honestly:
  Setup (same as the prior probe): LoCoMo, hybrid (BM25+nomic RRF) retriever, speaker metadata filter.
  A NOISY predicted extractor D1 (name-in-question match) is flipped to the WRONG speaker w.p. P_NOISE=0.25.
  Crucially we model ADVERSARIAL OVERCONFIDENCE: D1's self-reported confidence is HIGH (0.9) on ALL its
  firings, INCLUDING the wrong flips (this is the case jacksonxly says breaks self-confidence weighting;
  the prior probe used a flat 0.75 that didn't isolate it).

  Two trust-weight arms, both w in [0,inf) scaling the filter list's RRF contribution (w=0 -> pure hybrid):
   (A) SELF-CONF:   w = 0.9 (D1's own confidence, high even when wrong) * selectivity
   (B) ORTHOGONAL:  w = agreement(D1, D2) * selectivity, where D2 is an INDEPENDENT second opinion on the
                    speaker = the majority speaker among the top-M plain-hybrid retrieved turns for the
                    query (retrieval-based; uses NO gold, NOT D1's belief). agreement = 1.0 if D1==D2 else 0.
                    When D1 is wrong and D2 disagrees, w->0 -> graceful fallback to hybrid.

  This is NOT rigged: whether (B) beats (A) on the harm subset depends entirely on whether D2's errors are
  independent of D1's flip — an empirical question. We also report, on the harm subset, how often D2
  actually disagrees with the (wrong) D1 (the mechanism's coverage), so the result is interpretable, not
  a black box. If D2 is too correlated/weak, (B) won't help and we report that.

Metrics: overall recall@20 + the harm subset (D1 fired on the WRONG speaker) for hybrid / self-conf /
orthogonal. Needs numpy-free pure python + local Ollama nomic-embed-text. Reuses the warm cache. MIT.
Run: LOCOMO_PATH=agora_output/lab/data/locomo10.json \
     LOCOMO_CACHE=agora_output/lab/data/locomo_confweighted_cache.json \
     python research/probes/locomo_orthogonal_trust_weight.py
"""
import json, re, ast, time, math, hashlib, os, urllib.request, collections, random

DATA = os.environ.get("LOCOMO_PATH", "agora_output/lab/data/locomo10.json")
CACHE = os.environ.get("LOCOMO_CACHE", "agora_output/lab/data/locomo_confweighted_cache.json")
EMB_URL = "http://localhost:11434/api/embed"
K = 20
ANSWERABLE = ("1", "2", "3", "4")
P_NOISE = 0.25          # predicted-extractor error rate (same as prior probe)
OVERCONF = 0.9          # D1 self-reported confidence: HIGH even on wrong flips (adversarial overconfidence)
D2_TOPM = 10            # D2 = majority speaker of the top-M plain-hybrid turns (independent second opinion)
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
    nb = (len(miss) + batch - 1) // batch
    for bi, i in enumerate(range(0, len(miss), batch)):
        chunk = miss[i:i+batch]
        for c, v in zip(chunk, _post({"model": "nomic-embed-text", "input": [c[:2000] for c in chunk]})):
            _cache[_key(c)] = v
        if (bi + 1) % flush_every == 0 or (bi + 1) == nb:
            json.dump(_cache, open(CACHE, "w")); print(f"  warmup {bi+1}/{nb} (t+{time.time()-_t0:.0f}s)", flush=True)
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
    ra = {i: r for r, i in enumerate(rank_a)}; rb = {i: r for r, i in enumerate(rank_b)}
    return sorted(ids, key=lambda i: -(1.0/(c+ra[i]) + w * 1.0/(c+rb[i])))
def hybrid_over(cand_ids, order_index, bm, tvec, qv, question):
    idxs = [order_index[i] for i in cand_ids]
    bm_s = bm.scores(question, idxs)
    bm_rank = sorted(cand_ids, key=lambda i: -bm_s[order_index[i]])
    vec_rank = sorted(cand_ids, key=lambda i: -cos(qv, tvec[i]))
    return rrf(bm_rank, vec_rank, list(cand_ids))

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

METHODS = ("hybrid", "soft_selfconf", "soft_orthogonal")
per_conv = {m: [] for m in METHODS}
harm = {m: [] for m in METHODS}          # D1 wrong-fire subset
d2_caught = 0                            # on harm subset: D2 disagreed with the wrong D1 (mechanism fired)
d2_total = 0
fire = flips = n_q = 0
t0 = time.time()
for ci, D0 in enumerate(D):
    conv = D0["conversation"]; sa = conv["speaker_a"]; sb = conv["speaker_b"]
    order, text, spk = [], {}, {}
    for sk in sorted([k for k in conv if re.fullmatch(r"session_\d+", k)], key=lambda s: int(s.split("_")[1])):
        for t in conv[sk]:
            order.append(t["dia_id"]); text[t["dia_id"]] = t["text"]; spk[t["dia_id"]] = t["speaker"]
    turnset = set(order); oidx = {i: j for j, i in enumerate(order)}; N = len(order)
    bm = BM25([text[i] for i in order]); tvec = {i: embed(text[i]) for i in order}
    qs = [q for q in D0["qa"] if str(q.get("category")) in ANSWERABLE and gold_of(q, turnset)]
    acc = {m: [] for m in METHODS}
    for q in qs:
        n_q += 1; g = set(gold_of(q, turnset)); ng = len(g); qv = embed(q["question"])
        rk = hybrid_over(order, oidx, bm, tvec, qv, q["question"])
        acc["hybrid"].append(len(g & set(rk[:K])) / ng)
        qn = q["question"].lower(); na = sa.lower() in qn; nb = sb.lower() in qn
        wrong_noisy = None
        if na ^ nb:
            fire += 1
            named_gold = sa if na else sb
            named_noisy = named_gold
            if rng.random() < P_NOISE:                      # D1 flips to the wrong speaker
                named_noisy = sb if named_gold == sa else sa; flips += 1
            wrong_noisy = not all(spk[gi] == named_noisy for gi in g)
            cand = [i for i in order if spk[i] == named_noisy]
            selectivity = 1.0 - (len(cand) / N if N else 0.0)
            prior = [i for i in rk if spk[i] == named_noisy] + [i for i in rk if spk[i] != named_noisy]
            # D2: independent second opinion = majority speaker among top-M plain-hybrid turns (no gold, no D1)
            top = rk[:D2_TOPM]
            cnt = collections.Counter(spk[i] for i in top)
            d2 = cnt.most_common(1)[0][0] if cnt else named_noisy
            agree = 1.0 if d2 == named_noisy else 0.0
            # FAIR SCALE (fix after method-audit 2026-07-02): both arms use the SAME base weight
            # (OVERCONF) when they TRUST the filter; the orthogonal arm differs ONLY by dropping the
            # weight to 0 when the independent D2 DISAGREES. Earlier the orthogonal arm used agree*sel
            # (0 or 1.0), which up-weighted HARDER than self-conf's 0.9 on the 81% of harm cases where
            # D1 and D2 both agreed-wrong -- a scale artifact that made orthogonal look worse than it is.
            rk_selfconf = weighted_rrf(rk, prior, order, OVERCONF * selectivity)
            rk_orth = weighted_rrf(rk, prior, order, (OVERCONF if agree == 1.0 else 0.0) * selectivity)
            if wrong_noisy:
                d2_total += 1; d2_caught += (agree == 0.0)   # D2 disagreed with the wrong D1
        else:
            rk_selfconf = rk_orth = rk
        acc["soft_selfconf"].append(len(g & set(rk_selfconf[:K])) / ng)
        acc["soft_orthogonal"].append(len(g & set(rk_orth[:K])) / ng)
        if wrong_noisy:
            harm["hybrid"].append(len(g & set(rk[:K])) / ng)
            harm["soft_selfconf"].append(len(g & set(rk_selfconf[:K])) / ng)
            harm["soft_orthogonal"].append(len(g & set(rk_orth[:K])) / ng)
    for m in METHODS: per_conv[m].append(sum(acc[m]) / len(acc[m]))
    print(f"  conv {ci}: {len(order)} turns, {len(qs)} Q (t+{time.time()-t0:.0f}s)", flush=True)
json.dump(_cache, open(CACHE, "w"))

def mean(x): return sum(x)/len(x) if x else float("nan")
def boot_ci(deltas, iters=10000, seed=17):
    rnd = random.Random(seed); n = len(deltas); s = []
    for _ in range(iters): s.append(mean([deltas[rnd.randrange(n)] for _ in range(n)]))
    s.sort(); return s[int(.025*iters)], s[int(.975*iters)]
base = per_conv["hybrid"]
print(f"\n=== LoCoMo orthogonal-signal vs self-confidence trust weight (recall@{K}, n_q={n_q}, 10 conv) ===")
print(f"D1 fired {fire}/{n_q}; flipped-wrong {flips}; harm subset (D1 wrong-fire) n={len(harm['hybrid'])}")
print(f"D2 (independent retrieval prior) DISAGREED with the wrong D1 on {d2_caught}/{d2_total} harm cases "
      f"({100*d2_caught//max(d2_total,1)}%) -- this is the ceiling on how much orthogonal weighting can help")
print(f"\n{'method':<20}{'recall@20':>10}{'delta':>10}{'conv wins':>11}")
for m in METHODS:
    r = mean(per_conv[m])
    if m == "hybrid": print(f"{m:<20}{r:>10.3f}{'--':>10}{'--':>11}")
    else:
        dlt = [per_conv[m][i]-base[i] for i in range(len(base))]; lo, hi = boot_ci(dlt)
        print(f"{m:<20}{r:>10.3f}{mean(dlt):>+10.3f}{sum(1 for d in dlt if d>0):>9}/10   CI[{lo:+.3f},{hi:+.3f}]")
print(f"\nHARM SUBSET (D1 fired on the WRONG speaker), recall@{K} -- baseline is no-filter hybrid on THIS subset:")
for m in METHODS:
    print(f"  {m:<20}{mean(harm[m]):.3f}   n={len(harm[m])}")
print("\nReading: self-conf weight uses D1's OWN (overconfident) 0.9 -> should stay high on the filter even")
print("when wrong -> harm. Orthogonal weight drops to 0 when the independent D2 disagrees -> should fall")
print("back toward the no-filter (hybrid) recall on the harm subset. The gap between the two, and D2's")
print("disagreement coverage above, tell you whether jacksonxly's orthogonal-signal swap actually pays.")
out = {"k": K, "n_q": n_q, "fire": fire, "flips": flips, "p_noise": P_NOISE, "overconf": OVERCONF,
       "d2_topm": D2_TOPM, "harm_n": len(harm["hybrid"]),
       "d2_disagree_on_harm": {"caught": d2_caught, "total": d2_total,
                                "rate": round(d2_caught/max(d2_total,1), 4)},
       "recall@20": {m: round(mean(per_conv[m]), 4) for m in METHODS},
       "harm_subset": {m: {"mean": round(mean(harm[m]), 4) if harm[m] else None, "n": len(harm[m])} for m in METHODS}}
json.dump(out, open("research/probes/locomo_orthogonal_trust_weight_result.json", "w"), indent=1)
print("\nsaved: research/probes/locomo_orthogonal_trust_weight_result.json")
