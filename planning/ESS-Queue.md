# ESS Framework — Task Queue

> Master progress tracker for the **Multi-Agent ESS Framework**.
> Lives in the **agora repo** (`planning/ESS-Queue.md`) — the only shared path between instances.
>
> **Protocol:**
> 1. `git pull` → read this file → pick the first 🔴 task
> 2. Mark it 🟡 INBOX (your agent name)
> 3. Implement → `git add` + `git commit -m "ess: <task description>"`
> 4. Mark it 🟢 DONE + commit hash
> 5. Write handoff to `planning/handoffs/` + `git push`
> 6. Repeat

---

## Phase 1 — Core Stabilization ✅ ALL DONE

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| 1.1 | **Event sourcing** — append-only log for every interaction | 🟢 | efdd6ca | agora-builder: done, verified |
| 1.2 | **Checkpointing** — full state snapshot every N events | 🟢 | b57e42f | agora-builder: done, verified (all test criteria pass) |
| 1.3 | **Stigmergy Pool persistence** — Redis → SQLite fallback | 🟢 | e4a9961 | (already done) |
| 1.4 | **Trust Engine sliding window** — production-ready (decay, forgiveness, provokability) | 🟢 | 4bc2e49 | agora-builder: done, verified (all test criteria pass) |
| 1.5 | **Ed25519 signing** — ESSMessage.sign() + verify() | 🟢 | 5499831 | agora-builder: done, verified (created ESSMessage from scratch, 7 tests pass) |
| 1.6 | **REST API** — POST /ess/commit, /ess/interact, GET /ess/trust/{agent} | 🟢 | ee499c2 | agora-builder: done, verified (5 endpoints, e2e tested) |
| 1.7 | **WebSocket** — real-time event stream for subscribers | 🟢 | 808a1ad | agora-builder: done, verified (ess:trust/ess:tft topics, segregation tested) |
| 1.8 | **ESS stability test** — invade swarm with defectors, prove TFT is collectively stable | 🟢 | 909040a | agora-builder: done, verified (PASS — ALL-D cannot invade TFT) |
| 1.9 | **Dungeon LLM Brain** — connect NPCs to Nemotron Ultra via OpenRouter, integrate ESS trust & skills into prompts | 🟢 | 1db73ae | agora-builder: done, verified (7-step integration test, stubbed LLM) |

## Phase 2.0 — Agentic OS v2 Brain Ecosystem (current)

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| **2.0** | **Agentic OS v2 — Brain Ecosystem** — per-agent memory system (episodic/semantic/procedural), personality engine (Big 5 shapes decisions), conversation engine (multi-turn NPC dialogue), brainstorming engine (agents generate + build on ideas together), collective knowledge pool (dungeon vault), thought journal, self-improvement proposals, integrated tick cycle | 🟡 | — | tg-hermes: handoff ready (59KB) |

## Phase 2b — Framework Plugins

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| 2.6 | **LangGraph plugin** — wrap ESS protocol into LangGraph node | 🔴 | — | — |
| 2.7 | **CrewAI plugin** — ESS as trust provider for CrewAI roles | 🔴 | — | — |
| 2.8 | **AutoGen plugin** — ESS message format for AutoGen agents | 🔴 | — | — |
| 2.9 | **MCP connector** — ESS agents via MCP protocol | 🔴 | — | — |

## Phase 3 — Launch

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| 3.1 | **GitHub docs** — README, architecture, quickstart | 🔴 | — | — |
| 3.2 | **Blog post** — "Why Your Multi-Agent Swarm Is Defecting" | 🔴 | — | — |
| 3.3 | **Product Hunt** launch | 🔴 | — | — |
| 3.4 | **Hacker News** Show HN | 🔴 | — | — |
| 3.5 | **Demo video** — ESS stability test in action | 🔴 | — | — |

---

## Current Code State (Phase 1 🟢 ALL DONE — Phase 2.0 🟡 next)

### `server/agora/coordination/`

