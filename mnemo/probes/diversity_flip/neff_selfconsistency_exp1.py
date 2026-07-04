"""
N_eff on REAL systems — Experiment 1: real LLM self-consistency error-correlation + saturation.

The independence-law toy sims HAND-IMPOSE rho (errs = sqrt(rho)*common + sqrt(1-rho)*idio), so they only
re-derive the textbook equicorrelation formula. This measures rho on REAL frontier-LLM reasoning errors and
asks the genuinely-open question: are real LLM reasoning errors correlated enough across items that
self-consistency (majority vote) SATURATES early — i.e. naive independent-errors theory OVER-promises — and
does the measured rho set where it saturates (N_eff ceiling ~ 1/rho)?

Ceiling escape (mandatory, per the pre-mortem): single-agent already scores ~0.95 on the easy MuSiQue mix,
leaving no headroom. So: (1) HARD subset only (3-hop + 4-hop), (2) STRICT grading (gold/alias must appear in
the prediction; NO token-F1 leniency), (3) temperature 0.9 for real sample diversity. If single-sample acc
still > 0.9 the run is INCONCLUSIVE (reported, not claimed).

Reuses the proven real-LLM call infra from the single-vs-multi harness. Standalone detached script (the
/brain/lab/run runner has a 60s/10k-char cap); writes incrementally to neff_selfconsistency.json.
"""
import os, re, json, time, random, threading, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
random.seed(20260621)
DATA = os.path.join(BASE, "data", "musique_val_hopmix.json")
PROGRESS = os.path.join(BASE, "neff_sc_progress.txt")
OUTJSON = os.path.join(BASE, "neff_selfconsistency.json")
K = 10                # samples per question
TEMP = 0.9            # high temperature -> real sample diversity (decorrelation pressure)
CAP = 1000
WORKERS = 4
M_GRID = [1, 3, 5, 7, 9]

_all = json.load(open(DATA, encoding="utf-8"))
ITEMS = [it for it in _all if it["n_hops"] in (3, 4)]   # HARD subset only (ceiling escape)


def _cfg_val(path, key):
    txt = open(os.path.join(BASE, "..", "..", path), "rb").read().decode("utf-8", "replace")
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', txt)
    return m.group(1).strip() if m else None


MODELS = [
    {"name": "glm-5.2", "endpoint": (_cfg_val("server/.env", "AGORA_REASONING_BASE_URL") or "").rstrip("/") + "/chat/completions",
     "api_key": _cfg_val("server/.env", "AGORA_REASONING_KEY"), "model": "glm-5.2:cloud"},
    {"name": "deepseek-v4-flash", "endpoint": _cfg_val("agora-game-server/.env", "DUNGEON_LLM_URL"),
     "api_key": _cfg_val("agora-game-server/.env", "LLM_API_KEY"), "model": "deepseek-v4-flash"},
]


def _chat(cfg, messages, temp=TEMP, max_tokens=CAP):
    body = {"model": cfg["model"], "temperature": temp, "max_tokens": max_tokens, "messages": messages}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + (cfg["api_key"] or "")}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(cfg["endpoint"], data=json.dumps(body).encode(), headers=hdr), timeout=240).read())
            return (r["choices"][0]["message"].get("content") or ""), ((r.get("usage") or {}).get("completion_tokens") or 0)
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


def _correct_strict(pred, gold, aliases):
    """STRICT: a gold answer or alias must appear (normalized substring) in the prediction. No token-F1."""
    npred = _norm(pred)
    if not npred:
        return False
    for c in [gold] + list(aliases or []):
        nc = _norm(c)
        if nc and nc in npred:
            return True
    return False


def _ctx(paras):
    return "Paragraphs:\n" + "\n".join(f"[{i+1}] {p}" for i, p in enumerate(paras))


def sample_once(cfg, q, paras):
    txt, ct = _chat(cfg, [
        {"role": "system", "content": "You answer multi-hop questions using ONLY the paragraphs. Reason step by step, then end with exactly 'ANSWER: <short answer>'."},
        {"role": "user", "content": f"{_ctx(paras)}\n\nQuestion: {q}"}])
    return _extract(txt), ct


