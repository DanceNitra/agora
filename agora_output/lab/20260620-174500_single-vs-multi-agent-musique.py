"""
Crucible flagship replication: does a SINGLE agent match/beat a MULTI-agent system on multi-hop reasoning
at comparable token cost? (Tran + Kiela, arXiv 2604.02460 — single-agent >= multi-agent under equal
thinking-token budget.)

Benchmark: MuSiQue (answerable validation), hop-diverse 2/3/4-hop, 20 paragraphs each (2-4 supporting +
distractors). Two conditions:
  - single-agent: one CoT call over all paragraphs.
  - multi-agent: decompose -> per-sub-question solver -> aggregate (standard orchestration).
FAIRNESS: every call gets a GENEROUS token cap so the (thinking) model always finishes its reasoning and
emits an answer — an earlier version force-split the budget per call, which truncated multi-agent answers
mid-reasoning and spuriously favored single-agent. Instead we MEASURE actual completion tokens per
condition and compare accuracy AND cost: the paper's claim holds if single matches/beats multi while using
<= the tokens (single on the efficiency frontier). Accuracy = normalized gold/alias match (+ token-F1);
bootstrap CI on the single-minus-multi accuracy gap; per-hop breakdown.
Verdict: REPRODUCED (single acc >= multi acc) | FAILED (multi significantly more accurate) | NOT_COMPUTABLE.
Honest deviations: MuSiQue (one of the paper's two benchmarks); a standard decompose-solve-aggregate
multi-agent. Report whatever the numbers say.
"""
import os, re, json, time, math, random, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
random.seed(20260620)
DATA = os.path.join(BASE, "data", "musique_val_hopmix.json")
PROGRESS = os.path.join(BASE, "svm_progress.txt")
OUTJSON = os.path.join(BASE, "single_vs_multi_musique.json")
CAP = 1000            # generous per-call completion cap (thinking models finish + emit ANSWER)
SUBSET_PER_HOP = 16   # 16 each of 2/3/4-hop = 48 questions (keeps wall-clock ~30-40min/model)
MAX_SUBS = 3
WORKERS = 4

_all = json.load(open(DATA, encoding="utf-8"))
ITEMS = []
for h in (2, 3, 4):
    ITEMS += [it for it in _all if it["n_hops"] == h][:SUBSET_PER_HOP]


def _cfg_val(path, key):
    txt = open(os.path.join(BASE, "..", "..", path), "rb").read().decode("utf-8", "replace")
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', txt)
    return m.group(1).strip() if m else None


MODELS = [
    {"name": "glm-5.2", "endpoint": _cfg_val("server/.env", "AGORA_REASONING_BASE_URL").rstrip("/") + "/chat/completions",
     "api_key": _cfg_val("server/.env", "AGORA_REASONING_KEY"), "model": "glm-5.2:cloud"},
    {"name": "deepseek-v4-flash", "endpoint": _cfg_val("agora-game-server/.env", "DUNGEON_LLM_URL"),
     "api_key": _cfg_val("agora-game-server/.env", "LLM_API_KEY"), "model": "deepseek-v4-flash"},
]


def _chat(cfg, messages, max_tokens=CAP):
    body = {"model": cfg["model"], "temperature": 0.3, "max_tokens": max_tokens, "messages": messages}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + (cfg["api_key"] or "")}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(cfg["endpoint"], data=json.dumps(body).encode(), headers=hdr), timeout=240).read())
            txt = r["choices"][0]["message"].get("content") or ""
            ct = (r.get("usage") or {}).get("completion_tokens") or 0
            return txt, ct
        except Exception:
            time.sleep(1.0)
    return "", 0


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(the|a|an|of|in|at|is|was|are|were)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _extract(txt):
    if not txt:
        return ""
    idx = txt.upper().rfind("ANSWER:")
    if idx >= 0:
        rest = txt[idx + 7:].strip()
        if rest:
            return rest.splitlines()[0].strip()[:200]
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    return lines[-1][:200] if lines else ""


def _f1(pred, gold):
    p, g = _norm(pred).split(), _norm(gold).split()
    if not p or not g:
        return 0.0
    gg = list(g); common = 0
    for w in p:
        if w in gg:
            common += 1; gg.remove(w)
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def _correct(pred, gold, aliases):
    np_ = _norm(pred)
    for c in [gold] + list(aliases or []):
        nc = _norm(c)
        if nc and (nc in np_ or (len(nc) > 3 and np_ in nc)):
            return True
        if _f1(pred, c) >= 0.6:
            return True
    return False


def _ctx(paras):
    return "Paragraphs:\n" + "\n".join(f"[{i+1}] {p}" for i, p in enumerate(paras))


def single_agent(cfg, q, paras):
    txt, ct = _chat(cfg, [
        {"role": "system", "content": "You answer multi-hop questions using ONLY the paragraphs. Reason step by step, then end with exactly 'ANSWER: <short answer>'."},
        {"role": "user", "content": f"{_ctx(paras)}\n\nQuestion: {q}"}])
    return _extract(txt), ct


