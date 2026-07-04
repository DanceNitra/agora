"""
THE POSITIVE, in a new space: divergent generation (cloud-free). The whole day showed model/sample diversity
is useless for CONVERGENT tasks (one right answer: errors are shared, aggregation dead). Complementary
hypothesis: for DIVERGENT tasks (idea generation, where COVERAGE not consensus is the goal) the SAME diversity
is the lever. Test whether MODEL diversity yields complementary coverage (low cross-model overlap, high union)
that SAMPLE diversity does not (a model repeats its own ideas).

10 open divergent prompts; 3 models x 3 samples each (T=1.0). Parse list items, normalize, dedup. Compare at
EQUAL generation budget (3 gens): union of one model's 3 samples (intra-diversity) vs one sample from each of
3 models (inter-diversity); and the redundancy (Jaccard) within-model vs cross-model. POSITIVE if inter-model
union > intra-model union and cross-model overlap < within-model overlap: model diversity is real coverage for
generation -- the boundary law (diversity flips from noise to signal with task type).
"""
import os, re, json, time, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "divergent_generation_result.json")
URL = os.environ.get("DFLIP_URL", "http://localhost:11434/v1/chat/completions")
MODELS = os.environ.get("DFLIP_MODELS", "").split(",") if os.environ.get("DFLIP_MODELS") else ["qwen3-coder:30b", "llama3.1:8b", "gemma2:2b"]  # override: DFLIP_MODELS=a,b,c
SAMPLES = 3
WORKERS = 3
TASKS = [
    "different uses for a brick", "different uses for a paperclip", "different uses for an empty plastic bottle",
    "English words that rhyme with 'light'", "things that are typically colored red",
    "different kinds of fruit", "English words that start with the letters 'qu'",
    "different individual sports (not team sports)", "objects you might find in a kitchen drawer",
    "distinct human emotions",
]


def gen(model, task):
    body = {"model": model, "temperature": 1.0, "max_tokens": 500,
            "messages": [{"role": "system", "content": "Brainstorm. Output a plain list, one item per line, no numbering, no commentary."},
                         {"role": "user", "content": f"List as many {task} as you can. One per line."}]}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=120).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(1.0)
    return ""


def parse(txt):
    items = set()
    for line in (txt or "").splitlines():
        s = re.sub(r"^[\s\-\*\d\.\)\(]+", "", line).strip().lower()
        s = re.sub(r"[^a-z0-9 ']", "", s).strip()
        if 1 <= len(s) <= 40 and s and not s.startswith(("here", "sure", "list", "okay")):
            items.add(s)
    return items


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


if __name__ == "__main__":
    print(f"compile OK - divergent generation, {len(TASKS)} tasks, {len(MODELS)} models x{SAMPLES}", flush=True)
    jobs = [(m, t, s) for m in MODELS for t in TASKS for s in range(SAMPLES)]
    res = {}

    def run(j):
        m, t, s = j
        return (m, t, s, parse(gen(m, t)))

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for m, t, s, items in pool.map(run, jobs):
            res.setdefault(t, {}).setdefault(m, {})[s] = sorted(items)

    intra_unions, inter_unions, single_sizes = [], [], []
    within_j, cross_j = [], []
    for t in TASKS:
        sets = {m: [set(res[t][m][s]) for s in range(SAMPLES)] for m in MODELS}
        # single
        single_sizes += [len(sets[m][0]) for m in MODELS]
        # intra-model union of 3 samples
        for m in MODELS:
            intra_unions.append(len(set().union(*sets[m])))
        # inter-model: one sample (s=0) from each model
        inter_unions.append(len(set().union(*[sets[m][0] for m in MODELS])))
        # redundancy
        for m in MODELS:
            for i, jx in combinations(range(SAMPLES), 2):
                within_j.append(jaccard(sets[m][i], sets[m][jx]))
        for m1, m2 in combinations(MODELS, 2):
            cross_j.append(jaccard(sets[m1][0], sets[m2][0]))

    out = {"mean_single": round(float(np.mean(single_sizes)), 1),
           "mean_intra_model_union_3samples": round(float(np.mean(intra_unions)), 1),
           "mean_inter_model_union_3models": round(float(np.mean(inter_unions)), 1),
           "within_model_overlap_jaccard": round(float(np.mean(within_j)), 3),
           "cross_model_overlap_jaccard": round(float(np.mean(cross_j)), 3)}
    json.dump(out, open(OUT, "w"), indent=1)
    print("\n=== DIVERGENT GENERATION (unique-idea coverage, equal 3-generation budget) ===", flush=True)
    print(f"  single generation:                 {out['mean_single']} unique ideas", flush=True)
    print(f"  intra-model union (1 model x3):     {out['mean_intra_model_union_3samples']} unique ideas", flush=True)
    print(f"  INTER-model union (3 models x1):    {out['mean_inter_model_union_3models']} unique ideas", flush=True)
    print(f"  overlap: within-model={out['within_model_overlap_jaccard']}  cross-model={out['cross_model_overlap_jaccard']}", flush=True)
    intra, inter = out['mean_intra_model_union_3samples'], out['mean_inter_model_union_3models']
    cov_gain = (inter / intra - 1) * 100 if intra else 0
    print("\n=== VERDICT ===", flush=True)
    print(f"  inter-vs-intra coverage gain at equal budget = {cov_gain:+.0f}%   (cross-model overlap {out['cross_model_overlap_jaccard']} < within-model {out['within_model_overlap_jaccard']}? {out['cross_model_overlap_jaccard'] < out['within_model_overlap_jaccard']})", flush=True)
    if cov_gain >= 12 and out['cross_model_overlap_jaccard'] < out['within_model_overlap_jaccard']:
        print("  POSITIVE / BOUNDARY LAW: model diversity is COMPLEMENTARY coverage for divergent generation (lower cross-model overlap -> bigger union) where it was useless for convergent answering. Diversity's value FLIPS with task type: noise for finding THE answer, signal for finding NEW answers. The cross-model independence that bought ~0 on QA buys real coverage here.", flush=True)
    else:
        print("  WEAK: model diversity does not clearly out-cover sample diversity for generation here.", flush=True)
    print("DONE", flush=True)
