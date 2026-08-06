# CURRENT STATE — pointer

**Latest handoff: `HANDOFF_2026-08-06.md`** (inbox 100 -> 0; board edited to drop the retrieval axis;
5 GitHub comments out incl. one public retraction; 4 claims killed at the gate, 1 got stronger; the
swarm's five silent organs traced to a write path that is never called).

---

# HANDOFF — current state (2026-06-30, late) — READ THIS FIRST on resume

This is the exact resume point. Read it, then `agora_output/publish_audit_tracker.md`, then the
`/audit-post` skill (`.claude/skills/audit-post/SKILL.md`), then proceed. Chat with the owner in SLOVAK;
code + public output in ENGLISH. **Servers survive the reset — do NOT restart them.**

## THE ACTIVE TASK: professional audit of every published post
Re-auditing all 42 published posts to a scientific-organization standard, ONE AT A TIME, using the full
`/audit-post` procedure. Owner emphatic (repeatedly): **never shorten the procedure; fewer posts done
FULLY beats more done shallow.** The full panel has caught a real defect in EVERY post audited so far —
a 2-skeptic re-audit alone does NOT replace the 5-lens panel (the panel finds the DEFECTS; the skeptics
verify the FIXES). Memory: [[audit-publish-full-procedure-never-shorten]].

### The procedure = the `/audit-post` skill (9 steps, none optional)
0 read · 1 state claims · 2 RE-RUN our lab numbers from source · 3 `/stress-claim` FULL 5-lens panel
(prior-art hunter, steelman, method/confound, overclaim, blind-spot 6th) → PUBLISH/REFRAME/KILL · 4
`/verify-claims` every citation vs PRIMARY source · 5 apply fixes BILINGUAL EN+SK (body + FAQ visible AND
the JSON-LD FAQPage copy + footer + META `desc`/`title` which feed tldr/meta/og/twitter/schema) + SEO
(/seo Mode-A, bump dateModified) · **6 RE-AUDIT the corrected post (≥2 skeptics) until CLEAN — never skip** ·
7 capture new findings → `agora_output/audit_new_findings.md` · 8 leak-scan + anon commit
(`agora-builder@users.noreply.github.com`) + force-add any new lab script · 9 report.
HOW I run it: fan out the 5 lenses + verify-claims as PARALLEL general-purpose agents (seed each with the
re-run lab numbers + known issues); consolidate; DELEGATE the EN+SK application to one agent with an exact
spec; validate (tags/JSON-LD/leak); run 2 skeptics on the corrected post; commit substance, then a separate
"tracker: audit #N DONE (hash)" commit. Common recurring defects: truncated meta/TLDR (mid-word), SK locale
(dot-decimals, English "Research", empty SK footer, ASCII quote glyphs), EN/SK falsifier styling mismatch
(EN plain <p> vs SK styled blockquote), crediting the mechanism but not the REVERSAL/result of the cited
authors, headlines that drop a load-bearing qualifier.

### Audit progress — #1–#14 DONE to full standard; #15 TEED UP. (tracker = source of truth)
All commits below are LOCAL; deploy is owner-gated ("deploy"). #1–#13 already deployed (pushed earlier today);
**#14 + its tracker commit = 2 commits NOT yet pushed.**
- #1 causal-inference-phase-diagram (4eee700) — REFRAME: estimand error (total vs direct), retitled.
- #2 pre-trends-test-weak-evidence (6ee8239) — REFRAME: z-vs-t-on-4df bug, 31%→16%.
- #3 operating-point-trap (7eee3d8) · #4 why-crowds-get-dumber (5b6af3f) · #5 passing-pre-trends (b35c1ae,
  then COLLAPSED into #2 as a redirect — owner-approved dup removal) · #6 95%-CI-covers-31 (d1e18d3) ·
  #7 more-data-more-wrong (e8de83b→edae333) · #8 set-exit-criteria (2933528→9c98c37) · #9 ai-training-on-itself
  (d48f4e8→e5c7ace) · #10 second-brain-dying (519d10c) — all FULL panel + re-audit CLEAN.
- #11 ragfresh (0eeef31) — heavy REFRAME: RIGGED benchmark rebuilt (value is the lever, not freshness;
  hits-proxy ~91%); dropped "freshness beats retrieval"; +GDSF/LFUDA prior-art; crossover 0.09→0.07.
- #12 dunning-kruger (0c5c9aa) — REFRAME: +Krueger-Mueller 2002 + Nuhfer 2016/17 prior-art; "no skill-dependent
  self-insight" was FALSE (model corr 0.59); table top splice ~77→~73.
- #13 hot-hand (22cd8e3) — REFRAME: credited Miller-Sanjurjo for the REVERSAL (not just the mechanism); P0
  truncation; "small"→"substantial ~11-13pp"; added the per-player/pooling nuance.
- #14 anti-aging-scorecard (6ce3997) — REFRAME, medically SOUND (verify 7/7): restored "hard endpoint" to
  headline + calibration-led; "1 of 16 even tested/15 untested" reframe; BUILT the 16-row table; +Rejuvenation
  Roadmap prior-art; senolytics de-quote; ASPREE cancer-driven+primary-prevention.
- **NEXT = #15 the-calibrated-prior-for-we-reversed-aging-in-mice** (SISTER of #14; its core lab
  20260616-geroprotector-survival-statistic-artifact.py was re-run this session: 39.9% log-rank-vs-Gehan
  discordance, FPR 5.4→7.6%; #14 already cites it — keep #15 consistent). Tracker has the resume note.
  Then #16…#41 in tracker order, each at full /audit-post standard.

