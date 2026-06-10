# AGORA — FRONTIER UPGRADE PLANS (2026-06-09)

> Wave 1 DONE (Insight Engine → Prediction Ledger → Flywheel → Mind → Learning → Hands →
> Senses → visible HUD). **Wave 2 (#1-6) ALL SHIPPED.** **Wave 3 (#7-11) ALL SHIPPED.**
>
> **Wave 3 — the self-aware research organism (all live):**
> - **7 Observatory** (`8d3ddd7`): weekly vital-signs ledger `.vitals.json` (dead-weight, link
>   density, flywheel closure latency, exam, hit-rate). Telegram `vitals`. Baseline day 0 set.
> - **8 The Interview** (`931b974`): daily one highest-value question to Rasto; answers become
>   `owner-knowledge` vault notes feeding the user model. Telegram `answer`/`interview`/`ask me`.
> - **9 Causal Self-Experiments** (`8e33196`): variant registry + stable hash assignment +
>   auto-decision; first live A/B = exam answer style, graded by Claude. Telegram `experiments`.
> - **10 The Library** (`a17a3aa`): reads ONE full paper/day via ar5iv → structured paper note
>   (claims, evidence strength, limitations, vault links). Loop A11. Telegram `library`.
> - **11 Campaigns** (`f0db19d`): multi-day research — decompose, harvest findings per
>   sub-question over days, Claude writes a confidence-graded dossier. Loop A12. Telegram
>   `campaign <goal>`/`campaigns`.
>
> New loop task kinds: A9 grade-exam, A10 hypothesize, A11 read-paper, A12 campaign-dossier.
>
> **Wave 4 — integrity (all SHIPPED 2026-06-09 late):**
> - **12 Belief Revision** (`f136fba`): belief lifecycle active→survived/revised/retired;
>   challenge sweep ~2d picks the longest-untested belief; loop A13. Telegram `beliefs`.
> - **13 The Canon** (`90dd4e4`): one living "What Agora Currently Believes" vault doc,
>   Claude-merged when >=2 new artifacts (loop A14); v1 seeded. Telegram `canon`.
> - **14 The Tutor** (`7fd4404`): SM-2 spaced repetition over the owner's evergreen notes,
>   one-tap grading (`got 1`/`forgot 1`), retention feeds vitals. Telegram `quiz me`.
> - **15 Capability Forge** (`bac28f8`): gap registry + failure-trace detectors; weekly the
>   oldest gap queues as a build (loop A15). Telegram `gap <desc>` / `forge`.
> - **16 Attention Economy** (`4f72815`): yield-weighted run-probability [0.4,1.0] gates the
>   four noisy triggers; compute follows value. Telegram `attention`.
>
> **Wave 5 — the organism meets reality (all SHIPPED 2026-06-10 ~00:00):**
> - **17 The Desk** (`6b584f4`): activity-aware working context — owner's notes + fresh papers
>   + open questions for what he's actually working on; daily + `desk <topic>`.
> - **18 The Watchdog** (`94b275b`): mutual process supervision (brain⇄dungeon kill+restart,
>   crash-loop guard + Telegram alert), Startup-folder autostart for reboots.
> - **19 Contradiction Sweep** (`a6b761a`): close note pairs judged for INCOMPATIBILITY;
>   genuine contradictions feed the dialectic pipeline. Telegram `contradictions`.
> - **20 Source Reliability** (`92b8dc9`): per-source verdict ledger (hits vs non-answers),
>   weights injected into insight-inputs. Telegram `sources`.
> - **21 Agent Mastery** (`b16d986`): verification verdicts attributed to contributors;
>   standing now blends trust + forecast accuracy + mastery. Telegram `mastery`.
>
> **Wave 6 — time, computation, society (all SHIPPED 2026-06-10 early):**
> - **22 Night Shift** (`c982490`): nightly memory consolidation — full vault re-embed
>   (FIXED a silent defect: the index never rebuilt, fresh notes were unsearchable),
>   retrieval-log trim, bridge application. First run: 5685 notes, 4.1 min.
> - **23 Laboratory** (`73b0b21`): simulation as the third evidence channel — Claude-written
>   scripts, deterministic runner (60s cap), ledgered with source "simulation". Loop A16.
>   First result: the vault value distribution is bimodal (1227@4 vs 2845@8).
> - **24 Annals** (`e9047cd`): deterministic daily chronicle from real traces + Sunday Claude
>   retrospective (A17). First chronicle: 2026-06-09 (20+ commits, 25 artifacts).
> - **25 Board Meeting** (`1e303a8`): weekly agenda → owner directives become STANDING
>   PRIORITIES injected into mind/insight/predict inputs. Telegram `board <text>`.
> - **26 Salon** (`3bc0364`): 8 live-verified external feeds (Willison, Gelman, ACX, Quanta,
>   Interconnects, MR, Lil'Log, Appleton); one contestable claim a day into the dialectic.
>   First salon dialectic shipped (Willison on Apple Intelligence).
>
> **Wave 7 — signal hygiene + owner experience (all SHIPPED 2026-06-10 morning):**
> - **27 Gatekeeper** (`5d61c0e`): skip ledger + board priorities INSIDE the queue generators
>   (insight/predict/sense); capability map in the self-upgrade architect prompt. Seeded with
>   the night's 4 refusals.
> - **28 Atlas** (`fc166c7`): 12 auto-maintained per-domain Maps of Content + index (value-ranked
>   core concepts, fresh arrivals, orphans). Telegram `atlas`.
> - **29 Gauges** (`5acafcb`): GET /api/v1/agent-os/dashboard — every ledger on one dark page
>   with SVG sparklines. Telegram `dashboard`.
> - **30 Coherence Audit** (`6834574`): one new belief/day judged against its closest siblings;
>   tensions auto-queue internal dialectics. Telegram `coherence`.
> - **31 Thread** (`cdcdc32`): rolling 6-exchange Telegram memory (2h TTL) — follow-up questions
>   resolve against the conversation.
>
> **Wave 8 — skin in the game (in progress):**
> - **32 The Oracle** (`cf0b417`, SHIPPED): live Polymarket markets → independent Agora
>   probability vs market price, edge logged, Brier-scored vs hard reality on resolution
>   (loop A18; daily scan+resolve; Telegram `oracle`). First position: Anthropic best-model
>   EOJune — market 92%, agora 90%.
> - **33 Metabolism** (`af0d2a0`, SHIPPED): every LLM call metered + attributed to its organ
>   (HTTP-middleware contextvar, survives asyncio.to_thread); ROI = value-points/kilotoken from
>   existing ledgers. Telegram `metabolism`, dashboard card.
> - 34 Theory Engine (runnable beliefs), 35 Counterfactual Self (replay own history under
>   alternative policies), 36 Correspondent (gated outbound contact) — PLANNED, not yet built.
>
> Future-wave ideas parked: deeper Mind Chamber, calendar OAuth, more Hands action kinds,
> within-owner randomized OS-assistance experiment (the dossier's tier-3 attack).

---

## (Wave 2, all shipped) The Forecasting Tournament etc. — original plans below

---

## 1. The Forecasting Tournament — agents compete, trust follows truth
**WHAT:** Every dungeon agent makes its own prediction on the same theme (not just one ledger
entry); each agent carries a personal track record, and resolved outcomes feed ESS trust —
an agent that calls reality right gains standing (and curation authority), one that's wrong
loses it.
**WHY:** Closes the deepest loop in the system: REPUTATION = CALIBRATION. Standing currently
comes from cooperation; this makes it come from being RIGHT about the world. The Custodian
Principle applied to the agents themselves.
**BUILD:** Extend `.predictions.json` records with `agent` field; `_run_predictions` asks each
agent's persona (cloud flash, labeled-text) for a direction+confidence on the queued theme;
`resolve_due` maps outcomes → `TrustEngine` nudges; per-agent hit-rate in the roster HUD.
**TEST:** Unit-test the trust-nudge mapping; force-resolve a synthetic prediction; verify
standing shift in `trust_graph` broadcast.
**RISK:** Low — additive fields, the Claude ledger path stays untouched.

## 2. Calendar & Activity Senses — perceive Rasto's REAL day
**WHAT:** New senses: today's calendar (ICS export or Google Calendar MCP), recent vault edit
activity, agora repo git activity. `/brain/now` gains a `today` section: what Rasto is doing,
not just what the world is doing.
**WHY:** Rasto floated it; cognition should align to the owner's actual day — morning report
and queued themes become *relevant to today*, not generic.
**BUILD:** `senses.py` + `_ics_today()` (stdlib parse of an exported .ics path from `.env`) +
`_vault_recent_edits()` (mtime scan) + `_repo_activity()` (git log -5). `_sense_and_queue`
prefers a theme intersecting today's events. No external auth needed for v1 (ICS file path).
**TEST:** Fixture .ics file; assert `today` section shape; live `/brain/now` 200.
**RISK:** Low — read-only senses; degrade gracefully when no ICS configured.

## 3. The Memory Economy — the Custodian actually governs
**WHAT:** Agora starts ACTING on its own grand insight: per-note value accounting (retrieval
frequency via semantic-search hits, connectivity, age, verification tier) → weekly GATED
`curate` actions: "archive these 12 never-retrieved stubs", "merge these 3 near-duplicates"
(Rasto approves from Telegram before anything moves).
**WHY:** The vault only grows; the Custodian Principle says intelligence is governance of
scarce memory under challenge. This is the missing PRUNE half of curation.
**BUILD:** `semantic_index.py` logs query hits → `.retrieval_log.json`; `memory_economy.py`
scores notes; Hands gains GATED kind `curate` whose executor moves files to
`_vault_quarantine` (reversible, never deletes); weekly dungeon trigger proposes one batch.
**TEST:** Score a fixture set; verify a `curate` action stays PROPOSED until approval; verify
quarantine move + restore round-trip.
**RISK:** Medium — touches the vault, but gated + quarantine-reversible by design.

## 4. The Exam — is Agora (and Rasto) actually getting smarter?
**WHAT:** A measurable benchmark loop: monthly, Agora generates a fixed-size Socratic exam
from the vault's core concepts, ANSWERS IT ITSELF (flash), Claude grades it against the notes,
and the score lands in the ledger + HUD. Optionally the same exam goes to Rasto via Telegram
(`exam` command) — his score tracked too.
**WHY:** "The system learns" is currently inferred from lessons; this makes capability growth
a NUMBER with a time series. Also doubles as spaced repetition for Rasto.
**BUILD:** `exam.py` (`/brain/exam/generate`, `/exam/grade`, `.exams.json`), Socratic engine
reused; grading = inbox task for Claude; HUD shows last score + trend.
**TEST:** Generate from fixture notes; grade a known-good and known-bad answer sheet.
**RISK:** Low — read-only over the vault.

## 5. The Mind Chamber — a 3D room where the worldview lives
**WHAT:** A dedicated dungeon chamber (Three.js) visualizing cognition spatially: beliefs as
floating crystals (size = grounding count, color = domain), open flywheel questions as dim
portals that BRIGHTEN when deepened, prediction outcomes as falling green/red shards. Agents
physically walk there when they work on a related quest.
**WHY:** The dungeon is the FACE; the HUD shows numbers but the worldview itself is still
invisible. This makes the mind a PLACE you can watch evolve.
**BUILD:** `dungeon-os-threejs` skill; new room tiles + `mind_chamber` WS event derived from
`mind-inputs`; renderer module in `static/index.html` (instanced meshes, ≤100 objects).
**TEST:** `node --check` the module; page 200; event renders with fixture payload.
**RISK:** Low-medium — pure frontend + one broadcast; perf-bounded by instancing.

## 6. The Research Exchange — Agora publishes (gated)
**WHAT:** A weekly public digest: Agora compiles its best verified insights into a polished
markdown brief; a GATED `publish` action pushes it to a GitHub Gist / repo page only after
Rasto approves from Telegram. Public URL comes back as a `reference`.
**WHY:** Outputs currently land only in the vault. Publication = external challenge (the
strongest falsifier source there is) and a public track record.
**BUILD:** Hands executor for the already-GATED `gist` kind via `gh gist create`; composer
reuses `export_insights`; weekly dungeon trigger PROPOSES (never auto-runs).
**TEST:** Compose from fixtures; verify the action stays PROPOSED; dry-run `gh` auth.
**RISK:** Medium (outward-facing) — fully gated behind explicit approval, hence safe.

---

**STATUS (2026-06-09): ALL SIX SHIPPED.** 1 `2ac086b` (first tournament recorded), 2 `5c42822`,
4 `20f9f57` (first exam 7/8), 3 `e9d60da` (live audit: 4710 notes, 0 dead weight — young vault,
candidates will age in), 5 `a366cef` (verified live over WS: 10 belief crystals, 9 portals,
2 shards), 6 `c40a59b` (digest of 8 insights composed; publish proposal `907b62` awaits
`approve` on Telegram → goes to public/research_digest.md in this repo).

**Recommended order:** 1 → 2 → 4 (each small, each closes a real loop), then 3, then 5/6.
One frontier at a time; every step keeps the safety rules (small reversible commits,
py_compile, both servers 200, revert on breakage).
