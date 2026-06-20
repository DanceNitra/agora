# Overnight baseline (2026-06-20 ~21:15) — measure each change's effect in the morning

Owner rule: **after EVERY change, observe its effect (measure the intended metric) before the next change.**
Change → observe → measure → next. No blind stacking. Applies to the remaining per-agent rebuilds too
(one, measure, then the next).

## Baseline snapshot (compare against tomorrow)
- **Inbox: 27** — churn types now: Synthesize 9, Deepen 4, Dialectic 2 (= 15, all pre-flag). Hypothesize 3,
  Challenge 1, Replicate 1, Press 1, Forge 1, + misc.
- **Severe-test (Rooke):** methods Lab runs = **0**, gap-log = **0**.
- **Funnel:** Activity 15281 · Grounded 2154 · Curated 3213 · Shipped 33.
- **Replications ledger (.replications.json):** 0.

## What each change should PROVE by morning (the observation per change)
1. **Quiet generators** (AGORA_QUIET_GENERATORS): Synthesize/Deepen/Dialectic counts in the inbox do NOT
   grow (the 15 existing are pre-flag). If they grow → flag not working.
2. **Rooke severe-test** (AGORA_SCIENTIST_LAB): methods Lab runs > 0 AND/OR new hypotheses recorded that
   carry a real lab_id. If still 0 → the hypothesis_loop isn't reaching the Lab (check the matcher/LLM).
3. **Aldric matcher:** of hypotheses attempted, how many matched a template (ran) vs landed in the gap-log.
   Higher match share = the matcher fix working.
4. **Voss science gate** (AGORA_SCIENCE_GATE): new vault notes overnight are all really-grounded (citation
   or measured number); no "Source:"-only empties.
5. **Funnel honesty:** Grounded grows only with real findings; Shipped is the bottleneck (distribution).
6. **anti-manufactured-FAILED:** new .replications.json entries have honest verdicts (not a FAILED flood).

## Morning action
Pull these same metrics, compute the delta, report per-change effect to the owner. Then resume the per-agent
quality rebuilds ONE at a time (Mira GRADE cards → measure → Orin competing-hypotheses → measure → Kael →
Wren), per the change→observe→next rule.
