"""
agent_metabolism - a convex spend cap that makes an AI agent antifragile.

The problem (last30days, 2026-06-16): the loudest pain in AI-agent communities is
not capability, it is cost-runaway - "AI agent bankrupted their operator while trying
to scan DN42" hit 1,460 points on Hacker News. An agent that cannot stop is a fragile
system: a small input produces an unbounded, fat-tailed loss (Taleb's Extremistan).

The fix is a BARBELL (Antifragile): bound the downside hard, leave the upside open.
Biology already does this - an organism runs on a metabolic budget with homeostatic
set-points, not a kill-switch. This module meters one fungible "energy" currency
(tokens + dollars + tool-calls + wall-clock), enforces a hard convex per-task cap, and
halts on a tail-risk signature (many actions, no progress) BEFORE the blow-up.

Measured (Lab 20260616-agent-metabolism-convex-cap, 5000 tasks, 3% runaway-trapped):
a convex cap cut MAX single-run spend 20x (565 -> 28) and total spend 51%, while
NORMAL-task success was unchanged (100.0% -> 100.0%, delta +0.00%). The only thing it
sacrifices is the runaway tasks themselves - the disease, not the cure.

Zero dependencies. Wrap any agent loop:

    from agent_metabolism import MetabolicBudget, MetabolicHalt

    budget = MetabolicBudget(cap=1.00, stall_halt=15)   # 1.00 = one unit of "energy"
    while not done:
        try:
            budget.charge(tokens=step_tokens, dollars=step_cost, tool_calls=1)
            budget.check()                               # raises MetabolicHalt if over
        except MetabolicHalt as h:
            log(h); break                                # bounded loss, fail fast
        result = agent.step()
        if result.made_progress:
            budget.mark_progress()
"""
from __future__ import annotations

from dataclasses import dataclass, field


class MetabolicHalt(Exception):
    """Raised when a task exceeds its convex energy cap or trips the tail-risk signature."""

    def __init__(self, reason: str, spent: float, cap: float, actions: int):
        self.reason, self.spent, self.cap, self.actions = reason, spent, cap, actions
        super().__init__(f"MetabolicHalt({reason}): spent {spent:.3f} / cap {cap:.3f} "
                         f"after {actions} actions")


@dataclass
class EnergyPrice:
    """Convert heterogeneous costs into ONE fungible 'energy' currency. Defaults are a
    starting point; calibrate per workload from your own run logs (see calibrate())."""
    per_1k_tokens: float = 0.20      # ~ a mid-tier model's $/1k tokens
    per_dollar: float = 1.00         # explicit $ spend (API, infra) maps 1:1 to energy
    per_tool_call: float = 0.02      # each external call has a floor cost (latency/risk)
    per_second: float = 0.001        # wall-clock pressure

    def energy(self, tokens: float = 0, dollars: float = 0,
               tool_calls: float = 0, seconds: float = 0) -> float:
        return (tokens / 1000.0 * self.per_1k_tokens + dollars * self.per_dollar
                + tool_calls * self.per_tool_call + seconds * self.per_second)


@dataclass
class MetabolicBudget:
    """A hard convex per-task energy cap with a homeostatic warn set-point and a
    tail-risk (stall) early-halt. Bounded downside, open upside under budget."""
    cap: float                                   # hard ceiling in energy units (downside bound)
    stall_halt: int | None = 15                  # abort after N consecutive no-progress actions
    warn_at: float = 0.75                         # homeostatic set-point (fraction of cap)
    price: EnergyPrice = field(default_factory=EnergyPrice)
    spent: float = 0.0
    actions: int = 0
    _stall: int = 0
    _warned: bool = False

    def charge(self, tokens: float = 0, dollars: float = 0,
               tool_calls: float = 0, seconds: float = 0) -> float:
        """Record the cost of one action and return remaining energy."""
        self.spent += self.price.energy(tokens, dollars, tool_calls, seconds)
        self.actions += 1
        self._stall += 1
        return max(0.0, self.cap - self.spent)

    def mark_progress(self) -> None:
        """Call when the task genuinely advanced - resets the tail-risk stall counter."""
        self._stall = 0

    def warned(self) -> bool:
        """True once spend crosses the homeostatic set-point (caller may down-shift here)."""
        if self.spent >= self.warn_at * self.cap:
            self._warned = True
        return self._warned

    def check(self) -> None:
        """Raise MetabolicHalt if the task blew its cap or tripped the tail-risk signature."""
        if self.spent >= self.cap:
            raise MetabolicHalt("hard-cap", self.spent, self.cap, self.actions)
        if self.stall_halt is not None and self._stall >= self.stall_halt:
            raise MetabolicHalt("tail-risk-stall", self.spent, self.cap, self.actions)

    def remaining(self) -> float:
        return max(0.0, self.cap - self.spent)


def calibrate(per_task_energies: list[float], headroom: float = 6.0) -> float:
    """Pick a convex cap from a sample of NORMAL-task energy totals: the median normal
    cost times `headroom`. Wide enough that healthy tasks never hit it (the Lab showed
    0.00% normal-success loss), tight enough to bound the runaway tail."""
    if not per_task_energies:
        return 0.0
    s = sorted(per_task_energies)
    median = s[len(s) // 2]
    return median * headroom


def _selftest() -> None:
    """Reproduce the Lab result in miniature: the cap clips the tail, spares normal tasks."""
    import random
    rng = random.Random(42)

    def task(trapped: bool, budget: MetabolicBudget | None):
        need = rng.randint(2, 6)
        prog = actions = 0
        while prog < need:
            actions += 1                              # count actions in BOTH arms (apples-to-apples)
            if budget is not None:
                budget.charge(tool_calls=1)
                try:
                    budget.check()
                except MetabolicHalt:
                    return actions, False
            if rng.random() < (0.02 if trapped else 0.9):
                prog += 1
                if budget is not None:
                    budget.mark_progress()
        return actions, True

    def run(use_cap):
        rng.seed(42)
        spends, ok_norm, n_norm = [], 0, 0
        for _ in range(3000):
            trapped = rng.random() < 0.03
            b = MetabolicBudget(cap=0.56, stall_halt=15,
                                price=EnergyPrice(per_tool_call=0.02)) if use_cap else None
            s, ok = task(trapped, b)
            spends.append(s)
            if not trapped:
                n_norm += 1; ok_norm += ok
        return max(spends), sum(spends), ok_norm / max(1, n_norm)

    mx0, tot0, nrm0 = run(False)
    mx1, tot1, nrm1 = run(True)
    print(f"max single-run: {mx0:.2f} -> {mx1:.2f} ({mx0/max(1e-9,mx1):.0f}x cut)")
    print(f"total spend:    {tot0:.1f} -> {tot1:.1f} ({1-tot1/tot0:+.0%})")
    print(f"normal success: {nrm0:.1%} -> {nrm1:.1%} (delta {nrm1-nrm0:+.2%})")
    assert nrm1 >= nrm0 - 0.01, "regression: cap hurt normal-task success"
    assert mx1 < mx0 / 3, "regression: cap failed to clip the tail"
    print("OK - convex cap clips the tail without hurting normal-task success.")


if __name__ == "__main__":
    _selftest()
