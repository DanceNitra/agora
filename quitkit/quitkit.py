"""
quitkit — when to quit a depleting effort, with a MEASURED threshold.  (a inspeximus sibling)

Everyone says "set exit criteria and ignore the sunk cost." Nobody gives you the number. quitkit does:
quit a yield process when its recent yield falls a fraction theta below its running peak (a drawdown
stop), then reallocate. The catch most people miss is that there is an INTERIOR optimum — quitting too
early AND too late both lose — and we measured where it is.

The setup: you're working a "vein" whose yield decays as you exhaust it — a project, an ad campaign, a
research line, a content series, a sales channel, a job-search source. The decision: keep digging, or
cut and move to a fresh one?

    should_quit(history)        live KEEP/QUIT verdict from your recent yield stream
    Tracker(...)                streaming version: feed one period at a time
    optimal_theta()             the measured sweep — the interior optimum (~0.6) and why
    compare()                   drawdown-exit vs mine-to-depletion (+239% in the reference model)

Measured (reproduces Agora Lab 565aa7, `python quitkit.py`): across depletable pools, theta=0.6 beats
mining-to-depletion by +239% on the same budget, and the curve peaks at 0.6 (0.4 and 0.8 both do worse).
Zero dependencies, deterministic. The threshold is the product; the simulation is the proof.
"""
from __future__ import annotations

import random
import statistics


# --------------------------------------------------------------------------------- live decision
def should_quit(history, *, theta: float = 0.6, window: int = 25, min_observations: int | None = None) -> dict:
    """Should you quit the current effort? `history` = your per-period yields so far (newest last):
    1/0 for hit/miss, or any numeric yield (revenue, conversions, findings). QUIT when the recent
    average yield has fallen more than `theta` below its running peak — i.e. you've given back a
    fraction theta of your best, a drawdown stop. theta=0.6 is the measured interior optimum.

    Returns {quit, recent_rate, peak_rate, drawdown, threshold, reason}. drawdown = 1 - recent/peak.
    """
    h = [float(x) for x in history]
    need = window if min_observations is None else min_observations
    if len(h) < need:
        return {"quit": False, "recent_rate": None, "peak_rate": None, "drawdown": None,
                "threshold": theta, "reason": f"too early — need >= {need} periods to judge a drawdown"}
    # running peak of the rolling-mean yield, computed causally (no peeking at the future)
    peak = 0.0
    for i in range(window, len(h) + 1):
        peak = max(peak, statistics.fmean(h[i - window:i]))
    recent = statistics.fmean(h[-window:])
    drawdown = (1.0 - recent / peak) if peak > 0 else 0.0
    quit_now = peak > 0 and recent < (1.0 - theta) * peak
    return {"quit": quit_now, "recent_rate": round(recent, 4), "peak_rate": round(peak, 4),
            "drawdown": round(drawdown, 3), "threshold": theta,
            "reason": (f"recent yield is {drawdown:.0%} below peak (>= {theta:.0%}) — cut and reallocate"
                       if quit_now else
                       f"recent yield only {drawdown:.0%} below peak (< {theta:.0%}) — keep going")}


class Tracker:
    """Streaming drawdown-exit monitor: feed one period's yield at a time, ask should_quit() any time.
    Use when you don't want to keep the whole history yourself."""

    def __init__(self, *, theta: float = 0.6, window: int = 25):
        self.theta = theta
        self.window = window
        self._win: list[float] = []
        self._peak = 0.0

    def update(self, yield_value: float) -> dict:
        """Record one period's yield and return the current verdict."""
        self._win.append(float(yield_value))
        if len(self._win) > self.window:
            self._win.pop(0)
        verdict = {"quit": False, "recent_rate": None, "peak_rate": round(self._peak, 4),
                   "drawdown": None, "threshold": self.theta, "reason": "warming up"}
        if len(self._win) >= self.window:
            recent = statistics.fmean(self._win)
            self._peak = max(self._peak, recent)
            drawdown = (1.0 - recent / self._peak) if self._peak > 0 else 0.0
            quit_now = self._peak > 0 and recent < (1.0 - self.theta) * self._peak
            verdict = {"quit": quit_now, "recent_rate": round(recent, 4),
                       "peak_rate": round(self._peak, 4), "drawdown": round(drawdown, 3),
                       "threshold": self.theta,
                       "reason": ("drawdown stop hit — cut and reallocate" if quit_now
                                  else "within tolerance — keep going")}
        return verdict


