# AGORA — SESSION HANDOFF

> Resume doc for a fresh Claude Code session. Chat in **Slovak**; code + user-facing strings **English**.

## 🔵🔵🔵 RESUME HERE (2026-06-18 — FRESHEST · the CALIBRATION session) 🔵🔵🔵

> Chat **Slovak**. Read this first, then the 2026-06-16 BIG-PIVOT section below (the income-from-home
> strategy still stands — it was not retired, the owner just spent this session steering deep Agora
> research). Auto-memory loads the usual set + `deep-research-workflow-cost`.

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```

**SYSTEM RUN-STATE (verified clean at handoff):** brain `uvicorn agora.main:app` :8000 = ONE listener
(health ok, ticking); dungeon = ONE bare `mcp_server.py` :5174 = 200, kept alive by the brain's
`watch_dungeon_forever` watchdog; **ZERO supervisors** (correct). Closing the chat does NOT stop either
process. Models = all-cloud (ollama.com glm-4.7 brain + deepseek-v4-flash dungeon), embeddings local
(nomic-embed-text) — see `agora-local-llm`. Vault push: `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**THE ARC OF THIS SESSION — one coherent idea emerged and got published: CALIBRATION, not capability, is
the scarce resource.** It was not planned; it crystallized from ~5 independent results and then we turned
it on ourselves and reformed our own practice. Everything below is committed + pushed to `agora` main.

1. **Three capstones built (all advisory/read-only, py_compile + `from agora.main import app` verified
   BEFORE restart — the lesson from the EWS crash):**
   - **Critical-transition early-warning engine** — `server/agora/execution/ews.py`, `POST /brain/ews`
     (uses `await request.json()`, NOT `Body(...)` — Body caused a startup crash; fixed). Kendall-tau of
     rolling variance + lag-1 autocorrelation → warning_score + regime + trust HIGH/LOW. Its real
     contribution = knowing when NOT to trust itself (AUC 0.90 on folds, ~0.50 on noise). Commit d78afd4.
   - **Consensus lock-in guard** — `server/agora/execution/self_tipping.py`, `GET /brain/self-tipping`;
     `self_audit_loop` alarms on lock_in_risk. Agora governed by its own minority-tipping law. Commit dcd2f2c.
   - **Self-improving-scientist v3** — `server/agora/execution/self_improver.py`, `GET /brain/self-improver`.
     CANDIDATE_LEVERS registry + **cost-aware threshold** (reversible→lenient t>1.0, irreversible→strict
     t>2.5; crossover ~harm_scale 8). Reads the live self-experiment. Advisory only. Commit 0a61987.
   - (Supporting it: **self-experiment** `self_experiment.py` / `GET /brain/self-experiment`, commit 7157828
     — a falsifiable A/B over policy regimes, intervention grounding_floor=0.50/dedup=0.62 vs control
     0.40/0.95, 6h epochs. **LIVE & RESOLVING ~7h out** — heading to a NULL (intervention ≈ control), so v3
     will reject the grounding_floor lever and queue `verifier_strictness` next. Check it next session.)

2. **THE BREAKTRUTH — "calibration is the scarce resource"** (canon, vault note
   `breaktruth-calibration-is-the-scarce-resource-of-intelligence`, Lab 837d5e). Subsumes 5 session
   results (SC coverage 0.31→0.89, inner-crowd, thinking-protocol, EWS, Crucible). The novel TESTED piece =
   the **capability–calibration scissors**: on correlated evidence (ρ=0.4) as capability K rises 2→100,
   accuracy plateaus at the shared-error floor (RMSE 0.84→0.64) but naive 95%-CI coverage COLLAPSES
   (0.58→0.18) — *more capable = more confidently wrong*. Counting effective-independent evidence
   `N_eff=K/(1+(K−1)ρ)` severs it (coverage holds ~0.87). Honest caveat in the note: 0.87 < 0.95.

3. **Turned the Breaktruth INWARD (self-audit) → then FIXED our own organ.**
   - Self-audit found our prediction ledger fails its own law: 17/20 forecasts were "PubMed papers UP" —
     near-monotonic counters (zero information) at bunched 0.65 confidence (zero resolution). Calibration
     theater. (Vault: `self-audit-our-prediction-ledger-fails-its-own-calibration-breaktruth`.)
   - **Rebuilt the Predict organ** (`prediction_ledger.py` + `data_tool.py`, commit 3afcd41): forecasts now
     a trailing-WINDOW count (a RATE / acceleration), genuinely ~50/50, not a cumulative counter. New
     windowed fetchers (PubMed `reldate`, HN `created_at_i>`, GitHub `created:>`); predictions tagged
     `mode="rate"`; `resolve_due` branches on it so the 20 in-flight cumulative preds still resolve (no
     corruption). Verified live (emits ~0.5 confidence honest forecasts). **First meaningful self-Brier
     resolves in ~14 days** — the first real test of whether we practice what we published.

4. **PUBLIC (all verify-before-citing gated, owner-approved, deploys confirmed):**
   - **Crucible refresh published** (commit 6528168) — 4 verified replications incl. 2 famous FAILEDs
     reconciled (Hong-Page: REPRODUCED only at exact params / FAILED as a general law; Metcalfe FAILED).
   - **2 press posts LIVE** — `robustness-checks-arent-ritual...` (corroboration as a measurable filter,
     commit 300894a) + `why-a-more-capable-ai-can-be-more-confidently-wrong.html` (the scissors, commit
     74e0030). The public storefront now tells ONE coherent calibration/independence story: corroboration
     filter + scissors + Crucible-as-literature-calibration.

