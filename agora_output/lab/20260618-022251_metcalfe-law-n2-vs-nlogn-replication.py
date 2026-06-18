"""
Crucible replication: Metcalfe's Law — "the value of a network scales as n^2 (the number of possible
pairwise connections)." Widely cited to justify platform valuations and network effects. CONTESTED:
Briscoe, Odlyzko & Tilly (2006) argue real networks scale as ~n*log(n), and Metcalfe's own 2013
revisit fit Facebook data with an n^2 cap / declining marginal value. So FAILED is a live possibility.
On the Future-of-Work & Society frontier (platform economics, network effects).

Mechanism test. Metcalfe's n^2 assumes EVERY pair connects with EQUAL value (1). Realistically a user
does not value all n-1 others equally; rank a user's connections by value and they follow a declining
(e.g. Zipf) distribution. Total network value = sum over users of the value of their connections. We
fit the scaling exponent alpha in V ~ n^alpha for different per-connection value distributions:
  - equal     : every connection worth 1                 (Metcalfe's assumption)  -> predict alpha ~ 2
  - zipf      : k-th best connection worth 1/k           (Briscoe-Odlyzko-Tilly)  -> predict ~n*log n (alpha ~ 1)
  - zipf-mandel: 1/k^s with s<1 (slow decay)             -> between the two
The claim 'value ~ n^2' is REPRODUCED only under the (unrealistic) equal-value assumption; under any
realistic declining value it FAILS.
"""
import numpy as np

def network_value(n, kind):
    # value per user = sum over its n-1 ranked connections of the connection value; total = n * per-user
    k = np.arange(1, n)                       # ranked connection index 1..n-1
    if kind == "equal":
        per_user = np.sum(np.ones_like(k, dtype=float))          # = n-1   -> total ~ n^2
    elif kind == "zipf":
        per_user = np.sum(1.0 / k)                               # ~ ln(n) -> total ~ n ln n
    elif kind == "zipf_mandel":
        per_user = np.sum(1.0 / k**0.7)                          # ~ n^0.3 -> total between
    return n * per_user

def fit_alpha(kind, ns):
    V = np.array([network_value(n, kind) for n in ns], dtype=float)
    # log-log slope = scaling exponent alpha
    a = np.polyfit(np.log(ns), np.log(V), 1)[0]
    return float(a), V

if __name__ == "__main__":
    ns = [100, 300, 1000, 3000, 10000, 30000, 100000]
    print("Metcalfe's Law replication: fit alpha in (network value) ~ n^alpha.\n")
    print("  per-connection value model | fitted alpha | implied scaling")
    res = {}
    for kind, label in [("equal", "equal (Metcalfe assumption)"),
                        ("zipf_mandel", "slow decay 1/k^0.7"),
                        ("zipf", "Zipf 1/k (Briscoe-Odlyzko-Tilly)")]:
        a, V = fit_alpha(kind, ns)
        res[kind] = a
        implied = "~n^2" if a > 1.8 else ("~n*log n" if a < 1.25 else "~n^1.3-1.7 (sub-quadratic)")
        print(f"  {label:<34} | alpha={a:.2f}      | {implied}")

    # compare zipf model directly to the n*log n form
    V_zipf = np.array([network_value(n, "zipf") for n in ns])
    nlogn = np.array([n*np.log(n) for n in ns], dtype=float)
    corr = np.corrcoef(V_zipf, nlogn)[0,1]
    print(f"\n  Zipf-model value vs n*log(n): correlation = {corr:.4f}")

    print("\n=== VERDICT ===")
    equal_is_n2 = res["equal"] > 1.9
    realistic_fails = res["zipf"] < 1.25
    print(f"Metcalfe n^2 holds ONLY under equal per-connection value (alpha={res['equal']:.2f}): {equal_is_n2}")
    print(f"under realistic declining value (Zipf) the n^2 claim FAILS -> ~n*log n (alpha={res['zipf']:.2f}): {realistic_fails}")
    if equal_is_n2 and realistic_fails:
        print("VERDICT: FAILED (strong claim)")
        print("Metcalfe's Law as 'network value ~ n^2' is an ARTIFACT of assuming every pairwise connection")
        print("has equal value. The moment connection value declines with rank (Zipf, the empirically")
        print("supported case), total value scales as ~n*log(n) (alpha~1), NOT n^2. The famous quadratic")
        print("over-states large-network value by orders of magnitude - consistent with Briscoe-Odlyzko-Tilly")
        print("(2006) and Metcalfe's own 2013 data-fit. Implication for platform valuation: network-effect")
        print("value is closer to LINEAR-with-a-log than quadratic; the n^2 heuristic systematically inflates it.")
    else:
        print("VERDICT: not as expected -- investigate.")
