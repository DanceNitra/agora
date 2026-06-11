---
name: dungeon-os-threejs
description: Build and extend the Dungeon OS 3D game world using Three.js. Use this skill whenever the task involves rendering the dungeon, placing or moving agent characters, lighting, cameras, the isometric/2.5D view, loading 3D models or tiles, post-processing/bloom, or wiring the Three.js scene to game state. Trigger on any mention of the dungeon scene, the 3D world, agent avatars in 3D, tilemap-to-3D, or "the game looks bad/flat/laggy". Do NOT use for the LLM agent logic, the React dashboard panels, or the Node backend — those are separate.
---

# Dungeon OS — Three.js World Builder

You are building the **3D dungeon world** for Dungeon OS: a 2.5D isometric dungeon
where LLM-driven NPC agents move around, do quests, and transform the dungeon
into an "Agentic OS." This skill gives you the hard rules to produce a polished,
smooth, atmospheric result instead of a flat tutorial-grade scene.

> **First read.** Before writing any rendering code, read the **REALITY BRIDGE**
> below (it tells you what is *actually built today* vs. the target), then the live
> source of truth: `agora-game-server/game_state.py` and the renderer
> `agora-game-server/static/index.html`. The Three.js layer is a **view** of game
> state. It never owns game logic.

---

## ⚠️ REALITY BRIDGE — what is actually built today (READ FIRST)

The rules further down describe the **target** architecture (TypeScript/React +
WebGPU + InstancedMesh + bloom). The **current** Dungeon OS does NOT match that yet —
do not assume those files exist. Here is the real, running implementation:

### Where the code lives (this is the truth, `src/game/*.tsx` does NOT exist)
| Concern | Target (rules below) | **Actual today** |
|---|---|---|
| Source of truth (state) | `src/state/world.ts` | **`agora-game-server/game_state.py`** (`GameEngine`, `DungeonState`) |
| Renderer / scene | `src/game/*.tsx` (React) | **`agora-game-server/static/index.html`** — single-file vanilla ESM Three.js |
| Backend / agent loop | Node `backend/` | **`agora-game-server/mcp_server.py`** — FastMCP + WebSocket `:5175` + HTTP `:5174`; `ambient_life()` task sim + A* |
| Build/bundler | Vite/React | none — `index.html` served raw; `three` via `<script type="importmap">` from `/node_modules/three` |

Run it: `cd agora-game-server && python mcp_server.py` → open `http://localhost:5174`.

### How the real renderer works right now
- **WebGLRenderer** (NOT WebGPU; no `await init()`). `PCFSoftShadowMap`,
  `ACESFilmicToneMapping`, `toneMappingExposure ≈ 1.45`.
- **Grid = 1 world tile = 1 unit**, BUT the Quaternius "Ultimate Modular Ruins Pack"
  models are authored on a **2-unit grid**, so EVERY ruins model is placed at a
  **consistent `scale 0.5`** (2u model → 1u tile). This is the single most important
  scaling fact — inconsistent scales (0.4/0.5/0.6) are what made it look broken.
  Model pivots are centred on X/Z with base at y=0.
- **Floors are real `Floor_Standard` models** (tinted per zone, matte:
  `roughness=1, metalness=0`), one clone per tile — NOT colored boxes, NOT yet
  InstancedMesh.
- **Camera:** `OrthographicCamera` iso, `d ≈ 15`, with `OrbitControls` (rotation not
  hard-locked yet).
- **Night lighting:** ONE cool moonlight `DirectionalLight` + low cool `AmbientLight`
  + `HemisphereLight` + **~9 warm torch `PointLight`s only** (sparse on purpose) +
  `FogExp2`-style fog matching the dark bg. `flatShading` is forced on every loaded
  model after load. Torches also have cheap emissive flame meshes (no light).
- **Agents = 6** (King Aldric, Sgt Voss, Dame Elara, High Priest Orin, Shadow Kael,
  Sage Mira) — NOT the 7-NPC roster named below. They are **Quaternius glTF**
  characters: clone with **`SkeletonUtils.clone`** (plain `.clone()` shares the
  skeleton and piles all bodies at one spot — known bug we already hit),
  `AnimationMixer` per agent, tweened movement, billboard name + HP + thought sprites.
