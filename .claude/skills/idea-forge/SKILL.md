---
name: idea-forge
description: Generate GROUNDBREAKING, buildable ideas from everything the brain knows, across four standing targets — the System/OS, Agora itself, the MCP memory product, and a real-world product. Use when the owner asks to "generate ideas", "nové nápady", "forge ideas", "what should we build", when a "Forge ideas" inbox task appears, or on the 1–2×/day schedule. Agora gathers the whole rigorous cross-section; YOU (Claude) do the creative leap.
---

# Idea Forge — groundbreaking ideas from the whole brain

The owner wants a steady supply of **genuinely groundbreaking, non-obvious, buildable** ideas —
not a stream of tidy notes, not re-derived textbook results. This skill is the wide-angle
complement to the narrow engines (insight engine, synthesis organ, hypothesis induction): it
reads the brain's **entire rigorous cross-section** and asks you to make real creative leaps,
aimed squarely at four standing targets.

**The division of labour holds: Agora gathers, you create.** The gather is one endpoint. The
creative leap — the part that matters — is yours, at the owner's raised bar.

## The four targets (every run covers a spread, not all of one)
- **`os`** — the agent operating system & dungeon substrate (scheduling, memory, coordination, the loop, robustness, observability).
- **`agora`** — the epistemic engine itself (new organs, sharper loops, higher research yield, quality firewalls, compounding mechanisms).
- **`mcp_memory`** — the memory product (mnemo / second-brain-as-a-service over MCP): an outsider's notes becoming a thinking partner — retrieval, consolidation, recall.
- **`realworld`** — a shippable product the outside world would pay for, grounded in what the vault has actually *proven*.

## 1 · Gather (one call)
`GET /api/v1/agent-os/brain/ideation/inputs` returns the whole substrate:
- `canon` (the laws), `beliefs` (+`calibration`), `lessons`, `owner_priorities`
- `replications.reproduced` / `replications.failed`, `analogies`, `theory_runs`
- `synthesis_signals` (phase-transition precursors), `frontier`, `library_read`
- `recent_findings` (40 freshest grounded facts) — what the *agents* just grounded
- `vault_corpus` — `{indexed_notes, by_target}`: the owner's WHOLE second brain (~6000 notes,
  semantically indexed). `by_target` pulls the most relevant *real* notes per target straight
  from the full corpus, so the forge stands on the vault's depth, not just the recent stream.
- `recent_idea_titles` (the anti-repeat set), `targets`

Read it ALL before generating. The groundbreaking ideas live in the *collisions* between
distant items — a failed replication × a canon law, a finding from one domain × a belief from
another. That is where you look.

## 2 · Generate — the bar is GROUNDBREAKING, not tidy
Produce **4–6 ideas** spread across the four targets (aim for at least one per target over a
day; a single run may weight toward where the strongest material is). Each idea MUST clear this bar:

- **Non-obvious & original.** If it's a known pattern (RAG, "add caching", "use embeddings",
  textbook results the canon already states) — kill it. Ask: *would a sharp engineer who'd read
  our vault still say "I hadn't thought of that"?*
- **Grounded in OUR knowledge.** Cite the specific belief / finding / replication / analogy it
  stands on (by its text). An idea that doesn't rest on something the brain actually knows is a
  guess, not a forge.
- **Mechanism, not vibe.** State the *mechanism* that makes it work — the structural reason,
  the same rigor we demand of a hypothesis.
- **Falsifiable / testable.** The smallest test that would tell us it's wrong, ideally a Lab run
  or a measurable first prototype. No test → not an idea, a wish.
- **One concrete first step.** What you'd build first this week, small and reversible.

For each idea, write: **title · target · the insight · why it's non-obvious · the mechanism ·
the grounding (which vault knowledge) · the smallest test/falsifier · the first step.**

**Dedup:** skip anything whose essence is already in `recent_idea_titles`. Repetition is the
one unforgivable failure of a forge.

## 3 · Ship
- **Vault note** — collect the run's ideas in ONE note:
  `04 Resources/Concepts/Agora Agents/<YYYY-MM-DD>/idea-forge-<slug>.md`, tags
  `['agora','idea-forge','claude-synthesis']`. Push: `DUNGEON_AUTOPUSH=1 python tools/safe_vault_push.py "Idea Forge: <n> ideas (<targets>)"`.
- **Record each** (dedup + public trail): `POST /brain/ideation/record`
  `{title, target, mechanism, test, first_step, grounding, note}` (target = one of `os|agora|mcp_memory|realworld`).
- **Route the strong ones onward:**
  - An `agora`/`os` idea that's a concrete capability → `POST /brain/forge/add` (the engineering gap pool).
  - A `realworld`/`mcp_memory` idea worth showing the world → consider a gated `POST /brain/press/draft` (publishes only on owner `approve`).
- **Telegram a short digest** (ASCII, ≤6 lines): the idea titles with their target tags, e.g.
  `[FORGE] 5 ideas — 2 agora, 1 os, 1 mcp_memory, 1 realworld:` then one line each. Token in
  `server/.env` as `HERMES_TELEGRAM_BOT_TOKEN` / `HERMES_TELEGRAM_CHAT_ID`; send via `python -X utf8`.
- If invoked from an inbox task: `POST /brain/claude-inbox/done {id, result}`.

## 4 · Fire 1–2×/day
This skill is built to run on a schedule. Durable cloud cadence (survives session close):
use the `schedule` skill to create a routine, e.g. twice daily —
`/schedule run /idea-forge every day at 09:00 and 21:00`. In a live session you can also drive it
with `/loop 12h /idea-forge`. One run = one vault note + a Telegram digest; quality over volume.

## Gotchas
- The ledger file is `server/.ideation.json` (parents[2] = `server/`), not the repo root.
- Restarting the brain after editing `ideation.py`: kill **all** uvicorn/agora.main first
  (a stale process keeps the port and your new routes 404) — verify exactly ONE `:8000` listener.
- Vault push on Windows: always `tools/safe_vault_push.py`, never `git add -A` (see [[vault-push-ntfs-gotcha]]).
- Keep ideas English; the owner brief/digest can be Slovak. The bar is the owner's raised bar:
  rigorous, original, ambitious — see [[agora-frontier-direction]], [[agora-roadmap-firm-os]].
