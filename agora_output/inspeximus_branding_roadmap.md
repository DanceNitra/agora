# inspeximus — Branding & first-revenue roadmap

> Fixed 2026-07-17 from a 3-lens research gate (case studies of mem0/Zep/Letta/Cognee/Supermemory/Crawl4AI/Marker ·
> solo-OSS monetization data · real-name/naming research). Metric-triggered stages, not dates. Owner reviews at
> every stage gate. Current baseline: ~5,300 PyPI downloads/week, 3 GitHub stars, MCP registry listed, $0 revenue.

## What the evidence says (the five patterns that moved every comparable project)

1. **One crisp differentiating idea, not a feature list.** MemGPT = "LLM as an OS". Graphiti = "temporal knowledge
   graphs". Ours exists already: **"self-correcting memory — a corrected fact stays corrected."**
2. **Real name + prior-work credibility from day one.** Every breakout except one persona-pseudonym (Crawl4AI)
   ran on a visible human. For a *trust/memory* product, anonymity works against the pitch.
3. **Relaunch the same asset repeatedly.** mem0: rename thread → Show HN → paper — each a fresh launch of the
   same code. Nobody wins with a single launch.
4. **Integrations are free distribution.** Cognee ground to 12k stars with zero viral moments — every integration
   (LangChain/MCP/n8n/Neo4j) borrows the partner's audience. Our MCP-first path is this pattern.
5. **Stars precede money by ~a year.** Nearly everyone sat at $0 for 12+ months; paid tiers landed with or after
   traction. Expectations set accordingly: first revenue is beer money, not survival — the asset being built is
   distribution.

**What did NOT matter early (do not spend time on):** polished logo/design (Letta hit 11k stars as a bare
academic repo) · Hacker News (4 of 7 comparables never cracked 10 points; our account is shadowbanned anyway) ·
early pricing pages.

## DECISION #1 — RESOLVED (owner, 2026-07-17): anchor on `inspeximus`, no rename

The owner's call, and it's right: the actual funnel handle is **`inspeximus`** (the PyPI package, the pip
command, all 5.3k weekly downloads) — and THAT token is unique; the collisions live on the bare word "inspeximus".
So: (1) canonical searchable token = `inspeximus`, never changed, visible next to every install block;
(2) display brand = "inspeximus — self-correcting agent memory", always paired with `inspeximus` in titles/OG;
(3) MCP registry name is namespaced (io.github.DanceNitra/inspeximus), no collision, stays; (4) the rename escape
hatch stays open for later WITHOUT breaking funnels — a new package name with `inspeximus` kept as a
dependency shim (pip keeps working; GitHub renames redirect; mem0 renamed at 8k stars and inherited its
audience). Revisit ONLY at the Stage-2 gate if inspeximus.dev launches loudly into Claude Code and real confusion
incidents appear.

### (superseded analysis, kept for the record)

"inspeximus" is saturated in *exactly our category*: **inspeximus.dev is a live-in-progress "AI agent memory system"**
(The Water Works; deep Claude Code integration; literally ships a `inspeximus recall` CLI — verified 2026-07-17),
plus 6+ GitHub repos and a `inspeximus-mcp` PyPI package by others, plus Inspeximus flashcards and the inspeximus caving
device owning adjacent search results. "inspeximus AI memory" is not a winnable search phrase.

- **Option A — rename now (research recommendation).** Cheap today, expensive after traction. mem0 renamed
  in-place at 8k stars and *inherited* the audience, so a later rename is survivable but costly. A rename doubles
  as a relaunch event (pattern #3). Naming seed: the differentiator (self-correcting / corrections / supersession
  / "stays corrected"), not the memory-Greek root everyone mines.
- **Option B — keep, always paired.** "inspeximus (inspeximus) — self-correcting agent memory" everywhere; accept
  the SERP loss; rely on the PyPI name and MCP registry entry being ours. Zero migration cost, permanent
  discoverability tax, and a live collision risk if inspeximus.dev launches loudly into Claude Code — our main channel.
