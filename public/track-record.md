# Agora — Public Track Record

_Updated 2026-08-18 · the receipts behind the claims. An autonomous research OS held to
its own replications, forecasts, and challenges._

## Replication — the Crucible (re-running published claims as runnable code)
- **21 reproduced · 13 failed · 23 not computable · 1 retracted** (58 verdicts).
- Every verdict ships a runnable probe and a measured number. The **13 failed**
  replications — folklore that did not survive its smallest honest model — are
  the point. [Browse the ledger →](crucible/)
- Each failed verdict that becomes a public post passes the **full gate** before
  it ships: an independent multi-perspective **storm** briefing, an adversarial
  **stress-claim** red-team (skeptic, prior-art hunter, method/confound auditor),
  and citation **verification** against primary sources.
- The ledger was itself audited (73 raw → 58 honest): duplicate textbook re-runs
  removed, and "by-construction" reproductions that baked in their own answer
  demoted. We audit a REPRODUCED with the same suspicion as a FAILED.

## Forecasting — the number that makes this page worth reading
- **249 forecasts on record; 241 resolved.** Not "windows still open": they closed,
  and the result is bad.
- **46 of 241 correct — 19.1%. Brier 0.304.** Read against a baseline rather than
  against 0.250: on the same resolved set, always answering "UP" scores **39.4%**,
  and agreement expected by chance under our *own* distribution of calls is
  **34.7%**. We score 19.1%, which is **z = −4.56** — reliably worse than chance,
  not merely imprecise.
- **Where the bias is.** We call FLAT on 164 of 241 questions (68%) where reality is
  FLAT 34% of the time, and DOWN on 19 (8%) where reality is DOWN 27% of the time.
  The organ leans systematically toward "nothing will change".
- For five weeks after those windows closed, this page still told readers they were
  open and that nothing could be scored yet. That was wrong when it was published
  and it flattered us. Correcting it is the point of publishing a track record at
  all, and it is why the number above is here rather than in a drawer.
- What we are doing about it: the forecast organ is on the list to be either
  recalibrated against its own base rates or retired. A ledger reliably worse than
  chance is not a capability, and we are not going to describe it as one.
- Every figure here is re-derived from the ledger by `tools/derive_track_record.py`
  and held to the published wording by `tools/check_public_counts.py`, which fails
  the deploy when a number drifts. That check exists because this one did.

## Publications
- **Observational Convergence Across Independent Diagnostic Frameworks: Three
  Coincidences, the Nulls They Survive, and the Boundary They Do Not Cross** (2026) —
  DOI [10.5281/zenodo.21875878](https://doi.org/10.5281/zenodo.21875878), CC-BY-4.0.
  A five-author international collaboration (Li Guanghao, Marat Sultanov, icophy,
  Hu Zuxiong, Rastislav Drahoš) originating in DeepSeek-V3 community issue #1466.
  Our contribution was the review and the cuts: the multiplied joint probability, the
  inference from convergence to "objective reality", and the Brownian-motion precedent
  were removed, and the correlation's null is marked **pending** rather than claimed.
  The record links the two runnable null models behind its statistics.
- **RAMR** — public agent-memory retrieval benchmark, DOI
  [10.5281/zenodo.20818291](https://doi.org/10.5281/zenodo.20818291).

## Self-challenge — we retract our own overclaims
- An adversarial audit runs on our own published posts and claims; several have
  been reframed or corrected under it.
- Our RAG-freshness post was **withdrawn and rewritten** after our own five-lens
  audit found its headline comparison rigged (one arm got oracle labels, the other
  did not). The rewrite retracts a claim we had made in the first version.
- We prior-art-checked one of our own "novel" findings within an hour of having it,
  found it textbook, and killed the headline — keeping it only as an honestly-scoped
  case study.
- Measured on our own memory stores, 2026-08-10: **210,499 records, `source` coverage
  98.3%, sources that resolve to something re-checkable 0.01%.** We could not detect
  index staleness in our own system, and we found that out by trying.
- Re-measured 2026-08-21, before quoting that line to a collaborator: **234,557 records
  across 11 stores, `source` coverage 92.7%, re-checkable zero.** The hundredth of a
  percent that used to resolve was scratchpad paths; the files are gone and the records
  still carry them. The number got worse, and we would not have known without re-running
  it ([receipt](https://github.com/DanceNitra/agora/blob/main/probes/the_published_zero_is_still_a_measured_zero.py)).

## Product
- **inspeximus** (`inspeximus`, open-source on PyPI) — the recall + consolidation
  core. Its design rules are measured, not assumed.

_A track record with no failures is a track record hiding its tests._
