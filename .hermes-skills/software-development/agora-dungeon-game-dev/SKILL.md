---
name: agora-dungeon-game-dev
description: "Build a 2D dungeon game where AI agents cooperate, work on businesses, and an orchestrator (human) guides them — Phaser 3 + TypeScript + React + Node backend with LLM agents."
type: knowledge
triggers:
  - dungeon game
  - 2D game dev
  - agent game
  - Phaser AI
  - game dev study
  - game AI research
  - behavior tree
  - memory stream
  - multi-agent coordination
---

# 🎮 Agora Dungeon — Game Development Knowledge

## User Preferences
- **Language**: English for code/docs, even when user communicates in Slovak. The user expects all code, comments, file contents, and documentation in English.
- **Research workflow**: When the user provides research answers from NotebookLM, save them immediately as reference files in the skill's `references/` directory. One file per topic. Keep updating SKILL.md to point to new references.

## Overview
Build a visually stunning 2D browser dungeon game where AI agents (like Hermes/Claude Code) operate independently, cooperate, and build real businesses. An orchestrator (human) assigns tasks. Built with **TypeScript + Phaser 3 + React + Node.js + LLM API**.

## 🧠 Knowledge from Research (8 Series — NotebookLM)

All 8 series were researched via NotebookLM using 3 books + 4 papers. Answers were saved as TypeScript reference files in `references/`.

### Series 1: Memory Stream + Reflection (Generative Agents)
Full architecture and TypeScript implementation of the Generative Agents memory system.

**Key parameters:**
- Decay rate λ = 0.995 per game hour
- Importance: LLM-scored 1-10
- Retrieval = recency + importance + relevance (all α=1.0)
- Reflection trigger: sum(importance) > 150
- Reflection tree: leaf=observations, non-leaf=increasingly abstract

**Reference files:**
- `references/memory-stream-impl.md` — full architecture doc
- `references/generative-agent-ts-implementation.ts` — complete working TypeScript class

### Series 2: Behavior Trees
Full BT runtime with 6 node types + Phaser 3 visual editor.

**Nodes:** Action, Condition, Sequence, Selector, Parallel, Inverter, Repeat
**Visual debug:** Color-coded state display in Phaser, JSON serialization

**Reference files:**
- `references/behavior-tree-runtime.ts` — core BT runtime
- `references/bt-editor-phaser.ts` — Phaser 3 visual editor + BTFactory

### Series 3: Pathfinding + Steering
A* pathfinding + steering behaviors integrated into Phaser 3.

**A* features:** Binary heap priority queue, Manhattan/Euclidean/Octile heuristics, path smoothing via Bresenham, HPA* architecture
**Steering:** Seek, Flee, Arrival, Pursuit, Evasion, Wander, Obstacle Avoidance, Blended Steering, Path Following, Flocking (Separation/Alignment/Cohesion)

**Reference files:**
- `references/a-star-pathfinding.ts` — A* with binary heap + smoothPath
- `references/steering-behaviors-phaser.ts` — SteeringAgent class + FlockingSystem

### Series 4: Decision Making (4 techniques)

| Technique | File | Use Case |
|:----------|:-----|:---------|
| Hierarchical FSM | `references/hierarchical-fsm.ts` | State-based NPC behavior with nesting |
| Fuzzy Logic | `references/fuzzy-logic.ts` | Continuous threat/health assessment, COG defuzzification |
| Utility AI | `references/utility-ai.ts` | Dynamic action scoring with curves + BT hybrid |
| Decision Trees | (inline in session) | Binary branching for fast decisions |

**Key insight:** Utility Fallback node replaces hardcoded BT priority with dynamic scoring. Best for unpredictable situations.

### Series 5: Multi-Agent Coordination

| Pattern | File | Description |
|:--------|:-----|:------------|
| Contract Net Protocol | `references/contract-net-protocol.ts` | Task announcement → bids → award → execute → confirm |
| Vickrey Auctions | (in CNP file) | Second-price sealed-bid for scarce tasks |
| Shapley Value | `references/coalition-shapley.ts` | Fair reward distribution based on marginal contribution |
| Trust & Reputation | `references/trust-engine.ts` | Trust with decay, forgiveness, threshold gating |
| Negotiation + Persuasion | (inline in session) | Price negotiation + speech-act-based CONVINCE |

### Series 6: Game Architecture Patterns

| Pattern | File | Description |
|:--------|:-----|:------------|
| Fixed Timestep Game Loop | (inline) | Accumulator pattern, logic vs render separation |
| ECS | (inline) | Entity-Component-System: Entity=ID, Component=data, System=logic |
| Event Bus | (inline) | Typed events with strict payload interfaces |
| Game State Pattern | (inline) | Menu → Play → Pause → GameOver via Phaser scenes |
| Object Pool | (inline) | Generic pool with O(1) acquire/release, IPoolable interface |

### Series 7: LLM + Traditional AI Hybrid
- LLM for: dialogues, plans, reflections, creative decisions
- Traditional for: pathfinding, combat, physics, movement
- LLM-as-a-Service: async request queue, rate limiting, timeout fallback
- Cache LLM responses for repeated situations

### Series 8: Phaser 3 UI
- Tile-based maps from Tiled editor
- Turn-based combat with action menu
- Dialogue trees with branching responses
- Inventory/quest log with drag & drop
- Mini-map with fog of war

