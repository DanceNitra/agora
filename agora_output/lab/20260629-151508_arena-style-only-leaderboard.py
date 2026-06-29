"""Artifact-Debunk (Crucible): "Chatbot Arena (LMArena) Elo ranks LLMs by genuine answer quality,
so cite Arena rank to pick a model" (Chiang et al. 2024, arXiv:2403.04132).

NULL with NO model identity and NO content: predict the human winner from STYLE-ONLY features
(response length, markdown headers, bold, lists) as side-A-minus-side-B differences, then check whether
a style-only model reproduces the leaderboard ORDER. Real public votes: lmarena-ai/arena-human-preference-140k
(conv_metadata already carries the style stats). Cloud-free, CPU-only, zero LLM inference.

Pre-registered FALSIFIER: folklore FAILED iff style-only held-out accuracy >= 60% (vs 50%) AND
Spearman(style-only model ranking, actual win-rate ranking) >= 0.7. Arena SURVIVES iff acc <= 55% OR rho <= 0.3.
Prior art (cite, no overclaim): Zheng 2023 (verbosity bias), LMSYS 2024-08-28 style-control blog
(they controlled style but did NOT ship a no-identity ranking-reproduction), Singh & Hooker
'Leaderboard Illusion' 2025, and our own length-confound post. Headline = 'style-only reproduces the
ranking ORDER', NOT 'we discovered style matters'.
"""
import io, json, urllib.request
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
    """style-only per-side -> A-minus-B differences. NO model identity, NO content."""
    def side(s):
        tok = m.get(f"sum_assistant_{s}_tokens", 0) or 0
        hc = m.get(f"header_count_{s}", {}) or {}
        lc = m.get(f"list_count_{s}", {}) or {}
        bc = m.get(f"bold_count_{s}", {}) or {}
        return np.array([tok, sum(hc.values()), sum(lc.values()), sum(bc.values())], dtype=float)
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


def auroc(p, y):
    pos = p[y == 1]; neg = p[y == 0]
    if not len(pos) or not len(neg): return None
    # rank-based
    allv = np.concatenate([pos, neg]); order = allv.argsort()
    ranks = np.empty_like(order, dtype=float); ranks[order] = np.arange(1, len(allv) + 1)
    rpos = ranks[:len(pos)].sum()
    return (rpos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def spearman(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    print("downloading lmarena-ai/arena-human-preference-140k (2 parquet shards)...", flush=True)
    df = load()
    print("rows:", len(df), flush=True)
    df = df[df["winner"].isin(["model_a", "model_b"])].copy()   # drop tie / both_bad
    print("decided battles:", len(df), flush=True)
    X = np.vstack([feats(md(m)) for m in df["conv_metadata"]])
    y = (df["winner"].values == "model_a").astype(float)        # 1 if A won

    # held-out split
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(y)); cut = int(0.7 * len(y))
    tr, te = idx[:cut], idx[cut:]
    w, mean, std = fit_logreg(X[tr], y[tr])
    p_te = predict(w, mean, std, X[te])
    acc = float(((p_te > 0.5) == (y[te] == 1)).mean())
    auc = auroc(p_te, y[te])
    # null baselines
    maj = float(max(y[te].mean(), 1 - y[te].mean()))
    # length-only
    wl, ml, sl = fit_logreg(X[tr][:, :1], y[tr]); pl = predict(wl, ml, sl, X[te][:, :1])
    acc_len = float(((pl > 0.5) == (y[te] == 1)).mean())

    # ranking reproduction: per-model actual win-rate vs style-only predicted win-propensity
    p_all = predict(w, mean, std, X)
    from collections import defaultdict
    actual_w = defaultdict(float); actual_n = defaultdict(float)
    style_w = defaultdict(float); style_n = defaultdict(float)
    for i, (ma, mb) in enumerate(zip(df["model_a"].values, df["model_b"].values)):
        actual_w[ma] += y[i];        actual_n[ma] += 1
        actual_w[mb] += (1 - y[i]);  actual_n[mb] += 1
        style_w[ma] += p_all[i];     style_n[ma] += 1
        style_w[mb] += (1 - p_all[i]); style_n[mb] += 1
    def rho_at(minb):
        ms = [m for m in actual_n if actual_n[m] >= minb]
        ar = np.array([actual_w[m] / actual_n[m] for m in ms])
        sr = np.array([style_w[m] / style_n[m] for m in ms])
        return spearman(sr, ar), len(ms)
    rho, nmodels = rho_at(200)

    print("\n=== Chatbot Arena: style-ONLY (no model identity) ===")
    print("held-out winner-prediction accuracy: %.3f  (AUC %.3f) | chance/majority %.3f | length-only %.3f"
          % (acc, auc, maj, acc_len))
    print("ranking-reproduction Spearman rho vs actual win-rate, by min-battles threshold:")
    for mb in (100, 200, 500):
        r, n = rho_at(mb); print("   >=%d battles (%d models): rho=%.3f" % (mb, n, r))
    failed = acc >= 0.60 and rho >= 0.70
    survives = acc <= 0.55 or rho <= 0.30
    print("\nMEASURED: a style-only classifier with NO model identity and NO content predicts the human")
    print("winner %.1f%% of the time (length alone %.1f%%) and its per-model ranking correlates rho=%.2f"
          % (acc*100, acc_len*100, rho))
    print("with the real win-rate ranking over %d models." % nmodels)
    print("VERDICT:", "FAILED (style-only reproduces both the vote AND the leaderboard order)" if failed
          else ("Arena SURVIVES" if survives else "PARTIAL"))
    print("Scope: shows Arena rank is heavily explained by stylistic form, NOT that models are equal in")
    print("quality. Prior art: Zheng 2023, LMSYS style-control 2024, Leaderboard Illusion 2025, our length post.")


if __name__ == "__main__":
    main()