- **State → view wiring (matches the architecture rule):** client opens a WS, gets a
  `snapshot`, then applies incremental events: `entity_moved/state/health/thought/face`,
  `tasks_update`, `effect_added`. Client **reads, never writes**. Server drives a
  quest board + A* pathfinding (`_astar`) + `ambient_life()` social sim.
- **Layout = corner-stone night dungeon:** only NORTH (y=0) & WEST (x=0) are solid
  walls (backdrop); SOUTH/EAST and interior divisions are **open pillar colonnades**
  so the fixed iso camera always sees into rooms (no front-wall occlusion). Central
  **chasm (`void` tiles) + bridge**, throne dais + statues at the back, vault /
  library / barracks / crossroads / armory zones.

### Gaps from here to the target (the actual TODO toward the rules below)
- ❏ Tiles → **InstancedMesh** (still one clone per tile; fine at 24×20, won't scale).
- ❏ **Bloom / post-processing** (none yet) — biggest cheap visual win remaining.
- ❏ Optional **WebGPURenderer** migration (then `await renderer.init()` becomes mandatory).
- ❏ Lock camera rotation to protect the iso look.
- ❏ If/when ported to React/TS, adopt the `src/game/` layout below.

**When extending the world, match the ACTUAL files above.** Use the rules below as
the quality bar and the direction of travel, not as a description of today's tree.

---

## NON-NEGOTIABLE RULES (most failures come from breaking these)

### Version & API
- Target a modern Three.js (**r184+** for new work). Import as ESM: `import * as THREE from 'three'`.
- **Do NOT** copy old tutorial code. Forbidden/legacy patterns: `Geometry`
  (use `BufferGeometry`), `THREE.Math` (use `THREE.MathUtils`), `outputEncoding`
  (use `renderer.outputColorSpace = THREE.SRGBColorSpace`), `physicallyCorrectLights`
  (removed; it's the default now), `WebGL1Renderer` (gone).
- Color management is ON by default in modern Three. Set texture color spaces
  explicitly: `texture.colorSpace = THREE.SRGBColorSpace` for color maps, leave
  data maps (normal/roughness) in linear.

### Renderer
- Prefer **WebGPURenderer** with automatic WebGL2 fallback. It requires **async
  init** — this is the single most common silent-failure point:
  ```js
  import { WebGPURenderer } from 'three/webgpu';
  const renderer = new WebGPURenderer({ antialias: true });
  await renderer.init();           // MANDATORY — without it, nothing renders
  ```
  If the project explicitly wants WebGL only, use `WebGLRenderer` (no async init).
  Decide once, document it, don't mix. *(Today Dungeon OS uses WebGLRenderer — see Reality Bridge.)*
- Always set: `renderer.setPixelRatio(Math.min(devicePixelRatio, 2))`,
  `renderer.setSize(...)`, `renderer.shadowMap.enabled = true`.

### Materials & lighting (this is why scenes look "flat/cheap")
- **Never** light a scene with `MeshBasicMaterial` and expect depth — it ignores
  lights. Use `MeshStandardMaterial` (PBR) for dungeon geometry and agents.
- Every scene MUST have: one soft ambient/hemisphere light for base fill, plus
  motivated point/spot lights (torches, glowing station screens). A scene with a
  single directional light looks dead.
- Use **fog** (`scene.fog = new THREE.FogExp2(color, density)`) for atmosphere and
  depth — essential for the dungeon mood.
- For the stylised low-poly Quaternius look, force `material.flatShading = true`
  (set it after loading OBJ/glTF, then `material.needsUpdate = true`).

### Units, scale, and the grid
- **One tile = 1 world unit.** All dungeon geometry sits on an integer grid.
  Agents occupy tile centers. Never use arbitrary float positions for tiles.
- **Asset scale:** the ruins pack is a 2-unit kit → place every ruins model at a
  **single consistent `scale 0.5`**. Never hand-tune per-model scales.
- Y is up. The dungeon floor is the XZ plane at y=0. Walls rise in +Y.
- Map tile coords `[x, z]` directly to world `(x, 0, z)`. Keep this mapping in ONE
  helper; never inline it.

### Performance (why it gets laggy)
- Repeated geometry (floor tiles, wall blocks) MUST use **`InstancedMesh`**, not
  one `Mesh` per tile. A 40×40 dungeon = 1600 tiles; as separate meshes that's
  1600 draw calls and it will stutter. Instanced = ~1 draw call per tile type.
- **Dispose** everything you remove: `geometry.dispose()`, `material.dispose()`,
  `texture.dispose()`. On React unmount, dispose the renderer and cancel the
  animation frame. Memory leaks here cause the "fine at first, then chugs" bug.
- Reuse geometries and materials across instances. Don't `new` a material per object.
- Use one `requestAnimationFrame` loop. Clamp work with a fixed-timestep
  accumulator for movement so it's framerate-independent.

### Camera (why it looks "wrong")
- Default to an **OrthographicCamera** for the isometric look (see below), not a
  Perspective camera — perspective makes a top-down dungeon feel off.
- Position the camera at an iso angle, looking at the dungeon center. Keep camera
  setup in one place; expose pan/zoom but lock rotation to preserve the iso feel.

---

## THE RECOMMENDED DUNGEON APPROACH (2.5D isometric)

This is the look to build unless told otherwise. It reads as a premium isometric
dungeon AND lets the player see all agents at once (the point of the dashboard).

### Camera setup (isometric)
```js
const aspect = w / h;
const d = 20; // zoom: half-height of view in world units
const camera = new THREE.OrthographicCamera(-d*aspect, d*aspect, d, -d, 0.1, 1000);
camera.position.set(20, 20, 20);   // equal x,y,z gives the classic iso angle
camera.lookAt(0, 0, 0);
```
Pan by moving camera + target together; zoom by scaling `d` and updating the
projection. Do NOT let the user orbit freely — it breaks the iso aesthetic.

### Layout doctrine (corner-stone, so the fixed iso camera sees inside rooms)
- The camera looks from the south-east. SOUTH/EAST faces are nearest and would
  occlude interiors → build them as **open pillar colonnades**, not solid walls.
- Make only the far NORTH & WEST perimeter solid (the backdrop). Define rooms with
  corner columns + arches + floor-colour zones, not sealed boxes. This is the
  "corner-stone" technique and it removes the need for dynamic wall culling.
- Favour Jaquaying loops (multiple paths), 2–3 entrances, and a central focal
  feature (a chasm of `void` tiles + a narrow bridge).

### Building the dungeon from the tilemap
1. Read the grid from game state. Tile types: floor, wall, door, pillar/column,
   arch, window, void (pit), throne, stairs, plus props.
2. For each repeated tile **type**, build ONE `InstancedMesh` sized to its count.
3. Walk the grid; set each instance matrix at `tileToWorld(x, z)`.
   - Floor: the pack's `Floor_*` model (matte), base at y≈0.
   - Wall: `Wall`/`Wall_Half` model; orient from neighbours.
   - Door/throne/stairs: a few unique meshes (too few to need instancing).
4. Group everything under one `dungeon` Group so the camera frames it easily.

### Agent avatars
- Each agent is one model at `tileToWorld(agent.pos)`, y on the floor.
- glTF characters (Quaternius): clone with **`SkeletonUtils.clone`** (never plain
  `.clone()` — it shares skeletons and stacks every body at one point). One
  `AnimationMixer` per agent; map state → clip (idle/walk/attack/hit/cast/dead).
- **Movement = smooth tween, never teleport.** Each frame lerp the avatar toward
  its target tile; face the direction of travel.
- Float a small label/billboard with the agent's name (and HP / thought) above each.

### Atmosphere & "stunning" (where the payoff lives)
- **Torches/braziers:** a FEW warm `PointLight`s (~0xffa844), modest range; jitter
  intensity for flicker. Keep point lights sparse (they are expensive); use cheap
  emissive flame meshes for the rest.
- **Fog:** dark, low density — depth without hiding agents; match it to the bg colour.
- **Bloom (post-processing):** add an `UnrealBloomPass` (WebGL) or the WebGPU bloom
  node so torches and screens *glow*. This single effect does most of the visual
  heavy lifting. Tasteful threshold/strength, not blown out. *(Not yet in Dungeon OS.)*
- **OS-boot moment:** when subsystems cross threshold, animate the scene "coming
  online" — ramp emissive, increase bloom, shift fog cooler. Drive from state, tween.

---

## HOW THE SCENE CONNECTS TO STATE (the architecture rule)

```
game state (source of truth)  ──WS snapshot + events──▶  Three.js scene (this skill)
        ▲                                                       │
        │ mutations from the agent loop / MCP tools             │ reads, never writes
   backend (agent loop + LLM)                                   ▼
                                                        renders avatars/tiles/lights
```

- The render loop reconciles the scene to incoming state each frame/event (move
  avatars toward targets, update HP/thought, spawn effects).
- The scene **never** mutates game state. Player input that should change state
  goes through a state action / server tool, not a direct sprite edit.
- Keep all Three.js code in the renderer layer; keep dashboard UI and backend out
  of scope for this skill.

---

## FILE LAYOUT FOR THE 3D LAYER (TARGET, if/when ported to React/TS)

> Today there is no `src/game/`; the renderer is the single
> `agora-game-server/static/index.html`. Use this layout only when refactoring
> toward the target stack.

```
src/game/
├─ DungeonScene.tsx     # React component: mounts renderer, runs the loop, disposes on unmount
├─ renderer.ts          # creates WebGPU/WebGL renderer (async init), handles resize
├─ camera.ts            # ortho iso camera + pan/zoom (rotation locked)
├─ tileToWorld.ts       # the ONE grid→world mapping helper
├─ dungeon.ts           # builds InstancedMesh tiles from the map
├─ agents3d.ts          # avatar meshes/models + tweened movement + labels
├─ lighting.ts          # ambient/hemi + torches (flicker) + fog
├─ postfx.ts            # bloom / post-processing pipeline
└─ assets.ts            # GLTF/texture loading, colorSpace + dispose helpers
```

---

## DEFINITION OF DONE (self-check before claiming success)

1. Renderer initializes (async `init()` if WebGPU) and the scene actually shows.
2. Dungeon is built from the tilemap; repeated tiles via **InstancedMesh** (target).
3. Camera is **orthographic isometric**, framing the dungeon, rotation locked.
4. Lighting present: ambient/hemi fill + flickering torch point lights + fog.
   Geometry uses `MeshStandardMaterial`, not `MeshBasicMaterial`.
5. All agents render as **visually distinct** avatars at correct tile positions and
   **move smoothly** (tweened) toward their state targets.
6. Bloom/post-processing active; torches and screens glow.
7. No game logic in the renderer; scene reads state, never writes it.
8. On unmount: animation frame cancelled, renderer + geometries + materials +
   textures disposed (no WebGL/WebGPU context leak).
9. Frame stays smooth on a 40×40 dungeon (`renderer.info` draw calls in the tens,
   not thousands).

If any item fails, fix it before moving on. A scene that "renders something" but
fails 2, 4, 5, or 8 is exactly the weak result this skill exists to prevent.

---

## QUICK ANTI-PATTERNS CHECKLIST (scan your own output for these)

- ❌ `MeshBasicMaterial` on lit geometry → ✅ `MeshStandardMaterial`
- ❌ one `Mesh` per tile → ✅ `InstancedMesh`
- ❌ per-model hand-tuned scales → ✅ one consistent `scale 0.5` for the 2-unit ruins kit
- ❌ glTF `scene.clone()` for skinned agents → ✅ `SkeletonUtils.clone`
- ❌ avatars snapping between tiles → ✅ tweened movement
- ❌ PerspectiveCamera for the dungeon → ✅ OrthographicCamera iso
- ❌ solid front (S/E) walls that hide interiors → ✅ open corner-stone colonnades
- ❌ no `await renderer.init()` on WebGPU → ✅ awaited
- ❌ no fog / single light / dozens of point lights → ✅ fog + ambient + a FEW torches
- ❌ creating materials/geometries in the loop → ✅ created once, reused
- ❌ no dispose on unmount → ✅ full teardown
- ❌ copying r140-era API → ✅ r184 API (BufferGeometry, MathUtils, colorSpace)
- ❌ renderer owning state → ✅ renderer reads game state, never writes it
