"""RAMR v2b -- QUERY-ANCHOR adversarial distraction (the corrected v2 design). v2 showed lexical near-miss at the
BRIDGE (near-miss company) doesn't bite: a strong reader matches the full gold token. The corrected hypothesis:
confusability matters at the QUERY ANCHOR -- the entity the question pivots on. The question is 'currency of the
country where the company that <P> works at is headquartered'. So we seed K near-miss PERSON names sharing P's
name prefix (gold 'Vorander' -> 'Vorette','Vorovic'), each carrying a COMPLETE FALSE CHAIN (works-at / hq-in /
currency-of) to a DIFFERENT currency. No contradiction (P only works at the gold company; the near-miss people are
distinct). If the reader confuses the anchor (P vs P_near) it follows the wrong chain and answers wrong. Matched
RANDOM control: same #distractor facts, v1-style random. Falsifier: if adversarial accuracy is not materially
below the random control at equal noise, even anchor-level lexical near-miss doesn't bite -> the DISTRACTION metric
needs entity COLLISION or SCALE, not lexical similarity. Cloud-free. ASCII prints."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0
from concurrent.futures import ThreadPoolExecutor

N_Q = int(os.getenv("RAMR_N", "30"))
K_LEVELS = [0, 1, 3, 5, 7]      # near-miss PERSON false-chains (<=7 unique suffixes per prefix)
rng = np.random.default_rng(29)
PSUF = ["ander", "ette", "ovic", "wyn", "ash", "oro", "ill", "une"]   # mirrors v0 PEOPLE suffixes


def near_miss_people(gold_person, k):
    """People sharing gold's 3-char name prefix but a different suffix -> confusable as the query anchor."""
    prefix = gold_person[:3]
    cands = [prefix + s for s in PSUF if not gold_person.endswith(s)]
    rng.shuffle(cands)
    return cands[:k]


def anchor_false_chains(item, k):
    """K complete false chains, each anchored on a near-miss PERSON, leading to a DIFFERENT currency (fair)."""
    gold_p, gold_cur = item["entities"][0], item["answer"]
    out = []
    for pn in near_miss_people(gold_p, k):
        cd = rng.choice(v0.COMPANIES); xd = rng.choice(v0.COUNTRIES)
        dd = rng.choice(v0.CURRENCIES)
        while dd.lower() == gold_cur.lower():      # never let a distractor chain end at the gold answer
            dd = rng.choice(v0.CURRENCIES)
        out += [f"{pn} works at {cd}.", f"{cd} is headquartered in {xd}.", f"The currency of {xd} is the {dd}."]
    return out


if __name__ == "__main__":
    print(f"compile OK - RAMR v2b QUERY-ANCHOR distraction ({v0.MODEL}, N={N_Q}); near-miss persons vs random", flush=True)
    qs = [v0.gen_chain(rng) for _ in range(N_Q)]
    def run(item):
        out = {}
        for k in K_LEVELS:
            adv = anchor_false_chains(item, k)                      # 3*k confusable facts (complete false chains)
            ctx = list(item["facts"]) + adv; rng.shuffle(ctx)
            out[("adv", k)] = v0.hit(v0.call(ctx, item["q"]), item["answer"])
            ctxr = list(item["facts"]) + v0.distractors(rng, len(adv)); rng.shuffle(ctxr)   # matched random control
            out[("rnd", k)] = v0.hit(v0.call(ctxr, item["q"]), item["answer"])
        return out
    with ThreadPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(run, qs))
    print(f"\n  n={len(res)}; gold chain = 3 facts; each near-miss = a COMPLETE false 3-fact chain on a confusable person.", flush=True)
    print(f"  K persons | #distractor facts | ANCHOR-ADV acc | RANDOM-control acc (same #facts)", flush=True)
    adv_acc, rnd_acc = {}, {}
    for k in K_LEVELS:
        a = float(np.mean([r[("adv", k)] for r in res])); rr = float(np.mean([r[("rnd", k)] for r in res]))
        adv_acc[k] = a; rnd_acc[k] = rr
        print(f"    {k:2d}        |   {3*k:3d}             |   {a:.3f}        |   {rr:.3f}", flush=True)
    a_clean = adv_acc[0]; a_worst = adv_acc[K_LEVELS[-1]]; r_worst = rnd_acc[K_LEVELS[-1]]
    # bootstrap CI of the adversarial-vs-random gap at the worst noise level (paired over questions)
    da = np.array([r[("adv", K_LEVELS[-1])] for r in res], float) - np.array([r[("rnd", K_LEVELS[-1])] for r in res], float)
    bs = [da[rng.integers(0, len(da), len(da))].mean() for _ in range(5000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"\n  === FINDINGS ===", flush=True)
    print(f"  clean (0 distractors): {a_clean:.3f}", flush=True)
    print(f"  at {K_LEVELS[-1]} near-miss persons ({3*K_LEVELS[-1]} facts): anchor-adv {a_worst:.3f} vs random {r_worst:.3f}", flush=True)
    print(f"  adversarial-minus-random gap: {a_worst-r_worst:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]", flush=True)
    print(f"\n  === VERDICT ===", flush=True)
    if (a_clean - a_worst) >= 0.1 and hi < 0:
        print(f"  ANCHOR CONFUSABILITY BITES: near-miss PERSON false-chains collapse accuracy {a_clean:.2f}->{a_worst:.2f}, "
              f"significantly below the matched random control (gap {a_worst-r_worst:+.2f}, CI excludes 0). The "
              f"distraction tax is driven by confusability at the QUERY ANCHOR, not raw volume -- the reader follows "
              f"the wrong chain when a similarly-named entity offers a complete alternative. This is the v2 metric the "
              f"benchmark needed: a sharp, fair (non-contradictory), reproducible DISTRACTION test.", flush=True)
    elif (a_clean - a_worst) >= 0.1:
        print(f"  anchor distractors hurt ({a_clean:.2f}->{a_worst:.2f}) but NOT more than random ({r_worst:.2f}; gap "
              f"{a_worst-r_worst:+.2f}, CI [{lo:+.2f},{hi:+.2f}]) -> harm is volume-driven, not anchor-confusability.", flush=True)
    else:
        print(f"  NEGATIVE again: even complete false chains on near-miss PERSONS don't materially hurt ({a_worst:.2f} "
              f"vs clean {a_clean:.2f}). On clean synthetic chains this strong reader is robust to lexical "
              f"confusability at BOTH bridge and anchor. The DISTRACTION metric needs entity COLLISION (shared exact "
              f"tokens) or SCALE (50-100 facts), not lexical near-miss -> pivot v2c to scale + a weaker reader.", flush=True)
    json.dump({"adv": {str(k): adv_acc[k] for k in K_LEVELS}, "rnd": {str(k): rnd_acc[k] for k in K_LEVELS},
               "gap_ci": [lo, hi], "model": v0.MODEL, "n": len(res)},
              open("agora_output/benchmark/ramr_v2b_result.json", "w"))
    print("DONE", flush=True)