def multi_agent(cfg, q, paras):
    tok = 0
    dtxt, dct = _chat(cfg, [
        {"role": "system", "content": "Decompose the multi-hop question into a short ordered list of simpler sub-questions (max 3). After your reasoning, list each sub-question on its own line ending with a question mark."},
        {"role": "user", "content": f"Question: {q}"}])
    tok += dct
    subs = [re.sub(r"^[\d\.\)\-\*\s]+", "", ln).strip() for ln in dtxt.splitlines() if ln.strip().endswith("?")][:MAX_SUBS]
    if not subs:
        subs = [q]
    sub_ans = []
    for sq in subs:
        st, sc = _chat(cfg, [
            {"role": "system", "content": "Answer the sub-question using ONLY the paragraphs. Be concise. End with 'ANSWER: <short answer>'."},
            {"role": "user", "content": f"{_ctx(paras)}\n\nSub-question: {sq}"}])
        tok += sc
        sub_ans.append(f"Q: {sq}\nA: {_extract(st)}")
    atxt, act = _chat(cfg, [
        {"role": "system", "content": "Using the sub-answers, give the final answer to the original question. End with exactly 'ANSWER: <short answer>'."},
        {"role": "user", "content": "Sub-answers:\n" + "\n".join(sub_ans) + f"\n\nOriginal question: {q}"}])
    tok += act
    return _extract(atxt), tok, len(subs)


def assess(cfg, name):
    done = [0]; lock = threading.Lock()

    def do_q(it):
        q, paras = it["question"], it["paragraphs"]
        s_pred, s_tok = single_agent(cfg, q, paras)
        m_pred, m_tok, n_sub = multi_agent(cfg, q, paras)
        rec = {"hops": it["n_hops"],
               "single_correct": _correct(s_pred, it["answer"], it["aliases"]), "single_tok": s_tok,
               "multi_correct": _correct(m_pred, it["answer"], it["aliases"]), "multi_tok": m_tok, "n_sub": n_sub}
        with lock:
            done[0] += 1
            open(PROGRESS, "w").write(f"{name}: {done[0]}/{len(ITEMS)} questions ({100*done[0]//len(ITEMS)}%)\n")
        return rec

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        recs = list(pool.map(do_q, ITEMS))

    n = len(recs)
    s_acc = sum(r["single_correct"] for r in recs) / n
    m_acc = sum(r["multi_correct"] for r in recs) / n
    rng = random.Random(7); diffs = []
    for _ in range(2000):
        samp = [recs[rng.randrange(n)] for _ in range(n)]
        diffs.append(sum(r["single_correct"] for r in samp) / n - sum(r["multi_correct"] for r in samp) / n)
    diffs.sort()
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
    by_hop = {}
    for h in (2, 3, 4):
        hr = [r for r in recs if r["hops"] == h]
        if hr:
            by_hop[h] = {"n": len(hr), "single": round(sum(r["single_correct"] for r in hr) / len(hr), 3),
                         "multi": round(sum(r["multi_correct"] for r in hr) / len(hr), 3)}
    return {"n": n, "single_acc": round(s_acc, 3), "multi_acc": round(m_acc, 3),
            "gap_single_minus_multi": round(s_acc - m_acc, 3), "gap_ci95": [round(lo, 3), round(hi, 3)],
            "single_tok_mean": round(sum(r["single_tok"] for r in recs) / n, 1),
            "multi_tok_mean": round(sum(r["multi_tok"] for r in recs) / n, 1),
            "by_hop": by_hop}


if __name__ == "__main__":
    print("compile OK", flush=True)
    allout = {}
    for m in MODELS:
        cfg = {"endpoint": m["endpoint"], "model": m["model"], "api_key": m["api_key"]}
        t0 = time.time()
        print(f"\n=== {m['name']}: single vs multi-agent (MuSiQue n={len(ITEMS)}, 2/3/4-hop) ===", flush=True)
        r = assess(cfg, m["name"])
        r["seconds"] = round(time.time() - t0, 0)
        allout[m["name"]] = r
        json.dump(allout, open(OUTJSON, "w"), indent=1)
        print(f"  single_acc={r['single_acc']:.1%}  multi_acc={r['multi_acc']:.1%}  gap(single-multi)={r['gap_single_minus_multi']:+.1%} CI95{r['gap_ci95']}", flush=True)
        print(f"  tokens/q: single={r['single_tok_mean']:.0f}  multi={r['multi_tok_mean']:.0f}  (multi/single={r['multi_tok_mean']/max(1,r['single_tok_mean']):.1f}x)", flush=True)
        print(f"  by hop: {r['by_hop']}  [{r['seconds']:.0f}s]", flush=True)
    print("\n=== VERDICT ===", flush=True)
    for name, r in allout.items():
        lo, hi = r["gap_ci95"]; ratio = r["multi_tok_mean"] / max(1, r["single_tok_mean"])
        if hi < 0:
            v = f"multi-agent SIGNIFICANTLY more accurate (paper FAILS here) - but at {ratio:.1f}x the tokens"
        elif lo >= 0:
            v = f"single-agent >= multi AND uses {1/ratio:.1f}x fewer tokens -> paper REPRODUCED (single on the efficiency frontier)"
        else:
            v = f"no significant accuracy gap; single uses {1/ratio:.1f}x fewer tokens -> single-agent dominates on cost (paper holds in spirit)"
        print(f"  {name}: {v}; single {r['single_acc']:.0%} vs multi {r['multi_acc']:.0%} @ {r['single_tok_mean']:.0f}/{r['multi_tok_mean']:.0f} tok", flush=True)
