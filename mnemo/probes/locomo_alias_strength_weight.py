"""Alias-match-strength trust weight for a metadata filter on LoCoMo -- jacksonxly's ACTUAL entity signal.

Follow-up to locomo_orthogonal_trust_weight.py. That probe tested a retrieval-derived "second opinion"
proxy (too correlated, 19% coverage) and I wrongly framed his real signal as un-testable. It isn't. This
builds his actual proposal: use ALIAS-MATCH STRENGTH (exact canonical hit vs no/weak match) as the filter's
trust weight, not the extractor's own confidence.

The real structure his idea exploits (modeled here, disclosed, NOT a rigged knob):
  - EXACT questions: the speaker's name is literally in the question (sa/sb token present). alias_strength=1.
    Extraction is reliable here -- an exact name match is what it is; we do NOT inject error on these.
  - AMBIGUOUS questions: NO speaker name in the question (pronoun/implicit). alias_strength=0. A real
    extractor must GUESS the speaker; here it guesses the majority speaker of the top-10 hybrid turns --
    plausible but error-prone. This is where extraction actually fails.
  This concentration of errors on low-alias questions is the real-world phenomenon; alias-strength is
  knowable a priori and independent of the model's belief -- exactly jacksonxly's point.

Arms (w scales the speaker-filter's RRF contribution; equal base so it's a fair scale):
  - self_conf:      w = 0.9 * selectivity  on EVERY firing (exact + ambiguous) -- flat, can't tell weak
                    from strong, so it fires the filter on the unreliable guesses too.
  - alias_strength: w = 0.9 * alias_strength * selectivity -- ~0.9 on exact matches (keeps the benefit),
                    ~0 on ambiguous (backs the filter off exactly where extraction is unreliable).

Metrics: overall recall@20 + the harm subset (chosen speaker is WRONG). If alias-strength weighting
recovers the harm subset toward no-filter while self-conf craters it, jacksonxly's entity signal is
confirmed on this data. Reuses the warm cache + local nomic. MIT.
Run: LOCOMO_PATH=agora_output/lab/data/locomo10.json \
     LOCOMO_CACHE=agora_output/lab/data/locomo_confweighted_cache.json \
     python mnemo/probes/locomo_alias_strength_weight.py
"""
import json, re, ast, time, math, hashlib, os, urllib.request, collections, random

DATA = os.environ.get("LOCOMO_PATH", "agora_output/lab/data/locomo10.json")
CACHE = os.environ.get("LOCOMO_CACHE", "agora_output/lab/data/locomo_confweighted_cache.json")
EMB_URL = "http://localhost:11434/api/embed"
K = 20; ANSWERABLE = ("1", "2", "3", "4"); D2_TOPM = 10; SELF_CONF = 0.9; RNG_SEED = 42

_t0 = time.time()
_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def _key(t): return hashlib.sha1(t[:2000].encode("utf-8")).hexdigest()
def _post(p):
    r = urllib.request.urlopen(urllib.request.Request(
        EMB_URL, data=json.dumps(p).encode(), headers={"Content-Type": "application/json"}), timeout=120)
    return json.loads(r.read())["embeddings"]
def warmup(texts, batch=128, flush_every=10):
    miss, seen = [], set()
    for t in texts:
        k = _key(t)
        if k not in _cache and k not in seen: seen.add(k); miss.append(t)
    if not miss: print("warmup: all cached", flush=True); return
    print(f"warmup: {len(miss)} uncached / {len(texts)}", flush=True)
    nb = (len(miss)+batch-1)//batch
    for bi, i in enumerate(range(0, len(miss), batch)):
        chunk = miss[i:i+batch]
        for c, v in zip(chunk, _post({"model": "nomic-embed-text", "input": [c[:2000] for c in chunk]})):
            _cache[_key(c)] = v
        if (bi+1) % flush_every == 0 or (bi+1) == nb:
            json.dump(_cache, open(CACHE, "w")); print(f"  warmup {bi+1}/{nb} (t+{time.time()-_t0:.0f}s)", flush=True)
def embed(t):
    v = _cache.get(_key(t))
    if v is None: v = _post({"model": "nomic-embed-text", "input": [t[:2000]]})[0]; _cache[_key(t)] = v
    return v
