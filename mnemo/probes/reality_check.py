"""reality_check.py — locate a "method win" before you believe it. A tiny, dependency-free toolkit that
turns the reality-check genre (Lipton & Steinhardt 2018; Ferrari Dacrema RecSys 2019; Musgrave ECCV 2020;
Henderson AAAI 2018; Bouthillier et al. 2103.03098 on variance) into three runnable controls you drop next
to your eval. It prints PASS / CONFOUNDED per check.

The checks are DIAGNOSTICS, not verdicts: a firing check means "the win isn't coming from where you named
it," not "bad method." A method that wins by spending more compute can still be the right production call —
the check tells you *why* it won so you don't generalize a confound.

  1. variance    — is method−baseline a real delta or inside the noise band? (bootstrap CI on per-item deltas)
  2. compute/proxy — does a cheap proxy arm (length / recency / "just spend more tokens" / equal token budget)
                     tie the method? If method−proxy CI crosses 0, the method IS the proxy.
  3. verdict     — beats baseline AND survives the proxy -> PASS(located). beats baseline but proxy ties it
                     -> CONFOUNDED (the win is the proxy). doesn't beat baseline -> NOISE.

Bring your own scores (lists of per-item metric values for method / baseline / proxy). Zero dependencies.
MIT. Part of Agora / mnemo. See the four worked receipts in this folder.
Run the self-demo:  python mnemo/probes/reality_check.py
"""
import random, math, json, os


def bootstrap_ci(deltas, iters=10000, alpha=0.05, seed=17):
    """95% CI of the mean of per-item deltas (paired: method[i]-baseline[i]). No numpy."""
    n = len(deltas)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    mean = sum(deltas) / n
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        s = 0.0
        for _ in range(n):
            s += deltas[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int((alpha / 2) * iters)]
    hi = means[int((1 - alpha / 2) * iters)]
    return mean, lo, hi


def _paired_delta(a, b):
    if len(a) != len(b):
        raise ValueError("method and comparison score lists must be the same length (paired per item)")
    return [x - y for x, y in zip(a, b)]


def check(name, method, baseline, proxy=None, proxy_name="proxy"):
    """Run the reality check. `method`/`baseline`/`proxy` are per-item metric-score lists (paired).
    Returns a dict verdict and prints a readable report."""
    md, mlo, mhi = bootstrap_ci(_paired_delta(method, baseline))
    beats = mlo > 0                                   # method−baseline CI excludes 0
    out = {"name": name, "method_vs_baseline": {"delta": round(md, 4), "ci95": [round(mlo, 4), round(mhi, 4)],
           "significant": beats}}
    print(f"[{name}]")
    print(f"  variance     method−baseline = {md:+.4f}  CI95[{mlo:+.4f},{mhi:+.4f}]  -> "
          f"{'REAL delta' if beats else 'NOISE (inside band)'}")
    verdict = "NOISE (no real gain over baseline)"
    if proxy is not None:
        pd, plo, phi = bootstrap_ci(_paired_delta(method, proxy))
        ties = plo <= 0 <= phi                        # method−proxy CI crosses 0
        out["method_vs_proxy"] = {"proxy": proxy_name, "delta": round(pd, 4),
                                  "ci95": [round(plo, 4), round(phi, 4)], "proxy_ties": ties}
        print(f"  compute/proxy method−{proxy_name} = {pd:+.4f}  CI95[{plo:+.4f},{phi:+.4f}]  -> "
              f"{'PROXY TIES IT' if ties else 'beyond the proxy'}")
        if beats and ties:
            verdict = f"CONFOUNDED — the win is the {proxy_name}, not the method"
        elif beats and not ties:
            verdict = "PASS (located) — real gain beyond baseline AND beyond the proxy"
        else:
            verdict = "NOISE (no real gain over baseline)"
    elif beats:
        verdict = "PASS vs baseline — now add a proxy arm before believing it"
    out["verdict"] = verdict
    print(f"  VERDICT: {verdict}\n")
    return out


# — helpers for the compute-match control (a proxy arm = 'give the baseline equal tokens/calls') —
def token_matched_note():
    return ("compute-match is a DIAGNOSTIC, not a production verdict: if a method makes K calls, give the "
            "baseline K× the budget before comparing. A method that still wins may be worth its cost; a "
            "method whose win vanishes was buying a token gain, not a method gain.")


def _demo():
    print("=== reality_check.py self-demo ===\n")
    # Demo 1: synthetic — a 'method' that is secretly its proxy (length), vs a real one.
    rng = random.Random(1)
    base = [rng.gauss(0.50, 0.10) for _ in range(200)]
    length = [b + rng.gauss(0.05, 0.02) for b in base]          # a proxy that helps
    fake_method = [l + rng.gauss(0.0, 0.005) for l in length]    # 'method' == length + noise -> CONFOUNDED
    real_method = [b + rng.gauss(0.08, 0.02) for b in base]      # real gain independent of length
    check("synthetic: method that is really the length proxy", fake_method, base, proxy=length, proxy_name="length")
    check("synthetic: a genuinely real method", real_method, base, proxy=length, proxy_name="length")
    # Demo 2: reproduce the norm=length receipt from its result JSON if present (aggregate deltas + CIs).
    p = os.path.join(os.path.dirname(__file__), "norm_specificity_reranker_result.json")
    if os.path.exists(p):
        d = json.load(open(p))
        mvc = d.get("test_norm_vs_cos"); mvl = d.get("test_norm_vs_length")
        print("=== receipt: embedding-norm re-ranker (aggregate) ===")
        print(f"  norm − cosine   = {mvc[0]:+.4f} CI95[{mvc[1]:+.4f},{mvc[2]:+.4f}]  -> "
              f"{'REAL delta' if mvc[1] > 0 else 'NOISE'}")
        print(f"  norm − length   = {mvl[0]:+.4f} CI95[{mvl[1]:+.4f},{mvl[2]:+.4f}]  -> "
              f"{'PROXY TIES IT' if mvl[1] <= 0 <= mvl[2] else 'beyond proxy'}")
        confounded = mvc[1] > 0 and (mvl[1] <= 0 <= mvl[2])
        print(f"  VERDICT: {'CONFOUNDED — the norm win is the LENGTH proxy' if confounded else 'passes'}\n")
    print(token_matched_note())


if __name__ == "__main__":
    _demo()