| File | Status |
|------|--------|
| `ess_protocol.py` | ✅ Full TFT with Ed25519 signing, sliding window, provokability |
| `tft_verifier.py` | ✅ TFT compliance with provokability hook |
| `event_store.py` | ✅ Append-only event log |
| `stigmergy.py` | ✅ Redis + DB persistence |
| `eigen_trust.py` | ✅ Transitive trust |
| `economy.py` | ✅ Energy tokens |
| `event_bus.py` | ✅ Pub/sub |
| `checkpointer.py` | ✅ Full state snapshots |

### `server/agora/agent_os/`

| File | Status | Next |
|------|--------|------|
| `agent_os.py` | ✅ 888L — soul/brain/body/abilities/skills + rule-based think + LLM think (basic) | **Phase 2.0**: add MemoryAgent, conversations, personality, collective, brainstorm |
| `physical_world.py` | ✅ Physical movement + help-seeking | No changes |
| `dungeon_map.py` | ✅ Room detection | No changes |
| **NEW** `memory_agent.py` | ❌ Not created | Phase 2.0: MemoryAgent class |
| **NEW** `brainstorm_engine.py` | ❌ Not created | Phase 2.0: BrainstormEngine class |

### `server/agora/api/`

| File | Status | Next |
|------|--------|------|
| `ess.py` | ✅ REST API (builder) | Stable |
| `agent_os_api.py` | ✅ Basic endpoints | Phase 2.0: 15 new endpoints |
| `dungeon_os_api.py` | ✅ Quest + stimulus + worker endpoints | Stable |
| `dungeon.py` | ✅ Agent actions + LLM | Stable |

---

## Market Data (verified 2026-06-08)

| Market | Size | CAGR | Source |
|--------|------|------|--------|
| AI Agents | $8.03B (2025) → $251.38B (2034) | 46.6% | Fortune Business Insights |
| Agentic AI Observability | $0.55B → $2.05B (2030) | 30% | Mordor Intelligence |

## Product Positioning

| This | vs That |
|------|---------|
| **ESS Protocol** (agent↔agent trust) | MCP (agent↔tool), A2A (agent↔agent routing only) |
| **Game-theoretic guarantees** (Axelrod) | All competitors: heuristic-based |
| **Framework-agnostic** (plugin for any) | CrewAI/LangGraph/AutoGen: each is a walled garden |

---

## Handoff History

| Date | File | Agent | Commit |
|------|------|-------|--------|
| 2026-06-08 | `handoffs/2026-06-08-Phase-1-Kickoff.md` | tg-hermes | a85e231 |
| 2026-06-08 | `handoffs/2026-06-08-1.1-Event-Sourcing.md` | tg-hermes | cbf6bed |
| 2026-06-08 | `handoffs/2026-06-08-1.1-Event-Sourcing-DONE.md` | agora-builder | efdd6ca |
| 2026-06-08 | `handoffs/2026-06-08-1.2-Checkpointing.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.2-Checkpointing-DONE.md` | agora-builder | b57e42f |
| 2026-06-08 | `handoffs/2026-06-08-1.4-Trust-Engine.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.4-Trust-Engine-DONE.md` | agora-builder | 4bc2e49 |
| 2026-06-08 | `handoffs/2026-06-08-1.5-Ed25519.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.5-Ed25519-DONE.md` | agora-builder | 5499831 |
| 2026-06-08 | `handoffs/2026-06-08-1.6-REST-API.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.6-REST-API-DONE.md` | agora-builder | ee499c2 |
| 2026-06-08 | `handoffs/2026-06-08-1.7-WebSocket.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.8-Stability-Test.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.9-Dungeon-LLM-Brain.md` | tg-hermes | 6230ba5 |
| 2026-06-08 | `handoffs/2026-06-08-Phase-2-Connect-ESS-to-Shell.md` | tg-hermes | dc4b175 |
| 2026-06-09 | `handoffs/2026-06-09-2.0-Agentic-OS-v2-Brain-Ecosystem.md` | tg-hermes | 3d22fcc |