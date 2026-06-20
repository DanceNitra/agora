"""
SYNTHESIZE-INSIGHT task, grounded: "Test if specifying cue-validity distributions reduces the
conservatism gap" -- on real LLMs. (v2: fixed harness.)

Edwards (1968) conservatism: humans revise beliefs LESS than Bayes prescribes. Peterson & Beach (1967):
part of conservatism is misperceiving the DIAGNOSTICITY (cue validity / likelihood ratio). Prediction:
SPECIFYING the cue-validity distribution (giving exact likelihoods) shrinks the conservatism gap vs
having to INFER it.

v1 finding that drove the redesign: with EXPLICIT numeric likelihoods, LLMs just compute Bayes almost
exactly (no conservatism) -- they are calculators, not conservative humans. And a purely VERBAL ("tends
to") likelihood is ill-posed (models won't emit a calibrated probability -> unparseable). So the sharp,
well-posed contrast is TOLD vs INFER the cue validity, both with the SAME normative posterior:
  - TOLD : likelihoods stated numerically (cue validity SPECIFIED).
  - INFER: a training sample with EXACTLY 70%/30% composition is shown; the model must estimate q itself
           (learned cue validity, as humans do). MLE q = 0.70 == the TOLD q, so the Bayesian benchmark is
           identical across conditions; only the SOURCE of the cue validity differs.
Conservatism gap = how far the report falls SHORT of Bayes toward the 0.5 prior (>0 = conservative).
Hypothesis: INFER is more conservative than TOLD (specifying cue validity reduces the gap).
Falsifier: no gap difference (LLMs handle inferred and told cue validity the same).
"""
import os, re, json, time, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))


def _cfg(path, key):
    txt = open(os.path.join(BASE, "..", "..", path), "rb").read().decode("utf-8", "replace")
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', txt)
    return m.group(1).strip() if m else None


MODELS = [
    {"name": "deepseek-v4-flash", "endpoint": _cfg("agora-game-server/.env", "DUNGEON_LLM_URL"),
     "api_key": _cfg("agora-game-server/.env", "LLM_API_KEY"), "model": "deepseek-v4-flash"},
    {"name": "glm-5.2", "endpoint": _cfg("server/.env", "AGORA_REASONING_BASE_URL").rstrip("/") + "/chat/completions",
     "api_key": _cfg("server/.env", "AGORA_REASONING_KEY"), "model": "glm-5.2:cloud"},
]

Q = 0.70
ITEMS = [(6, 5), (8, 6), (10, 7), (10, 8), (12, 9)]   # (n, nR)
TRAIN_N = 20                                            # training-sample size per source in INFER condition


def bayes_posterior(nR, nB, q=Q):
    lr = (q / (1 - q)) ** (nR - nB)
    return lr / (1 + lr)


def _seq(nR, nB):
    return " ".join(["R"] * nR + ["B"] * nB)


