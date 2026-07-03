"""Severe-test: the ATOMIC-DECOMPOSITION CALIBRATION LAW.

Hypothesis (from arXiv:2606.27226 Ask-Don't-Judge + 2607.01223 Theoria + 2606.28277): a judge that
DECOMPOSES a composite claim into independent binary sub-checks beats a HOLISTIC one-shot judge by a margin
that GROWS with the number of independently-falsifiable sub-claims K, and VANISHES at K=1 (where the two are
the same task). The mechanism is a fixed holistic "attention/tracking budget" diluted across K items vs
per-item full attention.

DESIGN (ground-truthable, non-rigged):
  - sub-claim = an arithmetic fact "a x b = c" (a,b in [11,99]); TRUE if c is the real product, else c is the
    product +/- a plausible small offset. These need real verification (not knowledge recall) and tracking
    many at once genuinely taxes a holistic judge.
  - composite at level K = K such statements. Balanced 50/50: half CLEAN (all correct), half DIRTY (exactly
    ONE planted error — the hardest case, one needle among K). Balance keeps the base rate 50% at every K, so
    accuracy is not inflated by skew.
  - HOLISTIC judge: one call, "are ALL correct? YES=all correct / NO=at least one wrong."
  - DECOMPOSED judge: K calls, "is THIS one correct? YES/NO"; composite predicted clean iff every sub-check
    says YES.
  - metric: balanced classification accuracy of clean-vs-dirty, per judge, as a function of K.
  - LAW prediction: delta(K) = acc_decomposed - acc_holistic grows with K, and delta(1) ~ 0.
  - FALSIFIERS (any -> the law as stated fails): delta flat in K; delta(1) already large (the decomposition
    itself, not the K-scaling, does the work -> rigged); holistic does NOT degrade with K.

Real cloud judges (deepseek-v4-flash cheap tier, deepseek-v4-pro stronger), temperature 0, parallel with
429 backoff. Reads the API key from server/.env. MIT.
Run: python mnemo/probes/atomic_decomposition_calibration_law.py

OUTCOME (2026-07-03): REFUTED — the law was a TOKEN-BUDGET CONFOUND.
  Run 1 (holistic cap 250 tokens) LOOKED like a dramatic confirmation: delta grew to +0.73 (flash) / +1.00
  (pro) at K=8, with the K=1 anchor at 0. But decomposition makes K separate calls = K x the token budget,
  while the holistic judge got ONE tightly-capped call. A truncation smell (pro returned EMPTY at K=8, cap
  250) exposed it. Run 2 (holistic cap 2000 tokens, ample; unparseable=0): delta = 0.000 at EVERY K for BOTH
  models — holistic verifies K independent facts perfectly, no degradation. So the apparent
  "decomposition advantage grows with K" is COMPUTE ALLOCATION, not a cognitive attention-ceiling; at matched
  token budget it vanishes. The severe-test (K=1 anchor + a token-fairness control) killed a false positive
  that run 1 auto-labelled CONFIRMED.
  HONEST SCOPE: this refutes the law only for INDEPENDENT, cleanly-verifiable sub-claims (arithmetic). The
  literature's harder claim (Theoria 2607.01223 / Ask-Don't-Judge 2606.27226 on SUBTLE, ENTANGLED reasoning
  errors and hidden premises, where holistic may fail even at matched compute) is NOT tested here and remains
  open. The lesson for our own audit gate (roadmap A1): a decomposed judge is not free magic — control for
  the judge's token budget before crediting decomposition; on clean independent checks it buys nothing a
  well-resourced holistic pass doesn't."""
import os, re, json, time, random, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

random.seed(20260703)
KS = [1, 2, 4, 8]
N_PER_K = 30                       # 15 clean + 15 dirty per K
MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]
_ENVP = os.path.join(os.path.dirname(__file__), "..", "..", "server", ".env")
_env = {}
for ln in open(_ENVP, encoding="utf-8"):
    m = re.match(r'\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$', ln)
    if m:
        _env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
BASE = _env["AGORA_API_BASE_URL"].rstrip("/")
KEY = _env["AGORA_API_KEY"]


_unparse = {"holistic": 0, "sub": 0}


def ask(model, prompt, mx=2000, tries=5):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                         headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            return (r["choices"][0]["message"]["content"] or "").strip()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(2 * (i + 1) + random.random()); continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(1.5 * (i + 1)); continue
            raise
    return ""


def yesno(txt):
    """Parse a YES/NO (all-correct?) answer -> True=clean/all-correct, False=has-error, None=unparseable."""
    t = txt.strip().lower()
    # last explicit yes/no token wins (models sometimes reason then answer)
    m = re.findall(r"\b(yes|no)\b", t)
    if m:
        return m[-1] == "yes"
    if t.startswith("y"):
        return True
    if t.startswith("n"):
        return False
    return None


def make_stmt(rng):
    a, b = rng.randint(11, 99), rng.randint(11, 99)
    return a, b, a * b


def build_composite(K, dirty, rng):
    stmts = [make_stmt(rng) for _ in range(K)]
    err_idx = rng.randrange(K) if dirty else -1
    lines = []
    for i, (a, b, c) in enumerate(stmts):
        shown = c
        if i == err_idx:
            off = rng.choice([o for o in range(-40, 41) if o not in (0,)])
            shown = c + off
        lines.append((a, b, shown, i == err_idx))
    return lines  # list of (a,b,shown_c,is_error)


