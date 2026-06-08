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

## Phase 1 — Core Stabilization

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| 1.1 | **Event sourcing** — append-only log for every interaction | 🟢 | efdd6ca | agora-builder: done, verified |
| 1.2 | **Checkpointing** — full state snapshot every N events | 🟢 | b57e42f | agora-builder: done, verified (all test criteria pass) |
| 1.3 | **Stigmergy Pool persistence** — Redis → SQLite fallback | 🟢 | e4a9961 | (already done) |
| 1.4 | **Trust Engine sliding window** — production-ready (decay, forgiveness, provokability) | 🟢 | 4bc2e49 | agora-builder: done, verified (all test criteria pass) |
| 1.5 | **Ed25519 signing** — ESSMessage.sign() + verify() | 🟢 | 5499831 | agora-builder: done, verified (created ESSMessage from scratch, 7 tests pass) |
| 1.6 | **REST API** — POST /ess/commit, /ess/interact, GET /ess/trust/{agent} | 🟢 | ee499c2 | agora-builder: done, verified (5 endpoints, e2e tested) |
| 1.7 | **WebSocket** — real-time event stream for subscribers | 🟡 | — | tg-hermes: handoff ready |
| 1.8 | **ESS stability test** — invade swarm with defectors, prove TFT is collectively stable | 🟡 | — | tg-hermes: handoff ready |

## Phase 2 — Shell & God Console (handoff ready — UI exists, connect ESS API)

| # | Task | Status | Commit | Agent |
|---|------|--------|--------|-------|
| 2.1 | **Trust graph visualization** — D3.js / Three.js force-directed | 🟡 | — | tg-hermes: ✅ UI exists — connect ESS API |
| 2.2 | **Timeline** — real-time event log with filters | 🟡 | — | tg-hermes: ✅ UI exists — connect ESS topics |
| 2.3 | **Arena** — spawn/observe/kill agents | 🟡 | — | tg-hermes: ✅ UI exists — no ESS changes needed |
| 2.4 | **God Console** — intervene, bless, rollback UI | 🟡 | — | tg-hermes: ✅ UI exists — add ESS tab |
| 2.5 | **Agent detail panel** — trust score, history, TFT compliance | 🟡 | — | tg-hermes: ✅ UI exists — add ESS fields |

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

## Current Code State (commit `f37ebea` — Phase 1: 1 task done, 6 planned)

### `server/agora/coordination/`

| File | Status | What's Needed |
|------|--------|---------------|
| `ess_protocol.py` | ✅ Basic TFT | ❌ Ed25519, sliding window, provokability, event_bus pub |
| `tft_verifier.py` | ✅ TFT compliance | ❌ Provokability hook, event_bus pub |
| `event_store.py` | ✅ **NEW** (builder) | Append-only event log, all CRUD methods |
| `stigmergy.py` | ✅ Redis + DB persistence | ❌ Event sourcing hook |
| `eigen_trust.py` | ✅ Transitive trust | OK |
| `economy.py` | ✅ Energy tokens | OK |
| `event_bus.py` | ✅ Pub/sub | OK |

### What's Left in Phase 1

| Component | Status | Handoff |
|-----------|--------|---------|
| Checkpointing | 🟡 READY | `1.2-Checkpointing.md` (19KB) |
| Trust Engine upgrade | 🟡 READY | `1.4-Trust-Engine.md` (10KB) |
| Ed25519 signing | 🟡 READY | `1.5-Ed25519.md` (7.5KB) |
| REST API | 🟡 READY | `1.6-REST-API.md` (13.5KB) |
| WebSocket ESS stream | 🟡 READY | `1.7-WebSocket.md` (7KB) |
| Stability Test | 🟡 READY | `1.8-Stability-Test.md` (15KB) |

---

## Architecture Reference

```
~/agora/server/agora/
├── coordination/
│   ├── ess_protocol.py       ← TrustEngine (TFT scoring)
│   ├── tft_verifier.py       ← TFT compliance analysis
│   ├── stigmergy.py          ← Stigmergy Pool (trace coordination)
│   ├── eigen_trust.py        ← Transitive trust computation
│   ├── event_store.py        ← **NEW**: append-only event log
│   ├── event_bus.py          ← Pub/sub event system
│   ├── economy.py            ← Energy token economy
│   └── economy_config.py     ← Economy parameters
├── storage/
│   └── schema.sql            ← DB schema
├── main.py                   ← FastAPI entry point (937 lines)
├── api/                      ← REST endpoints
│   ├── agents.py
│   ├── tasks.py
│   ├── god.py
│   ├── graph.py
│   └── ...
└── observability/
    └── csd.py                ← CSD early-warning
```

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
| 2026-06-08 | `handoffs/2026-06-08-1.4-Trust-Engine.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.4-Trust-Engine-DONE.md` | agora-builder | 4bc2e49 |
| 2026-06-08 | `handoffs/2026-06-08-1.5-Ed25519.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.6-REST-API.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.7-WebSocket.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-1.8-Stability-Test.md` | tg-hermes | f37ebea |
| 2026-06-08 | `handoffs/2026-06-08-Phase-2-Connect-ESS-to-Shell.md` | tg-hermes | dc4b175 |
