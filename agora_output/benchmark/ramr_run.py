"""RAMR single runner / scoring CLI (point-2 hardening). Loads the FROZEN versioned dataset (data/ramr_chains_*.jsonl)
-- never regenerates -- and scores a model on the three LLM-reader metrics with paired bootstrap CIs:
  CONVERSION      = gold accuracy (complete chain)
  CHAIN-FRAGILITY = gold - partial (drop the fixed hop)
  DISTRACTION     = gold - noisy  (gold + first DIST distractor-pool facts)
Usage:
  python ramr_run.py --model qwen3-coder:30b [--n 200] [--dist 30] [--maxtok 300]
Verifies contamination (closed-book ~0) on a small probe. Cloud allowed (owner 2026-06-23): --model glm-5.2:cloud
etc. via the local Ollama route. ASCII prints; writes data/run_<model>.json."""
import os, sys, json, time, argparse, urllib.request, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_frozen():
    files = sorted(glob.glob(os.path.join(DATA, "ramr_chains_v*.jsonl")))
    if not files:
        sys.exit("no frozen dataset -- run build_dataset.py first")
    path = files[-1]
    items = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    man = json.load(open(os.path.join(DATA, "manifest.json")))
    return path, items, man


def call(model, ctx, q, maxtok):
    sysmsg = ("Answer using ONLY the provided facts; reason step by step in at most two sentences. If the facts "
              "are insufficient, say UNKNOWN. End with exactly:\nANSWER: <short answer>")
    usr = (("Facts:\n" + "\n".join(ctx) + "\n\n") if ctx else "") + "Question: " + q
    body = {"model": model, "temperature": 0.0, "max_tokens": maxtok,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}]}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                v0.OLL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=240).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(1.0)
    return ""


def paired_ci(a, b, rng, B=5000):
    d = np.array(a, float) - np.array(b, float)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(B)]
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3-coder:30b")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--dist", type=int, default=30)
    ap.add_argument("--maxtok", type=int, default=300)
    a = ap.parse_args()
    path, items, man = load_frozen()
    items = items[:a.n]
    rng = np.random.default_rng(7)
    print(f"RAMR v{man['version']} | dataset {os.path.basename(path)} (sha "
          f"{list(man['files'].values())[0]['sha256'][:12]}) | model {a.model} | n={len(items)} | dist={a.dist}", flush=True)

    def run(it):
        gold = list(it["gold_facts"])
        partial = list(it["gold_facts"]); partial.pop(it["drop_index"])
        noisy = list(it["gold_facts"]) + it["distractor_pool"][:a.dist]; rng.shuffle(noisy)
        g = v0.hit(call(a.model, gold, it["question"], a.maxtok), it["answer"])
        p = v0.hit(call(a.model, partial, it["question"], a.maxtok), it["answer"])
        nz = v0.hit(call(a.model, noisy, it["question"], a.maxtok), it["answer"])
        return (g, p, nz)
    with ThreadPoolExecutor(max_workers=3) as pool:
        out = list(pool.map(run, items))
    G = [o[0] for o in out]; P = [o[1] for o in out]; Nz = [o[2] for o in out]
    # contamination probe: closed-book on a 20-item sample (should be ~0)
    cb = [v0.hit(call(a.model, [], items[i]["question"], a.maxtok), items[i]["answer"]) for i in range(min(20, len(items)))]
    conv = float(np.mean(G))
    cf, cf_lo, cf_hi = paired_ci(G, P, rng)
    ds, ds_lo, ds_hi = paired_ci(G, Nz, rng)
    print(f"\n  CONVERSION (gold acc)       : {conv:.3f}", flush=True)
    print(f"  CHAIN-FRAGILITY (gold-part) : {cf:+.3f}  95% CI [{cf_lo:+.3f},{cf_hi:+.3f}]", flush=True)
    print(f"  DISTRACTION (gold-noisy@{a.dist}) : {ds:+.3f}  95% CI [{ds_lo:+.3f},{ds_hi:+.3f}]", flush=True)
    print(f"  contamination (closed-book) : {float(np.mean(cb)):.3f}  (should be ~0 -> uncontaminated)", flush=True)
    res = {"version": man["version"], "dataset": os.path.basename(path), "model": a.model, "n": len(items),
           "dist": a.dist, "conversion": conv, "chain_fragility": {"v": cf, "ci": [cf_lo, cf_hi]},
           "distraction": {"v": ds, "ci": [ds_lo, ds_hi]}, "closed_book": float(np.mean(cb))}
    safe = re.sub(r"[^a-z0-9]+", "_", a.model.lower())
    json.dump(res, open(os.path.join(DATA, f"run_{safe}.json"), "w"), indent=2)
    print(f"\n  wrote data/run_{safe}.json", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
