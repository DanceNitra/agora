# 🏛️ Dungeon OS — Roadmap

> Commit: `335b7b3` | Repo: `github.com/DanceNitra/agora`
> Server: `agora-game-server/` | Live: `http://localhost:5174/`

---

## ✅ Phase 1 — Engine Foundation (HOTOVÉ)

| Časť | Stav | Detail |
|:-----|:-----|:-------|
| Three.js engine | ✅ | Izometrická orthographic kamera, OrbitControls, tiene |
| MCP server | ✅ | FastMCP tooly (spawn, move, anim, thought, health) |
| WebSocket sync | ✅ | Real-time broadcast na port 5175 |
| HTTP server | ✅ | Static files na port 5174 |
| Game state engine | ✅ | `game_state.py` — tiles, entities, lights, tick |

## ✅ Phase 2 — Layout (HOTOVÉ)

| Časť | Stav | Detail |
|:-----|:-----|:-------|
| Rozmery | ✅ | 24×20 grid (480 tiles) |
| Throne Room | ✅ | Centrálna sever, fialová podlaha, Diamond floor |
| Library | ✅ | Severozápad, modrá podlaha |
| Treasury | ✅ | Severovýchod, zlatá podlaha + chesty |
| Great Hall | ✅ | Stred, 10 stĺpov (Column_Round), modrá podlaha |
| Barracks | ✅ | Juhozápad, sivá podlaha |
| Entrance Hall | ✅ | Juh, modrá podlaha, GATE otvor |
| Armory | ✅ | Juhovýchod, tmavá podlaha |
| Vnútorné steny | ✅ | Oddeľujú miestnosti, archway otvory |
| Gate | ✅ | Otvor v južnej stene |

## ✅ Phase 3 — 3D Assety (HOTOVÉ)

| Model | Formát | Scale | Použitie |
|:------|:-------|:------|:---------|
| Wall.obj | OBJ+MTL | 0.5 | Dvojtile steny (vnútorné) |
| Wall_Half.obj | OBJ+MTL | 1.0 | Jednotile steny (vonkajší border) |
| Column_Round.obj | OBJ+MTL | 0.4 | Stĺpy v Great Hall |
| Torch.obj | OBJ+MTL | 1.0 | Pochodne na stenách |
| Chest.obj | OBJ+MTL | 0.5 | Truhlice v Treasury |
| Chest_Gold.obj | OBJ+MTL | 0.5 | Zlaté truhlice |
| Floor_Diamond.obj | OBJ+MTL | 0.5 | Diamantová podlaha v Throne Room |
| Statue_Fox.obj | OBJ+MTL | — | (načítaný, nepoužitý) |
| Flag_Wall.obj | OBJ+MTL | — | (načítaný, nepoužitý) |
| Bush_2x2.obj | OBJ+MTL | — | (načítaný, nepoužitý) |

## ✅ Phase 4 — Postavičky (HOTOVÉ)

| Agent | Model | Animácie | Umiestnenie |
|:------|:------|:---------|:------------|
| 👑 King Aldric | King.gltf | Idle_Neutral | Throne Room (12.5, 3.5) |
| 🗡️ Sergeant Voss | Adventurer.gltf | Idle_Neutral | Entrance (10, 18) |
| 🛡️ Dame Elara | Adventurer.gltf | Idle_Neutral | Entrance (14, 18) |
| 🙏 High Priest Orin | Adventurer.gltf | Idle_Neutral | Great Hall (12, 7) |
| 🥷 Shadow Kael | Worker.gltf | Idle_Neutral | Treasury area (20, 11) |
| 📚 Sage Mira | Adventurer.gltf | Idle_Neutral | Library (4, 3) |

---

## ⬜ Phase 5 — Čo treba DORIEŠIŤ (NEXT)

