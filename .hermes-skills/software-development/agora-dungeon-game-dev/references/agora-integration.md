# Agora Dungeon — Integration Reference

## From Existing Agora Backend
The dungeon game reuses these Agora components:

- **ESS Protocol** (server/agora/coordination/ess_protocol.py): Trust engine with TFT strategy — agent cooperation in dungeon
- **Stigmergy Pool** (server/agora/coordination/stigmergy.py): Agent traces as environmental signals (footprints, workbench use)
- **Model Router** (server/agora/execution/model_router.py): Tiered LLM calls per agent importance
- **God Console** (server/agora/api/god.py): !spawn, !reward, !punish, !pause commands → game UI
- **Agent API** (server/agora/api/agents.py): CRUD for agent identities
- **Schema** (server/agora/storage/schema.py): agent_identities, trust_scores, artifacts tables

## Architecture Pattern for Game
The game client (Phaser) sits alongside the React dashboard, both connecting to the same Node backend:

```
┌──────────────┐    ┌──────────────┐    ┌────────────────────┐
│  Phaser 3    │    │  React UI    │    │  Node.js Backend   │
│  (Dungeon)   │◄──►│ (Dashboard)  │◄──►│  + Express + WS    │◄──► Anthropic API
│  Canvas      │    │  React DOM   │    │  + SQLite/Postgres │
└──────────────┘    └──────────────┘    └────────────────────┘
```

## Perceive → Decide → Act Loop
```
1. GAME STATE → serialized to JSON → LLM prompt
2. LLM → {action: "move_north" | "use_workbench" | "talk:Bob" | "craft:sword"}
3. Game engine executes action (animations, physics)
4. New state → next LLM call (cycle repeats)
```

The LLM is just a Behavior Tree leaf node — same interface as FSM states.
