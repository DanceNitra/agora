# 🎮 Agora Dungeon — Game Development Study Plan

> *"A 2D dungeon game where AI agents cooperate, operate independently, build real businesses, and an orchestrator (human) guides them — all in a stunning immersive UI."*

---

## 📊 Campaign Progress

| Phase | Status | Tasks | Completion |
|:------|:------:|:-----:|:----------:|
| 🏗️ **Phase 0** — Foundations | ⬜ | 6 | 0/6 |
| 🤖 **Phase 1** — Fake Agents | ⬜ | 5 | 0/5 |
| 🧠 **Phase 2** — One Real Agent | ⬜ | 5 | 0/5 |
| 👥 **Phase 3** — Multi-Agent + Orchestrator | ⬜ | 6 | 0/6 |
| ✨ **Phase 4** — Immersive Polish | ⬜ | 5 | 0/5 |

**Rank:** 🪵 Apprentice *(0/5 phases cleared → Novice → Journeyman → Expert → Archmage)*

---

## 🏗️ Phase 0 — Foundations (2–4 weeks)

> *Learn TypeScript basics, get one Phaser scene running, move a sprite around a tilemap with a camera following it.*

### Questy

- [ ] **Q0.1** — TypeScript fundamentals (types, interfaces, classes, modules)
- [ ] **Q0.2** — Phaser 3: create a scene, load assets, render a sprite
- [ ] **Q0.3** — Tilemap: draw a dungeon room, load Tiled JSON map
- [ ] **Q0.4** — Player movement: keyboard input, camera follows player
- [ ] **Q0.5** — Collision: walls block movement, basic overlap detection
- [ ] **Q0.6** — Camera: scrolling, zoom, world bounds

### 📚 Literature