def assess(cfg, name):
    done = [0]; lock = threading.Lock()

    def do_q(it):
        q, paras = it["question"], it["paragraphs"]
        samples = []   # list of (extracted_answer, is_correct)
        for _ in range(K):
            pred, _tok = sample_once(cfg, q, paras)
            samples.append((pred, _correct_strict(pred, it["answer"], it["aliases"])))
        with lock:
            done[0] += 1
            open(PROGRESS, "w").write(f"{name}: {done[0]}/{len(ITEMS)} questions\n")
        return {"hops": it["n_hops"], "samples": samples}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        recs = list(pool.map(do_q, ITEMS))

    Q = len(recs)
    # ---- single-sample accuracy ----
    single_acc = float(np.mean([s[1] for r in recs for s in r["samples"]]))
    # ---- error matrix E (K x Q), 1 = wrong ----
    E = np.array([[0 if recs[qi]["samples"][i][1] else 1 for qi in range(Q)] for i in range(K)], dtype=float)
    # ---- rho = mean pairwise correlation of error vectors ACROSS items ----
    rhos = []
    for i in range(K):
        for j in range(i + 1, K):
            a, b = E[i], E[j]
            if a.std() > 1e-9 and b.std() > 1e-9:
                rhos.append(float(np.corrcoef(a, b)[0, 1]))
    rho = float(np.mean(rhos)) if rhos else 0.0
    n_eff_ceiling = (1.0 / rho) if rho > 1e-6 else float("inf")
    # ---- realized majority-vote (plurality) accuracy vs vote-width m ----
    def mv_curve(R=80):
        out = {}
        for m in M_GRID:
            if m > K:
                continue
            accs = []
            for _ in range(R):
                c = 0
                for r in recs:
                    idx = random.sample(range(K), m)
                    norm_correct = {}
                    for t in range(K):
                        norm_correct[_norm(r["samples"][t][0])] = r["samples"][t][1]
                    plur = Counter(_norm(r["samples"][t][0]) for t in idx).most_common(1)[0][0]
                    c += 1 if norm_correct.get(plur, False) else 0
                accs.append(c / Q)
            out[m] = {"acc": round(float(np.mean(accs)), 4), "sd": round(float(np.std(accs)), 4)}
        return out
    mv = mv_curve()
    # ---- saturation diagnostics ----
    g_early = mv[3]["acc"] - mv[1]["acc"] if 3 in mv and 1 in mv else 0.0
    g_late = (mv[9]["acc"] - mv[5]["acc"]) if 9 in mv and 5 in mv else 0.0
    saturates = g_late < 0.5 * g_early if g_early > 1e-6 else (g_late <= 0.005)
    return {"n_items": Q, "K": K, "temp": TEMP, "grading": "strict",
            "single_sample_acc": round(single_acc, 4),
            "rho_error_correlation": round(rho, 4), "n_eff_ceiling": round(n_eff_ceiling, 2) if rho > 1e-6 else None,
            "majority_vote_curve": mv,
            "gain_m1_to_m3": round(g_early, 4), "gain_m5_to_m9": round(g_late, 4), "saturates_early": bool(saturates)}


if __name__ == "__main__":
    print(f"compile OK — N_eff self-consistency, {len(ITEMS)} hard (3+4 hop) items, K={K}, T={TEMP}, strict grading", flush=True)
    allout = {}
    for m in MODELS:
        cfg = {"endpoint": m["endpoint"], "model": m["model"], "api_key": m["api_key"]}
        if not cfg["endpoint"] or not cfg["api_key"]:
            print(f"  SKIP {m['name']}: missing endpoint/key", flush=True); continue
        t0 = time.time()
        print(f"\n=== {m['name']}: self-consistency rho + saturation ===", flush=True)
        try:
            r = assess(cfg, m["name"]); r["seconds"] = round(time.time() - t0, 0)
        except Exception as e:
            print(f"  ERROR {m['name']}: {e}", flush=True); continue
        allout[m["name"]] = r
        json.dump(allout, open(OUTJSON, "w"), indent=1)
        ceil = r["n_eff_ceiling"]
        print(f"  single-sample acc={r['single_sample_acc']:.1%}  rho={r['rho_error_correlation']:+.3f}  N_eff ceiling~{ceil}", flush=True)
        print(f"  majority-vote: " + "  ".join(f"m{k}={v['acc']:.1%}" for k, v in r["majority_vote_curve"].items()), flush=True)
        print(f"  saturates early: {r['saturates_early']} (gain m1->m3 {r['gain_m1_to_m3']:+.3f} vs m5->m9 {r['gain_m5_to_m9']:+.3f})  [{r['seconds']:.0f}s]", flush=True)
    print("\n=== VERDICT ===", flush=True)
    for name, r in allout.items():
        if r["single_sample_acc"] > 0.9:
            v = "INCONCLUSIVE — single-sample acc still >0.9, no headroom (ceiling not escaped); harder regime needed"
        elif r["rho_error_correlation"] < 0.05:
            v = f"errors ~INDEPENDENT (rho={r['rho_error_correlation']:.3f}) — naive theory holds here, self-consistency keeps helping"
        elif r["saturates_early"]:
            v = (f"N_eff REGIME ON REAL LLM — errors correlated (rho={r['rho_error_correlation']:.3f}, N_eff ceiling ~{r['n_eff_ceiling']}); "
                 f"self-consistency SATURATES early as N_eff predicts; naive independent-errors theory over-promises")
        else:
            v = f"correlated (rho={r['rho_error_correlation']:.3f}) but NOT clearly saturating in range — inconclusive on the ceiling"
        print(f"  {name}: {v}", flush=True)
    print("\nFALSIFIER (pre-committed): N_eff regime SUPPORTED on real LLMs iff rho>>0 AND self-consistency saturates early; "
          "if rho~0 or the curve keeps rising to ~1, errors are effectively independent and the law does not bind here. "
          "Either way -> Crucible. Next: does this rho PREDICT the multi-agent crossover (transfer).", flush=True)
