"""Flagship v2: verbalized (single-shot) confidence vs multi-sample (consistency) confidence.

Tests the r/LLMDevs point (u/Combinatorilliance, arXiv:2502.18389): single-shot self-reported confidence
is a coin flip on small models, but MULTI-SAMPLE consistency confidence (sample N times, use answer-agreement
as confidence) is more predictive — even on small models. Same contamination-free arithmetic task.

Per item, per model:
  - VERBALIZED: one call (temp 0), parse (answer, confidence). conf_vb = stated confidence.
  - SAMPLED: N calls (temp>0), parse answers. modal = most common; conf_ms = count(modal)/N_valid (agreement).
We then compare AUROC(conf -> correctness) for the two signals. If sampled AUROC >> verbalized AUROC on a
small model, Combinatorilliance is right and our claim is correctly SCOPED to verbalized confidence.

Local models (qwen*) run on local Ollama (free). Runnable: python exp_multisample_confidence.py <n> <model> <lvl_base> <N> <out>
"""
import sys, json, re, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA = "http://localhost:11434/api/chat"
SYS_VB = ("You are a careful calculator. Solve the arithmetic exactly. End with EXACTLY two lines:\n"
          "ANSWER: <integer>\nCONFIDENCE: <integer 0-100>\nCONFIDENCE = your honest probability the ANSWER is correct.")
SYS_S = ("You are a careful calculator. Solve the arithmetic. End with exactly one line:\nANSWER: <integer>")


def gen_problems(n, seed=7, lvl_base=4):
    import random
    rng = random.Random(seed); probs = []
    for i in range(n):
        level = lvl_base + (i % 5); nterms = level + 1; hi = 10 ** level
        terms = [rng.randint(2, hi) for _ in range(nterms)]
        ops = [rng.choice(["+", "-", "*"]) for _ in range(nterms - 1)]
        expr = str(terms[0])
        for op, t in zip(ops, terms[1:]):
            expr += " %s %s" % (op, t)
        probs.append({"id": i, "expr": expr, "answer": eval(expr)})
    return probs


def call(model, sysmsg, expr, temp, timeout=180):
    body = json.dumps({"model": model, "stream": False,
                       "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": "Compute: " + expr}],
                       "options": {"temperature": temp, "num_predict": 8000}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    for a in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read())["message"]["content"]
        except Exception as e:
            if a == 2:
                return "ERR"
            time.sleep(2 * (a + 1))


def p_ans(txt):
    m = re.findall(r"ANSWER:\s*\**\s*(-?\d[\d,]*)", txt or "", re.I)
    cand = m[-1] if m else None
    if cand is None:
        nums = re.findall(r"-?\d[\d,]{2,}", txt or "")
        cand = nums[-1] if nums else None
    if cand is None:
        return None
    cand = cand.replace(",", "")
    if len(cand.lstrip("-")) > 60:        # hallucinated mega-number, not a real answer
        return None
    try:
        return int(cand)
    except ValueError:
        return None


def p_conf(txt):
    c = re.findall(r"CONFIDENCE:\s*\**\s*(\d{1,3})", txt or "", re.I)
    return max(0, min(100, int(c[-1]))) / 100.0 if c else None


def auroc(pairs):
    pos = [c for c, ok in pairs if ok]; neg = [c for c, ok in pairs if not ok]
    if not pos or not neg:
        return None
    return sum((1.0 if p > q else 0.5 if p == q else 0.0) for p in pos for q in neg) / (len(pos) * len(neg))


def run(model, probs, N, workers=6):
    def work(p):
        # verbalized (single shot, temp 0)
        vb = call(model, SYS_VB, p["expr"], 0.0)
        vb_ans, vb_conf = p_ans(vb), p_conf(vb)
        # sampled (N calls, temp 0.7)
        sa = [p_ans(call(model, SYS_S, p["expr"], 0.7)) for _ in range(N)]
        sa = [x for x in sa if x is not None]
        modal, ms_conf = (None, None)
        if sa:
            modal, cnt = Counter(sa).most_common(1)[0]
            ms_conf = cnt / len(sa)
        return {"gold": p["answer"], "vb_conf": vb_conf, "vb_correct": int(vb_ans == p["answer"]) if vb_ans is not None else 0,
                "vb_ok": vb_ans is not None and vb_conf is not None,
                "ms_conf": ms_conf, "ms_correct": int(modal == p["answer"]) if modal is not None else 0,
                "ms_ok": modal is not None}
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(work, p) for p in probs]):
            r = f.result(); rows.append(r)
            print("  %d/%d vb_conf=%s vb=%d | ms_conf=%s ms=%d" % (
                len(rows), len(probs), r["vb_conf"], r["vb_correct"],
                ("%.2f" % r["ms_conf"]) if r["ms_conf"] is not None else "?", r["ms_correct"]), flush=True)
    vb = [(r["vb_conf"], bool(r["vb_correct"])) for r in rows if r["vb_ok"]]
    ms = [(r["ms_conf"], bool(r["ms_correct"])) for r in rows if r["ms_ok"]]
    return {"model": model, "n": len(rows), "N_samples": N,
            "verbalized": {"n": len(vb), "acc": round(sum(c for _, c in vb) / len(vb), 3) if vb else None,
                           "AUROC": round(auroc(vb), 3) if auroc(vb) is not None else None},
            "sampled": {"n": len(ms), "acc": round(sum(c for _, c in ms) / len(ms), 3) if ms else None,
                        "AUROC": round(auroc(ms), 3) if auroc(ms) is not None else None},
            "rows": rows}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5:7b"
    lvl = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    N = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    out = sys.argv[5] if len(sys.argv) > 5 else "agora_output/lab/multisample_result.json"
    probs = gen_problems(n, lvl_base=lvl)
    print("=== %s n=%d N=%d L%d-%d ===" % (model, n, N, lvl, lvl + 4))
    res = run(model, probs, N)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    json.dump([res], open(out, "w"), indent=1)
    print("wrote " + out)


if __name__ == "__main__":
    main()
