# Pre-registration — AI-Claim Crucible flagship #1

**Claim under test (2026 agent-engineering folklore):**
> "Multi-agent systems (an orchestrator delegating to sub-agents) outperform a single agent on complex
> tasks." — the most-repeated agent-architecture claim of 2026 (contested: Cognition's "Don't Build
> Multi-Agents" vs Anthropic's multi-agent research system; no settled, cost-controlled answer).

**The honest question we actually test:** does multi-agent beat single-agent **at fixed cost** (same base
model, same total token budget per task)? Folklore compares multi-agent to a *weak* single-agent baseline
and ignores that the multi-agent run spends far more tokens. We hold $/task (total tokens) FIXED.

**This is committed BEFORE running.** The verdict is decided by the pre-set rule below, not chosen after.

## Protocol
- **Base model:** one fixed model for BOTH arms (`deepseek-v4-flash`), temperature 0.7. Only the *scaffold*
  differs. Cost = total tokens (prompt + completion, from the API `usage` field), summed over all calls in
  a task. The two arms are compared only at **matched total-token budgets**.
- **Task slice (decomposable, ground-truth, tuned to the model's error zone):** each task bundles K=5
  INDEPENDENT hard sub-problems (multi-step arithmetic/logic with distractors) whose answers are combined
  (sum). This is the regime where multi-agent folklore claims its win — clean per-sub-task context vs a
  single long context prone to interference / lost-in-the-middle. Ground truth is computed exactly.
  Difficulty (steps per sub-problem) is set so a single pass is NOT at ceiling (room to discriminate).
- **SINGLE-agent arm:** the model solves all K sub-problems in ONE context. Budget is spent via
  self-consistency: k independent solves (k = 1, 3, 5), majority vote per task. (A strong single baseline —
  it uses its budget, not a one-shot strawman.)
- **MULTI-agent arm:** orchestrator splits the task → ONE worker per sub-problem (fresh context each) →
  aggregator combines. Total tokens are accounted the same way. Scaled by worker reasoning budget.
- **Sweep** both arms across budgets to trace the **accuracy vs avg-tokens Pareto frontier**.

## Verdict rule (pre-set)
- **REPRODUCED** (folklore right): multi-agent **strictly dominates** the single-agent accuracy-cost Pareto
  at a realistic budget — i.e. at equal total tokens, multi-agent accuracy is higher by > 1 SE.
- **FAILED** (folklore wrong at fixed cost): single-agent **matches or beats** multi-agent at equal $/task
  (multi-agent accuracy ≤ single + 1 SE at the same token budget).
- **NOT_COMPUTABLE:** the minimal scaffold cannot be made a faithful instance of the claim (e.g. the
  decomposition is degenerate) — record and say why.

## Direction-level kill-switch (for the whole AI-Claim Crucible bet)
Abandon the direction if, within the first 5 ledger entries: (a) every verdict is REPRODUCED (we are
cherry-picking safe folklore → no news), OR (b) NOT_COMPUTABLE dominates (agent claims aren't faithfully
reducible), OR (c) zero inbound (no shares/citations/submissions) after the flagship + 2 follow-ups.

*Committed 2026-06-19. Lab + measured cost-accuracy frontier to follow; nothing published until owner-approved.*
