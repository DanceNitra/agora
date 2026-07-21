"""M1 severe-test: does an EMBEDDING-NORM re-ranking term improve recall over pure cosine?

Motivation: arXiv:2606.30625 claims contrastive training imprints concept SPECIFICITY into the vector
NORM that cosine normalizes away. inspeximus keeps raw vectors, so if true it's a free re-ranking signal.

PRECHECK (run separately): nomic-embed-text is NOT unit-normalized (norm 18.9-23.3, CV ~7.8%) — so there
IS a norm signal. BUT the norms are confounded with LENGTH (short/generic text -> higher norm, long/specific
-> lower norm, a mean-pooling artifact), so a "norm re-ranker" may just be a length prior, not specificity.

SEVERE TEST (this file), on the REAL LoCoMo benchmark, no hand-built corpus, strong baseline (cosine over
real nomic), and an HONEST protocol that cannot cherry-pick:
  - score_beta(q,d) = cosine(q,d) * |d|^beta   (beta=0 -> pure cosine; beta<0 up-weights low-norm/specific
    docs; beta>0 up-weights high-norm/generic docs). |q| is constant per query so it never affects ranking.
  - Split conversations into DEV (odd index) and TEST (even index). TUNE beta on DEV only (max mean
    recall@K), then evaluate the DEV-chosen beta on TEST, next to the cosine baseline on TEST. Bootstrap CI
    on the per-query recall delta (TEST). A win requires the CI to exclude 0 on HELD-OUT data.
  - CONFOUND CHECK: report corr(|d|, token_length). If the winning beta's benefit is explained by a pure
    length prior (rank by 1/length), we say so — it's a length re-ranker, not a specificity one.
Metric recall@K, pure VECTOR (semantic) recall — the norm is a vector property; hybrid lexical would muddy
it. Reuses the warm LoCoMo embed cache + local nomic. MIT.
Run: LOCOMO_PATH=agora_output/lab/data/locomo10.json \
     LOCOMO_CACHE=agora_output/lab/data/locomo_confweighted_cache.json \
     python research/probes/norm_specificity_reranker.py"""
import json, os, re, ast, time, hashlib, urllib.request, random, math, sys

DATA = os.environ.get("LOCOMO_PATH", "agora_output/lab/data/locomo10.json")
CACHE = os.environ.get("LOCOMO_CACHE", "agora_output/lab/data/locomo_confweighted_cache.json")
EMB_URL = "http://localhost:11434/api/embed"
K = 10
ANS = ("1", "2", "3", "4")
BETAS = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
# normalized-vector cache (from /api/embed) -> gives CORRECT cosine (cosine is norm-invariant).
_cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
_dirty = 0
# SEPARATE raw-NORM cache (own file, incremental flush) -> the raw |d| that /api/embeddings preserves and
# /api/embed strips. We store only the scalar norm per text (not the full raw vector).
RAWCACHE = "research/probes/_norm_reranker_rawnorms.json"
EMB_RAW = "http://localhost:11434/api/embeddings"
_rawnorm = json.load(open(RAWCACHE)) if os.path.exists(RAWCACHE) else {}
_raw_since_flush = 0


def _key(t): return hashlib.sha1(t[:2000].encode("utf-8")).hexdigest()


def _post_batch(texts):
    r = urllib.request.urlopen(urllib.request.Request(
        EMB_URL, data=json.dumps({"model": "nomic-embed-text", "input": [t[:2000] for t in texts]}).encode(),
        headers={"Content-Type": "application/json"}), timeout=120)
    return json.loads(r.read())["embeddings"]


def embed(t):
    global _dirty
    k = _key(t)
    v = _cache.get(k)
    if v is None:
        v = _post_batch([t])[0]
        _cache[k] = v
        _dirty += 1
    return v


def raw_norm(t):
    """Raw (un-normalized) embedding norm via /api/embeddings, cached by text key; own file, flushed
    every 200 to survive interruption without O(n^2) rewrites (probe-cache lesson)."""
    global _raw_since_flush
    k = _key(t)
    n = _rawnorm.get(k)
    if n is None:
        r = urllib.request.urlopen(urllib.request.Request(
            EMB_RAW, data=json.dumps({"model": "nomic-embed-text", "prompt": t[:2000]}).encode(),
            headers={"Content-Type": "application/json"}), timeout=60)
        v = json.loads(r.read())["embedding"]
        n = math.sqrt(sum(x * x for x in v))
        _rawnorm[k] = n
        _raw_since_flush += 1
        if _raw_since_flush >= 200:
            json.dump(_rawnorm, open(RAWCACHE, "w")); _raw_since_flush = 0
    return n