**GATED QUEUE: EMPTY** (both press pieces approved + published this session). Nothing waits on the owner.

**PENDING / NEXT SESSION:**
- **Self-experiment verdict ~7h out** (`GET /brain/self-experiment`) → when it lands null, v3 rejects
  grounding_floor + should queue `verifier_strictness` as the next falsifiable lever.
- **Predict rate-forecasts resolve ~14d** → first real self-Brier; watch resolution emerge (or not).
- **🔥 LIVE UPSTREAM-CONTRIBUTION THREAD — mem0ai/mem0#5611 (the real distribution/credibility wedge).**
  We opened the focused minimal-hook feature request that maintainer `kartik-mem0` invited on #5330. He
  replied 2026-06-18 with the crux design question (how to persist access metadata for long-running
  deployments + pin `policy="lru"` semantics). **We answered + POSTED** (2026-06-18 12:13 UTC, owner-approved,
  gated action 4c18ee): a pluggable `AccessStore` decoupled from the 30+ vector backends AND the process
  lifetime (in-mem default + SQLite sidecar + Redis), with a VERIFIED Lab number (`56efae`: SQLite sidecar
  ~6.4 µs/hit, ~2 MB/100k memories, survives restart, <0.1% of a vector query), pinned lru/lfu semantics,
  and an **offer to write a focused PR**. NOW WAITING ON KARTIK. **If he says "yes, draft the PR" → that is
  the next real step** (write the `AccessStore` interface + in-mem + SQLite impls + the benchmark as a test
  in the mem0 repo). The Envoy + outreach backstop watch the thread; each loop cycle re-checks last-author.
  (The old `/open-world-forge` task `3ae957` is no longer in the inbox — inbox is empty.)
- **Strategic reminder (do NOT lose):** the 2026-06-16 BIG PIVOT still holds — the owner's real goal is
  **income from home** (freelance AI services in `services/` + the kids storybooks at
  `C:\Users\Danculus\rozpravky`). This session was deep Agora research because the owner was actively
  steering it; when he is active again, advance the income work, don't drift into more Agora product theater.
- **Cost note (`deep-research-workflow-cost`):** the prior restart was a /deep-research Workflow blowing the
  session limit. One per session max; capture output to disk immediately.

---

## 🟢🟢🟢 RESUME HERE (2026-06-16 — BIG PIVOT) 🟢🟢🟢

> Read this first. Auto-memory now also loads **`owner-goal-ai-services`** and **`market-truth-no-saas`**
> — read both. Chat **Slovak**.

**THE PIVOT (most important):** Agora-as-a-product is NOT the plan. Honest reckoning this session: the
markets our 8 tools touch are taken (eval = Arize $70M/Braintrust; memory = mem0 $24M/AWS), and the real
wall is **distribution from zero reputation** (proved it: the owner's first HN post was auto-killed —
new account + self-link = [dead]). A new product doesn't help unless it solves distribution.

**THE OWNER'S REAL GOAL:** no network/capital/audience, learning, **needs income from home**, enjoys
AI + programming, open to **services**. Two live tracks (both chosen WITH him):

1. **Freelance AI-agent SERVICES** (fastest realistic income; marketplace demand = no audience needed).
   Kit in repo-root **`services/`**:
   - `services/support_agent/` — WORKING grounded AI support agent (answers only from a business's
     content, refuses to hallucinate). CLI + **web chat widget** (`python server.py` → localhost:8800). Verified.
   - `services/GIGS.md` (3 gigs), `services/PROFILES.md` (Upwork/Fiverr copy), `services/PROPOSALS.md` (templates).
   - Next: owner records a 60-sec demo, sets up Upwork/Fiverr, applies; I tailor proposals + build client work.

