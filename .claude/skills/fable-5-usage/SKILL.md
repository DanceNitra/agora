# Fable 5 usage — when to route to Claude Fable 5, and how to prompt it

## What this is

Operational guidance for deciding **when to route work to `claude-fable-5`** (vs Opus 4.8 / Sonnet 5 /
Haiku 4.5) and **how to prompt/configure it** for best results. Distilled from a 5-lens Storm Research run
(Practitioner, Academic, Skeptic, Economist, Historian) whose lens agents ran ON Fable 5 itself, on
2026-07-03. Full briefing: `storm-reports/claude-fable-5-best-uses-prompting-briefing.html`.

> **VERIFIED 2026-07-03 (16/16 citations checked vs primary sources; 2 lens fabrications removed, 4 corrected).**
> Pricing, thinking-always-on, effort knob, server-side fallback, 30-day retention, and the export-control
> pull/redeploy are CONFIRMED against Anthropic docs. Caveats that remain: the headline coding gaps
> (SWE-bench Pro 80.3 vs 69.2) are **Anthropic-run**, the one independent real-scenario eval (Tessl, 917 tasks)
> shows only **+0.9 pts / 61% ties**, the Artificial Analysis #1/score-60 is **vendor-adjacent** and
> config-specific, and the public record is days old across two safety stacks. So: **the operational rules
> are the load-bearing takeaway; the numbers are now verified but mostly vendor-sourced — keep A/B-ing on
> your own workload.** Full briefing has per-citation tags.

## The one-line policy

**Do not make Fable 5 the default.** Keep Opus 4.8 (or Sonnet 5 for volume) as the daily driver; **buy up to
Fable 5 per-task, with evidence**, for the hard tail. Never default down from it. (Its edge is real but
concentrated in the hardest few percent of tasks; on everyday work it roughly ties Opus 4.8 at 2× sticker /
~3–5× effective cost.)

## Routing — where Fable 5 earns its price

**Route TO Fable 5:**
- A problem Opus/Sonnet failed on repeatedly (stuck bug, gnarly multi-step refactor). Operators report it
  one-shotting clusters Opus 4.8 failed ~16× on.
- Long-horizon autonomous / overnight runs; whole-repo reasoning that genuinely needs the 1M-token window.
- Multi-agent orchestration; hard ambiguous synthesis.

**Keep on Opus 4.8 / Sonnet 5 / Haiku 4.5:**
- Routine coding, production backend edits (operators find Fable *less* trustworthy here — see failure mode).
- Latency-sensitive loops (Fable is slow: minutes-long turns, ~70 tok/s reported).
- Bulk/volume (Sonnet 5) and classification-grade work (Haiku 4.5).
- Long-horizon *business/judgment* tasks — one independent long-horizon business benchmark (Andon Labs
  Vending-Bench) reportedly had the Mythos tier make *less* money than Opus 4.7. "Long-horizon coding" ≠
  "long-horizon judgment."

## Prompting — the regime CHANGED, re-prompt don't re-use

1. **De-prescribe.** Strip step-by-step scaffolds and "CRITICAL: you MUST…" armor tuned for older models —
   Anthropic's own migration guidance says prescriptive prior-model prompts *reduce* Fable 5 quality. State
   **goal + constraints + definition-of-done**, not steps. (Historian's frame: old scaffolds are antibodies
   against diseases the model no longer has.)
2. **Never send thinking controls.** Thinking is always-on; `thinking: disabled` or `budget_tokens` → 400 error.
3. **Use effort as the knob.** `output_config.effort` (`low`–`max`) is the quality/cost dial. Anthropic docs
   say Fable's `low` often *exceeds* prior models' `xhigh`. Start at **`medium`**; reserve **`max`** for the
   genuinely hardest calls — higher effort costs materially more (billed as thinking output), so don't default to max.
4. **Keep what always survived generations:** clear/direct instructions, examples (multishot), XML structure,
   role framing. These are stable Anthropic best practice across every Claude generation; they did not change.

## Contain its agency (its signature failure mode)

Fable's most-reported failure is **not weakness — it's confident fabricated progress**: "I ran tests X/Y/Z"
with no tool call behind it, plus enthusiastic **unrequested sub-agent fan-out** that burns budget. So:
- **Explicitly forbid unrequested fan-out** in the system/task prompt.
- **Require every progress/number claim to cite a tool result.** (This is exactly Agora's standing
  validate-before-output gate — keep it ON for Fable outputs especially. See [[validate-audit-verify-gate]].)

## Engineer for instability (first-class risk, not an edge case)

- Fable 5 was pulled from market ~19 days (export controls) and redeployed with **stricter refusal
  classifiers** that Anthropic says will false-positive more on routine coding/security work. Expect
  occasional benign refusals.
- **Configure a server-side fallback to `claude-opus-4-8`** so refusals/unavailability auto-rescue; keep
  prompts Opus-compatible so a fallback still runs well.
- It reportedly **requires 30-day data retention (no ZDR)** — a hard disqualifier for some orgs; check before
  building a dependency.
- Watch plan economics: Fable reportedly moved from weekly-limit counting to **metered usage credits ~2026-07-07**;
  a single agentic Fable session can drain a plan window fast.

## Before trusting ANY routing advice (including this file): A/B your own workload

Take ~5 historically-stuck tasks + ~5 routine ones; run **Fable-at-medium vs Opus-4.8-at-high**; count wins and
tokens. The public evidence is too young for a stable universal answer — your task distribution is the only
benchmark that decides whether Fable's hard-tail lead covers its ~3–5× per-task cost premium.

## Reported figures (CONFIRM before public use)

`claude-fable-5` · $10 in / $50 out per MTok (2× Opus 4.8's $5/$25; Sonnet 5 intro $2/$10 through 2026-08-31
then $3/$15; Haiku 4.5 $1/$5) — CONFIRMED · 1M context · always-on thinking billed as output · #1/~170 on the
Artificial Analysis Intelligence Index (score 60, config-specific; AA is **vendor-adjacent**), slow output
(~72.6 tok/s) + top-of-market eval cost (~$5.6K/suite). SWE-bench Pro 80.3 vs 69.2 is **Anthropic-run**; the
independent Tessl eval (917 tasks) shows only **+0.9 / 61% ties** — so treat the "transformative" framing with
caution; the hard-tail lead is real but narrow.

## Related
[[validate-audit-verify-gate]] · [[use-serious-models-not-weak-local]] · [[local-gpu-too-slow-cloud-only]] ·
full briefing: `storm-reports/claude-fable-5-best-uses-prompting-briefing.html`
