"""Chatbot Arena and style: a length bias in the VOTES, but the leaderboard ORDER is mostly skill.

Public probe for the Crucible result "How much of Chatbot Arena is style?"
(dancenitra.github.io/agora/public/posts/chatbot-arena-style-not-skill.html).

CLAIM under test (Chiang et al. 2024, arXiv:2403.04132): Chatbot Arena (LMArena) Elo, from millions of human
pairwise votes, ranks LLMs by genuine answer quality -- cite the rank to pick a model.

TWO tests on the real public votes (lmarena-ai/arena-human-preference-140k; conv_metadata carries the style
stats; ties dropped; NO model identity, NO content):
  [A] STYLE-ONLY vote prediction: a logistic classifier on style-only features (length + markdown headers /
      lists / bold, as side-A-minus-B diffs) predicts the human winner ~61.5% (chance ~50.8%).
  [B] WITHIN-PAIR control (the decisive vote-level test): among battles between the SAME two models (quality
      held fixed), does the LONGER answer still win? If it were pure quality-proxy it would fall to ~chance;
      instead it STAYS ~62% -- so the length preference in votes is GENUINE, not just "better models write
      longer".
  [C] leaderboard-ORDER reproduction: rank models by the style-only classifier's win-propensity and correlate
      with the real win-rate rank -> Spearman ~0.74.

HONEST READING (the important part): [A]+[B] show individual VOTES carry a real length/style bias. But [C]'s
0.74 is a CORRELATIONAL upper bound, NOT "74% of the order is style" -- style and quality co-move ACROSS models
(better models write longer), so a style-only rank tracks the order without style causing it. The decisive
ORDER-level test is LMSYS's style-CONTROLLED Elo (length+markdown regressed out): it reorders only MODESTLY
(GPT-4o-mini 6->11, Grok-2-mini 6->18, Claude 3.5 Sonnet 6->4; the top stays near the top) -- so the leaderboard
ORDER is mostly quality, with style a partial confound that moves specific models. Takeaway: use style controls
for individual votes; the rank order is mostly real skill. Prior art: Zheng 2023 (verbosity), LMSYS style-control
2024, Feuer et al. "Style Outweighs Substance" 2024 (LLM judges, not the human Arena).

Runnable (needs numpy + pandas + network; downloads the public HF dataset):  python arena_style_only.py
MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/agora/tree/main/inspeximus).
"""
import io
import json
import urllib.request
from collections import defaultdict

import numpy as np
import pandas as pd

FILES = [f"https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k/resolve/refs%2Fconvert%2Fparquet/default/train/000{i}.parquet" for i in (0, 1)]


def load():
    dfs = []
    for u in FILES:
        raw = urllib.request.urlopen(u, timeout=300).read()
        dfs.append(pd.read_parquet(io.BytesIO(raw), columns=["model_a", "model_b", "winner", "conv_metadata"]))
    return pd.concat(dfs, ignore_index=True)


def md(x):
    return json.loads(x) if isinstance(x, str) else x


def feats(m):
    def side(s):
        tok = m.get(f"sum_assistant_{s}_tokens", 0) or 0
        hc = sum((m.get(f"header_count_{s}", {}) or {}).values())
        lc = sum((m.get(f"list_count_{s}", {}) or {}).values())
        bc = sum((m.get(f"bold_count_{s}", {}) or {}).values())
        return np.array([tok, hc, lc, bc], dtype=float)
    return side("a") - side("b")


def fit_logreg(X, y, iters=300, lr=0.3):
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    Xs = np.hstack([np.ones((len(Xs), 1)), Xs])
    w = np.zeros(Xs.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xs @ w))
        w -= lr * (Xs.T @ (p - y)) / len(y)
    return w, X.mean(0), X.std(0)


def predict(w, mean, std, X):
    Xs = (X - mean) / (std + 1e-9)
    Xs = np.hstack([np.ones((len(Xs), 1)), Xs])
    return 1 / (1 + np.exp(-Xs @ w))


def spearman(a, b):
    return float(np.corrcoef(pd.Series(a).rank().values, pd.Series(b).rank().values)[0, 1])


def main():
    print("downloading lmarena-ai/arena-human-preference-140k ...", flush=True)
    df = load()
    df = df[df["winner"].isin(["model_a", "model_b"])].copy()
    print("decided battles:", len(df), flush=True)
    X = np.vstack([feats(md(m)) for m in df["conv_metadata"]])
    y = (df["winner"].values == "model_a").astype(float)
    tokdiff = X[:, 0]

    # [A] style-only held-out vote prediction
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(y)); cut = int(0.7 * len(y))
    tr, te = idx[:cut], idx[cut:]
    w, mean, std = fit_logreg(X[tr], y[tr])
    p_te = predict(w, mean, std, X[te])
    acc = float(((p_te > 0.5) == (y[te] == 1)).mean())
    maj = float(max(y[te].mean(), 1 - y[te].mean()))
    wl, ml, sl = fit_logreg(X[tr][:, :1], y[tr])
    acc_len = float(((predict(wl, ml, sl, X[te][:, :1]) > 0.5) == (y[te] == 1)).mean())
    print("\n[A] STYLE-ONLY held-out vote accuracy: %.3f  | length-only %.3f | chance/majority %.3f" % (acc, acc_len, maj))

    # [B] WITHIN-PAIR control: quality (model pair) held fixed -> does the longer answer still win?
    longer_wins = (y == (tokdiff > 0)).astype(float)  # side with more tokens won?
    keep = tokdiff != 0
    byp = defaultdict(list)
    for i in np.where(keep)[0]:
        byp[tuple(sorted([df["model_a"].values[i], df["model_b"].values[i]]))].append(longer_wins[i])
    print("[B] WITHIN-PAIR longer-answer-wins (model pair fixed = quality held constant):")
    print("    unconditional: %.3f" % longer_wins[keep].mean())
    for N in (20, 50):
        pooled = [x for v in byp.values() if len(v) >= N for x in v]
        npairs = sum(1 for v in byp.values() if len(v) >= N)
        print("    >=%d battles/pair (%d pairs, %d battles): %.3f  (still ~62%% -> a GENUINE length bias)"
              % (N, npairs, len(pooled), np.mean(pooled)))

    # [C] leaderboard-ORDER reproduction
    p_all = predict(w, mean, std, X)
    aw, an, sw, sn = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for i, (ma, mb) in enumerate(zip(df["model_a"].values, df["model_b"].values)):
        aw[ma] += y[i]; an[ma] += 1; aw[mb] += 1 - y[i]; an[mb] += 1
        sw[ma] += p_all[i]; sn[ma] += 1; sw[mb] += 1 - p_all[i]; sn[mb] += 1
    print("[C] leaderboard-ORDER reproduction (Spearman: style-only rank vs real win-rate rank):")
    for minb in (100, 200, 500):
        ms = [m for m in an if an[m] >= minb]
        rho = spearman([sw[m] / sn[m] for m in ms], [aw[m] / an[m] for m in ms])
        print("    >=%d battles (%d models): rho=%.3f" % (minb, len(ms), rho))

    print("\nREADING: [A]+[B] -> individual VOTES carry a real length bias (survives holding the model pair fixed).")
    print("[C]'s rho~0.74 is a CORRELATIONAL upper bound, not '74%% of the order is style' (style co-moves with")
    print("quality across models). The decisive ORDER test -- LMSYS's style-CONTROLLED Elo -- reorders only")
    print("MODESTLY (top stays), so the leaderboard ORDER is mostly skill. Bias the votes, not (mostly) the order.")


if __name__ == "__main__":
    main()