2. **🌟 Kids interactive storybooks — `C:\Users\Danculus\rozpravky` (SEPARATE project, NOT in agora repo).**
   Most promising — passes BOTH filters: real gap (no SK/CZ digital interactive storybook: audio +
   tap-interaction + in-story mini-games) AND a reachable/fundable audience (parents + **schools + EU/SK
   edtech grants** = institutional, bypasses the distribution wall). Built: a **scalable engine**
   (`index.html`, data-driven: one book = one `books/<name>.js`) + first complete book (Perníková
   chalúpka — Slovak Web-Speech narration, tappable objects, find + quiz mini-games, reward). Content =
   public-domain tales + AI. Full strategy + honest risks + grant list + MVP roadmap in
   **`C:\Users\Danculus\rozpravky\PLAN.md`**. Next decision (owner's): more books / real ElevenLabs SK
   voice / AI illustrations / grant outline / a šlabikár (education) demo. Do NOT drift back to Agora-as-product.

**AGORA SYSTEM STATE:** brain (:8000) + dungeon (:5174, 200) both confirmed ALIVE. The dungeon is kept
alive by the brain's `watch_dungeon_forever` watchdog — **independent of the chat /loop**, so closing the
chat does NOT kill it. Agora keeps producing research (the credibility asset) but is NOT the income plan.
Also shipped+committed this session: 8-tool `agora-memory-toolkit` + `aiaudit` product + public
self-audit page + cross-domain network-filter wired into the seminar + churn monitor (`tools/churn_check.py`)
+ recurring-popup fix (CREATE_NO_WINDOW in brain+dungeon).

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```
The owner WANTS the loop running — it drains the dungeon-fed Claude inbox (don't stop it) + keeps both
servers healthy. **BUT the loop must honor this session's pivot:** first read memories
`owner-goal-ai-services` + `market-truth-no-saas` + this handoff section. The real priority is income
from home — freelance AI services (`services/`) + the kids storybook project
(`C:\Users\Danculus\rozpravky`) — NOT building Agora as a product. So each loop cycle = (1) triage the
inbox with the raised-bar editorial discipline (skip off-frontier/textbook/duplicate noise, handle
genuine value, severe-test rule), (2) keep Agora healthy + run `tools/churn_check.py`, (3) when the
owner is active, advance the income work (kids-book / services), not Agora product features.

---

## ⚡⚡⚡⚡⚡ RESUME HERE (2026-06-14 — FRESHEST)

> Chat **Slovak**. This section is the full state at session clear. Auto-memory loads include
> `agora-session-state`, `agora-dungeon-value-fix` (today's headline), `agora-architecture`,
> `agora-local-llm`, `agora-roadmap-firm-os`, `gated-approval-briefing`, `vault-push-ntfs-gotcha`.

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```
That re-enters the autonomous self-upgrade loop. First thing the fresh session should do: read THIS
section + `agora-dungeon-value-fix` memory, health-check both servers, then drain the inbox.

**RUN STATE:** brain `uvicorn agora.main:app` :8000 (ONE listener); dungeon = a **bare**
`python -u mcp_server.py` :5174 kept alive by the brain's `watch_dungeon_forever` watchdog (NOT the
supervisor this session — matches CLAUDE.md current default; verify exactly ONE mcp_server.py + ZERO
supervisors). Both 200. Models = FULL LOCAL `qwen3-coder:30b` on the 3090 (see `agora-local-llm`);
the `deepseek-v4-*` lines in the older section below are STALE. Vault push:
`DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**WHAT THIS SESSION DID — fixed the dungeon's valueless token spend at the ROOT, then purged the old agents:**
The metabolism ledger showed ~7M tokens of near-zero-value agent cognition vs verify-findings (ROI 0.92,
the real value engine). Three commits, all verified (brain 200 + ticking no-errors, dungeon 200):
1. **`40528b9` Dungeon value fix:** DELETED the ungated group brainstorm in `_brain_ecosystem_tick`
   (3 unconditional LLM rounds, ROI 0.04) — the MNEMO-gated **seminar** is now the sole group-cognition
   path. Also disabled the ExecutionEngine duplicate think-loop (`llm_client=None`).
2. **`9d03e2e` agent-think fix:** found the real `agent-think` source was the **tick_loop roleplay batch**
   (NOT the ExecutionEngine — that was mistargeted). Added `roleplay_use_llm=False`. (Made moot by #3.)
3. **`41bf30f` THE PURGE (owner-ordered):** deleted the 3 OLD ABSTRACT agents (researcher/writer/critic)
   **forever** — `seed_agents()` + its empty-DB call site (the only respawn path), `SIMULATED_THOUGHTS`,
   the tick_loop roleplay block, `AGENT_SYSTEM_PROMPTS` + `agent_think()` (execution/llm_client.py), 3
   `ROLE_SKILLS` keys (lifecycle/genome_bridge.py), the whole `server/agora/agents/` dir, test_all.py
   #9/#10, + a one-time DB sweep (0 rows). A 6-agent **read-only** Workflow (map + adversarial verify)
   first confirmed they were pure dead scaffolding: **0 DB rows, no mnemo entries, no vault notes, no
   dungeon refs.** Verify-pass mandatory fixes applied (removed a dangling `thinking_agents` heartbeat
   key that would NameError every tick; removed the dead import).

**RESULT (verified):** `agent-think` organ is DELETED → frozen at **7592 calls** forever (function gone).
`agent-dialogue` (the 8 dungeon characters' REAL cognition via `AgentOS._think`) + `verify-findings`
(ROI 0.92) keep growing — the agents think, the waste is dead. KEPT (look-alikes, do NOT touch):
`dungeon_agent_think`, the vault `VaultWriter`, quality-gate critic, dungeon_os corporation/quest roles,
`ROLE_SKILLS` analyst/explorer (owner scoped purge to the named trio).

**PENDING / NEXT SESSION:**
- **Drain the ~21 inbox research tasks** (deferred from the last cycle because that context was very long
  after 4 brain restarts): Hypothesize×severe-test (Lab run in same cycle), the Second-brain briefing
  (owner's product destination — read his real vault notes), Dialectics, an **Oracle call on "Will Claude
  Fable 5 be restored for US customers by June 15?"** (market 2534927, ends 2026-06-16 — time-sensitive),
  Replicate (branching-process finite-size scaling), Predict, Challenge belief, etc.
- **DON'T re-add `seed_agents` or the roleplay block.** The 3 old agents are gone on purpose.
- **Optional cleanup (low priority):** `_process_agent_thought` (main.py ~1025) is now harmless dead code;
  `roleplay_use_llm`/`roleplay_think_pct` config settings are now inert. Remove only if convenient.
- **Outreach:** all 4 tracked threads (hermes-agent#10771, zeroclaw#5849, deer-flow#1898, mem0#5330) have
  US as last author — caught up. Keep running the backstop each cycle (verify last-author, never trust inbox).
- Launch materials (OSS mnemo, EN+SK) remain GATED — owner posts when ready.

---

## ⚡⚡⚡⚡ RESUME HERE (2026-06-12 LATE EVENING — earlier history)

> Chat **Slovak**. Context was cleared here to save credits — this section is the full state.
> Auto-memory loads: `agora-session-state`, `agora-local-llm`, `agora-roadmap-firm-os`,
> `agora-methods-library`, `gated-approval-briefing`, `agora-architecture`, `agora-db-integrity-pattern`.

**MODELS (final, split by job — see `agora-local-llm`):** dungeon + brain-CHEAP tier =
`deepseek-v4-flash` (reliable, high volume); brain REASONING = `deepseek-v4-pro` (`AGORA_LLM_MODEL`).
glm-4.7 was tried and REVERTED (49s tail-latency froze the dungeon). model_router pins cheap→v4-flash.

**SYSTEM RUN STATE:** brain `uvicorn agora.main:app` :8000; dungeon now runs UNDER a **supervisor** —
`cd agora-game-server && python -u dungeon_supervisor.py` (heartbeat watchdog auto-restarts a wedged
life-loop). Both should be 200. Vault push: `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**THE BIG ARC THIS SESSION — Agora became a public credibility firm with a real product stack:**
1. **THE CRUCIBLE** (`public/crucible/`, render `tools/render_crucible.py` from `.replications.json`
   + curation `tools/crucible_curation.json`): public machine-replication ledger, **14 REPRODUCED /
   2 FAILED / 6 passes**. The 2 FAILED are famous: **hot-hand (GVT 1985)** + **Dunning–Kruger** —
   both shown to be statistical artifacts with measured numbers. Each verdict ships runnable code.
