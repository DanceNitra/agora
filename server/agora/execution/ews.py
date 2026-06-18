"""
Critical-Transition Early-Warning Engine (operational organ) — the capstone, made callable.

Scores a supplied time series for an APPROACHING critical transition (critical slowing down: rising
rolling variance + rising lag-1 autocorrelation), AND — the capstone's point — reports its OWN
trustworthiness. Critical slowing down is the signature of a slow approach to a FOLD/bifurcation;
a series whose variance rises WITHOUT the autocorrelation slowing-down signature is in a
volatility/noise regime where this detector has no skill (validated: AUC 0.90 fold vs 0.50 noise-
induced, Lab 775359; the S&P "AUC 0.81" was a volatility/pseudo-replication artifact, Lab 6cd915).

Pure-Python (no deps), read-only; safe to call from anywhere.
"""
from __future__ import annotations


def _kendall_tau(y):
    n = len(y)
    if n < 2:
        return 0.0
    s = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = y[j] - y[i]
            s += (d > 0) - (d < 0)
    return 2.0 * s / (n * (n - 1))


def _var(w):
    m = sum(w) / len(w)
    return sum((v - m) ** 2 for v in w) / len(w)


def _lag1_ac(w):
    m = sum(w) / len(w)
    dev = [v - m for v in w]
    denom = sum(d * d for d in dev)
    if denom <= 0:
        return 0.0
    return sum(dev[i + 1] * dev[i] for i in range(len(dev) - 1)) / denom


def assess(series, win: int = 0) -> dict:
    """Return the early-warning score for `series` PLUS an honest trustworthiness verdict."""
    x = [float(v) for v in series if v is not None]
    n = len(x)
    if n < 40:
        return {"status": "insufficient_data", "n": n, "need": 40}
    if win <= 0:
        win = max(15, n // 8)
    var_s = [_var(x[i - win:i]) for i in range(win, n + 1)]
    ac_s = [_lag1_ac(x[i - win:i]) for i in range(win, n + 1)]
    var_tau = _kendall_tau(var_s)
    ac_tau = _kendall_tau(ac_s)
    warning = round(0.5 * (var_tau + ac_tau), 3)
    ac_level = round(sum(ac_s[-max(1, len(ac_s) // 5):]) / max(1, len(ac_s) // 5), 3)  # recent AC level

    # Trustworthiness = is this the engine's IN-SCOPE (fold / critical-slowing-down) regime?
    # Thresholds set above Kendall-tau sampling noise so a stationary series isn't mislabelled.
    rising_both = var_tau > 0.25 and ac_tau > 0.25
    rising_var_only = var_tau > 0.35 and ac_tau <= 0.15
    if rising_both and warning > 0.25:
        regime, trust = "fold-like (critical slowing down)", "HIGH"
        note = ("Both variance AND autocorrelation are rising coherently — the critical-slowing-down "
                "signature of a slow approach to a fold/bifurcation. This is the engine's validated "
                "in-scope regime (AUC 0.90); the warning is trustworthy.")
        alarm = warning > 0.4
    elif rising_var_only:
        regime, trust = "volatility / noise regime", "LOW"
        note = ("Variance is rising but autocorrelation is NOT slowing down — the signature of a "
                "volatility/noise regime (e.g. markets), NOT a fold approach. The engine has no skill "
                "here (validated: AUC ~0.50 / 0.81-artifact). Treat any 'warning' as OUT OF SCOPE.")
        alarm = False
    else:
        regime, trust = "stationary / no approach", "HIGH"
        note = "No coherent rising trend in variance or autocorrelation — no approaching fold detected."
        alarm = False

    return {"status": "ok", "n": n, "window": win, "warning_score": warning,
            "variance_trend": round(var_tau, 3), "autocorr_trend": round(ac_tau, 3),
            "recent_autocorr": ac_level, "regime": regime, "trust": trust,
            "alarm": alarm, "note": note}


def format_ews(a: dict) -> str:
    if a.get("status") != "ok":
        return f"📡 *Early-warning engine*: {a.get('status')} (n={a.get('n')})"
    flag = "🚨 ALARM" if a.get("alarm") else "•"
    return "\n".join([
        "📡 *Critical-transition early-warning engine*:",
        f"{flag} warning={a['warning_score']} (var-trend {a['variance_trend']}, AC-trend {a['autocorr_trend']})",
        f"• regime: *{a['regime']}* — trust *{a['trust']}*",
        f"• {a['note']}",
    ])
