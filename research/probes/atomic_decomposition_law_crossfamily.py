"""Cross-family confirmation of the atomic-decomposition-law REFUTATION (owner: don't kill on one family;
test kimi + Claude before concluding). Same design as atomic_decomposition_calibration_law.py — arithmetic
sub-claims, balanced clean/1-error, HOLISTIC vs DECOMPOSED judge, per-K balanced accuracy, AMPLE tokens so
NO judge is token-starved (the confound that faked a 'CONFIRMED' on run 1). K in {1 (anchor), 4, 8}.

If delta(K) stays ~0 with ample tokens on kimi (different family) and Claude (independent anchor) too, the
refutation is robust: the decomposition 'advantage' is compute allocation (K calls = Kx tokens), not a
cognitive attention-ceiling. If a model shows delta>0 at ample tokens, the ceiling is REAL for that judge
and the law is REFINED (weaker/limited judges have a genuine tracking ceiling decomposition fixes), not
killed. Either way we learn honestly.

Backends: kimi-k2.6:cloud via the local Ollama cloud-route (chat/completions); claude-opus-4-8 via the
Anthropic messages API. Both AMPLE tokens + unparseable counters. temperature 0. MIT.
Run: python research/probes/atomic_decomposition_law_crossfamily.py"""
import os, re, json, time, random, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

random.seed(20260703)
KS = [1, 4, 8]
N_PER_K = 20                       # 10 clean + 10 dirty
_ENVP = os.path.join(os.path.dirname(__file__), "..", "..", "server", ".env")
_env = {}
for ln in open(_ENVP, encoding="utf-8"):
    m = re.match(r'\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$', ln)
    if m:
        _env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
_unparse = {}


