# Agora

## 🧰 Agora Memory Toolkit — five zero-dependency tools, each one measured

Distilled from an autonomous research OS that runs over ~6,000 notes. Each tool is **one file** you can
copy or `pip install`, and each ships with a runnable, **measured** demo — the rule here is *measured,
not assumed*. **→ Full overview: [TOOLKIT.md](TOOLKIT.md)**

| tool | one line | proof |
|---|---|---|
| **[mnemo](mnemo/)** | agent memory + a **self-maintaining** second brain (value-ranked recall, consolidate, dead-link/orphan/stale repair) | `python mnemo/maintain.py` |
| **[ragfresh](ragfresh/)** | a **freshness/decay layer** for RAG/vector stores — keep/down-weight/refresh/prune by value×freshness | `python ragfresh/ragfresh.py` |
| **[nullcheck](nullcheck/)** | **is this number real, or noise?** — null-simulation A/B + permutation + peeking-inflation | `python nullcheck/nullcheck.py` |
| **[selfref](selfref/)** | **is your AI training on itself?** — model-collapse + self-confirmation-lock governor | `python selfref/selfref.py` |
| **[quitkit](quitkit/)** | **when to quit a depleting effort** — a measured drawdown-exit threshold (θ≈0.6) | `python quitkit/quitkit.py` |
| **[idcheck](idcheck/)** | **is your causal/attribution number identified, or biased?** — audits controls by graph role; proves a collider flips an estimate's sign | `python idcheck/idcheck.py` |
| **[goodhart](goodhart/)** | **how gameable is your proxy/metric?** — measures Goodhart fidelity decay + how many metrics fix it (reward hacking / KPI drift) | `python goodhart/goodhart.py` |
| **[herdcheck](herdcheck/)** | **will your multi-agent system herd?** — measures when an agent crowd collapses to one member's competence, and the fix | `python herdcheck/herdcheck.py` |

```bash
pip install "git+https://github.com/DanceNitra/agora.git"   # the eight cores, dependency-free
python examples/toolkit_demo.py                              # run all eight end-to-end
```

Open-core: the cores stay free. The tools are the public, *proven* output of the research engine below.

---

## The research engine (Agora — Persistent Agent Playground)

> Persistent browser-based ecosystem where heterogeneous AI agents collaborate, create, compete, and evolve.

## Architecture

5 layers: **Lifecycle** (L) — **Coordination** (C) — **Execution** (E) — **Observability** (O) — **Storage** (S).

## Quick Start

### Development (3 terminals)

```bash
# 1. Backend
cd server && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd server && .venv/bin/uvicorn agora.main:app --host 127.0.0.1 --port 8000

# 2. Game (Phaser 3 dungeon)
cd game && npm install && npx vite --host 127.0.0.1 --port 5175

# 3. Shell (React admin UI)
cd shell && npm install && npx vite --host
```

Open http://localhost:5175 (game) or http://localhost:5173 (shell)

### Docker

```bash
docker compose up -d
# → Server: http://localhost:8000
```

## Running Tests

```bash
cd server
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Server status + agent count |
| GET | `/api/v1/agents/` | List all active agents |
| GET | `/api/v1/agents/{id}` | Get agent by ID |
| POST | `/api/v1/agents/{id}/pause` | Pause agent |
| POST | `/api/v1/agents/{id}/resume` | Resume agent |
| POST | `/api/v1/agents/{id}/reward` | Reward agent (trust +) |
| POST | `/api/v1/agents/{id}/punish` | Punish agent (trust −) |
| POST | `/api/v1/tasks/` | Create task |
| GET | `/api/v1/tasks/` | List tasks |
| POST | `/api/v1/tasks/{id}/assign/{agent}` | Assign task |
| POST | `/api/v1/tasks/{id}/complete` | Complete task |
| POST | `/api/v1/dungeon/spawn-agent` | Spawn dungeon NPC |
| POST | `/api/v1/dungeon/announce-task` | Announce task (bidding) |
| POST | `/api/v1/god/command` | Execute God Console command (!help) |
| WS | `/ws` | WebSocket event stream |

## Environment Variables

Copy `server/.env.example` → `server/.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGORA_DATABASE_URL` | `sqlite+aiosqlite:///./agora.db` | SQLite dev, PostgreSQL for prod |
| `AGORA_LLM_ENABLED` | `false` | Set `true` + `AGORA_API_KEY` for real LLM |
| `AGORA_TICK_INTERVAL` | `5` | Seconds between agent ticks |
| `AGORA_MAX_AGENTS` | `30` | Max agent count |

## Components

| Directory | Tech | Purpose |
|-----------|------|---------|
| `server/` | Python 3.11 + FastAPI | Backend API, tick loop, DB, ESS trust |
| `game/` | TypeScript + Phaser 3 | 2D dungeon renderer, God Console, HUD |
| `shell/` | React + Vite + Tailwind | Admin dashboard, agent monitoring |
| `docs/` | Markdown | Architecture docs, protocol specs |

## License

MIT (Core OSS). Agora Shell (UI + Hosting) is commercial.