def warmup(texts, batch=128):
    miss, seen = [], set()
    for t in texts:
        k = _key(t)
        if k not in _cache and k not in seen:
            seen.add(k); miss.append(t)
    if not miss:
        print("warmup: all cached", flush=True); return
    print(f"warmup: {len(miss)} uncached", flush=True)
    for i in range(0, len(miss), batch):
        ch = miss[i:i + batch]
        for c, v in zip(ch, _post_batch(ch)):
            _cache[_key(c)] = v
    json.dump(_cache, open(CACHE, "w"))


def gold_of(q, tset):
    e = q.get("evidence")
    try:
        ids = ast.literal_eval(e) if isinstance(e, str) else e
    except Exception:
        ids = []
    return [i for i in (ids or []) if i in tset]


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


D = json.load(open(DATA))
_all = []
for d0 in D:
    conv = d0["conversation"]; tset = set()
    for sk in [k for k in conv if re.fullmatch(r"session_\d+", k)]:
        for t in conv[sk]:
            _all.append(t["text"]); tset.add(t["dia_id"])
    for q in d0["qa"]:
        if str(q.get("category")) in ANS and gold_of(q, tset):
            _all.append(q["question"])
warmup(_all)

# per-query records: (conv_idx, gold set, cos_scores{did:cos}, norm{did:|d|}), plus length corr data
dev_recall = {b: [] for b in BETAS}
test_recall = {b: [] for b in BETAS}
dev_len = {b: [] for b in BETAS}     # CONTROL: pure length prior score = cosine * (token_len)^b
test_len = {b: [] for b in BETAS}
len_pairs = []   # (|d|, token_len)
n_q = 0
_t0 = time.time()
for ci, d0 in enumerate(D):
    conv = d0["conversation"]
    turns = []
    for sk in sorted([k for k in conv if re.fullmatch(r"session_\d+", k)], key=lambda s: int(s.split("_")[1])):
        for t in conv[sk]:
            turns.append((t["dia_id"], t["text"]))
    if not turns:
        continue
    vecs = {did: embed(txt) for did, txt in turns}                 # unit-normalized -> correct cosine
    rawn = {did: raw_norm(txt) for did, txt in turns}              # RAW norm (the M1 signal)
    tlen = {did: max(1, len(txt.split())) for did, txt in turns}   # token length (confound control)
    for did, txt in turns:
        len_pairs.append((rawn[did], tlen[did]))
    turnset = set(vecs)
    qs = [q for q in d0["qa"] if str(q.get("category")) in ANS and gold_of(q, turnset)]
    is_test = ci % 2 == 0
    bucket = test_recall if is_test else dev_recall
    lbucket = test_len if is_test else dev_len
    for q in qs:
        n_q += 1
        qv = embed(q["question"])                                  # unit vector; |q| constant per query
        g = set(gold_of(q, turnset)); ng = len(g)
        cos = {did: dot(qv, vecs[did]) for did in turnset}         # both unit-norm -> dot == cosine
        for b in BETAS:
            r_norm = sorted(turnset, key=lambda did: -(cos[did] * (rawn[did] ** b)))[:K]
            bucket[b].append(len(g & set(r_norm)) / ng)
            r_len = sorted(turnset, key=lambda did: -(cos[did] * (tlen[did] ** b)))[:K]
            lbucket[b].append(len(g & set(r_len)) / ng)
    print(f"  conv {ci} ({'TEST' if ci % 2 == 0 else 'DEV'}): {len(qs)} q (t+{time.time()-_t0:.0f}s)", flush=True)
if _dirty:
    json.dump(_cache, open(CACHE, "w"))
json.dump(_rawnorm, open(RAWCACHE, "w"))   # final flush of raw-norm cache


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def boot(dl, it=10000, seed=17):
    r = random.Random(seed); n = len(dl)
    if not n:
        return float("nan"), float("nan")
    s = sorted(mean([dl[r.randrange(n)] for _ in range(n)]) for _ in range(it))
    return s[int(.025 * it)], s[int(.975 * it)]