def kimi_ask(prompt, mx):
    body = json.dumps({"model": "kimi-k2.6:cloud", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0}).encode()
    for i in range(5):
        try:
            req = urllib.request.Request("http://localhost:11434/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {_env.get('AGORA_REASONING_KEY', 'local')}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=180).read())
            return (r["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            if i < 4: time.sleep(2 * (i + 1)); continue
            raise
    return ""


def claude_ask(prompt, mx):
    # NOTE: claude-opus-4-8 REJECTS the `temperature` param ("deprecated for this model") -> 400. Omit it.
    body = json.dumps({"model": "claude-opus-4-8", "max_tokens": mx,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for i in range(5):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": _env["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            return "".join(b.get("text", "") for b in r.get("content", [])).strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < 4: time.sleep(5 * (i + 1)); continue
            raise
        except Exception:
            if i < 4: time.sleep(2 * (i + 1)); continue
            raise
    return ""


BACKENDS = {"kimi-k2.6": (kimi_ask, 3000, 1000), "claude-opus-4-8": (claude_ask, 1500, 500)}   # (fn, holistic_mx, sub_mx)


def yesno(txt):
    t = txt.strip().lower()
    m = re.findall(r"\b(yes|no)\b", t)
    if m: return m[-1] == "yes"
    if t.startswith("y"): return True
    if t.startswith("n"): return False
    return None


def make_stmt(rng):
    a, b = rng.randint(11, 99), rng.randint(11, 99); return a, b, a * b


def build_composite(K, dirty, rng):
    stmts = [make_stmt(rng) for _ in range(K)]
    err_idx = rng.randrange(K) if dirty else -1
    out = []
    for i, (a, b, c) in enumerate(stmts):
        shown = c + rng.choice([o for o in range(-40, 41) if o != 0]) if i == err_idx else c
        out.append((a, b, shown, i == err_idx))
    return out


def holistic_prompt(lines):
    body = "\n".join(f"{a} x {b} = {c}" for a, b, c, _ in lines)
    return ("Here are arithmetic statements. Verify each product. Are ALL of them correct?\n"
            f"{body}\n\nAnswer with exactly one word: YES (all correct) or NO (at least one is wrong).")


def sub_prompt(a, b, c):
    return f"Is this arithmetic statement correct? {a} x {b} = {c}\nAnswer with exactly one word: YES or NO."


def eval_backend(name):
    fn, hmx, smx = BACKENDS[name]
    rng = random.Random(hash(name) & 0xffff)
    tasks = []
    for K in KS:
        for j in range(N_PER_K):
            dirty = (j % 2 == 1)
            tasks.append((K, j, not dirty, build_composite(K, dirty, rng)))
    _unparse[name] = {"holistic": 0, "sub": 0}
    hol, dec = {}, {}
    def run_hol(t):
        K, j, clean, lines = t
        p = yesno(fn(holistic_prompt(lines), hmx))
        if p is None: _unparse[name]["holistic"] += 1
        return (K, j, clean, p)
    def run_dec(t):
        K, j, clean, lines = t
        preds = []
        for a, b, c, _ in lines:
            p = yesno(fn(sub_prompt(a, b, c), smx))
            if p is None: _unparse[name]["sub"] += 1
            preds.append(p)
        return (K, j, clean, all(p is True for p in preds))
    workers = 4 if name.startswith("claude") else 4
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(run_hol, t) for t in tasks]):
            K, j, clean, pred = f.result(); hol[(K, j)] = (clean, pred)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(run_dec, t) for t in tasks]):
            K, j, clean, pred = f.result(); dec[(K, j)] = (clean, pred)
    out = {}
    for K in KS:
        def bacc(store):
            pos = [store[(K, j)] for j in range(N_PER_K) if store[(K, j)][0]]
            neg = [store[(K, j)] for j in range(N_PER_K) if not store[(K, j)][0]]
            tpr = sum(1 for c, p in pos if p is True) / max(1, len(pos))
            tnr = sum(1 for c, p in neg if p is False) / max(1, len(neg))
            return 0.5 * (tpr + tnr), tnr
        ah, ch = bacc(hol); ad, cd = bacc(dec)
        out[K] = {"acc_holistic": round(ah, 3), "acc_decomposed": round(ad, 3), "delta": round(ad - ah, 3),
                  "errcatch_holistic": round(ch, 2), "errcatch_decomposed": round(cd, 2)}
    return out


results = {}
t0 = time.time()
for name in BACKENDS:
    print(f"\n=== {name} (ample tokens) ===", flush=True)
    try:
        results[name] = eval_backend(name)
    except Exception as e:
        print(f"  BACKEND FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True); continue
    for K in KS:
        r = results[name][K]
        print(f"  K={K}: holistic={r['acc_holistic']:.3f} decomposed={r['acc_decomposed']:.3f} "
              f"delta={r['delta']:+.3f} | err-catch hol={r['errcatch_holistic']:.2f} dec={r['errcatch_decomposed']:.2f}", flush=True)
    print(f"  unparseable: {_unparse[name]}  (t+{time.time()-t0:.0f}s)", flush=True)

print("\n=== CROSS-FAMILY LAW CHECK (ample tokens) ===")
verdicts = {}
for name in results:
    d1, d8 = results[name][KS[0]]["delta"], results[name][KS[-1]]["delta"]
    v = "delta stays ~0 -> REFUTATION HOLDS (compute, not ceiling)" if abs(d8) <= 0.10 else \
        f"delta(8)={d8:+.3f} -> REAL CEILING for this judge (law REFINED, not killed)"
    verdicts[name] = v
    print(f"{name}: delta(1)={d1:+.3f} delta(8)={d8:+.3f} -> {v}")

out = {"design": "cross-family confirmation, ample tokens", "ks": KS, "n_per_k": N_PER_K,
       "results": results, "unparseable": _unparse, "verdicts": verdicts}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "atomic_decomposition_law_crossfamily_result.json"),
                    "w"), indent=1)
print("\nsaved: research/probes/atomic_decomposition_law_crossfamily_result.json")