| # | Resource | Type | Link |
|:-:|:---------|:----:|:----:|
| 1 | TypeScript Handbook | 📖 free | https://www.typescriptlang.org/docs/ |
| 2 | Eloquent JavaScript (Marijn Haverbeke) | 📖 free | https://eloquentjavascript.net/ |
| 3 | Phaser 3 Official Examples | 📖 free | https://phaser.io/examples |
| 4 | Phaser 3 API Docs | 📖 free | https://newdocs.phaser.io/ |
| 5 | Mozilla MDN Game Dev Guides | 📖 free | https://developer.mozilla.org/en-US/docs/Games |
| 6 | HTML5 Game Development (O'Reilly) | 📕 book | ISBN 978-1449362900 |
| 7 | **Game Programming Patterns** (Robert Nystrom) | 📕 book | https://gameprogrammingpatterns.com/ |

---

## 🤖 Phase 1 — Fake Agents (2–3 weeks)

> *Add 2–3 NPCs with hardcoded behavior (state machines / behavior trees). No LLMs yet. Build the visible behavior system first.*

### Questy

- [ ] **Q1.1** — NPC class: idle, wander, work states
- [ ] **Q1.2** — Finite State Machine (FSM) for NPC behavior
- [ ] **Q1.3** — Behavior Tree: sequence/selector/condition nodes
- [ ] **Q1.4** — Multiple NPCs with different roles visible on map
- [ ] **Q1.5** — Basic interaction: NPC ↔ workbench, NPC → player messages

### 📚 Literature

| # | Resource | Type | Link |
|:-:|:---------|:----:|:----:|
| 1 | **Programming Game AI by Example** (Mat Buckland) | 📕 book | ISBN 978-1556220784 |
| 2 | **Behavior Trees in Robotics and AI** (Colledanchise & Ögren) | 📖 free | arXiv:1709.00084 |
| 3 | **Artificial Intelligence for Games** (Millington & Funge) | 📕 book | ISBN 978-0123747310 |
| 4 | **Game AI Pro** (Steve Rabin, ed.) | 📕 book | ISBN 978-1466565643 |
| 5 | State vs. Behavior Tree comparison articles | 📖 free | https://www.gamedeveloper.com/ |
| 6 | Phaser 3 NPC movement examples | 📖 free | Phaser example gallery |

---

## 🧠 Phase 2 — One Real Agent (2–3 weeks)

> *Wire up Node.js backend → Anthropic API → one LLM agent decides its next action from a small menu.*

### Questy

- [ ] **Q2.1** — Node.js + Express backend, API endpoint for agent decisions
- [ ] **Q2.2** — Call LLM API with structured output (JSON mode)
- [ ] **Q2.3** — Perceive → Decide → Act loop: game state → LLM → action
- [ ] **Q2.4** — One agent follows LLM decisions: navigate, use stations, talk
- [ ] **Q2.5** — Agent memory: short-term (session) + long-term (summary)

### 📚 Literature

| # | Resource | Type | Link |
|:-:|:---------|:----:|:----:|
| 1 | Anthropic Docs: Building Agents & Tool Use | 📖 free | https://docs.anthropic.com/ |
| 2 | **ReAct** (Yao et al., 2022) | 📄 paper | arXiv:2210.03629 |
| 3 | **Generative Agents** (Park et al., 2023) | 📄 paper | arXiv:2304.03442 |
| 4 | **Generative Agents** open-source repo | 🔧 code | https://github.com/joonspk-research/generative_agents |
| 5 | OpenAI Function Calling / Structured Outputs | 📖 free | OpenAI docs |
| 6 | Node.js + Express + Anthropic SDK examples | 📖 free | Anthropic cookbook |
| 7 | **Voyager** (Wang et al., 2023) | 📄 paper | arXiv:2305.16291 |

---

## 👥 Phase 3 — Multi-Agent + Orchestrator (4–8 weeks)

> *Multiple agents, orchestrator assigns tasks, cooperation layer, dashboard UI. The "running a business" simulation.*

### Questy

- [ ] **Q3.1** — Multi-agent coordination: message passing between agents
- [ ] **Q3.2** — Agent roles: miner, crafter, trader, builder, scout
- [ ] **Q3.3** — Orchestrator (human): assign tasks via dashboard UI
- [ ] **Q3.4** — Task graph with resources, dependencies, goals
- [ ] **Q3.5** — Economy: resource collection, crafting, trading values
- [ ] **Q3.6** — React dashboard: agent status, task queue, map overview

### 📚 Literature

| # | Resource | Type | Link |
|:-:|:---------|:----:|:----:|
| 1 | LangGraph Docs: Multi-agent systems | 📖 free | https://langchain-ai.github.io/langgraph/ |
| 2 | CrewAI: Orchestrator/Worker pattern | 📖 free | https://docs.crewai.com/ |
| 3 | Anthropic: Multi-agent research systems blog | 📖 free | Anthropic engineering blog |
| 4 | **Multi-Agent Systems** (Weiss, ed., MIT Press) | 📕 book | ISBN 978-0262731317 |
| 5 | **Swarm Intelligence** (Kennedy & Eberhart) | 📕 book | ISBN 978-1558605954 |
| 6 | React + Phaser integration patterns | 📖 free | GitHub examples |
| 7 | WebSocket for real-time agent updates | 📖 free | MDN WebSocket guide |

---

## ✨ Phase 4 — Immersive Polish

> *Lighting, particles, animation, sound, OS-style interface. Looks come last — cheap to add to a working system.*

### Questy

- [ ] **Q4.1** — Dynamic lighting + torch/glow effects
- [ ] **Q4.2** — Particle systems: dust, fire, magic effects
- [ ] **Q4.3** — Sprite animations: idle, walk, work, interact
- [ ] **Q4.4** — Sound: ambient dungeon, footsteps, UI clicks
- [ ] **Q4.5** — OS-style "God Console" overlay: terminals, windows, agent logs

### 📚 Literature

| # | Resource | Type | Link |
|:-:|:---------|:----:|:----:|
| 1 | Phaser 3: Particle System Guide | 📖 free | https://phaser.io/examples/v3/particles |
| 2 | Phaser 3: Dynamic Lighting Plugin | 📖 free | Phaser plugin examples |
| 3 | Phaser 3: Animation System Docs | 📖 free | Phaser API docs |
| 4 | Web Audio API (MDN) | 📖 free | https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API |
| 5 | **Game Feel** (Steve Swink) | 📕 book | ISBN 978-0123747341 |
| 6 | **Juice It Or Lose It** (GDC talk) | 🎥 free | YouTube: GDC 2012 |
| 7 | Tiled Map Editor: Advanced lighting layers | 📖 free | https://www.mapeditor.org/ |

---

## 🧰 Recommended Stack

| Layer | Technology |
|:------|:-----------|
| 🎮 Game Engine | **Phaser 3** (2D rendering, tilemaps, physics, camera) — or **PixiJS** for more control |
| 🖥️ Orchestrator UI | **React** + **Tailwind** (dashboard around the canvas) |
| 🧠 Backend API | **Node.js + Express** (never call LLM from browser — keys leak) |
| 🔌 Real-time | **WebSocket** (agent status, task updates, logs) |
| 🗄️ Database | **SQLite** (dev) → **PostgreSQL** (prod) — reuse from Agora |
| 🤖 LLM | **Anthropic Claude** (structured JSON output, tool use) |

---

## 🔗 Integration with Agora Project

This game is the **visual frontend** to the Agora agent ecosystem already built:

| Agora Component | Will Power |
|:----------------|:-----------|
| ESS Protocol (TFT) | Agent trust & cooperation in the dungeon |
| Stigmergy Pool | Agent traces → environmental signals |
| Model Router | Tiered LLM calls per agent importance |
| God Console | Existing `/god` commands adapt to game UI |
| Agent Roles | Expand from 3 to 10+ dungeon roles |

---

## 📖 Master Reading List (All Literature)

### Free Online Resources
1. TypeScript Handbook — https://www.typescriptlang.org/docs/
2. Eloquent JavaScript — https://eloquentjavascript.net/
3. Game Programming Patterns — https://gameprogrammingpatterns.com/
4. Phaser 3 Examples — https://phaser.io/examples
5. MDN Game Dev — https://developer.mozilla.org/en-US/docs/Games
6. Anthropic Docs — https://docs.anthropic.com/
7. LangGraph Docs — https://langchain-ai.github.io/langgraph/
8. CrewAI Docs — https://docs.crewai.com/
9. Behavior Trees paper — arXiv:1709.00084
10. MDN WebSocket — https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
11. Web Audio API — https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API

### Papers (arXiv / free PDF)
- ReAct — Yao et al., 2022 (arXiv:2210.03629)
- Generative Agents — Park et al., 2023 (arXiv:2304.03442)
- Voyager — Wang et al., 2023 (arXiv:2305.16291)

### Books to Buy
- Game Programming Patterns — Nystrom (free online, buy for offline)
- Programming Game AI by Example — Buckland (ISBN 978-1556220784)
- Artificial Intelligence for Games — Millington & Funge (ISBN 978-0123747310)
- Game AI Pro — Rabin (ISBN 978-1466565643)
- Multi-Agent Systems — Weiss (ISBN 978-0262731317)
- Game Feel — Swink (ISBN 978-0123747341)

---

*Created: 2026-06-06 | Last updated with Phase 0–4 study plan*
