# Agent redesign — per-agent rebuild tracker

Rebuild each agent's ORGAN (the code that embodies its function) so it produces measured value, not
formatted churn. One agent per cycle, flag-gated + reversible (CLAUDE.md rules). Priority = the critique's
"build the load-bearing two first (Rooke, Voss), defer the over-engineered meta-structure." Full design:
`20260620_agent-redesign.md`.

## Done
- [x] **Rooke** (Confirmation Scientist — the Lab linchpin) → `execution/scientist.py` severe-test path,
  flag `AGORA_SCIENTIST_LAB=1` (live). A hypothesis now runs a REAL minimal model via the Methods Library
  with a pre-commitment (no HARKing); no template fit / no measured number → verdict NONE → **not recorded**;
  a relevance gate drops results that don't bear on the claim. Proof: ~1/5 hypotheses get a real, relevant
  measured test → **the bottleneck is Lab template COVERAGE**, not orchestration.
- [x] **Voss** (Adversarial gate) → `execution/quality_gate.py` science gate, flag `AGORA_SCIENCE_GATE=1`
  (live). Vault entry now needs REAL grounding — a citation shape (DOI/arXiv/Author-year) OR a measured
  number — never the literal word "Source:" (which an empty note faked). Calibrated: real lab + literature
  findings pass; "Source:"-only / stub / buzzword-soup reject.

- [x] **Aldric** (Compute CFO / Methods Library) — **corrected diagnosis**: the library already has **32
  templates** (not 8 — earlier undercount), so the proof's 40% match rate was the **MATCHER under-matching
  (none-bias), not missing coverage**. Fixed the matcher to map by underlying MECHANISM/claim-shape →
  verified the proof's 3 previous misses now match 3/3 (power-law→preferential-attachment,
  criticality→csd-earlywarning, multi-agent→diversity-vs-ability). Added gap-logging (`.methods_gaps.json`).
  Dropped a duplicate + a buggy power-law template (didn't ship bad science). Auto-template-writing loop
  deferred (32 templates is already broad; the matcher was the real lever).

## Next (priority order)
- [x] **Funnel metric honesty** — `execution/funnel.py` `_GROUNDED` now requires a real citation OR a
  measured result/lab receipt (not the words Hypothesis/Falsifier/Source:). Effect: grounded 7369 (48%) ->
  honest 2145 (14%). Read-side only, verified live. (metabolism value-weights already reward replication/
  press; the FAILED/NULL=1.0 extension folds into the Rooke fair-baseline work below.)
- [x] **Anti-gaming guard (Rooke)** — metabolism now values FAILED == REPRODUCED (both 2.5; was 4.0 vs 2.0),
  killing the incentive to manufacture failures. **Process rule** (for recording Crucible replications):
  before logging a FAILED, confirm a known-true control REPRODUCES in the same harness (so a FAILED is a
  real refutation, not a broken harness). The full in-code control-run is deferred (Methods templates are
  self-controlled - they test vs a null - so the live severe-test path is low-risk; the gap is the manual
  replication process, which is gated + verified by Claude).
- [ ] **Mira** (Curator) — write a GRADE evidence card only AFTER a Lab receipt exists; null/FAILED curated
  as first-class. Note volume stops being a credit metric.
- [x] **Orin** (Idea Alchemist) — DONE 2026-06-20: hypothesis generation now names a concrete MECHANISM +
  predicted direction a minimal model can measure (favours simulation-settleable shapes). OBSERVED: 3/4
  generated hypotheses match a Lab template (vs proof's 2/5) → severe-test conversion ~40%→~75%. (Single
  testable hypothesis; full multi-hypothesis Platt trees deferred - the matchability win was the lever.)
  Also: **agent_activity_monitor.py** launched - watches if agents work + what they produce (loop/grounded/
  lab-runs/shipped deltas; ~3h Telegram summary; alerts on frozen OR busy-but-idle).
- [ ] **Kael** (Scout) — claim-gap retrieval (one best-grounded finding per side of a hole) + mandatory
  effect-size/credibility audit (flag N<50 / no-prereg as low-credibility).
- [ ] **Wren** (Cartographer) — ranked structural-hole list that feeds Orin's bridges + forced-collision.

## Overnight run (2026-06-20, owner: "dorobme to vsetko a nechame to pracovat cez noc")
The 4 generator agents' NOISE is quieted at the source (flag `AGORA_QUIET_GENERATORS=1`): the 3 dominant
inbox-churn generators (`_queue_insight_theme`=synthesize, `_queue_deepening`=deepen, `_queue_dialectic`)
skip. The VALUE path stays live: hypothesize→severe-test (Rooke), replication, scout outreach, belief
challenge. Combined with the 5 brain-side rebuilds (severe-test, science gate, fixed matcher, honest funnel,
anti-manufactured-FAILED), the system should produce MEASURED findings overnight, not churn. Verified: dungeon
1.1s/loop advancing, brain healthy, canary watching. **Per-agent QUALITY polish (Mira GRADE cards, Orin
competing-hypotheses, Kael effect-size audit, Wren structural-holes) is the listed-but-unchecked work below —
deliberately deferred: shipping unverified deep rewrites to run unattended overnight is the wrong risk.
Measure the overnight output FIRST, then polish.**

## Deferred (critique: unproven meta-structure / weakest)
- **Elara** — redesign is pure bookkeeping (can't earn value under the new gate); keep for the 3D world only
  until there's measured evidence it reduces FAILED rate.
- **Squads / Elo tournaments / credibility ledgers / 90-day clocks** — build only after the core loop proves
  it produces measured value at acceptable cost.

## Standing guards
- Big-Five persona strings stay OUT of scientific-task prompts (cost up to -0.65 on retrieval); souls are for
  the 3D world + trust only.
- One agent per cycle, flag-gated, py_compile + verify both servers 200 + one :8000 listener, revert on breakage.
