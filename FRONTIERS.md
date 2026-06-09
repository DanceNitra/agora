# AGORA — FRONTIER UPGRADE PLANS (v2, 2026-06-09)

> The first frontier wave is DONE (Insight Engine → Prediction Ledger → Flywheel → Mind →
> Learning → Hands → Senses → visible HUD). These are the NEXT frontiers — each numbered so
> Rasto can pick one from Telegram (`cc frontier N`) or in chat. Each plan: WHAT / WHY /
> BUILD / TEST / RISK. Ordered by leverage-to-effort.

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

**Recommended order:** 1 → 2 → 4 (each small, each closes a real loop), then 3, then 5/6.
One frontier at a time; every step keeps the safety rules (small reversible commits,
py_compile, both servers 200, revert on breakage).
