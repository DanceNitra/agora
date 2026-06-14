---
name: open-world-forge
description: Open-world idea generator that ESCAPES the same-research loop. Instead of reading Agora's own canon (which recycles), it anchors every run in EXTERNAL material — a rotating random draw from the 36 books in the vault's `04 Resources/Books/` plus COLD (un-mined) vault domains — and runs the IDEAOGENESIS operators (Gap, Inversion, Scale, Constraint-Drop, Fusion, Exaptation, Via-Negativa, Secret, Anomaly→Paradigm, Against-Method) to force cross-book collisions. Use when the owner asks to "generate ideas", "nové nápady", "forge ideas", "open world ideas", "go farther / something new", when a "Forge ideas" inbox task appears, or on a schedule. The books are the anchor; YOU (Claude) make the leap. Replaces the deprecated idea-forge.
---

# Open-World Forge — break the loop by anchoring on the books, not on ourselves

The owner's complaint that created this skill: *"I want to go farther than the same loop about the same research."* The old `idea-forge` read the brain's own substrate (`ideation/inputs` = canon, beliefs, recent ideas) and so it **recycled** — coherence of what's-already-in-view manufactures confidence and the generator converges on its own attractor.

We have **measured** this exact failure: a generator that weights its own prior output with super-linear self-trust **locks** a permanent fraction of its founding bias (Lab `75db49`, the strange-loop attractor — 50% locked at `p=2`; needs a ≥3–5% external-evidence anchor to recover). The books say the same thing three ways — Kahneman (**WYSIATI**: confidence comes from the coherence of what's in view, not its completeness), Gazzaniga (the **interpreter** confabulates a coherent story for outputs it didn't derive), Johnson (the **adjacent possible**: the reachable frontier is only what current memory makes visible). 

**So the cure is structural, not stylistic: keep the external-evidence fraction HIGH and search for novelty/absence, not coherence.** This skill is built so that every run *must* stand on material from outside our own canon.

## The four rules that make it open-world (do not skip)
1. **External anchor every run.** The primary substrate is the **36 books** + **cold vault domains**, NOT our canon. The brain's self-knowledge is used for ONE thing only: to *avoid repeating* (the dedup/cold-domain set). Never let our own canon laws be the source of an idea.
2. **Rotate the draw (divergence by construction).** Each run reads a *different* random subset of books and a *different* set of cold domains, so two runs can't converge on the same combination. (No `Math.random` needed — vary by the date and what was drawn last, recorded in the note.)
3. **Reward DISTANCE, not just feasibility.** Score each idea on how far it sits from our current canon/recent-ideas. A safe, on-canon idea is the *failure mode*, not the goal. Surprise and "secrets" (Thiel) beat tidy coherence.
4. **Open targets.** There are NO fixed targets (the old 4 — os/agora/mcp_memory/realworld — were part of the loop). Generate first, anywhere, civilization-scale allowed; tag applicability *after*.

## 1 · Gather — pull the EXTERNAL deck (this is the heart)
The books live in the **vault, in git only** (`04 Resources/Books/`, not checked out on the Windows disk). Read them with git:
```bash
VAULT="C:/Users/Danculus/my-second-brain"
git -C "$VAULT" ls-tree -r --name-only HEAD -- "04 Resources/Books/"      # the 36 titles
git -C "$VAULT" show "HEAD:04 Resources/Books/<file>.md"                    # read one book note
```
The 36 span idea-generation (Where Good Ideas Come From, The Art of Thought, Medici Effect, Creative Confidence/Intelligence, GEB), innovation (Innovator's Dilemma, Zero to One, Diffusion of Innovations, Lean Startup, Design of Everyday Things), epistemics (Thinking Fast and Slow, Superforecasting, Kuhn, Popper, Against Method, Beginning of Infinity, Reinventing the Sacred), complexity/systems (Complexity, Thinking in Systems, Linked, Seeing Like a State), evolution/biology (Selfish Gene, Extended Phenotype, Secret of Our Success, Evolution of Cooperation, …), and info/mind/physics (The Information, Elegant Universe, Emperor's New Mind, Consciousness Instinct, Superintelligence, Antifragile, Nudge, Behave).