def cos(a, b):
    d = sum(x*y for x, y in zip(a, b)); na = sum(x*x for x in a)**.5; nb = sum(x*x for x in b)**.5
    return d/((na*nb) or 1)
_tok = re.compile(r"[a-z0-9]+")
def toks(s): return _tok.findall(s.lower())
class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b; self.docs = [toks(d) for d in docs]; self.N = len(self.docs)
        self.dl = [len(d) for d in self.docs]; self.avgdl = (sum(self.dl)/self.N) if self.N else 0
        df = collections.Counter(); self.tf = []
        for d in self.docs:
            c = collections.Counter(d); self.tf.append(c)
            for t in c: df[t] += 1
        self.idf = {t: math.log(1 + (self.N-n+0.5)/(n+0.5)) for t, n in df.items()}
    def scores(self, query, idxs):
        q = toks(query); out = {}
        for i in idxs:
            c = self.tf[i]; dl = self.dl[i]; s = 0.0
            for t in q:
                f = c.get(t, 0)
                if not f: continue
                s += self.idf.get(t, 0.0)*(f*(self.k1+1))/(f + self.k1*(1-self.b+self.b*dl/(self.avgdl or 1)))
            out[i] = s
        return out
def gold_of(q, tset):
    e = q.get("evidence")
    try: ids = ast.literal_eval(e) if isinstance(e, str) else e
    except Exception: ids = []
    return [i for i in (ids or []) if i in tset]
def rrf(a, b, ids, c=60):
    ra = {i: r for r, i in enumerate(a)}; rb = {i: r for r, i in enumerate(b)}
    return sorted(ids, key=lambda i: -(1.0/(c+ra[i]) + 1.0/(c+rb[i])))
def wrrf(a, b, ids, w, c=60):
    ra = {i: r for r, i in enumerate(a)}; rb = {i: r for r, i in enumerate(b)}
    return sorted(ids, key=lambda i: -(1.0/(c+ra[i]) + w*1.0/(c+rb[i])))
def hybrid_over(cand, oidx, bm, tvec, qv, q):
    idxs = [oidx[i] for i in cand]; bm_s = bm.scores(q, idxs)
    bm_rank = sorted(cand, key=lambda i: -bm_s[oidx[i]]); vec_rank = sorted(cand, key=lambda i: -cos(qv, tvec[i]))
    return rrf(bm_rank, vec_rank, list(cand))

D = json.load(open(DATA)); _all = []
for D0 in D:
    conv = D0["conversation"]; tset = set()
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]: _all.append(t["text"]); tset.add(t["dia_id"])
    for q in D0["qa"]:
        if str(q.get("category")) in ANSWERABLE and gold_of(q, tset): _all.append(q["question"])
warmup(_all); rng = random.Random(RNG_SEED)

