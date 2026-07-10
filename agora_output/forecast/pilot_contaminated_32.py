"""CONTAMINATED PILOT — replication-forecast smoke test on the existing Crucible R/F verdicts.

Purpose (per the gate): debug the frozen forecaster prompt and get a sober signal check.
This is NOT evidence of forecasting skill: our verdicts have been public on GitHub Pages
since ~2026-05, so any model may have seen them (contamination cannot be bounded). The
result is labeled CONTAMINATED and is never citable outward.

Design:
  - Blind claim cards: claim text + source ONLY (no verdict, no lab note, no code link).
  - Frozen prompt v1 (the same prompt the prospective layer will pin + publish).
  - Two model families (glm-5.2, deepseek-v4-flash) — per-model and mean-ensemble Brier.
  - Score: Brier on P(REPRODUCED) vs the constant base-rate predictor.
  - Decision rule (pre-stated): if neither model beats the constant base-rate Brier even
    WITH the retrospective/contamination advantage, the research framing is dead and the
    forecast layer ships as a storefront credibility protocol only.
"""
import json, os, re, sys, time, urllib.request

sys.stdout.reconfigure(errors="replace", line_buffering=True)
env = {}
for line in open("server/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")
URL = "https://ollama.com/v1/chat/completions"
MODELS = ["glm-5.2", "deepseek-v4-flash"]
CACHE = "agora_output/forecast/pilot_contaminated_32_cache.json"
OUT = "agora_output/forecast/pilot_contaminated_32_result.json"

# ---- FROZEN PROMPT v1 (the prospective layer will pin exactly this) ----------------
PROMPT_V1 = """You are a calibrated forecaster of computational replication outcomes.

A replication team takes a published/stated claim about AI/ML/computational systems and
re-runs it as the SMALLEST faithful computational model (a "severe test": the replication
is designed so that FAILED is a live possibility). The verdict is REPRODUCED (the claimed
effect/bound/behavior shows up in the minimal model) or FAILED (it does not).

Claim card:
  CLAIM: {claim}
  SOURCE: {source}

Give your probability that the verdict was REPRODUCED. Consider: is the claim a proven
theorem or a fragile empirical effect? vendor benchmark or academic result? does it have
a plausible confound (resource, selection, metric mismatch)? how large/specific is the
claimed effect? Do NOT assume the team replicates only safe claims.

Reply with ONLY a JSON object: {{"p_reproduced": <float 0..1>, "reason": "<one sentence>"}}"""
# -------------------------------------------------------------------------------------

def chat(model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 6000, "temperature": 0}).encode()
    for a in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                         "Content-Type": "application/json"}), timeout=180).read())
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            if a == 3:
                print(f"    [{model} FAIL: {e}]", flush=True); return None
            time.sleep(5 * (a + 1))

def parse_p(text):
    if not text:
        return None
    m = re.search(r'"p_reproduced"\s*:\s*([0-9.]+)', text)
    if not m:
        m = re.search(r'\b(0\.\d+|1\.0|0|1)\b', text)
    if not m:
        return None
    try:
        p = float(m.group(1))
        return p if 0.0 <= p <= 1.0 else None
    except ValueError:
        return None

def main():
    d = json.load(open("public/crucible/crucible.json", encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("entries") or d.get("items")
    rf = [i for i in items if i.get("verdict") in ("REPRODUCED", "FAILED")]
    print(f"scoreable R/F claims: {len(rf)}")
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    n_flush = 0
    for idx, it in enumerate(rf):
        cid = f"{idx}|{it['claim'][:50]}"
        rec = cache.setdefault(cid, {})
        for model in MODELS:
            if model in rec and rec[model] is not None:
                continue
            txt = chat(model, PROMPT_V1.format(claim=it["claim"], source=it.get("source", "unknown")))
            rec[model] = parse_p(txt)
            n_flush += 1
            if n_flush % 8 == 0:
                json.dump(cache, open(CACHE, "w"), indent=1)
        print(f"  {idx+1}/{len(rf)} " + " ".join(f"{m}={rec.get(m)}" for m in MODELS), flush=True)
    json.dump(cache, open(CACHE, "w"), indent=1)

    # scoring
    y = [1.0 if it["verdict"] == "REPRODUCED" else 0.0 for it in rf]
    base = sum(y) / len(y)
    def brier(ps, ys): return sum((p - t) ** 2 for p, t in zip(ps, ys)) / len(ps)
    out = {"n": len(rf), "base_rate_reproduced": round(base, 3),
           "brier_constant_base_rate": round(brier([base] * len(y), y), 4),
           "label": "CONTAMINATED PILOT — verdicts public since 2026-05; never citable as skill",
           "prompt_version": "v1", "models": {}}
    ens = []
    for model in MODELS:
        ps, ys = [], []
        for idx, it in enumerate(rf):
            p = cache.get(f"{idx}|{it['claim'][:50]}", {}).get(model)
            if p is not None:
                ps.append(p); ys.append(y[idx])
        out["models"][model] = {"n_answered": len(ps), "brier": round(brier(ps, ys), 4) if ps else None,
                                "mean_p": round(sum(ps) / len(ps), 3) if ps else None}
    # mean-ensemble over claims where BOTH answered
    ps, ys = [], []
    for idx, it in enumerate(rf):
        rec = cache.get(f"{idx}|{it['claim'][:50]}", {})
        vals = [rec.get(m) for m in MODELS]
        if all(v is not None for v in vals):
            ps.append(sum(vals) / len(vals)); ys.append(y[idx])
    out["ensemble_mean"] = {"n": len(ps), "brier": round(brier(ps, ys), 4) if ps else None}
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