def _ask_prob(cfg, prompt, max_tokens=1800):
    """Return a posterior in [0,1] or None. STRICT: parse ONLY the final 'PROB: x' line (no fallback to
    grabbing stray numbers from the reasoning trace -- that produced spurious values in v1)."""
    sysmsg = ("Answer the probability question. You may reason briefly, but you MUST finish with exactly "
              "one final line in the form 'PROB: <number from 0 to 1>'. Do not omit that line.")
    body = {"model": cfg["model"], "temperature": 0.5, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": prompt}]}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + (cfg["api_key"] or "")}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(cfg["endpoint"], data=json.dumps(body).encode(), headers=hdr), timeout=150).read())
            txt = r["choices"][0]["message"].get("content") or ""
            m = re.findall(r"PROB:\s*([01](?:\.\d+)?|0?\.\d+|\d{1,3}\s*%)", txt)
            if m:
                tok = m[-1].replace("%", "").strip()
                v = float(tok)
                if v > 1:
                    v = v / 100.0
                if 0.0 <= v <= 1.0:
                    return v
        except Exception:
            time.sleep(1.5)
    return None


def told_prompt(nR, nB):
    return (f"Two sources are equally likely a priori (50/50). "
            f"Source A emits signal R with probability {Q:.2f} and signal B with probability {1-Q:.2f}. "
            f"Source B emits signal R with probability {1-Q:.2f} and signal B with probability {Q:.2f}. "
            f"You observe this sequence of independent signals: {_seq(nR, nB)}. "
            f"What is the probability that the source is A? End with 'PROB: <0..1>'.")


def infer_prompt(nR, nB):
    # training samples with EXACTLY 70/30 and 30/70 composition (MLE q = 0.70 == the TOLD q)
    a_train = _seq(int(TRAIN_N * Q), TRAIN_N - int(TRAIN_N * Q))
    b_train = _seq(TRAIN_N - int(TRAIN_N * Q), int(TRAIN_N * Q))
    return ("Two sources are equally likely a priori (50/50). Here are past outputs from each:\n"
            f"Source A previously emitted: {a_train}\n"
            f"Source B previously emitted: {b_train}\n"
            f"Now you observe a NEW sequence from one unknown source: {_seq(nR, nB)}. "
            f"What is the probability that the source is A? End with 'PROB: <0..1>'.")


def assess(cfg, k=3):
    rows = []
    for (n, nR) in ITEMS:
        nB = n - nR
        bayes = bayes_posterior(nR, nB)
        for cond, mk in (("told", told_prompt), ("infer", infer_prompt)):
            vals = [v for v in (_ask_prob(cfg, mk(nR, nB)) for _ in range(k)) if v is not None]
            if not vals:
                rows.append({"n": n, "nR": nR, "bayes": round(bayes, 3), "cond": cond,
                             "reported": None, "gap": None, "k": 0})
                continue
            rep = sum(vals) / len(vals)
            gap = (bayes - 0.5) - (rep - 0.5)         # >0 = conservative (under-revised toward 0.5 prior)
            rows.append({"n": n, "nR": nR, "bayes": round(bayes, 3), "cond": cond,
                         "reported": round(rep, 3), "gap": round(gap, 3), "k": len(vals)})
    return rows


if __name__ == "__main__":
    all_results = {}
    for m in MODELS:
        cfg = {"endpoint": m["endpoint"], "model": m["model"], "api_key": m["api_key"]}
        print(f"=== {m['name']} ===", flush=True)
        rows = assess(cfg)
        all_results[m["name"]] = rows
        by = {"told": [], "infer": []}
        print(f"  {'n':>3} {'nR':>3} {'bayes':>6} {'cond':>6} {'reported':>9} {'cons_gap':>9} {'k':>2}")
        for r in rows:
            rep = "  none" if r["reported"] is None else f"{r['reported']:>9.3f}"
            g = "     none" if r["gap"] is None else f"{r['gap']:>+9.3f}"
            print(f"  {r['n']:>3} {r['nR']:>3} {r['bayes']:>6.3f} {r['cond']:>6} {rep} {g} {r['k']:>2}")
            if r["gap"] is not None:
                by[r["cond"]].append(r["gap"])
        gt = sum(by["told"]) / len(by["told"]) if by["told"] else float("nan")
        gi = sum(by["infer"]) / len(by["infer"]) if by["infer"] else float("nan")
        print(f"  -> mean conservatism gap: TOLD={gt:+.3f} (n={len(by['told'])})  "
              f"INFER={gi:+.3f} (n={len(by['infer'])})  extra-conservatism(INFER-TOLD)={gi-gt:+.3f}\n", flush=True)
        all_results[m["name"] + "_summary"] = {"gap_told": gt, "gap_infer": gi, "infer_minus_told": gi - gt,
                                               "n_told": len(by["told"]), "n_infer": len(by["infer"])}

    json.dump(all_results, open(os.path.join(BASE, "llm_conservatism_cue_validity.json"), "w"), indent=1)
    print("=== SUMMARY: does SPECIFYING (vs inferring) cue validity reduce the conservatism gap? ===")
    for m in MODELS:
        s = all_results.get(m["name"] + "_summary")
        if not s or s["n_told"] == 0 or s["n_infer"] == 0:
            print(f"  {m['name']:<18} INSUFFICIENT DATA (told n={s['n_told'] if s else 0}, infer n={s['n_infer'] if s else 0})")
            continue
        d = s["infer_minus_told"]
        verdict = ("YES - inferring is more conservative; specifying cue validity reduces the gap" if d > 0.03 else
                   "NO - specifying cue validity does NOT reduce the gap (falsifier)" if abs(d) <= 0.03 else
                   "REVERSED - inferring is LESS conservative than being told")
        print(f"  {m['name']:<18} TOLD gap={s['gap_told']:+.3f}  INFER gap={s['gap_infer']:+.3f}  -> {verdict}")