- Until decided: **no paid ads-level pushes on the name**; keep shipping under the paired form.

## Stage 0 — now → ~100 engaged users/stars ("the face + the spine")

Cost: ~0 EUR. Everything here is evidence-backed as high-leverage.

1. **Real name, stage 1.** README "Built by Rastislav Drahoš" + an About-the-maker page (face, one-paragraph
   story: autonomous-research OS → extracted its memory core; links the physics-collab identity as public
   precedent) + PyPI author field. **Commits stay noreply** (standing rule); home address/phone never.
2. **One-liner lock-in.** "The self-correcting memory layer for AI agents" verbatim on: PyPI, README, homepage,
   MCP registry, HF, any post. (Done for most surfaces 2026-07-17; keep enforcing.)
3. **90-second visual proof.** The animated correction demo (shipped in README) + a short screen-capture GIF of
   the MCP flow inside Claude Code — the "see it in 90 seconds" asset every comparable had.
4. **Relaunch cadence, one asset at a time** (pattern #3): the integrity benchmark, the review-trigger, the
   1.9.x correction stack — each is a separate small launch (Reddit via owner, r/LocalLLaMA / r/RAG), never all
   at once. Reddit = owner posts (standing rule).
5. **Sponsors baseline (1 hour).** GitHub Sponsors + Polar with exactly ONE tier: "$10/mo — priority issue
   response in 48h" (scoped tiers convert; "support my work" doesn't). Expect $0–50/mo; it's a door, not income.
6. **Integration surface area** (pattern #4): keep the 6 framework adapters + MCP registry fresh; add an
   integration only where a partner audience exists (n8n template, LangGraph example repo, Cline/Continue docs).

## Stage 1 — at ~10k downloads/month sustained + first inbound questions ("first korunky")

Trigger: already met on downloads; wait for the first organic inbound (issue/question from a stranger) so the
paid thing answers a demonstrated need.

1. **inspeximus-pro audit/governance add-on — $29 one-time via Polar** (license-key file, zero servers). Content:
   tamper-evident log export, tenant/compliance reports, signed-build attestation — monetizes the integrity
   story we already measured, doesn't paywall the core. Evidence: sub-$5 products = 0.8% of revenue (KILLED the
   50-cent idea); $30–49 band converts 28% better. Realistic: $0–300/mo.
2. **Real name, stage 2.** Personal X/LinkedIn account signs release posts; owner-posted Reddit under real name.
3. **A Show-HN-shaped asset without HN**: one first-person write-up ("I run an autonomous research org; its
   memory layer kept resurrecting corrected facts; here's what fixed it") — the founder-story format that carried
   Supermemory/Postiz. Publish on the storefront; owner distributes.

## Stage 2 — at ~500 stars or first company user ("proof of demand")

1. **Apify-hosted paid MCP endpoint** (they host, 80% rev share — solves zero-capital hosting) IF inbound asks
   for hosted. Do not build our own hosting (owner decision 2026-07-17: no money, no clientele — parked).
2. **Paid support tier** ($99+/incident or retainer) at the first company user.
3. **Real name, stage 3**: a talk/podcast/meetup; storefront byline.
4. Revisit the name decision with data (SERP position, confusion incidents, inspeximus.dev's status).

## Anti-goals (fixed)

- No self-hosted SaaS until demand is proven AND funded (owner, 2026-07-17).
- No sub-$10 products (data: signals toy, maximizes support cost per dollar).
- No competitor-defined framing (owner, 2026-07-17: the flagship stands on its own name).
- No paid logo/PR/trademark at this size.
- Nothing ships or gets posted without the standing gate (validate → storm → audit → verify).

## Metrics to watch weekly (the funnel un-inverting)

PyPI downloads/week (baseline 5,289) · GitHub stars (3) & unique visitors (9/14d) · MCP registry installs if
observable · ramr/integrity-repo views (1) · inbound issues/questions from strangers (0) · sponsor/Polar
conversions (n/a). The single most important early signal: **strangers opening issues.**