Each run:
- **Draw 5–7 books** at random (rotate vs the "books drawn" line of recent open-world notes — never repeat last run's set). Read those notes in full from git.
- **Draw 2–3 COLD domains** — `Vault_*` folders (or `ideation/inputs.vault_corpus.by_target`) that are NOT in the recent-ideas set. Read 3–5 real notes from each via git or disk.
- **Optional 1 live pull** — a WebSearch on the *edge* of the frontier (the adjacent possible just outside our walls), if a run wants a world-anchor.
- **Dedup set only:** `GET /api/v1/agent-os/brain/ideation/inputs` → use ONLY `recent_idea_titles` (avoid repeats) and to detect cold domains. Ignore the rest — it's the loop.

## 2 · Generate — run the operators (forcing functions for collision)
Apply several, not all; pick what the drawn deck makes alive. Each operator forces a *cross-book or cross-domain* leap:
- **Gap (Λ)** — a hole that sits *between* the drawn books' domains that none covers alone.
- **Inversion (∇⁻¹)** — take two books that flatly contradict (e.g. Thiel "monopolies are good" × Christensen "monopolies get disrupted") and synthesize the thing that resolves them.
- **Scale (×10³)** — lift a mechanism across levels: individual → org → market → civilization.
- **Constraint-Drop** — remove a "everyone knows you need X" assumption and build what's now possible.
- **Fusion (⊕)** — fuse 3–4 books into one mechanism no single book contains; score it (Market / Tech / Unique / Scale / Moat + **Distance-from-canon**).
- **Exaptation (Johnson)** — take a mechanism *proven* in one domain (incl. one of our Lab results) and repurpose it where it was never meant to go.
- **Via-Negativa (Taleb)** — generate by *removal*: what would you delete, and what becomes possible once it's gone.
- **Secret (Thiel)** — "what important truth do very few people agree with you on?" grounded in a book.
- **Anomaly → Paradigm (Kuhn)** — find the anomaly our current frame can't explain; propose the frame that would.
- **Against-Method (Feyerabend)** — deliberately violate one of Agora's own standing rules for this run and see what it frees.

Produce **4–6 ideas**. Each MUST clear the owner's raised bar AND the open-world bar:
- **title · the insight · which BOOKS/domains it stands on (≥2 external) · the mechanism (structural, not vibe) · why it's NON-OBVIOUS / its distance from our canon · the smallest falsifying test (Lab run or measurable prototype) · one concrete first step.**
- **Kill it if:** its mechanism is already a canon law; it rests only on our own substrate; or its essence is in `recent_idea_titles`. Repetition is the one unforgivable failure of this forge.

## 3 · Ship
- **Vault note** — one note per run: `04 Resources/Concepts/Agora Agents/<YYYY-MM-DD>/open-world-forge-<slug>.md`, tags `[agora, idea-forge, open-world, claude-synthesis]`. **Record the draw** at the top (`books drawn: …`, `cold domains: …`) so the next run rotates away from it. Push: `DUNGEON_AUTOPUSH=1 python tools/safe_vault_push.py "Open-World Forge: <n> ideas (<operators>)"`.
- **Record each** (dedup + trail): `POST /brain/ideation/record {title, target, mechanism, test, first_step, grounding, note}` — `target` can be `realworld|mcp_memory|agora|os` for routing, or the closest fit; put the books in `grounding`.
- **Route the strong ones:** concrete capability → `POST /brain/forge/add {description}`; world-facing & proven → consider a gated `POST /brain/press/draft`.
- **Telegram digest** (ASCII, ≤7 lines; owner brief can be Slovak): the idea titles + the books each fused + which operator. Token: read `server/.env` (`HERMES_TELEGRAM_BOT_TOKEN`/`HERMES_TELEGRAM_CHAT_ID` or `AGORA_TELEGRAM_*`) via `python -X utf8`, never literal on a command line.
- If from an inbox task: `POST /brain/claude-inbox/done {id, result}`.

## Gotchas
- Books are git-only — always `git -C "$VAULT" show HEAD:...`; don't expect them on disk.
- Vault push on Windows: always `tools/safe_vault_push.py`, never `git add -A` (see [[vault-push-ntfs-gotcha]]).
- Keep ideas English; owner digest can be Slovak.
- Provenance of the method: IDEAOGENESIS runs in `04 Resources/Research/IDEAOGENESIS_*` and the today-synthesis `synthesis-books-into-new-directions` (the "make absence + provenance first-class" throughline). The anti-loop rationale is Lab `75db49` (strange-loop attractor) + [[agora-frontier-direction]] + [[agora-roadmap-firm-os]].