# length confound
mn = mean([p[0] for p in len_pairs]); ml = mean([p[1] for p in len_pairs])
cov = mean([(p[0] - mn) * (p[1] - ml) for p in len_pairs])
sn = math.sqrt(mean([(p[0] - mn) ** 2 for p in len_pairs]))
sl = math.sqrt(mean([(p[1] - ml) ** 2 for p in len_pairs]))
corr_norm_len = cov / (sn * sl + 1e-12)

print(f"\n=== M1 embedding-norm re-ranker on LoCoMo (recall@{K}, pure vector) ===")
print(f"queries: {n_q} | turns: {len(len_pairs)} | corr(|d|, token_len) = {corr_norm_len:+.3f}")
print("\nDEV recall@K by beta (tuning set):")
for b in BETAS:
    print(f"  beta={b:+.2f}  {mean(dev_recall[b]):.4f}")
best_beta = max([b for b in BETAS if b != 0.0], key=lambda b: mean(dev_recall[b]))
print(f"\nDEV-chosen best beta (excl 0) = {best_beta:+.2f}")

best_len_beta = max([b for b in BETAS if b != 0.0], key=lambda b: mean(dev_len[b]))
cos_test = mean(test_recall[0.0])
best_test = mean(test_recall[best_beta])
len_test = mean(test_len[best_len_beta])
dl = [test_recall[best_beta][i] - test_recall[0.0][i] for i in range(len(test_recall[0.0]))]
lo, hi = boot(dl)
# norm vs length control (both dev-tuned, evaluated on the same held-out queries)
dnl = [test_recall[best_beta][i] - test_len[best_len_beta][i] for i in range(len(test_recall[0.0]))]
lo2, hi2 = boot(dnl)
print(f"\nHELD-OUT TEST:")
print(f"  cosine (beta=0)                 recall@{K} = {cos_test:.4f}")
print(f"  NORM re-rank  (beta={best_beta:+.2f})       recall@{K} = {best_test:.4f}  (delta vs cos {mean(dl):+.4f} CI[{lo:+.4f},{hi:+.4f}])")
print(f"  LENGTH re-rank (beta={best_len_beta:+.2f}, control) recall@{K} = {len_test:.4f}")
print(f"  NORM - LENGTH = {mean(dnl):+.4f}  CI95 [{lo2:+.4f}, {hi2:+.4f}]")

out = {"metric": f"recall@{K}", "queries": n_q, "corr_norm_len": round(corr_norm_len, 3),
       "dev_recall": {str(b): round(mean(dev_recall[b]), 4) for b in BETAS},
       "dev_len": {str(b): round(mean(dev_len[b]), 4) for b in BETAS},
       "best_beta": best_beta, "best_len_beta": best_len_beta,
       "test_cosine": round(cos_test, 4), "test_norm": round(best_test, 4), "test_length": round(len_test, 4),
       "test_norm_vs_cos": [round(mean(dl), 4), round(lo, 4), round(hi, 4)],
       "test_norm_vs_length": [round(mean(dnl), 4), round(lo2, 4), round(hi2, 4)]}
if lo <= 0:
    verdict = (f"REFUTED - norm does not beat cosine on held-out data ({mean(dl):+.4f}, CI crosses/below 0).")
elif lo2 > 0:
    verdict = (f"CONFIRMED (specificity beyond length) - norm beats cosine (+{mean(dl):.4f}) AND beats the "
               f"pure length control (+{mean(dnl):.4f}, CI excludes 0), so the raw norm carries a re-ranking "
               f"signal NOT reducible to token length. corr(|d|,len)={corr_norm_len:+.2f}.")
elif hi2 < 0:
    verdict = (f"REFRAME - norm beats cosine (+{mean(dl):.4f}) but LENGTH beats norm ({mean(dnl):+.4f}, CI "
               f"below 0): the gain is a LENGTH prior and length is the better feature. Ship length, not norm.")
else:
    verdict = (f"REFRAME (length-equivalent) - norm beats cosine (+{mean(dl):.4f}) but is statistically "
               f"INDISTINGUISHABLE from a pure length prior (norm-length {mean(dnl):+.4f}, CI crosses 0; "
               f"corr(|d|,len)={corr_norm_len:+.2f}). The 'norm re-ranker' IS a length prior on this data; "
               f"no evidence of a specificity signal beyond length. A length re-rank is the honest, simpler feature.")
out["verdict"] = verdict
print(f"\nVERDICT: {verdict}")
json.dump(out, open("research/probes/norm_specificity_reranker_result.json", "w"), indent=1)
print("saved: research/probes/norm_specificity_reranker_result.json")