## 🧪 Research Pipeline (NotebookLM Workflow)

When the user wants to research a topic for game dev upgrades:

1. **Prepare questions**: Write research questions in `research-questions.md`, organized by topic
2. **User feeds to NotebookLM**: User pastes questions + uploads source PDFs to notebooklm.google.com
3. **User pastes answers back**: User returns with LLM-generated answers
4. **Save immediately**: Create a reference file in `references/` with the full answer
5. **Ask next question**: Continue through the series one question at a time
6. **Periodically update SKILL.md**: Add pointers to new reference files as they accumulate

## 📚 Reference Files

| File | Content | Type |
|:-----|:--------|:-----|
| `memory-stream-impl.md` | Memory Stream + Reflection + Planning + ReAct architecture | Architecture |
| `generative-agent-ts-implementation.ts` | Complete GenerativeAgent class (Memory, Retrieval, Planning, ReAct) | TypeScript |
| `generative-agents-full-architecture.md` | Full paper architecture breakdown | Architecture |
| `generative-agents-pattern.md` | Condensed Generative Agents pattern | Pattern |
| `react-pattern.md` | ReAct perceive→decide→act loop | Pattern |
| `voyager-pattern.md` | Voyager skill discovery + iterative refinement | Pattern |
| `behavior-trees-pattern.md` | Behavior Trees summary | Pattern |
| `behavior-tree-runtime.ts` | BT runtime: Action, Condition, Sequence, Selector, Parallel, Inverter | TypeScript |
| `bt-editor-phaser.ts` | Phaser 3 visual BT editor + BTFactory (JSON→BT) | TypeScript |
| `a-star-pathfinding.ts` | A* with binary heap, path smoothing, HPA*, Bresenham raycast | TypeScript |
| `steering-behaviors-phaser.ts` | SteeringAgent class + FlockingSystem + Path Following | TypeScript |
| `hierarchical-fsm.ts` | HFSM with State, StateMachine, Transition + dungeon NPC example | TypeScript |
| `fuzzy-logic.ts` | Fuzzy sets (Triangle/LeftShoulder/RightShoulder), COG defuzzification | TypeScript |
| `utility-ai.ts` | Utility curves, UtilityAction, UtilityFallback (BT hybrid) | TypeScript |
| `contract-net-protocol.ts` | CNP + Vickrey auction + marginal cost bidding | TypeScript |
| `coalition-shapley.ts` | CoalitionalGame, Shapley value, superadditivity check | TypeScript |
| `trust-engine.ts` | Trust with decay, forgiveness, threshold gating, partner selection | TypeScript |
| `agora-integration.md` | How to integrate with existing Agora backend (ESS, Stigmergy, God Console) | Integration |

## 📖 Quick Reference: Free Resources
- TypeScript Handbook: https://typescriptlang.org/docs
- Game Programming Patterns (free): https://gameprogrammingpatterns.com
- Phaser 3 Examples: https://phaser.io/examples
- ReAct paper: arXiv:2210.03629
- **Generative Agents paper**: arXiv:2304.03442 ⭐ (most important!)
- **Generative Agents code**: https://github.com/joonspk-research/generative_agents ⭐
- Voyager paper: arXiv:2305.16291
- Behavior Trees paper: arXiv:1709.00084
- Eloquent JavaScript (free): https://eloquentjavascript.net

## ⚡ Critical Architecture Decisions
1. **LLM calls NEVER from browser** — Node backend only (API keys safe)
2. **Build FSM/BehaviorTree first** before hooking LLM — testable, debuggable visible AI
3. **LLM is a Behavior Tree leaf node** — same interface, swappable
4. **Perceive → Decide → Act** loop is the core — get this right first
5. **No pixel art until Phase 4** — use colored rectangles/capsules for early dev
6. **Memory with importance**: not all events equally important — LLM scores 1-9
7. **Skills as programs**: verifiable, reusable action sequences, not text descriptions
8. **Environment as tree**: world→areas→objects, agents build subgraphs individually
9. **ALL agent state in JSON**: location, action, object interaction — single source of truth
10. **Reflect every ~150 importance**: reflection trees enable higher-level reasoning
11. **Utility Fallback > hardcoded BT**: dynamic scoring adapts to unpredictable situations
12. **A* path smoothing**: always run line-of-sight smoothing before feeding waypoints to steering
13. **Trust thresholds for task assignment**: never assign tasks to agents below trust threshold
14. **Shapley for fair rewards**: use marginal contribution, not equal split, for coalition rewards

## 🔗 Agora Integration
Reuse from existing Agora project:
- **ESS Protocol** → agent trust & cooperation in dungeon
- **Stigmergy Pool** → agent traces as environmental signals
- **Model Router** → tiered LLM calls per agent importance
- **God Console** → existing commands adapt to game UI
- **Agent Roles** → expand from 3 to 10+ dungeon professions

## 🧰 Recommended Stack
| Layer | Tech |
|:------|:-----|
| Game Engine | **Phaser 3** (same as Generative Agents sandbox!) |
| Orchestrator UI | **React + Tailwind** |
| Backend Server | **Node.js + Express** (Generative Agents used Django + JSON server) |
| Real-time | **WebSocket** |
| LLM | **DeepSeek** (via ModelRouter: flash/pro) |
| DB | SQLite → PostgreSQL |
| Embeddings | For memory relevance scoring |
