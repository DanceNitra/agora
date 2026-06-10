# AGORA — SESSION HANDOFF

> Resume doc for a fresh Claude Code session. Chat in **Slovak**; code + user-facing strings **English**.

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