def holistic_prompt(lines):
    body = "\n".join(f"{a} x {b} = {c}" for a, b, c, _ in lines)
    return ("Here are arithmetic statements. Verify each product. Are ALL of them correct?\n"
            f"{body}\n\nAnswer with exactly one word: YES (all correct) or NO (at least one is wrong).")


def sub_prompt(a, b, c):
    return f"Is this arithmetic statement correct? {a} x {b} = {c}\nAnswer with exactly one word: YES or NO."


def eval_model(model):
    # build the dataset: for each K, N_PER_K composites, balanced clean/dirty
    rng = random.Random(hash(model) & 0xffff)
    tasks = []  # (K, comp_idx, clean_truth(bool), lines)
    for K in KS:
        for j in range(N_PER_K):
            dirty = (j % 2 == 1)
            lines = build_composite(K, dirty, rng)
            tasks.append((K, j, not dirty, lines))  # clean_truth = not dirty
    # HOLISTIC: one call per composite
    hol = {}
    def run_hol(t):
        K, j, clean, lines = t
        ans = ask(model, holistic_prompt(lines), mx=2000)   # ample tokens: NOT token-starved
        p = yesno(ans)
        if p is None:
            _unparse["holistic"] += 1
        return (K, j, clean, p)
    # DECOMPOSED: K calls per composite -> predict clean iff all sub-checks say YES
    dec = {}
    def run_dec(t):
        K, j, clean, lines = t
        preds = []
        for a, b, c, _ in lines:
            p = yesno(ask(model, sub_prompt(a, b, c), mx=800))
            if p is None:
                _unparse["sub"] += 1
            preds.append(p)
        pred_clean = all(p is True for p in preds)   # any not-True (incl None) -> dirty
        return (K, j, clean, pred_clean)
    with ThreadPoolExecutor(max_workers=6) as ex:
        for f in as_completed([ex.submit(run_hol, t) for t in tasks]):
            K, j, clean, pred = f.result(); hol[(K, j)] = (clean, pred)
    with ThreadPoolExecutor(max_workers=6) as ex:
        for f in as_completed([ex.submit(run_dec, t) for t in tasks]):
            K, j, clean, pred = f.result(); dec[(K, j)] = (clean, pred)
    # balanced accuracy per K
    out = {}
    for K in KS:
        def bacc(store):
            pos = [store[(K, j)] for j in range(N_PER_K) if store[(K, j)][0]]      # clean
            neg = [store[(K, j)] for j in range(N_PER_K) if not store[(K, j)][0]]  # dirty
            tpr = sum(1 for c, p in pos if p is True) / max(1, len(pos))            # clean called clean
            tnr = sum(1 for c, p in neg if p is False) / max(1, len(neg))           # dirty called dirty
            return 0.5 * (tpr + tnr), tnr   # balanced acc, and dirty-catch (error recall)
        ah, catch_h = bacc(hol); ad, catch_d = bacc(dec)
        out[K] = {"acc_holistic": round(ah, 3), "acc_decomposed": round(ad, 3),
                  "delta": round(ad - ah, 3), "errcatch_holistic": round(catch_h, 3),
                  "errcatch_decomposed": round(catch_d, 3)}
    return out


results = {}
t0 = time.time()
for model in MODELS:
    _unparse["holistic"] = 0; _unparse["sub"] = 0
    print(f"\n=== {model} ===", flush=True)
    results[model] = eval_model(model)
    results[model]["_unparseable"] = dict(_unparse)
    print(f"  unparseable (should be ~0 with ample tokens): holistic={_unparse['holistic']} sub={_unparse['sub']}", flush=True)
    for K in KS:
        r = results[model][K]
        print(f"  K={K}: holistic={r['acc_holistic']:.3f} decomposed={r['acc_decomposed']:.3f} "
              f"delta={r['delta']:+.3f} | error-catch hol={r['errcatch_holistic']:.2f} dec={r['errcatch_decomposed']:.2f}",
              flush=True)
    print(f"  (t+{time.time()-t0:.0f}s)", flush=True)

# ── verdict: does delta grow with K and vanish at K=1? ──
print("\n=== LAW CHECK ===")
verdicts = {}
for model in MODELS:
    d1 = results[model][KS[0]]["delta"]
    dmax = results[model][KS[-1]]["delta"]
    deltas = [results[model][K]["delta"] for K in KS]
    grows = dmax > d1 + 0.10 and dmax >= max(deltas) - 1e-9
    anchored = abs(d1) <= 0.10
    v = ("CONFIRMED" if (grows and anchored) else
         "REFUTED (delta(1) large -> decomposition not K-scaling)" if not anchored and dmax > 0.1 else
         "REFUTED (no K-scaling)")
    verdicts[model] = v
    print(f"{model}: delta(K={KS[0]})={d1:+.3f}  delta(K={KS[-1]})={dmax:+.3f}  deltas={deltas}  -> {v}")

out = {"design": "arithmetic sub-claims, balanced clean/1-error, holistic vs decomposed, per-K balanced acc",
       "ks": KS, "n_per_k": N_PER_K, "results": results, "verdicts": verdicts}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "atomic_decomposition_calibration_law_result.json"),
                    "w"), indent=1)
print("\nsaved: mnemo/probes/atomic_decomposition_calibration_law_result.json")
