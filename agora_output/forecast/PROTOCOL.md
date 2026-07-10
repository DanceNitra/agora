# Crucible Live — pre-registered replication-forecast protocol (v1)

Every claim that enters the Crucible gets a public, tamper-evident forecast BEFORE the
replication is designed or run. Over time this yields the first executed prospective
calibration record of machine skepticism about AI/ML claims (proposed in 2020 — arXiv
2005.04543 — never executed; closest prior work is retrospective, human-forecast, or
social-science-domain).

## Protocol (per claim, in this exact order)

1. **INTAKE** — a claim card is written to `claim_cards/<id>.json`:
   `{id, claim, source, source_url, date_claimed, intake_channel, date_intake}`.
   The card contains ONLY public information about the claim — no replication design.
   Intake rule: claims are selected for (a) freshness/attention, (b) computability as a
   minimal single-machine model, (c) FAILED being a live possibility. Claims considered
   but rejected are logged in `claim_cards/rejected.jsonl` with a one-line reason.
2. **FORECAST** — the frozen forecaster (prompt v1 in `forecast_prompt_v1.txt`; models
   pre-registered below) reads ONLY the claim card and outputs P(REPRODUCED), a 3-way
   distribution (R/F/NC), and a one-sentence reason, written to `forecasts/<id>.json`.
   An optional owner (human) forecast may be recorded in the same file at this step.
3. **COMMIT** — the claim card + forecast are committed and pushed to the public repo
   BEFORE any harness/Lab code for that claim exists. The git push to GitHub provides
   the public timestamp; the commit hash is recorded in the forecast file on the next
   commit. (CI check planned: any Lab artifact for id X must postdate forecast commit X.)
4. **REPLICATE** — the standard Crucible severe-test pipeline runs (smallest faithful
   computational model, runnable receipt). The replication designer may not edit the
   forecast; forecasts are append-only.
5. **RESOLVE** — the verdict (REPRODUCED / FAILED / NOT_COMPUTABLE) is written to the
   ledger as usual; `forecasts/<id>.json` gets `{verdict, resolved_date, brier}` appended
   as a NEW commit. Primary score: binary Brier on R-vs-F conditional on computable
   (pre-registered); NC forecasts scored separately. Base-rate comparator: trailing
   20-computable-verdict reproduce rate, frozen at forecast time in the forecast file.

## Pre-registered choices (epoch 1, 2026-07-10)

- Forecaster models: `glm-5.2` and `deepseek-v4-flash` (two families), temperature 0,
  prompt v1 verbatim; ensemble = mean of the two. Any change = new epoch, new file.
- Primary metric: Brier on P(REPRODUCED) over computable verdicts; comparator =
  frozen trailing base rate; secondary = 5-bin calibration once n >= 100.
- NO skill/calibration claims will be published before >= 60 resolved prospective
  forecasts. The retro-fit on pre-2026-07-10 verdicts (`pilot_contaminated_32_result.json`)
  is CONTAMINATED (verdicts public since ~2026-05) and is never citable as skill.
- Known limitation (declared upfront): the same org selects claims, forecasts, and
  adjudicates. The intake rule + rejected-claims log + append-only forecasts mitigate;
  base-rate endogeneity (we hunt FAILED-likely claims) cannot be eliminated and is why
  the comparator is the trailing base rate, not 50/50. Third-party claim submissions
  welcome — they remove the selection loop entirely.