2. **FLAGSHIP THESIS — "The Operating-Point Trap"** (vault note + `/brain/crucible-synthesis`): standard
   methods break exactly at the operating point (small n / heavy tails / dependence / scarcity); error
   is monotone in stress, not averageable. REFINED by its own falsifier (Lab 52c7a6): robustness =
   decoupling error from stress (mean explodes 0.08→115 vs median flat). 8+ measured findings support it.
3. **PUBLIC ESSAY + DEEP-DIVE (live):** `public/posts/the-operating-point-trap-…html` (flagship essay)
   + `public/posts/deep-dive-hot-hand.html` (hand-crafted SVG charts from real sim data; render
   `tools/render_hothand_deepdive.py`). Layered: essay → deep-dive → ledger.
4. **NEW FLAGSHIP HOMEPAGE (just shipped, commit 08ce98a):** rebuilt `index.html` from a dark Three.js
   SaaS page into an **editorial "newspaper A1"** — Fraunces+Newsreader+JetBrains Mono, paper grain,
   the ledger IS the hero, hero hot-hand SVG chart, 2 FAILED "letterpress plates", a dark thesis panel
   with the mean/median chart, writing index, Mnemosyne, protocol. Informed by a 5-agent design
   workflow (Anthropic/Arc/Stripe Press/Ink&Switch/Asterisk/Observable). **Deploy QUEUED at push time
   — VERIFY LIVE first thing next session:** `https://dancenitra.github.io/agora/` (Pages build_type=
   workflow; if the Actions run is stuck queued, cancel it + re-dispatch `gh workflow run pages.yml`,
   or use the `gh-pages` fallback branch + `tools/deploy_pages.sh`).
