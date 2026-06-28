"""The Overconfidence Tax — flagship Lab baseline (2026-06-28).

Question (severe-testable, NOT the textbook maxmin-EU theorem): when an agent may ANSWER or ABSTAIN
under an asymmetric payoff (correct +1, wrong -c, abstain 0), do REAL models lose utility by being
overconfident — and does adding a CONSERVATIVE MARGIN on top of the textbook-rational threshold
recover utility? Falsifier: the utility-maximizing margin m* is ~0 (then conservatism is folklore).
Capability-gradient: does the tax shrink frontier->weak (REAL & intrinsic) or vanish (artifact)?

Clean, contamination-free task: multi-step integer arithmetic of escalating difficulty (exact grading,
genuinely mixed accuracy). Confidence elicited per item. Cloud-OK (data measurement, not claim-gen).
"""
import sys, json, re, time, random, urllib.request, os

OLLAMA = "http://localhost:11434/api/chat"


def _anthropic_key():
    return os.environ.get("ANTHROPIC_API_KEY")   # set this env var to include a Claude model


def _ask_anthropic(model, sysmsg, usr, timeout=120):
    key = _anthropic_key()
    if not key:
        return "ERR:no-anthropic-key"
    body = json.dumps({"model": model, "max_tokens": 1500, "system": sysmsg,
                       "messages": [{"role": "user", "content": usr}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    for attempt in range(3):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        except Exception as e:
            if attempt == 2:
                return "ERR:" + str(e)[:80]
            time.sleep(2 * (attempt + 1))


def gen_problems(n, seed=7, lvl_base=1):
    rng = random.Random(seed)
    probs = []
    for i in range(n):
        level = lvl_base + (i % 5)               # difficulty lvl_base..lvl_base+4, balanced
        nterms = level + 1
        hi = 10 ** level
        terms = [rng.randint(2, hi) for _ in range(nterms)]
        ops = [rng.choice(["+", "-", "*"]) for _ in range(nterms - 1)]
        expr = str(terms[0])
        for op, t in zip(ops, terms[1:]):
            expr += " %s %s" % (op, t)
        ans = eval(expr)                          # ground truth (trusted: our own expr)
        probs.append({"id": i, "level": level, "expr": expr, "answer": ans})
    return probs


def ask(model, expr, timeout=240):
    sysmsg = ("You are a careful calculator. Solve the arithmetic exactly. You MAY reason briefly, "
              "but you MUST end with EXACTLY two lines:\nANSWER: <integer>\nCONFIDENCE: <integer 0-100>\n"
              "CONFIDENCE is your honest probability (percent) that your ANSWER is exactly correct.")
    if model.startswith("claude"):                          # Anthropic API path (frontier anchor)
        return _ask_anthropic(model, sysmsg, "Compute: " + expr, timeout=min(timeout, 120))
    body = json.dumps({"model": model, "stream": False,
                       "messages": [{"role": "system", "content": sysmsg},
                                    {"role": "user", "content": "Compute: " + expr}],
                       # cap generation so a reasoning model can't emit a runaway trace that never
                       # returns (the L6-10 hang: 0.2 CPU in 110min). 6000 is ample for reason+answer.
                       "options": {"temperature": 0, "num_predict": 12000}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            txt = json.loads(r.read())["message"]["content"]
            return txt
        except Exception as e:
            if attempt == 2:
                return "ERR:" + str(e)[:60]
            time.sleep(2 * (attempt + 1))


def parse(txt):
    # primary: explicit ANSWER:/CONFIDENCE: tags (take the last, after any reasoning)
    a = re.findall(r"ANSWER:\s*\**\s*(-?\d[\d,]*)", txt, re.I)
    c = re.findall(r"CONFIDENCE:\s*\**\s*(\d{1,3})", txt, re.I)
    ans = int(a[-1].replace(",", "")) if a else None
    conf = max(0, min(100, int(c[-1]))) / 100.0 if c else None
    # fallback: model gave a final number without the exact tag — take the last standalone integer
    if ans is None:
        nums = re.findall(r"-?\d[\d,]{2,}", txt)        # >=3-digit to avoid grabbing the confidence %
        if nums:
            ans = int(nums[-1].replace(",", ""))
    return ans, conf


def run_model(model, probs, workers=8):
    """Run all problems CONCURRENTLY (workers parallel calls) — the per-item cost is network-wait on a
    slow reasoning model, so concurrency cuts wall-time ~workers-fold. Order-independent (analyze works
    on the row set)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    rows = []

    def work(p):
        txt = ask(model, p["expr"])
        ans, conf = parse(txt)
        correct = (ans is not None and ans == p["answer"])
        return {"level": p["level"], "correct": int(correct),
                "conf": conf,                      # None if the model gave no parseable confidence
                "ans_ok": ans is not None,         # did we get a usable answer
                "conf_ok": conf is not None,       # did we get a real confidence (NOT defaulted)
                "_ans": ans, "_gold": p["answer"], "_expr": p["expr"]}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, p) for p in probs]
        for f in as_completed(futs):
            r = f.result(); rows.append(r)
            print("  %3d/%d L%d pred=%-16s gold=%-16s conf=%s %s" % (
                len(rows), len(probs), r["level"], r["_ans"], r["_gold"],
                ("%.2f" % r["conf"]) if r["conf"] is not None else "  ?  ",
                "OK" if r["correct"] else "x"), flush=True)
    return rows


def _auroc(pairs):
    """AUROC of confidence predicting correctness over (conf, correct) pairs with REAL confidences.
    0.5 = confidence is useless for selective abstention; >0.5 = discriminative."""
    pos = [c for c, ok in pairs if ok]
    neg = [c for c, ok in pairs if not ok]
    if not pos or not neg:
        return None
    wins = sum((1.0 if p > q else 0.5 if p == q else 0.0) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def analyze(model, rows):
    n = len(rows)
    # CLEAN set: only items with a REAL confidence AND a usable answer — no defaulting, the credible base.
    clean = [r for r in rows if r["conf_ok"] and r["ans_ok"]]
    answered = [r for r in rows if r["ans_ok"]]
    nclean = len(clean)
    n_parse_fail = n - len(answered)
    n_no_conf = sum(1 for r in answered if not r["conf_ok"])

    # headline AUROC is computed on the CLEAN set only (this is the validity-critical fix: parse-failures
    # were previously defaulted to conf=0.5 + counted wrong, which could inflate AUROC by separating
    # 'parsed' from 'unparsed' rather than 'right' from 'wrong').
    auroc_clean = _auroc([(r["conf"], bool(r["correct"])) for r in clean])
    acc_answered = (sum(r["correct"] for r in answered) / len(answered)) if answered else None
    mc = (sum(r["conf"] for r in clean) / nclean) if nclean else None
    acc_clean = (sum(r["correct"] for r in clean) / nclean) if nclean else None

    out = {"model": model, "n": n, "n_clean": nclean, "n_parse_fail": n_parse_fail,
           "n_answered_no_conf": n_no_conf,
           "accuracy_answered": round(acc_answered, 3) if acc_answered is not None else None,
           "accuracy_clean": round(acc_clean, 3) if acc_clean is not None else None,
           "mean_conf_clean": round(mc, 3) if mc is not None else None,
           "overconfidence_clean": round(mc - acc_clean, 3) if (mc is not None and acc_clean is not None) else None,
           "conf_AUROC_clean": round(auroc_clean, 3) if auroc_clean is not None else None,
           "n_wrong_clean": sum(1 for r in clean if not r["correct"]),
           "by_penalty": {}}
    if nclean:
        ncorr = sum(r["correct"] for r in clean)

        def util(thresh, c):
            return sum((1.0 if r["correct"] else -c) for r in clean if r["conf"] >= thresh)
        for c in (1.0, 2.0, 4.0):
            tau = c / (1 + c)
            u_tau = util(tau, c)
            best_t, best_u = 1.01, 0.0
            for k in range(0, 102):
                t = k * 0.01; uu = util(t, c)
                if uu > best_u + 1e-9:
                    best_u, best_t = uu, t
            out["by_penalty"]["c=%s" % c] = {
                "tau_star": round(tau, 3), "util_at_tau_on_conf": round(u_tau, 2),
                "best_thresh": round(min(best_t, 1.0), 3), "best_util": round(best_u, 2),
                "abstain_all_is_best": best_t > 1.0,
                "overconfidence_tax": round(best_u - u_tau, 2),
                "oracle_util": round(float(ncorr), 2),
                "confidence_gap_vs_oracle": round(float(ncorr) - best_u, 2)}
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    models = sys.argv[2].split(",") if len(sys.argv) > 2 else ["qwen2.5:7b"]
    lvl_base = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out_file = sys.argv[4] if len(sys.argv) > 4 else "agora_output/lab/overconfidence_tax_result.json"
    probs = gen_problems(n, lvl_base=lvl_base)
    results = []
    for m in models:
        print("\n=== %s (n=%d) ===" % (m, n))
        t0 = time.time()
        rows = run_model(m, probs)
        res = analyze(m, rows)
        res["secs"] = round(time.time() - t0, 1)
        res["rows"] = rows                                 # raw per-item data — auditable / re-checkable
        results.append(res)
        print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    open(out_file, "w").write(json.dumps(results, indent=2))
    print("\nwrote " + out_file)


if __name__ == "__main__":
    main()