# ------------------------------------------------------------------------- the measured threshold
def _simulate(theta, *, M=40, T=4000, seed=3):
    """Reference model (Agora Lab 565aa7): M depletable pools, each with a random richness. Digging a
    pool finds a NEW result with prob = remaining/richness (marginal yield falls as you mine it). With
    a fixed dig budget T, compare drawdown-exit at `theta` (leave once recent yield falls theta below
    the in-pool peak) vs mine-to-depletion (theta=None). Returns (findings, pools_touched)."""
    rng = random.Random(seed)
    rich = [rng.randint(20, 199) for _ in range(M)]
    rem = [float(r) for r in rich]
    found = 0
    di = 0
    visited = 1
    peak = 0.0
    win: list[int] = []
    for _ in range(T):
        if di >= M:
            break
        p = rem[di] / rich[di] if rich[di] else 0.0
        hit = rng.random() < p
        if hit:
            found += 1
            rem[di] -= 1
        win.append(1 if hit else 0)
        if len(win) > 25:
            win.pop(0)
        rate = sum(win) / len(win)
        peak = max(peak, rate)
        exhausted = rem[di] <= 0.5
        drawdown_exit = theta is not None and len(win) >= 25 and peak > 0 and rate < (1 - theta) * peak
        if exhausted or drawdown_exit:
            di += 1
            peak = 0.0
            win = []
            if di < M:
                visited += 1
    return found, visited


def optimal_theta(thetas=(0.4, 0.5, 0.6, 0.7, 0.8), **kw) -> dict:
    """Sweep theta on the reference model and return the argmax plus the whole curve — so you can SEE
    the interior optimum (quitting too early or too late both lose). Returns
    {best_theta, curve: [{theta, findings}], baseline_deplete, lift_pct}."""
    base, _ = _simulate(None, **kw)
    curve = [{"theta": t, "findings": _simulate(t, **kw)[0]} for t in thetas]
    best = max(curve, key=lambda r: r["findings"])
    return {"best_theta": best["theta"], "curve": curve, "baseline_deplete": base,
            "lift_pct": round(100 * (best["findings"] - base) / base, 1) if base else None}


def compare(theta: float = 0.6, **kw) -> dict:
    """Drawdown-exit at `theta` vs mine-to-depletion on the same pools/budget — the headline lift."""
    base, base_dom = _simulate(None, **kw)
    ex, ex_dom = _simulate(theta, **kw)
    return {"deplete": {"findings": base, "pools": base_dom},
            "drawdown_exit": {"findings": ex, "pools": ex_dom, "theta": theta},
            "lift_pct": round(100 * (ex - base) / base, 1) if base else None}


if __name__ == "__main__":
    print("quitkit — when to quit, measured (reproduces Agora Lab 565aa7)\n")
    print("1) the measured threshold — interior optimum (too tight AND too loose both lose):")
    opt = optimal_theta()
    print(f"   mine-to-depletion baseline: {opt['baseline_deplete']} findings (same budget)")
    for r in opt["curve"]:
        mark = "  <- best" if r["theta"] == opt["best_theta"] else ""
        print(f"   theta={r['theta']:.1f}: {r['findings']:>5} findings{mark}")
    print(f"   => quit at theta={opt['best_theta']} -> +{opt['lift_pct']}% vs mining to depletion")

    print("\n2) live decision on a yield stream:")
    strong = [1, 1, 1, 0, 1, 1, 0, 1] * 4          # ~75% hit rate, healthy
    fading = strong + [0, 0, 1, 0, 0, 0, 0, 0] * 3  # then it dries up
    print("   healthy run :", should_quit(strong)["reason"])
    print("   faded run   :", should_quit(fading)["reason"])