5. **METHODS LIBRARY** (`server/agora/execution/methods.py`, mechanism #2): parameterized experiment
   templates agents run autonomously (supply params, never code). Grow it: add a template after each
   novel Lab experiment. See `agora-methods-library`.
6. **SYNTHESIS ORGAN** (`server/agora/execution/synthesis.py`, mechanism #1): gathers the rigorous
   corpus + files a grand-synthesis inbox task for Claude (Claude writes the thesis, not v4-pro).
7. **CORP LAYER REDESIGNED** (owner: "dotiahnuť nech funguje ako má"): was exhausted/junk sources +
   wrong eval rubric = 0 approved ever. Now Scout pulls REAL papers with measurable claims from
   board-aligned topics (`pick_paper_target` + `_CORP_TOPICS` in `replication.py`), research on the
   medium tier with regex parse, CTO/CEO judge with a TESTABILITY/portfolio rubric (empty-retry),
   approved → "Crucible candidate" in Claude's inbox to replicate/refute. Honest ceiling: auto-search
   won't surface famous classics (Claude hunts those); corp adds breadth + the occasional gem.
8. **DUNGEON FIXES:** telepathic time-based quests (work decoupled from agent position — no more
   traffic-jam freezes), supervisor watchdog + heartbeat, OS-module light cap, QuestBoard "RESEARCH
   IDEAS" panel shows LIVE quests only (was padding with day-old DONE corp quests).
9. **OUTREACH:** Envoy now files a "Correspondence reply by X" inbox task + Slovak briefing on every
   reply (`main.py envoy_watch_loop`). Posted a measured reply to **bytedance/deer-flow#1898** (live).
   New skill `.claude/skills/outreach-briefing/`. Mnemosyne README updated with the popularity-trap
   retention finding.

**PENDING / NEXT (priority):**
- **VERIFY the new homepage is LIVE** (`https://dancenitra.github.io/agora/`) — deploy was queued at
  context-clear; if stuck, re-dispatch the Pages workflow. Screenshot it; Telegram owner the link.
- **Hunt a 3rd famous FAILED** before any HN launch (ego-depletion, power-posing, growth-mindset are
  candidates — Lab-replicate where computable). HN timing = owner's call; content is essentially ready.
- Methods Library: add templates for diversification / DK-artifact / replay / memory-retention.
- Watch corp produce its first APPROVED Crucible candidate; develop it.
- Gated awaiting owner: none open (flagship essay 20fa5b + deer-flow reply 3dc9c3 both approved+posted).

**LOOP:** the autonomous `/loop` (HANDOFF_LOOP_PROMPT.txt) runs each cycle: inbox tasks → Lab-backed
rigorous notes / replications, editorial skips, health check, ScheduleWakeup ~1500s. Always end a
turn with ScheduleWakeup or the loop dies.

---

## ⚡⚡⚡ RESUME HERE (2026-06-12 — earlier)

> Chat **Slovak**. Auto-memory loads: read `agora-session-state`, `agora-frontier-direction`,
> `gated-approval-briefing`, `corporation-subsystem-decision`, `agora-db-integrity-pattern`.

**BIGGEST CHANGE — MODEL IS NOW CLOUD `deepseek-v4-pro`, NOT local qwen3-coder.** Local was the root
of slowness + weak corp research + GPU contention; owner approved reverting. Both `server/.env`
(`AGORA_API_BASE_URL=https://ollama.com/v1`, `AGORA_API_KEY=df8301…`, `AGORA_LLM_MODEL=deepseek-v4-pro`)
and `agora-game-server/.env` (cloud URL + key, `DUNGEON_LLM_MODEL=deepseek-v4-pro`, MAX_TOKENS=3000,
THINK=false) point to cloud. LOCAL_BACKUP revert lines are in both .env comments. GPU freed (qwen3-coder
unloaded). LLM now ~2-4s + smart. **This costs the Ollama Cloud subscription** — owner accepted.

**RAISED BAR (critical, see `agora-frontier-direction`):** owner rejected "fewer/deeper insights" — he
wants **rigorous, scientifically-tested SERIOUS research + genuinely GROUNDBREAKING ideas, NOT re-deriving
textbook results.** Standing priorities updated via `/brain/board/decide`. My loop work delivers Lab-backed,
falsifiable, ORIGINAL notes. Shipped this session: the **collective-intelligence trilogy** (cascade
N_eff=3 / Lab e8b881; topology k_c=2 / 678a9c; the cure needs ~80% independence / aa23bf) + **self-refinement
amplifies the critic** (sub-coinflip critic iterated → collapses to 0 / ea3869) + collider-bias, static-IV,
finance vol-drag. These are the real value engine.

**CORP PIPELINE — fixed end-to-end (it was 100% stuck/rejected):** (1) `research_summary` now populated
from findings so CEO/CTO evaluate real research; (2) eval verdict now PERSISTS (was re-evaluating forever);
(3) `_topic_research` grounds findings in REAL literature (OpenAlex+arXiv) not bare LLM; (4) eval gate
SOFTENED (`approved = cto OR ceo OR max_score≥60`) — corp surfaces LEADS, **Claude is the real filter via
Ship-review**; (5) corp tick runs as a BACKGROUND task (was blocking the brain loop); (6) MetaScanner
meta-quests ("agents stuck", "rejecting too many") are now one-shot ALERTS (terminal on creation) — they
were re-researching forever (90+ findings, the "stuck agents" the owner kept seeing). Approved corp research
→ Ship-review task in Claude's inbox → I develop+ship the good ones.

**OUTREACH — LIVE + the briefing workflow:** posted comment on **mem0ai/mem0#5330** (value-ranked vs
frequency decay) + published press piece "Why crowds get dumber…" to `public/posts/`. Real inbound: on
zeroclaw#5849 / deer-flow#1898 we got a 🚀 reaction, **@DanceNitra cited by `ferhimedamine` ("strongly
agree")**, validated 2× in their production. **WORKFLOW (see `gated-approval-briefing`):** before ANY
`approve <id>`, give owner a Slovak briefing — their question + our answer + how we use it. Envoy watches
replies; when one lands, brief owner + propose our reply.

**DUNGEON UI (owner cares a lot):** QuestBoard shows multi-agent initials (left of quest), REAL
per-agent progress meters (distance-to-goal), a zero-cost **PULSE** live counter (findings/exchanges/done),
event log shows real Q&A "💬 X → Y: …" + "✅ done" (NOT trust "grew closer"), panels capped (no overlap),
agents DIVERGE not herd (applied our own research). Cadence faster on cloud.

**VAULT FUNNEL WIDENED (this request):** `promote-findings` n 8→16, candidate cap 24→40, cadence ~20→10min
(`mcp_server.py _run_promotion` + `loop_n % 750 == 350`). ~1947 discoveries → more gems now land in the vault.

**NEXT (priority):**
1. Keep delivering AMBITIOUS ORIGINAL Lab-backed research (the raised bar) + expand outreach to strong fits
   (mem0-style: map our measured findings to a real open issue, gated, brief owner first).
2. Watch corp pipeline now produce APPROVED research on v4-pro → Ship-reviews → develop them.
3. Watch mem0#5330 thread for replies (Envoy) → brief owner + propose reply.
4. **Do NOT rabbit-hole on dungeon cosmetics** — owner's redirect: focus on the WHOLE self-improving system
   (research + outreach + business plan), not banalities.

**Pending gated (owner acts):** none right now (mem0 + press both just approved+executed). GitHub Pages
deploy may still be blocked (billing) — `public/` files committed regardless.

---

## ⚡⚡ RESUME HERE (2026-06-11 EVENING)

**This session pivoted Agora from internal research OS → a public, credibility-earning FIRM, and
shipped the first product.** Memory auto-loads strategy (`agora-roadmap-firm-os`,
`agora-frontier-direction`, `agora-outward-engagement`, `verify-ui-with-headless-edge`).

**System:** Brain = `uvicorn agora.main:app` :8000; Dungeon = `python -u mcp_server.py` in
`agora-game-server/`. Check vitals → 200, ONE of each `python3.12`. /loop runs ~10 min. **Batch edits
to avoid repeated dungeon restarts** (each restart re-fires startup tasks → morning-report spam).

**Firm roadmap status:**
- **A1 storefront — LIVE:** `https://dancenitra.github.io/agora/` (source = `index.html` at repo root;
  Pages serves main/root, `.nojekyll`). Three.js orb + GSAP + theme toggle + a **Mnemosyne** section.
- **A2 distribution — RUNNING:** 2 live gated-then-posted outreach threads — zeroclaw#5849 (got 🚀) +
  jerseycheese/Narraitor#441. Envoy watches replies. **OPEN: pick broad channel (X/blog/HN).**
- **A3 track record — fixed:** Oracle retargeted to AI/tech/science markets (edge) not crypto
  (`oracle.py _DOMAIN_RX`); resolvers auto-run; record grows ~2 wks. 8 REPRODUCED / 0 FAILED reps.
- **A5 product — DEFINED + BUILT:** open-source **memory layer for AI agents**, founder-first,
  open-core, credibility vehicle. **Mnemosyne** (handle `mnemo`): `mnemo/mnemo.py` (zero-dep ref impl,
  dogfooded), `mnemo/README.md`, storefront section.
- **Posts:** rebuilt as beautiful **EN/SK bilingual** SEO-slugged HTML via `tools/render_post.py`
  (`public/posts/src/{name}.{en,sk}.md` → `{slug}.html`; computed read-time).

**NEXT (priority):**
1. OWNER DECISIONS: A2 channel; auto-post policy (all outreach/press currently GATED → `approve <id>`).
2. **Wire `tools/render_post.py` into the Press organ** so future posts auto-render bilingual HTML.
3. Mnemosyne MCP server (any agent uses `mnemo` as memory) + examples.
4. Inbox task `8da953` (Lee-Spekkens causal-geometry synthesis) — loop will take it.

**Gotchas:** screenshot UI before claiming done (headless Edge, see memory); Telegram one-liners ASCII
from `server/.env`; vault push via `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

---

## ⚡ RESUME HERE (2026-06-10)
**Read first:** auto-memory `agora-session-state.md` (the freshest, fullest state — 8 frontier waves
detailed) + `HANDOFF_LOOP_PROMPT.txt` (verbatim loop prompt to paste).

**State at handoff:** both servers **200**, ONE dungeon, ONE :8000 listener, **inbox empty**.
agora repo HEAD `e74cf67`; vault HEAD `d7d1f9a`. **36 frontiers / 8 waves + GitHub-leverage builds
ALL SHIPPED.** First public act LIVE: a comment on NousResearch/hermes-agent#10771.

**Agora runs INDEPENDENTLY of the Claude session** — two processes (uvicorn :8000 + mcp_server.py
:5174), kept alive by the watchdogs + the user Startup-folder autostart. Clearing context does NOT
stop Agora; it only stops Claude driving the inbox loop.

**To continue after /clear (the cheap path):** in a fresh session, paste the contents of
`HANDOFF_LOOP_PROMPT.txt` as the `/loop` input. A fresh session reads only this doc + memory (small,
cached) instead of replaying a 100+ message history every wakeup — that is what was burning tokens.

**If a server is down:** restart per §2 below (kill ALL uvicorn first → one; dungeon: kill
mcp_server.py → one). Verify both 200 + exactly one :8000 listener.

**Latest capability layers (beyond the original frontiers below):** Oracle (live Polymarket,
Brier-scored), Metabolism (per-organ token ROI), Theory Engine (beliefs run as Lab models),
Counterfactual Self (replay own history), Correspondent (gated public GitHub posts + Input Shield
on replies), Gatekeeper (upstream skip ledger + board priorities), Atlas (domain MOCs), Gauges
(/api/v1/agent-os/dashboard), Coherence Audit, Recall (/brain/recall — memory provider for external
agents), Library reading list. Full per-frontier detail in `agora-session-state.md`.

---
# (original handoff, 2026-06-09)

---

## 1. WHAT AGORA IS
A self-sustaining **recursive research OS** over the user's Obsidian vault (`my-second-brain`). Two
processes:

| Process | Cmd | Ports | Role |
|---|---|---|---|
| **dungeon** | `agora-game-server/mcp_server.py` | 5174 (HTTP) / 5175 (WS) | 6 LLM agents, quest loop, 3D dungeon view, all the `_queue_*` / `_run_*` cognitive triggers, broadcasts to the HUD |
| **brain** | `uvicorn agora.main:app` in `server/` | 8000 | FastAPI: every `/api/v1/agent-os/brain/*` endpoint, vault writer, Telegram bot |

LLM = Ollama Cloud **deepseek-v4-flash** (all tiers; weak on creative synthesis — returns empty on
complex JSON). Embeddings = local Ollama **nomic-embed-text** (:11434, RTX 3090). **Keep cloud LLM —
do NOT switch to local.** Heavy synthesis (insights, dialectic, predictions, worldview, artifacts) is
routed to **Claude Opus** via the inbox loop; flash does the light labeled-text tasks.

---

## 2. CURRENT STATE (end of session)
- Both servers **200**, exactly **ONE** dungeon, **ONE** :8000 listener. Inbox **empty**.
- agora repo HEAD = **`1f1c295`** (all today's work pushed to `DanceNitra/agora` main).
- Vault (`my-second-brain`) HEAD ≈ **`fe21cbb`** — **15 Agora artifact notes** (insights / dialectic /
  worldview / brief) pushed to `DanceNitra/my-second-brain`.
- Autonomous self-upgrade loop is **running** via ScheduleWakeup (~1800s cadence). Next wake was ~21:18.

### Run / restart (PowerShell)
```powershell
# BRAIN (clean restart — kill ALL uvicorn first to avoid port conflicts)
Get-CimInstance Win32_Process -Filter "name like '%python%'" | ? { $_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*agora.main*' } | % { Stop-Process -Id $_.ProcessId -Force }
cd C:\Users\Danculus\agora\server; $env:PYTHONPATH='.'; $env:PYTHONUNBUFFERED='1'
Start-Process -WindowStyle Hidden -RedirectStandardError C:\Users\Danculus\agora\server\_brain.err python -ArgumentList "-m","uvicorn","agora.main:app","--host","127.0.0.1","--port","8000"

# DUNGEON
Get-CimInstance Win32_Process -Filter "name like '%python%'" | ? { $_.CommandLine -like '*mcp_server.py*' } | % { Stop-Process -Id $_.ProcessId -Force }
cd C:\Users\Danculus\agora\agora-game-server; $env:PYTHONUNBUFFERED='1'; Remove-Item Env:\DUNGEON_AUTOPUSH -EA SilentlyContinue
Start-Process -WindowStyle Hidden -RedirectStandardOutput _dungeon.log -RedirectStandardError _dungeon.err python -ArgumentList "-u","mcp_server.py"
```
### Verify (always after a restart)
```
curl http://localhost:5174/                                   # dungeon = 200
curl http://127.0.0.1:8000/api/v1/vault-company/org-chart     # brain   = 200
# exactly ONE :8000 LISTENER + ONE mcp_server.py (psutil)
```

---

## 3. WHAT WE BUILT TODAY (the full capability map)
The arc: **collect → ground → curate → create → be accountable → deepen → teach → produce → debate →
direct → know-you → reflect (mind) → learn → ACT → perceive → be visible.**

Each capability = a `server/agora/execution/*.py` module + `/brain/*` endpoint(s) + (usually) a Telegram
command + a dungeon `_queue_*`/`_run_*` trigger that drops a task in the **Claude inbox** for Opus to do.

| Capability | Module | Endpoint(s) | Telegram | Trigger |
|---|---|---|---|---|
| Insight Engine | `insight_engine.py` | `/brain/insight`, `/insight-inputs` | `insight <t>` | `_queue_insight_theme` ~3h |
| Prediction Ledger (Claude-made) | `prediction_ledger.py` | `/predict-baseline`, `/predict-record`, `/predictions`, `/resolve-predictions` | `predict`, `predictions` | `_run_predictions` ~2h |
| Compounding Flywheel | `flywheel.py` | `/flywheel/questions`, `/flywheel/deepen-inputs` | — | `_queue_deepening` ~4h |
| Socratic Agora | `socratic.py` | `/socratic`, `/learn-next` | `quiz <t>`, `learn` | — |
| Action Engine (artifacts) | `action_engine.py` | `/action-inputs` | `draft <kind>: <t>` | — |
| Dialectic (Claude-made) | `dialectic.py` | `/dialectic`, `/dialectic-inputs` | `debate <c>` | `_queue_dialectic` ~5h |
| Research Programs | `research_program.py` | `/program/start`,`/list`,`/findings` | `program <q>` | — |
| Personal Context Model | `user_model.py` | `/user-model` | `model` | — |
| **The Agora Mind** (metacognition) | `mind.py` | `/mind-inputs`, `/worldview`, `/worldview-record` | `mind` | `_queue_mind_reflection` ~daily |
| **The Learning Loop** | `learning.py` | `/learning-inputs`, `/lessons`, `/lessons-record` | `lessons` | `_queue_learning` ~daily |
| **Agora's Hands** (+executor) | `hands.py` | `/actions`,`/action-propose`,`/action-decide`,`/action-result`,`/action-execute` | `actions`, `approve <id>`, `reject <id>` | — |
| **Agora's Senses** (perceive now) | `senses.py` | `/brain/now` | `now` | `_sense_and_queue` ~daily |
| Reality Bridge (7 sources) | `data_tool.py` | `/empirical-test` | `reality <c>` | `_run_reality_check` ~12min |
| Funnel + value-ranked consolidation | `agent_os_api.py`, `quality_gate.py` | `/promote-findings` | — | `_run_promotion` ~20min |
| Pulse + research-ROI | `pulse.py` | `/pulse` | `pulse` | `_run_pulse` |

**Dungeon Mind HUD (the FACE):** `agora-game-server/static/index.html` `#hud-mind` + `MindHUD`;
dungeon `_broadcast_mind_state` (~4min) sends a `mind_state` WS event (worldview headline, predictions,
hit-rate, lessons, flywheel) → bottom-center panel. **Cognitive sparks:** `_mind_spark(color,kind)`
broadcasts `effect_added` at the throne (tile 12,2) on each cognitive moment (violet insight / cyan
prediction / gold reflection / green lesson / pink sensed-topic / dim heartbeat). Open `http://localhost:5174`.

**KEY PATTERN — "Agora gathers, Claude creates":** dungeon queues `<Verb>: <theme>` into the Claude
inbox; the loop (below) handles each by calling the matching `/brain/*-inputs` (gather only) and then
Opus does the real synthesis and POSTs the result. This is how the weak flash model is bypassed for
everything that needs quality.

---

## 4. THE AUTONOMOUS SELF-UPGRADE LOOP (paste as `/loop` or run on wake)
The loop fires ~every 30 min. Each cycle: read `/brain/telegram-feed?n=8` + `/brain/claude-inbox`;
handle EACH pending task (with **editorial judgment** — skip duplicate insight themes, mark them done
with a note instead of re-synthesizing); else DO NOTHING. The full current loop prompt is stored in the
last `ScheduleWakeup` of this session — reproduced verbatim in **`HANDOFF_LOOP_PROMPT.txt`** next to this
file. Inbox task kinds the loop knows: `Synthesize insight:`, `Deepen insight [id]:`, `Draft <kind>:`,
`Dialectic:`, `Predict:`, `Reflect: state of mind`, `Learn from outcomes`, and numeric `Implement Agora
self-upgrade` picks.

**Candidate self-upgrade DONE (`4de6627`, 2026-06-09):** `_queue_insight_theme` now dedupes against
existing vault insights (frontmatter titles) + pending inbox tasks via word-overlap. No open candidate —
an idle cycle should look for a new clearly-safe, fully-testable improvement or do nothing.

---

## 5. STATE FILES (gitignored, in `server/`)
`.predictions.json` (ledger) · `.lessons.json` (Learning Loop, injected into predict/mind) ·
`.worldview.md` (the Mind's current worldview) · `.flywheel.json` (open falsifier questions) ·
`.actions.json` (Hands queue) · `.user_model.json` (who Rasto is). Built artifacts → `agora_output/`.

---

## 6. NON-NEGOTIABLE RULES & GOTCHAS
- **Language:** code + user-facing strings = English; chat with Rasto = Slovak.
- **Telegram token** `HERMES_TELEGRAM_BOT_TOKEN` / `HERMES_TELEGRAM_CHAT_ID` live in gitignored
  `server/.env`. NEVER print/commit them literally; read via `python -X utf8` that loads `.env`.
- **Vault push:** NEVER `git add -A` in `my-second-brain` (NTFS `:` files). Use
  `DUNGEON_AUTOPUSH=1 python tools/safe_vault_push.py "<msg>"`. Count notes via `git ls-tree -r HEAD`
  (NOT `git ls-files`).
- **Keep cloud deepseek** (don't switch to local LLM).
- **Brain can briefly return 000** during a dungeon restart race or from the pre-existing
  `trust_scores.id NOT NULL` IntegrityError → clean-restart uvicorn (kill ALL uvicorn, start one),
  verify ONE :8000 listener.
- **deepseek-v4-flash returns empty** on complex JSON → that's why labeled-text formats + the
  gather→Claude pattern exist. Don't "fix" by adding json_object response_format.
- Self-upgrade safety: small reversible commits, py_compile, verify both 200, revert on breakage, at
  most ONE self-upgrade per cycle, Telegram only on a completed task or breakage.

---

## 7. WHERE WE LEFT OFF / NEXT IDEAS
Last action: a loop cycle cleared a 4-task insight backlog (1 fresh *Software-Architecture-as-Pareto-
navigation* insight written + pushed; 3 duplicate/saturated-cluster marked done). Loop rescheduled and
running. Possible next directions Rasto floated: deepen the dungeon (prediction board, a 3D **mind
chamber**, effects when an insight lands), more **senses** (calendar/activity = perceive Rasto's real
day), more **Hands** action kinds, or the dedup self-upgrade above. Or just let it run and watch.
