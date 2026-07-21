"""The Overconfidence Tax on a REAL hard benchmark — OpenAI SimpleQA (third task family).

Closes the "arithmetic only" gap: SimpleQA is short-answer factual QA designed to be hard, so models err a
lot -> a genuine right/wrong mix -> robust discrimination + risk-coverage measurement. For each question we
measure BOTH confidence signals on the SAME items and report AUROC + risk-coverage (selective accuracy):
  VERBALIZED = ask once, the model states a confidence 0-100 (the cheap signal an agent gate reads).
  SAMPLED    = sample N times at temperature, use answer-agreement (fraction matching the modal answer).

Grading = normalized token containment vs the SimpleQA gold answer (lowercased, punctuation/stop-words
stripped; every significant gold token must appear). Single file, parallel, re-runnable.

Data: SimpleQA is OpenAI's public benchmark. Download it (e.g. https://github.com/openai/simple-evals or the
HuggingFace mirror) to a CSV with columns `problem,answer` and point SIMPLEQA_CSV at it (default
./simpleqa.csv). Local models run free on Ollama (http://localhost:11434); a `:cloud` model routes via the
OpenAI-compatible /v1 endpoint.

Run:  python simpleqa_confidence.py <n> <model> <N_samples> <out.json>
e.g.  python simpleqa_confidence.py 150 "qwen2.5:7b" 5 result_simpleqa_weak.json
"""
import sys, os, json, re, csv, time, random, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA = "http://localhost:11434/api/chat"
REASON_URL = "http://localhost:11434/v1/chat/completions"   # OpenAI-compatible route for ":cloud" models
CSV = os.environ.get("SIMPLEQA_CSV", "simpleqa.csv")        # columns: problem, answer
SYS_VB = ("Answer with the SHORTEST correct factual answer (a name, date, place, or number). If unsure, still "
          "give your best guess. End with EXACTLY two lines:\nANSWER: <short answer>\nCONFIDENCE: <integer 0-100>\n"
          "CONFIDENCE is your honest probability the ANSWER is correct.")
SYS_S = ("Answer with the SHORTEST correct factual answer (a name, date, place, or number). End with exactly "
         "one line:\nANSWER: <short answer>")


def load_qa(n, seed=7):
    rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8")) if r.get("problem") and r.get("answer")]
    return [(r["problem"], r["answer"]) for r in random.Random(seed).sample(rows, min(n, len(rows)))]


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(the|a|an|of|in|is|was|at|on)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def grade(pred, gold):
    if not pred:
        return False
    p, g = _norm(pred), _norm(gold)
    if not g:
        return False
    if g in p or (len(p) >= 3 and p in g):
        return True
    # token-aware: every significant gold token (len>=4, e.g. surnames/places) present in the prediction
    toks = [t for t in g.split() if len(t) >= 4]
    return bool(toks) and all(t in p for t in toks)


def call(model, sysmsg, q, temp, timeout=120):
    if model.endswith(":cloud"):
        body = json.dumps({"model": model, "messages": [{"role": "system", "content": sysmsg},
                          {"role": "user", "content": q}], "temperature": temp, "max_tokens": 4000}).encode()
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(REASON_URL, data=body,
                   headers={"Content-Type": "application/json"}), timeout=timeout).read())["choices"][0]["message"]["content"]
        except Exception:
            return ""
    body = json.dumps({"model": model, "stream": False, "messages": [{"role": "system", "content": sysmsg},
                      {"role": "user", "content": q}], "options": {"temperature": temp, "num_predict": 4000}}).encode()
    for a in range(3):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(OLLAMA, data=body,
                   headers={"Content-Type": "application/json"}), timeout=timeout).read())["message"]["content"]
        except Exception:
            if a == 2:
                return ""
            time.sleep(2 * (a + 1))


def p_ans(txt):
    if not txt:
        return None
    m = re.search(r"ANSWER:\s*\**\s*(.+)", txt, re.I)
    if m:
        return m.group(1).strip().strip("*").strip()[:90]
    for line in txt.strip().splitlines():
        s = line.strip().strip("*").strip()
        if s and not re.fullmatch(r"(CONFIDENCE\s*[:=]\s*)?\d{1,3}\s*%?", s, re.I):
            return s[:90]
    return None


def p_conf(txt):
    c = re.findall(r"CONFIDENCE\s*[:=]\s*\**\s*(\d{1,3})", txt or "", re.I)
    if c:
        return max(0, min(100, int(c[-1]))) / 100.0
    nums = re.findall(r"(?m)^\s*(\d{1,3})\s*%?\s*$", txt or "")
    for v in reversed(nums):
        if 0 <= int(v) <= 100:
            return int(v) / 100.0
    return None


def auroc(pairs):
    pos = [c for c, ok in pairs if ok]; neg = [c for c, ok in pairs if not ok]
    if not pos or not neg:
        return None
    return round(sum((1.0 if p > q else 0.5 if p == q else 0.0) for p in pos for q in neg) / (len(pos) * len(neg)), 3)


def risk_coverage(pairs):
    ps = sorted(pairs, key=lambda x: -x[0]); n = len(ps)
    if not n:
        return None
    def acc_at(cov):
        k = max(1, round(cov * n)); return round(sum(1 for _, c in ps[:k] if c) / k, 2)
    def cov_at(t):
        best = 0.0
        for k in range(1, n + 1):
            if sum(1 for _, c in ps[:k] if c) / k >= t:
                best = round(k / n, 2)
        return best
    return {"answer_all": acc_at(1.0), "top_half": acc_at(0.5), "top_quarter": acc_at(0.25),
            "coverage@90acc": cov_at(0.9)}


def run(model, qa, N, workers=6):
    def work(item):
        q, gold = item
        vb = call(model, SYS_VB, q, 0.0)
        vb_ans, vb_conf = p_ans(vb), p_conf(vb)
        sa = [p_ans(call(model, SYS_S, q, 0.7)) for _ in range(N)]
        sa = [_norm(x) for x in sa if x]
        modal, ms_conf = None, None
        if sa:
            modal, cnt = Counter(sa).most_common(1)[0]; ms_conf = cnt / len(sa)
        ms_correct = bool(modal) and grade(modal, gold)
        return {"vb_conf": vb_conf, "vb_correct": int(grade(vb_ans, gold)),
                "vb_ok": vb_ans is not None and vb_conf is not None,
                "ms_conf": ms_conf, "ms_correct": int(ms_correct), "ms_ok": modal is not None}
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(work, it) for it in qa]):
            r = f.result(); rows.append(r)
            print("  %d/%d vb=%d ms=%d" % (len(rows), len(qa), r["vb_correct"], r["ms_correct"]), flush=True)
    vb = [(r["vb_conf"], bool(r["vb_correct"])) for r in rows if r["vb_ok"]]
    ms = [(r["ms_conf"], bool(r["ms_correct"])) for r in rows if r["ms_ok"]]
    return {"model": model, "task": "simpleqa", "n": len(rows), "N_samples": N,
            "verbalized": {"n": len(vb), "AUROC": auroc(vb), "risk_coverage": risk_coverage(vb)},
            "sampled": {"n": len(ms), "AUROC": auroc(ms), "risk_coverage": risk_coverage(ms)},
            "rows": rows}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5:7b"
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    out = sys.argv[4] if len(sys.argv) > 4 else "simpleqa_result.json"
    qa = load_qa(n)
    print("=== %s SimpleQA n=%d N=%d ===" % (model, len(qa), N))
    res = run(model, qa, N)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    json.dump([res], open(out, "w"), indent=1)
    print("wrote " + out)


if __name__ == "__main__":
    main()