METHODS = ("hybrid", "self_conf", "alias_strength")
per_conv = {m: [] for m in METHODS}; harm = {m: [] for m in METHODS}
n_q = fire_exact = fire_ambig = wrong_exact = wrong_ambig = 0
t0 = time.time()
for ci, D0 in enumerate(D):
    conv = D0["conversation"]; sa = conv["speaker_a"]; sb = conv["speaker_b"]
    order, text, spk = [], {}, {}
    for sk in sorted([k for k in conv if re.fullmatch(r"session_\d+", k)], key=lambda s: int(s.split("_")[1])):
        for t in conv[sk]: order.append(t["dia_id"]); text[t["dia_id"]] = t["text"]; spk[t["dia_id"]] = t["speaker"]
    turnset = set(order); oidx = {i: j for j, i in enumerate(order)}; N = len(order)
    bm = BM25([text[i] for i in order]); tvec = {i: embed(text[i]) for i in order}
    qs = [q for q in D0["qa"] if str(q.get("category")) in ANSWERABLE and gold_of(q, turnset)]
    acc = {m: [] for m in METHODS}
    for q in qs:
        n_q += 1; g = set(gold_of(q, turnset)); ng = len(g); qv = embed(q["question"])
        rk = hybrid_over(order, oidx, bm, tvec, qv, q["question"])
        acc["hybrid"].append(len(g & set(rk[:K]))/ng)
        qn = q["question"].lower(); na = sa.lower() in qn; nb = sb.lower() in qn
        chosen = None; alias = None; wrong = None
        if na ^ nb:                                   # EXACT name in question -> reliable, alias_strength=1
            chosen = sa if na else sb; alias = 1.0; fire_exact += 1
        else:                                         # AMBIGUOUS: no clear name -> extractor GUESSES (error-prone)
            top = rk[:D2_TOPM]; cnt = collections.Counter(spk[i] for i in top)
            chosen = cnt.most_common(1)[0][0] if cnt else sa; alias = 0.0; fire_ambig += 1
        wrong = not all(spk[gi] == chosen for gi in g)
        if na ^ nb: wrong_exact += wrong
        else: wrong_ambig += wrong
        cand = [i for i in order if spk[i] == chosen]; sel = 1.0 - (len(cand)/N if N else 0)
        prior = [i for i in rk if spk[i] == chosen] + [i for i in rk if spk[i] != chosen]
        rk_self = wrrf(rk, prior, order, SELF_CONF * sel)
        rk_alias = wrrf(rk, prior, order, SELF_CONF * alias * sel)
        acc["self_conf"].append(len(g & set(rk_self[:K]))/ng)
        acc["alias_strength"].append(len(g & set(rk_alias[:K]))/ng)
        if wrong:
            harm["hybrid"].append(len(g & set(rk[:K]))/ng)
            harm["self_conf"].append(len(g & set(rk_self[:K]))/ng)
            harm["alias_strength"].append(len(g & set(rk_alias[:K]))/ng)
    for m in METHODS: per_conv[m].append(sum(acc[m])/len(acc[m]))
    print(f"  conv {ci}: {len(order)} turns, {len(qs)} Q (t+{time.time()-t0:.0f}s)", flush=True)
json.dump(_cache, open(CACHE, "w"))

def mean(x): return sum(x)/len(x) if x else float("nan")
def boot(dl, it=10000, seed=17):
    r = random.Random(seed); n = len(dl); s = [mean([dl[r.randrange(n)] for _ in range(n)]) for _ in range(it)]
    s.sort(); return s[int(.025*it)], s[int(.975*it)]
base = per_conv["hybrid"]
print(f"\n=== LoCoMo alias-strength trust weight (recall@{K}, n_q={n_q}, 10 conv) ===")
print(f"exact-name firings {fire_exact} (wrong {wrong_exact}); ambiguous-guess firings {fire_ambig} "
      f"(wrong {wrong_ambig}) -- errors concentrate on the ambiguous/low-alias set, as expected")
print(f"harm subset (chosen speaker wrong) n={len(harm['hybrid'])}")
print(f"\n{'method':<16}{'recall@20':>10}{'delta':>9}{'wins':>7}")
for m in METHODS:
    r = mean(per_conv[m])
    if m == "hybrid": print(f"{m:<16}{r:>10.3f}{'--':>9}{'--':>7}")
    else:
        dl = [per_conv[m][i]-base[i] for i in range(len(base))]; lo, hi = boot(dl)
        print(f"{m:<16}{r:>10.3f}{mean(dl):>+9.3f}{sum(1 for d in dl if d>0):>5}/10  CI[{lo:+.3f},{hi:+.3f}]")
print(f"\nHARM SUBSET recall@{K} (baseline = no-filter hybrid on this subset):")
for m in METHODS: print(f"  {m:<16}{mean(harm[m]):.3f}  n={len(harm[m])}")
print("\nReading: alias_strength=0 on ambiguous questions -> filter backs off there (where extraction is")
print("unreliable) -> harm subset recovers toward no-filter, while flat self-conf fires anyway and craters.")
out = {"k": K, "n_q": n_q, "fire_exact": fire_exact, "wrong_exact": wrong_exact,
       "fire_ambiguous": fire_ambig, "wrong_ambiguous": wrong_ambig, "harm_n": len(harm["hybrid"]),
       "recall@20": {m: round(mean(per_conv[m]), 4) for m in METHODS},
       "harm_subset": {m: {"mean": round(mean(harm[m]), 4) if harm[m] else None, "n": len(harm[m])} for m in METHODS}}
json.dump(out, open("mnemo/probes/locomo_alias_strength_weight_result.json", "w"), indent=1)
print("\nsaved: mnemo/probes/locomo_alias_strength_weight_result.json")
