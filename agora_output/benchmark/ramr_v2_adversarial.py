"""RAMR v2 -- ADVERSARIAL distraction: does distraction bite when distractors are CONFUSABLE (vs the obviously-
irrelevant ones in v1, where a strong model shrugged them off)? For each gold 3-hop chain (P works at C; C in X;
currency of X is D), add K adversarial distractor sub-chains built on NEAR-MISS companies that share C's name
prefix (e.g. gold 'Zyncorp' -> 'Zyntech','Zyndyne'), each: '<C_near> is headquartered in <Xd>' + 'The currency
of <Xd> is <Dd>'. NO contradiction (P only works at C), but at hop-2 the model may grab the confusable
'<C_near> is headquartered in ...' instead of '<C> is headquartered in ...'. Compare against a MATCHED RANDOM
control (same #facts, v1-style random distractors). If adversarial accuracy << random accuracy at the same noise,
distraction bites specifically on CONFUSABILITY -> retrieval PRECISION (entity disambiguation) is the real lever.
Cloud-free. ASCII prints."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

N_Q = int(os.getenv("RAMR_N", "30"))
K_LEVELS = [0, 1, 2, 4, 8]      # number of adversarial near-miss sub-chains
rng = np.random.default_rng(23)
SUFFIXES = ["corp","tech","dyne","labs","works","soft","grid","ware"]


def near_miss_companies(gold_company, k):
    """Companies sharing gold's name prefix (first 3 chars) but a different suffix -> lexically confusable."""
    prefix = gold_company[:3]
    cands = [prefix + s for s in SUFFIXES if not gold_company.endswith(s)]
    rng.shuffle(cands)
    return cands[:k] if k <= len(cands) else (cands * (k // len(cands) + 1))[:k]


def adversarial_facts(item, k):
    gold_c = item["entities"][1]            # the gold company (P works at C)
    out = []
    for cn in near_miss_companies(gold_c, k):
        xd = rng.choice(v0.COUNTRIES); dd = rng.choice(v0.CURRENCIES)
        out += [f"{cn} is headquartered in {xd}.", f"The currency of {xd} is the {dd}."]
    return out


if __name__ == "__main__":
    print(f"compile OK - RAMR v2 ADVERSARIAL distraction ({v0.MODEL}, N={N_Q}); near-miss vs random control", flush=True)
    qs = [v0.gen_chain(rng) for _ in range(N_Q)]
    def run(item):
        out = {}
        for k in K_LEVELS:
            adv = adversarial_facts(item, k)                       # 2*k confusable facts
            ctx = list(item["facts"]) + adv; rng.shuffle(ctx)
            out[("adv", k)] = v0.hit(v0.call(ctx, item["q"]), item["answer"])
            # matched random control: same #distractor facts, but random (v1-style)
            ctxr = list(item["facts"]) + v0.distractors(rng, len(adv)); rng.shuffle(ctxr)
            out[("rnd", k)] = v0.hit(v0.call(ctxr, item["q"]), item["answer"])
        return out
    with ThreadPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(run, qs))
    print(f"\n  n={len(res)}; gold chain = 3 facts. Accuracy at each adversarial sub-chain count:", flush=True)
    print(f"  K adv-chains | #distractor facts | ADVERSARIAL acc | RANDOM-control acc (same #facts)", flush=True)
    adv_acc, rnd_acc = {}, {}
    for k in K_LEVELS:
        a = float(np.mean([r[("adv", k)] for r in res])); rr = float(np.mean([r[("rnd", k)] for r in res]))
        adv_acc[k] = a; rnd_acc[k] = rr
        print(f"    {k:2d}           |   {2*k:3d}              |   {a:.3f}          |   {rr:.3f}", flush=True)
    a_clean = adv_acc[0]; a_worst = adv_acc[K_LEVELS[-1]]; r_worst = rnd_acc[K_LEVELS[-1]]
    print(f"\n  === FINDINGS ===", flush=True)
    print(f"  clean (0 distractors): {a_clean:.3f}", flush=True)
    print(f"  at {K_LEVELS[-1]} near-miss chains ({2*K_LEVELS[-1]} facts): adversarial {a_worst:.3f} vs random {r_worst:.3f} "
          f"(adversarial penalty {a_worst-r_worst:+.3f})", flush=True)
    print(f"\n  === VERDICT ===", flush=True)
    if (a_clean - a_worst) >= 0.1 and (r_worst - a_worst) >= 0.1:
        print(f"  CONFUSABILITY IS THE REAL DISTRACTION LEVER: adversarial near-miss distractors collapse accuracy "
              f"{a_clean:.2f}->{a_worst:.2f}, while the SAME COUNT of random distractors barely hurts ({r_worst:.2f}). "
              f"So the distraction tax is driven by ENTITY-CONFUSABILITY, not raw context volume -- retrieval "
              f"PRECISION (disambiguating near-miss entities), not just recall, gates multi-hop accuracy. This is "
              f"the v2 metric the benchmark needed, and a sharp, defensible finding.", flush=True)
    elif (a_clean - a_worst) >= 0.1:
        print(f"  adversarial distractors hurt ({a_clean:.2f}->{a_worst:.2f}) but random ones hurt similarly "
              f"({r_worst:.2f}) -> harm is volume-driven here, not confusability-specific.", flush=True)
    else:
        print(f"  even adversarial near-miss distractors don't materially hurt ({a_worst:.2f}); the model "
              f"disambiguates well -- need harder confusability (shared bridge entities / longer chains).", flush=True)
    json.dump({"adv": {str(k): adv_acc[k] for k in K_LEVELS}, "rnd": {str(k): rnd_acc[k] for k in K_LEVELS},
               "model": v0.MODEL, "n": len(res)}, open("agora_output/benchmark/ramr_v2_result.json", "w"))
    print("DONE", flush=True)