### 5.1 Layout — chýbajúce prvky
- [ ] **Rohové steny** — na rohoch sa prekrývajú dva segmenty, chýba corner piece
- [ ] **Wall_ArchGothic** — namiesto prázdnych archway otvorov vložiť gotické oblúky
- [ ] **Dvere** — Doors_GothicArch.obj do archway otvorov
- [ ] **Statues** — Statue_Fox / Statue_Stag do Throne Room
- [ ] **Vlajky** — Flag_Wall.obj na steny v Throne Room
- [ ] **Kríky/Stromy** — Bush_2x2, Tree_1 v Barracks / Entrance
- [ ] **Schody** — Stairs.obj do Entrance alebo Great Hall
- [ ] **Studňa/ohnisko** — Support_Center.obj ako centrálny bod
- [ ] **Knižnica** — Bookcase_Full.obj do Library

### 5.2 Osvetlenie
- [ ] **PointLights** — momentálne vypnuté (spôsobovali diery v stenách)
- [ ] **Štúdium Three.js osvetlenia** — správne nastaviť PointLights, aby nerobili artrifakty
- [ ] **Ambient light** — aktuálne 0x222244, možno doladiť
- [ ] **Torch glow** — dynamické svetlo z Torch objektov

### 5.3 Animácie
- [ ] **Walk animácia** — prepnúť z Idle na Walk keď sa agent pohybuje
- [ ] **MCP tool na zmenu animácie** — `set_agent_state("guard_l", "walking")`
- [ ] **Think/Cast animácie** — pre priest a scholar
- [ ] **Death animácia** — keď health klesne na 0

### 5.4 UI
- [ ] **Thought bubble** — HTML element nad agentom (už je v HTML, nefunkčný)
- [ ] **Event log** — zoznam akcií v dungeon
- [ ] **Agent list** — panel s menami a HP
- [ ] **Quest board** — questy/misie
- [ ] **OS meters** — CPU/memory metafory

### 5.5 MCP rozšírenia
- [ ] **Walk tool** — `move_agent` + auto prepnutie animácie na Walk
- [ ] **Pathfinding** — A* algoritmus pre agentov
- [ ] **Corporation tick** — autonomné správanie agentov
- [ ] **Agent dialógy** — thought bubble + speech
- [ ] **Weather/time** — denná noc, dážď

### 5.6 Herné mechaniky
- [ ] **Inventory** — agents môžu zbierať predmety
- [ ] **Combat** — útok, obrana, HP
- [ ] **Quest system** — quest board + plnenie questov
- [ ] **Trading** — výmena predmetov medzi agentmi

---

## 📦 Asset knižnica (dostupné, neintegrované)

| Kategória | Súbory |
|:----------|:-------|
| 🧱 Steny | Wall_Broken, Wall_Double_Hole, Wall_Hole, Wall_Overgrown, Wall_ArchGothic, Wall_ArchRound (+ broken, overgrown varianty) |
| 🚪 Dvere | Doors_GothicArch, Doors_GothicArch_Covered, Doors_RoundArch, Doors_RoundArch_Covered |
| 🏛️ Oblúky | Arch_Gothic, Arch_Round (+ RoundColumn varianty) |
| 🪟 Okná | Window_Bars, Window_Bars_Overgrown, Window_Bars_Double_Overgrown, Window_Open, Window_Open_Double |
| 🪑 Nábytok | Bookcase_Full, Bookcase_Empty, Crate, Barrel, Cart, Candles_1, Candles_2 |
| 🪴 Dekor | Pot1-3 (+ broken), Skull, BearTrap, Trapdoor, Grass |
| 🎌 Vlajky | Flag_GothicArch, Flag_RoundArch, Flag_Wall, Flag_Wall2 |
| 📐 Podlahy | Floor_Squares, Floor_SquareLarge, Floor_Standard_Half, Floor_Hole_Corner, Floor_Hole_Straight, Floor_Tree |
| 🌳 Príroda | Tree_1-3, DeadTree_1-3, Bush_1x1, Bush_2x1, Bush_Large, Bush_Round |
| 🪜 Ostatné | Stairs, Stairs_2, BridgeSection, Rail_Corner/Divider/Straight, Support_Center/Left/Right/Tall, Column_BridgeSupport, Column_Square, Column_Round_Short, Curve_1/2 (+ overgrown), Brick, Bricks |

## 🚀 Server príkaz
```bash
cd ~/agora/agora-game-server
python3 mcp_server.py
# HTTP: http://localhost:5174
# WS: ws://localhost:5175
```
