"""RAMR point-1 hardening: SCALE the flagship CHAIN-FRAGILITY result to n>=200 with tight bootstrap CIs, to make
our strongest, most-defensible claim unshakeable (the readiness red-team flagged 'tiny n' as attack #1). Reuses the
contamination-resistant synthetic 3-hop chains from v0. Per model, measure gold (complete chain) and partial (one
hop dropped) accuracy at large n, and the CHAIN-FRAGILITY = gold - partial with a PAIRED bootstrap CI over the n
questions. Models default to a local + a frontier cloud reader (cloud allowed; owner 2026-06-23). ASCII prints."""
import os, sys, json, time, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

N_Q = int(os.getenv("RAMR_N", "200"))
MODELS = os.getenv("RAMR_MODELS", "qwen3-coder:30b,glm-5.2:cloud").split(",")
MAXTOK = int(os.getenv("RAMR_MAXTOK", "300"))
rng = np.random.default_rng(73)


def call_model(model, ctx, q):
    sysmsg = ("Answer using ONLY the provided facts; reason step by step in at most two sentences. If the facts "
              "are insufficient, say UNKNOWN. End with exactly:\nANSWER: <short answer>")
    usr = (("Facts:\n" + "\n".join(ctx) + "\n\n") if ctx else "") + "Question: " + q
    body = {"model": model, "temperature": 0.0, "max_tokens": MAXTOK,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}]}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                v0.OLL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=240).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(1.0)
    return ""


if __name__ == "__main__":
    print(f"compile OK - RAMR SCALE chain-fragility (N={N_Q}, models={MODELS})", flush=True)
    qs = [v0.gen_chain(rng) for _ in range(N_Q)]
    # fixed partial: drop one hop per question (same dropped index across models for fairness)
    drop = [int(rng.integers(3)) for _ in range(N_Q)]
    results = {}
    for model in MODELS:
        print(f"\n  >>> {model} (warming)...", flush=True)
        _ = call_model(model, [], "warmup: reply ANSWER: ok")
        def one(i):
            it = qs[i]
            g = v0.hit(call_model(model, list(it["facts"]), it["q"]), it["answer"])
            pf = list(it["facts"]); pf.pop(drop[i])
            p = v0.hit(call_model(model, pf, it["q"]), it["answer"])
            return (g, p)
        with ThreadPoolExecutor(max_workers=3) as pool:
            out = list(pool.map(one, range(N_Q)))
        g = np.array([o[0] for o in out], float); p = np.array([o[1] for o in out], float)
        cf = g - p
        bs = [cf[rng.integers(0, N_Q, N_Q)].mean() for _ in range(5000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        results[model] = {"gold": float(g.mean()), "partial": float(p.mean()),
                          "chain_fragility": float(cf.mean()), "ci": [float(lo), float(hi)], "n": N_Q}
        print(f"      gold {g.mean():.3f} | partial {p.mean():.3f} | CHAIN-FRAGILITY {cf.mean():+.3f} "
              f"95% CI [{lo:+.3f},{hi:+.3f}]  (n={N_Q})", flush=True)
    print(f"\n  === SCALED CHAIN-FRAGILITY (n={N_Q}) ===", flush=True)
    for m, r in results.items():
        print(f"  {m:18s} gold {r['gold']:.3f} partial {r['partial']:.3f} -> CF {r['chain_fragility']:+.3f} "
              f"CI [{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]", flush=True)
    allpos = all(r["ci"][0] > 0.3 for r in results.values())
    print(f"\n  VERDICT: {'flagship HOLDS at scale -- every model CF CI lower-bound > 0.30' if allpos else 'mixed -- inspect per model'}", flush=True)
    json.dump({"results": results, "n": N_Q}, open("agora_output/benchmark/ramr_scale_cf_result.json", "w"))
    print("DONE", flush=True)
