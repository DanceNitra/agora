"""Every number in "An agent's past lessons helped when outside outcomes wrote them, not when a ranker picked them".

Recomputes each rate and each paired 95% bootstrap interval from the per-fork results in
taste_outcome_not_ranking_data/: one 0/1 per fork and arm, 1 when the model answered right in both
option orders. No model is called; standard library only.

    python taste_outcome_not_ranking.py
    python taste_outcome_not_ranking.py --parquet engineering.parquet   # also the near-duplicate share

The per-fork files hold fork ids and 0/1 outcomes, no Taste-Bench text. Taste-Bench (Pan et al.,
arXiv 2609.25804) is gated on Hugging Face (wenbopan/taste-bench); the near-duplicate check reads its
engineering parquet only if you pass one.

Runs behind the files (2026-09-25..28): Qwen3.8 27B and Gemma4 12B on a local Ollama, thinking off,
390 forks; Claude Opus 5.5 through `claude -p`, 160 forks (default effort for the poisoning run,
medium effort for the same-repository control). Three lessons per prompt, leave-task-out recall with
nomic-embed-text in inspeximus.
"""
import argparse
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "taste_outcome_not_ranking_data")
SEED = 20260925


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def rate(v):
    return sum(v) / len(v)


def boot(a, b, n=5000):
    """Paired bootstrap over forks, the harness's own procedure: mean difference and 95% interval."""
    rnd = random.Random(SEED)
    d = [x - y for x, y in zip(a, b)]
    stats = sorted(sum(d[rnd.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return sum(d) / len(d), stats[int(0.025 * n)], stats[int(0.975 * n)]


def arms(res):
    raw = res["raw"]
    ids = raw["ids"]
    out = {}
    for k, v in raw.items():
        if k in ("ids", "ids_per_arm") or not isinstance(v, list) or len(v) != len(ids):
            continue
        out[k] = v
    return out


def show(label, x, y=None, a=None):
    if y is None:
        print(f"  {label:58s} {rate(x):.3f}")
    else:
        m, lo, hi = boot(x, y)
        print(f"  {label:58s} {m:+.3f}  ({lo:+.3f} to {hi:+.3f})")


def repo_of(task_id):
    m = re.match(r"instance_(.+?__.+?)-[0-9a-f]{20,}", task_id)
    return m.group(1) if m else task_id.split("-")[0]


def near_duplicates(parquet, fork_ids):
    """Share of forks for which some lesson in the same repository (another task) shares at least half
    the words of one of the fork's options (word overlap over the smaller set)."""
    import pandas as pd
    rows = pd.read_parquet(parquet).to_dict("records")
    by_id = {r["id"]: r for r in rows}
    tok = lambda s: set(re.findall(r"[a-z0-9_]{3,}", s.lower()))
    hits = 0
    for fid in fork_ids:
        q = by_id[fid]
        best = 0.0
        for p in rows:
            if p["task_id"] == q["task_id"] or repo_of(p["task_id"]) != repo_of(q["task_id"]):
                continue
            for c in q["choices"]:
                for o in p["choices"]:
                    A, B = tok(c), tok(o)
                    best = max(best, len(A & B) / max(1, min(len(A), len(B))))
        hits += best >= 0.5
    return hits, len(fork_ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", help="Taste-Bench engineering parquet, for the near-duplicate share")
    a = ap.parse_args()

    s = load("taste_samerepo_opus55_medium_result.json")
    S = arms(s)
    print(f"Opus 5.5, medium effort, {len(s['raw']['ids'])} forks: the same-repository control")
    show("none", S["none"])
    show("random lessons, same repository, same surface cues", S["random_repo_match"])
    show("top 3 by embedding similarity (inspeximus recall)", S["memory_sem"])
    print(f"  {'zero-model two-line rule':58s} {s['heuristic_rate']:.3f}")
    show("same-repository random minus none", S["random_repo_match"], S["none"])
    show("similarity ranking minus same-repository random", S["memory_sem"], S["random_repo_match"])
    b = s["control_build"]
    print(f"  recalled lessons from the fork's own repository: {b['same_repo']}/{b['recalled']} "
          f"= {b['same_repo'] / b['recalled']:.1%}")
    print(f"  unparsed answers {s['unparsed']}, errors {s['errors']}")

    q = load("taste_memory_engineering_result.json")
    Q = arms(q)
    print(f"\nQwen3.8 27B, {len(q['raw']['ids'])} forks")
    show("recall minus cue-matched random lessons from any project", Q["memory_sem"], Q["control_matched"])
    show("other-repository recall", Q["memory_sem_xrepo"])
    show("cue-matched random lessons from any project", Q["control_matched"])
    show("other-repository recall minus none", Q["memory_sem_xrepo"], Q["none"])
    show("other-repository recall minus cue-matched random", Q["memory_sem_xrepo"], Q["control_matched"])

    g = load("taste_q5_engineering_gemma_full_result.json")
    G = arms(g)
    print(f"\nGemma4 12B, {len(g['raw']['ids'])} forks")
    show("recall minus cue-matched random lessons from any project", G["memory_sem"], G["control_matched"])

    w = load("taste_selfwritten_engineering_result.json")
    W = arms(w)
    print(f"\nQwen3.8 27B writes its own lessons, {len(w['raw']['ids'])} forks")
    show("told the outcome, minus none", W["self_outcome"], W["none"])
    show("judging itself, minus none", W["self_nooutcome"], W["none"])

    p = load("taste_poison_opus55_result.json")
    P = arms(p)
    print(f"\nOpus 5.5, default effort, {len(p['raw']['ids'])} forks: every lesson has a flipped twin")
    show("clean memory", P["memory_sem"])
    show("plain retrieval over the poisoned store", P["poisoned_naive"])
    show("recall only outcome-credited lessons", P["poisoned_guard"])
    print(f"  share of flipped lessons in plain retrieval's top 3: {p['poison_share_top3']['poisoned_naive']:.3f}")

    print("\nnone arms against the zero-model rule:",
          ", ".join(f"{n} {rate(v):.3f}" for n, v in (("Qwen", Q["none"]), ("Gemma", G["none"]), ("Opus", S["none"]))))

    if a.parquet:
        h, n = near_duplicates(a.parquet, s["raw"]["ids"])
        print(f"\nforks with a same-repository lesson sharing half its option words: {h}/{n} = {h / n:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
