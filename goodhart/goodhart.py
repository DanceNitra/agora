"""
goodhart — when a measure becomes a target, it stops measuring. How gameable is YOUR proxy, and how
many independent metrics does it take to fix it?  (a inspeximus / nullcheck / idcheck sibling)

"Optimize the proxy" is everywhere now — reward models in RLHF, KPIs and OKRs, eval benchmarks, ad
metrics — and the failure mode is universal: the proxy reward keeps rising while the TRUE goal peaks
and then declines (reward hacking / Goodhart's law). We measured the decay: select the top 10% by a
proxy that's a fraction `gameability` corruptible, and the share of selected items that are TRULY top
falls 80% -> 19% as gameability rises. The fix the literature points to — "it's harder to game five
metrics than one" — we also measured: combining independent metrics restores the precision, and this
tells you HOW MANY you need.

    fidelity(gameability)              measured: proxy-goal correlation + selection precision at a gameability
    metrics_needed(gameability)       smallest # of independent metrics to restore precision (the fix)
    audit(gameability, n_metrics)     SAFE / GAMED verdict for your current proxy + the recommended # of metrics

Grounding (reproduced this cycle): Agora Lab e97ad5 (Goodhart / proxy degrades under optimization) —
precision 80% -> 19% as gameability rises. Zero dependencies, deterministic. `python goodhart.py`
reruns it so you can watch a single optimized proxy stop selecting the good ones.
"""
from __future__ import annotations

import math
import random


def _percentile(sorted_vals, q):
    """q-th percentile (0..1) of an already-sorted list, nearest-rank."""
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(q * len(sorted_vals))))
    return sorted_vals[i]


def _corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb) if va and vb else 0.0


def fidelity(gameability: float, *, n_metrics: int = 1, top_frac: float = 0.10,
             n: int = 20000, seed: int = 21) -> dict:
    """Measured proxy fidelity. A proxy selects for a true goal G; with `n_metrics` independent proxy
    measures each corrupted by a gameable dimension scaled by `gameability`, select the top `top_frac`
    by the (averaged) proxy. Returns the proxy-goal correlation and the PRECISION: of those the proxy
    picks, what fraction are truly in the top `top_frac` by G. Higher gameability -> lower precision."""
    rng = random.Random(seed)
    G = [rng.gauss(0, 1) for _ in range(n)]
    # combined proxy = G + gameability * mean(independent gameable dims) + measurement noise
    gdims = [[rng.gauss(0, 1) for _ in range(n)] for _ in range(max(1, n_metrics))]
    P = []
    for i in range(n):
        gmean = sum(gd[i] for gd in gdims) / len(gdims)
        P.append(G[i] + gameability * gmean + 0.3 * rng.gauss(0, 1))
    p_cut = _percentile(sorted(P), 1 - top_frac)
    g_cut = _percentile(sorted(G), 1 - top_frac)
    sel = [i for i in range(n) if P[i] >= p_cut]
    precision = sum(1 for i in sel if G[i] >= g_cut) / len(sel) if sel else 0.0
    return {"gameability": gameability, "n_metrics": max(1, n_metrics),
            "proxy_goal_corr": round(_corr(P, G), 3), "precision": round(precision, 3)}


def metrics_needed(gameability: float, *, target_precision: float = 0.7, max_metrics: int = 12,
                   **kw) -> dict:
    """How many INDEPENDENT proxy metrics must you combine so the proxy still selects the truly-good
    at >= target_precision? (Independent gameable noise averages out — "harder to game five than one".)
    Returns the smallest sufficient count + the precision curve over metric counts."""
    curve = []
    need = None
    for m in range(1, max_metrics + 1):
        prec = fidelity(gameability, n_metrics=m, **kw)["precision"]
        curve.append({"n_metrics": m, "precision": prec})
        if need is None and prec >= target_precision:
            need = m
    return {"gameability": gameability, "target_precision": target_precision,
            "metrics_needed": need, "curve": curve,
            "advice": (f"combine >= {need} independent metrics to hold precision >= {target_precision:.0%}"
                       if need else
                       f"even {max_metrics} metrics don't reach {target_precision:.0%} — the proxy is too "
                       f"gameable; change what you measure, don't just add more of the same")}


def audit(gameability: float, n_metrics: int = 1, *, target_precision: float = 0.7, **kw) -> dict:
    """Verdict for your current setup: at this gameability and number of metrics, is the proxy still
    selecting the good ones? Returns SAFE / DEGRADED / GAMED + the recommended number of metrics."""
    f = fidelity(gameability, n_metrics=n_metrics, **kw)
    prec = f["precision"]
    rec = metrics_needed(gameability, target_precision=target_precision, **kw)["metrics_needed"]
    if prec >= target_precision:
        verdict = f"SAFE — precision {prec:.0%} at {n_metrics} metric(s); the proxy still tracks the goal"
    elif prec >= 0.4:
        verdict = (f"DEGRADED — precision {prec:.0%}; optimization is eroding fidelity. "
                   + (f"Combine >= {rec} independent metrics." if rec else "Change the metric."))
    else:
        verdict = (f"GAMED — precision {prec:.0%}; the target has stopped measuring the goal "
                   "(reward hacking). " + (f"Need >= {rec} independent metrics." if rec else "Re-define the metric."))
    return {**f, "verdict": verdict, "recommended_metrics": rec}


if __name__ == "__main__":
    print("goodhart — how gameable is your proxy? (reproduces Agora Lab e97ad5)\n")
    print("1) MEASURED fidelity decay — select top 10% by a single proxy as gameability rises:")
    print(f"   {'gameability':>11} | {'proxy-goal corr':>15} | {'precision (selected truly top)':>30}")
    for lam in (0.0, 0.5, 1.0, 2.0, 4.0):
        f = fidelity(lam)
        print(f"   {lam:>11.1f} | {f['proxy_goal_corr']:>15.2f} | {f['precision']:>29.0%}")
    print("   => 'when a measure becomes a target it ceases to be a good measure.'\n")

    print("2) the FIX — how many independent metrics restore precision (harder to game N than 1):")
    for lam in (1.0, 2.0):
        mn = metrics_needed(lam)
        print(f"   gameability {lam}: {mn['advice']}")
        print("      curve:", ", ".join(f"m={c['n_metrics']}:{c['precision']:.0%}" for c in mn["curve"][:6]))

    print("\n3) audit a setup:")
    print("   single gameable proxy (gameability 2):", audit(2.0, 1)["verdict"])
    print("   five independent metrics (gameability 2):", audit(2.0, 5)["verdict"])
