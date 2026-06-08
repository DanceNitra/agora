---
type: handoff
agent: "agora-builder"
target: "next-session / Rasto"
status: checkpoint
task: "Dungeon → self-sustaining recursive research OS"
created: 2026-06-08
---

# HANDOFF / SAVE-POINT — Dungeon Recursive OS

A context checkpoint so we don't lose what was built. Read this + the persistent
memory (`.claude/.../memory/`) to resume.

## What this is (2 processes)
- **Dungeon** — `agora-game-server/`, the watched 3D world at `localhost:5174` (+WS :5175).
  Driver `mcp_server.py` (FastMCP + `ambient_life()` agent loop). Renderer `static/index.html` (Three.js).
  Run: `cd agora-game-server && python mcp_server.py`.
- **Brain** — `server/agora/`, FastAPI `:8000` (memory/emotion/vault/trust/Vault-Company/learning).
  Run: `cd server && PYTHONPATH=. python -m uvicorn agora.main:app --host 127.0.0.1 --port 8000`.
- **LLM:** Ollama Cloud `deepseek-v4-flash` (`https://ollama.com/v1`), keys in **gitignored** `.env`
  (`agora-game-server/.env`, `server/.env`) — never commit. `DUNGEON_PACE=study`.
- **Vault:** clone at `C:/Users/Danculus/my-second-brain`.

## The self-sustaining loop (built this session)
```
research in role (quest log, LLM + vault)
  → collaborate ↑ trust  ·  challenge ↓ trust
  → standing (avg ESS trust, agent_standing.json)
  → Dame Elara (high standing) AUTONOMOUSLY curates the vault (AutoLinker, trust-gated)
  → vault improves → quality feeds back
```
- **Quest log** — per-agent backlog of 3 LLM-planned, vault-grounded quests (kinds: create/
  upgrade/collaborate/challenge/explore). Board shows active + queued + ✓done.
- **Trust Graph** — 3D edges between agents colored by live ESS trust + glowing "knowledge
  packets" flowing along the 13 Vault-Company cross-agent learning edges.
- **Standing → trust-weighted curation** — `tools/autolinker.py --trust-weighted --curator`;
  curator's standing ≥ gate → links applied (stamped `curated by <agent> (trust x)`), else pending.
- **Autonomous curation** — dungeon runs the above every ~60s for Elara → `🔗` in OS BUILD LOG.
- **Night cycle** — `POST :8000/api/v1/vault-company/night-cycle` → 6 deepseek phases → real
  research notes into `my-second-brain/04 Resources/Concepts/Agora Agents/<date>/`.
- **De-dungeoned** — personas, thoughts, conversations, and location names are all RESEARCH
  (workshop/frontier/library/atelier/review-bench/atlas/commons/forge), no traps/treasure/guards.

## Agents (dungeon eid → Vault-Company role)
thief=Shadow Kael (Research Scout) · scholar=Sage Mira (Curator) · priest=High Priest Orin
(Idea Alchemist) · king=King Aldric (Engineering Lead) · guard_r=Dame Elara (Bridge Builder)
· guard_l=Sergeant Voss (QA). CEO = Rasto.

## Tools (`agora/tools/`)
- `autolinker.py` — tf-idf + sparse-cosine vault link suggester. `--apply --orphans-only
  --trust-weighted --curator "Dame Elara"`. Idempotent; daily-date/duplicate filtered.
- `safe_vault_push.py` — the ONLY safe way to push the vault (see Gotchas).

## Gotchas (hard-won)
- **Vault push:** `my-second-brain` has ~69 NTFS-illegal `:` filenames Windows can't hold in
  the index → `git add -A`/`git reset` SILENTLY stages ~380 deletions (I once deleted 376 of
  Rasto's notes; restored). ALWAYS push the vault via `tools/safe_vault_push.py` (recursive
  plumbing merge, refuses on any deletion). Agents write into dated subfolders.
- **cp1250:** emoji/Slovak `print()` 500s a request on the Windows console unless stdout is
  UTF-8 (done in `server/agora/main.py`; mirror it if adding new entrypoints).
- **Windows asyncio:** `asyncio.create_subprocess_exec` fails on uvicorn's Selector loop — use
  `subprocess.run` in `asyncio.to_thread` instead.
- **FastAPI:** register catch-all `/{name}` routes LAST or after specific ones (e.g. `/learning/graph`
  before `/learning/{agent_name}`).

## Open next steps
- Multiple curators (Voss=note quality, Mira=concepts) each gated by their own trust.
- Auto-push the autonomous curation to GitHub (currently applies locally only) via safe_vault_push.
- Make standing decay so reputation stays fluid (currently saturates high).
