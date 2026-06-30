# HANDOFF — current state (2026-06-30) — READ THIS FIRST on resume

This is the exact resume point. Read it, then `agora_output/publish_audit_tracker.md`, then the
`/audit-post` skill (`.claude/skills/audit-post/SKILL.md`), then proceed. Chat with the owner in SLOVAK;
code + public output in ENGLISH.

## THE ACTIVE TASK: professional audit of every published post
Re-auditing all 42 published posts to a scientific-organization standard, ONE AT A TIME, using the full
`/audit-post` procedure. Owner was emphatic twice: **never shorten the procedure; we don't ship missteps.**
A shortened audit (the trap I fell into) misses real errors — the full panel has caught a real bug in
EVERY post audited so far.

### The procedure = the `/audit-post` skill (9 steps, none optional)
0 read · 1 state claims · 2 RE-RUN our lab numbers from source · 3 `/stress-claim` FULL 5-lens panel
(prior-art hunter, steelman, method/confound, overclaim, blind-spot) → PUBLISH/REFRAME/KILL · 4
`/verify-claims` every citation vs PRIMARY source · 5 apply fixes BILINGUAL EN+SK (body + FAQ visible AND
the JSON-LD FAQPage copy + footer + META `desc`/`title` which feed tldr/meta/og/twitter/schema) + SEO
(/seo Mode-A, bump dateModified) · **6 RE-AUDIT the corrected post (≥2 skeptics) until CLEAN — the step I
once dropped; never skip** · 7 capture new findings → `agora_output/audit_new_findings.md` · 8 leak-scan +
anon commit (`agora-builder@users.noreply.github.com`) + push + force-add any new lab script · 9 report.
Memory: [[audit-publish-full-procedure-never-shorten]].

### Audit progress (tracker = source of truth: agora_output/publish_audit_tracker.md)
- **#1 causal-inference-phase-diagram — DONE, FULL /audit-post + re-audit CLEAN (4eee700).** Heavy
  REFRAME: the "96% RCT bias / phase diagram" was an ESTIMAND error (difference-in-means estimates the
  TOTAL effect; tau=2 is DIRECT) → retitled "Spillovers Don't Bias Your Experiment — They Change the
  Estimand"; credited Manski 1993 + Glaeser-Sacerdote-Scheinkman 2003 + Hudgens-Halloran + Aronow-Samii.
- **#2 pre-trends-test-weak-evidence — DONE, FULL /audit-post + re-audit CLEAN (6ee8239).** Fixed a real
  stats bug: z(1.96) used on a t-stat with 4 df → detection 31%→16%, removed spurious 12% false-positive
  (correct size = nominal 5%); "misses 2/3"→"misses ~5/6"; foregrounded Rambachan-Roth HonestDiD + Roth
  `pretrends`.
- **NEXT = #3 the-operating-point-trap** (render_piece HTML, NO src — edit HTML directly; FAQ exists twice:
  visible + JSON-LD). Then #4…#42 in tracker order, EACH at full /audit-post standard.
- CAVEAT on #3–#10: they got EARLIER preliminary passes (some light REFRAME, some a 5-lens panel WITHOUT
  the re-audit step) before `/audit-post` was standardized — re-do each to the #1/#2 standard (full panel
  + re-audit) when reached. #11–#41 + #42 are not yet at full standard. (#42 ai-coding got an early
  verify-claims live-validation only.) Each tracker row says what's been done; trust the tracker.

## Inbound collaborations (all GATED; balls currently on THEIR side — just watch)
- **Elina-Seed #47 (qingkong66)** — we posted our drop-in Supersession spec text + offered a draft PR
  (`store()` optional `key`). He's folding supersession into the Elina spec. Last = us; awaiting him.
- **agora Discussion #2 (Neeraj Yadav / MemStrata, arXiv:2606.26511)** — we posted the equal-peer reply +
  `schema_v0` payload (mnemo = standalone peer, NOT a feeder; MemStrata owns the bitemporal ledger in a
  combined deploy). Last = us; awaiting him. If he likes it: pin `schema_v0` in the repo.
- **DeepSeek-V3 #1447 / #1462 (HeartFlow yun520-1 + qingkong66 + maratsultanov2/TAT + icophy)** — qingkong66
  is ORGANIZING a cross-framework memory-validation effort (Discussions per benchmark scenario; #1462 has
  Type-B scenarios B-001..003 = preference retrieval / identity under domain shift / belief update without
  overwrite — exactly mnemo's supersession+corroboration). DECISION: do NOT barge into #1447 as a rival
  organizer; participate THROUGH qingkong (offer to run our probes on the #1462 scenarios) — don't step on
  our collaborator. Owner value: [[collaboration-fair-never-snub]].
- hermes #10771 (NousResearch) — our 3rd reply drafted+gated, last = us. openclaw 35203 — drafted earlier.

## What shipped earlier this session (done, live)
- **agent-receipts** project LIVE: PyPI `agora-agent-receipts` v0.1.0 + Zenodo DOI 10.5281/zenodo.21043921
  + GitHub release. Hash-chain + Ed25519 receipts + external-mediator + verifier CLI + mnemo integration.
  Credits Otto Jongerius's "Agent Receipts" protocol (prior art). See [[agent-receipts-project]].
- **agora-mnemo 0.2.2** on PyPI — native opt-in tamper-evident write receipts (`receipts=True`,
  `verify_writes()`, `new_receipt_keypair()`); zero-dep core preserved; backward-compatible.
- New skills (committed, public repo): `/audit-post`, `/stress-claim`, `/verify-claims`, `/storm-research`.

## Reddit watch — CORRECT method (don't regress)
WALK the nested t1 reply tree + sort by created_utc + check LAST author per thread (like the GitHub
last-author watch). A flat top-level-authors list LIES. Threads: 1ui031b (overconf, we're last), 1uhajcp
(mem-poison; u/carc "feels like an LLM" deliberately LEFT ALONE), 1ugb45a, 1uhal5r. [[reddit-watch-walk-reply-tree]]

## Health / ops
Brain :8000 (one LISTEN), dungeon mcp_server.py :5174, + dungeon_canary, agent_activity_monitor,
self_improvement_controller = exactly ONE each (5 python procs). Verify loop_n advances (HTTP 200 lies).
Don't restart casually — the live mnemo.py change is additive/backward-compatible, safe on next restart.
Local GPU too slow → all LLMs cloud, only embeddings local. PUBLISH GATE + outreach all owner-gated.

## EXACT RESUME PASTE (what the owner types after a session reset)
**To continue the audits (primary):**
> pokračuj v profesionálnom audite publikovaných článkov od #3 — na KAŽDÝ použi /audit-post skill (celý 5-lens /stress-claim + /verify-claims + re-run nášho labu + re-audit-po-oprave kým nie je clean + EN/SK + SEO), nič neskracuj. Stav: HANDOFF_CURRENT_STATE.md + agora_output/publish_audit_tracker.md. Po každom: report + ďalší.

**To run the ops/distribution watch (separate, optional):**
> /loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt

(First action on resume: read this file + the tracker + the /audit-post skill, verify 5 python procs healthy, then start #3. Don't relaunch servers — they survive the reset.)
