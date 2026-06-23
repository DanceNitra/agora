"""RAMR v2c -- MODEL-ZOO + SCALE validation (guard against single-model premature conclusions).
All prior RAMR findings were on qwen3-coder:30b alone. The reframed thesis (retrieval COMPLETENESS dominates
PRECISION: a missing hop is catastrophic, distraction is mild) must hold across MODEL FAMILIES and CAPABILITY
LEVELS or it's a qwen quirk. This runs the thesis-critical conditions across a cloud-free zoo spanning 3 families:
  qwen3-coder:30b (strong, Qwen) | qwen2.5:7b (weak, Qwen) | llama3.1:8b (Meta) | gemma2:9b (Google)
Conditions:
  gold     : complete chain (CONVERSION ceiling)
  partial  : gold minus ONE hop (CHAIN-FRAGILITY -- the completeness axis)
  dist10/30/60 : gold + N random distractors (DISTRACTION at SCALE -- the precision axis, into the realistic
                 ~50-60-chunk regime where v1/v2 only went to ~30)
Per model we report CHAIN-FRAGILITY (gold-partial) and DISTRACTION (gold-dist60), so we can see whether:
  (a) chain-fragility stays catastrophic across ALL families (robustness of the killer metric), and
  (b) distraction bites MORE on weaker models / at scale (precision-sensitivity as a CAPABILITY axis).
Also dumps a fixed BLIND subset for the Claude (different-family strong reasoner) cross-check -> ramr_v2c_claude_tasks.json
(+ a separate hidden key). Models loaded sequentially (Ollama stays hot per model). Cloud-free. ASCII prints."""
import os, sys, json, time, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

N_Q = int(os.getenv("RAMR_N", "20"))
MODELS = os.getenv("RAMR_MODELS", "qwen3-coder:30b,qwen2.5:7b,llama3.1:8b,gemma2:9b").split(",")
MAXTOK = int(os.getenv("RAMR_MAXTOK", "300"))   # bump for reasoning models that spend budget on thinking
DIST = [10, 30, 60]
rng = np.random.default_rng(43)


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


def ctx_for(item, cond):
    if cond == "gold": return list(item["facts"])
    if cond == "partial":
        f = list(item["facts"]); f.pop(int(rng.integers(len(f)))); return f
    if cond.startswith("dist"):
        n = int(cond[4:]); c = list(item["facts"]) + v0.distractors(rng, n); rng.shuffle(c); return c
    return []


if __name__ == "__main__":
    conds = ["gold", "partial"] + [f"dist{n}" for n in DIST]
    print(f"compile OK - RAMR v2c MODEL-ZOO+SCALE (N={N_Q}; models={MODELS}; conds={conds})", flush=True)
    qs = [v0.gen_chain(rng) for _ in range(N_Q)]
    # precompute the context for each (item,cond) ONCE so every model sees identical inputs (fair comparison)
    ctxs = [{c: ctx_for(it, c) for c in conds} for it in qs]
    results = {}   # model -> cond -> acc
    for model in MODELS:
        print(f"\n  >>> {model} (warming)...", flush=True)
        _ = call_model(model, [], "warmup: reply ANSWER: ok")     # load model hot
        acc = {}
        def one(args):
            i, c = args
            return (i, c, v0.hit(call_model(model, ctxs[i][c], qs[i]["q"]), qs[i]["answer"]))
        jobs = [(i, c) for i in range(N_Q) for c in conds]
        with ThreadPoolExecutor(max_workers=3) as pool:
            out = list(pool.map(one, jobs))
        for c in conds:
            acc[c] = float(np.mean([h for (i, cc, h) in out if cc == c]))
        results[model] = acc
        cf = acc["gold"] - acc["partial"]; ds = acc["gold"] - acc[f"dist{DIST[-1]}"]
        print(f"      gold {acc['gold']:.2f} | partial {acc['partial']:.2f} | "
              + " | ".join(f"d{n} {acc[f'dist{n}']:.2f}" for n in DIST), flush=True)
        print(f"      CHAIN-FRAGILITY {cf:+.2f} | DISTRACTION(@{DIST[-1]}) {ds:+.2f}", flush=True)

    print(f"\n  === ZOO SUMMARY (n={N_Q}) ===", flush=True)
    print(f"  {'model':16s} | gold | part | d{DIST[-1]:<2d} | CHAIN-FRAG | DISTRACT@{DIST[-1]}", flush=True)
    cfs, dss = [], []
    for m in MODELS:
        a = results[m]; cf = a["gold"]-a["partial"]; ds = a["gold"]-a[f"dist{DIST[-1]}"]
        cfs.append(cf); dss.append(ds)
        print(f"  {m:16s} | {a['gold']:.2f} | {a['partial']:.2f} | {a[f'dist{DIST[-1]}']:.2f} | {cf:+.3f}     | {ds:+.3f}", flush=True)
    print(f"\n  === VERDICT (cross-family) ===", flush=True)
    cf_min = min(cfs); ds_max = max(dss)
    if cf_min >= 0.3 and (np.mean(cfs) - np.mean(dss)) >= 0.2:
        print(f"  THESIS HOLDS ACROSS FAMILIES: chain-fragility is large for EVERY model (min {cf_min:+.2f}; mean "
              f"{np.mean(cfs):+.2f}) and dominates distraction (mean {np.mean(dss):+.2f}). Completeness >> precision "
              f"is NOT a qwen artifact -- it reproduces across Qwen, Meta and Google families. {('Distraction does '+'grow on weaker models / at scale (max %.2f).'%ds_max) if ds_max>=0.2 else 'Distraction stays mild even on the weakest model and at 60 facts.'}", flush=True)
    elif np.mean(cfs) > np.mean(dss):
        print(f"  PARTIAL: completeness still beats precision on average (CF {np.mean(cfs):+.2f} > DIST {np.mean(dss):+.2f}) "
              f"but the margin/robustness is weaker than on qwen alone -- model-dependent. Distraction max {ds_max:+.2f}.", flush=True)
    else:
        print(f"  THESIS DOES NOT GENERALIZE: distraction (mean {np.mean(dss):+.2f}) rivals/exceeds chain-fragility "
              f"(mean {np.mean(cfs):+.2f}) once weaker models / scale are included -> the qwen-only conclusion was "
              f"premature. Precision matters too; report both axes, no single-model headline.", flush=True)

    # --- dump a fixed BLIND subset for the Claude (different-family strong reasoner) cross-check ---
    sub_conds = ["gold", "partial", f"dist{DIST[-1]}"]
    n_claude = min(12, N_Q)
    tasks, key = [], {}
    for i in range(n_claude):
        for c in sub_conds:
            tid = f"q{i}_{c}"
            tasks.append({"id": tid, "facts": ctxs[i][c], "question": qs[i]["q"]})
            key[tid] = qs[i]["answer"]
    json.dump(tasks, open("agora_output/benchmark/ramr_v2c_claude_tasks.json", "w"), indent=1)
    json.dump(key, open("agora_output/benchmark/ramr_v2c_claude_key.json", "w"))
    _rp = "agora_output/benchmark/ramr_v2c_result.json"
    merged = {}
    if os.path.exists(_rp):
        try: merged = json.load(open(_rp)).get("results", {})
        except Exception: merged = {}
    merged.update(results)
    json.dump({"results": merged, "models": list(merged.keys()), "n": N_Q, "dist": DIST, "conds": conds},
              open(_rp, "w"))
    print(f"\n  dumped {len(tasks)} blind Claude tasks ({n_claude} items x {sub_conds}) -> ramr_v2c_claude_tasks.json", flush=True)
    print("DONE", flush=True)