## Config / doctrine (changed this session)
- **CLAUDE.md rewritten to the all-cloud reality** (it's gitignored, local only): all LLM tiers on Ollama
  Cloud — brain main `glm-5.2`, cheap/bulk `deepseek-v4-flash`, reasoning `glm-5.2:cloud` via the local
  cloud-route (`localhost:11434/v1`), dungeon `deepseek-v4-flash`. **Do NOT reintroduce local LLMs** (3090
  too slow; constraint is cloud quota/429s). Embeddings (`nomic-embed-text`) are the ONE local piece.
- **Reasoning token budget:** `AGORA_REASONING_MAX_TOKENS` is a FLOOR (default **16000**), NOT a cap — glm-5.2
  burns thousands of tokens thinking before content, so a small cap → empty completion → the recurring
  "0 notes" bug. NEVER lower it. (Owner asked for "5-7k thinking room" believing it was capped low; it's
  already 16k = generous. Left at 16k.) [[reasoning-tier-token-budget]] [[local-gpu-too-slow-cloud-only]]
- **Dungeon health signals to watch (validated alive, loop_n ~1.1s/loop):** (1) vault note production drifting
  low (11→3→1 over 3 days) — likely the glm-5.2:cloud route intermittently 429-ing, NOT tokens; (2) scout
  `scanned_count` flat at 26 since 2026-06-29 14:14Z. Collective still has grounded hypotheses+Measured
  results, so the engine isn't dead. Diagnose deeper only if it persists.

## agent-receipts distribution (owner asked: do #3, prep #1+#2)
GSC query "zero proof ai mcp receipts" is GROWING; the product is fully shipped (PyPI/Zenodo/CLI/MCP-wrapper/
inspeximus). Done this session: post title front-loaded "MCP & Proof" to convert the query; **#3 README now leads
with the one-line MCP drop-in quickstart** (`ReceiptedDispatcher(chain, tools)`; verified runnable; pushed).
**AWAITING OWNER APPROVAL (gated drafts in agora_output/distribution_radar/):**
- `agent_receipts_mcp_listing_draft.md` (#1) — listing in awesome-MCP lists (Tools/Security section ONLY; it's
  a tool not a server; don't force the fit). On approval: read CONTRIBUTING, fork, one entry, anon PR.
- `agent_receipts_rmcp_post_draft.md` (#2) — r/mcp value-first post (NOT HN, shadowbanned). Owner posts in his
  own voice; Draft A recommended.

## Inbound collaborations (all GATED; balls on THEIR side — just watch; envoy-watch surfaces replies)
- **Elina-Seed #47 (qingkong66)** — we posted the Supersession drop-in spec; last=us (2026-06-30 05:46Z),
  awaiting him. He's warm + folding our design into the Elina spec.
- **agora Discussion #2 (Neeraj Yadav / MemStrata, arXiv:2606.26511)** — equal-peer reply + schema_v0 payload;
  last=us (2026-06-30 06:07Z, which CONCEDES his bitemporal-source-of-truth point — NOT pushy), awaiting him.
  reply #3 draft ready (neeraj_disc2_reply3_ready.md) if he re-engages. He's positive throughout.
- DeepSeek-V3 #1447/#1462 (qingkong organizing cross-framework mem-validation) — participate THROUGH qingkong,
  don't rival-organize. hermes #10771, openclaw 35203 — drafts gated, last=us. [[collaboration-fair-never-snub]]

## What shipped earlier (live)
agent-receipts v0.1.0 + inspeximus 0.2.2 (native tamper-evident receipts) on PyPI. Skills committed:
`/audit-post`, `/stress-claim`, `/verify-claims`, `/storm-research`. Sitemap now derives `<lastmod>` from each
post's JSON-LD `dateModified` (audited posts signal freshness for re-crawl) — `tools/render_sitemap.py`.
After a deploy: optionally GSC request-index the audited URLs (async; sitemap nudges the rest).

## Reddit watch — CORRECT method (don't regress)
WALK the nested t1 reply tree + sort by created_utc + check LAST author per thread. A flat top-level list LIES.
u/carc "feels like an LLM" thread (1uhajcp) deliberately LEFT ALONE. [[reddit-watch-walk-reply-tree]]

## Health / ops
Brain :8000 (one LISTEN, PID varies), dungeon mcp_server.py :5174, ZERO supervisors (don't run one — it fights
the brain watchdog). Verify loop_n advances via `tools/dungeon_health.py` (HTTP 200 LIES). Vault pushes ONLY via
`tools/safe_vault_push.py`. PUBLISH GATE + all outreach owner-gated.

## EXACT RESUME PASTE (what the owner types after a session reset)
**To continue the audits (primary):**
> pokračuj v profesionálnom audite publikovaných článkov od #15 — na KAŽDÝ použi /audit-post skill (celý 5-lens /stress-claim + /verify-claims + re-run nášho labu + re-audit-po-oprave kým nie je clean + EN/SK + SEO), nič neskracuj. Stav: HANDOFF_CURRENT_STATE.md + agora_output/publish_audit_tracker.md. Po každom: report + ďalší.

**Open side-items to mention if relevant:** 2 commits (#14) waiting on "deploy"; agent-receipts #1/#2 drafts waiting on approval; Elina/Neeraj threads (we're last, just watch).

(First action on resume: read this file + the tracker + the /audit-post skill, verify the dungeon loop_n advances, then start #15. Don't relaunch servers.)
