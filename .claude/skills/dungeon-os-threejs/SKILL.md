---
name: dungeon-os-threejs
description: Build and extend the Dungeon OS 3D world (the live Three.js renderer in agora-game-server/static/index.html). Use whenever the task touches the dungeon scene, agent avatars in 3D, tiles/walls/props, lighting, the isometric camera, post-processing/bloom, sprites/labels, or "the game looks flat/cheap/laggy/should look presentable". NOT for the LLM agent loop (mcp_server.py), the brain (server/agora), or the React dashboard.
---

# Dungeon OS — Three.js World Builder

The **3D dungeon** is a 2.5-D isometric night scene where six LLM-driven agents move
around and build an "Agentic OS." The renderer is a **view** of game state — it reads
state over a WebSocket and never owns game logic.

> **Before writing render code, read the two source-of-truth files** (don't trust memory):
> - `agora-game-server/static/index.html` — the entire renderer (single-file vanilla ESM Three.js, ~1500 lines).
> - `agora-game-server/game_state.py` — `GameEngine`/`DungeonState` (the tilemap + entities the scene renders).
> Run it: `cd agora-game-server && python mcp_server.py` → open `http://localhost:5174`.
> The dungeon process is launched/restarted by the loop's standard procedure; after editing
> `index.html` you only need a **browser hard-refresh** (it's served raw, no build step).

---

## GROUND TRUTH — the actual stack (build to match this, not a target)

| Concern | Reality |
|---|---|
| Three.js | **r0.170.0**, vendored at `agora-game-server/node_modules/three`. ESM via `<script type="importmap">`: `"three" → /node_modules/three/build/three.module.js`, `"three/addons/" → /node_modules/three/examples/jsm/`. |
| Renderer | **`WebGLRenderer({ antialias:true })`** — synchronous, **no `await init()`**. `setPixelRatio(min(dpr,2))`, `shadowMap.enabled`, `PCFSoftShadowMap`, `ACESFilmicToneMapping`, `toneMappingExposure ≈ 1.45`. *(A WebGPU build `three.webgpu.js` is vendored but UNUSED — see Upgrade Path before touching it.)* |
| Camera | **`OrthographicCamera`** iso, `d ≈ 15`, `position (d,d,d)` looking at `(0,0,0)`, **`OrbitControls`** (rotation NOT locked yet). |
| Atmosphere | `scene.background = 0x0a0e18` (deep night); `scene.fog = new THREE.Fog(0x0a0e18, 45, 95)` (linear, matches bg). |
| Lights | `AmbientLight(0x37466a, .5)` + cool moonlight `DirectionalLight(0x9fb2da, 1.0)` with a **tight shadow frustum (±16)** for crisp shadows + `HemisphereLight(0x5a6e98, 0x2a2420, .5)` + **~9 warm torch `PointLight`s from state** (`radius`, `decay 1.8`) + cheap **emissive flame meshes** flickered each frame. Point lights are sparse ON PURPOSE. |
| Floors/walls/props | The **Quaternius "Ultimate Modular Ruins Pack"** (`Floor_Standard`, `Floor_Diamond`, `Wall*`, `Statue_*`, `Flag_Wall`, columns…). Loaded once into a `ruinsCache`, then **one clone per tile** (floors are real models, not boxes; one tinted template per zone colour). |
| Agents | **6** (King Aldric, Sgt Voss, Dame Elara, High Priest Orin, Shadow Kael, Sage Mira). Quaternius **glTF**, cloned with **`SkeletonUtils.clone`**, one `AnimationMixer` each, tweened movement, `CanvasTexture` **Sprite** labels (name / HP bar / thought bubble). |
| State→view | Client opens WS `:5175`, gets a `snapshot`, applies incremental events (`entity_moved/state/health/thought/face`, `tasks_update`, `effect_added`, `os_build`, trust/HUD). **Reads, never writes.** HTTP is `:5174`. |
| Post-processing | **NONE yet.** `EffectComposer`, `UnrealBloomPass`, `SSAOPass`, `GTAOPass`, `SMAAPass`, `OutputPass` are all present in `node_modules/three/examples/jsm/postprocessing/` and unused. **This is the single biggest visual win available.** |

### The hard-won facts (breaking these is what made it look broken before)
- **One tile = 1 world unit.** The ruins kit is authored on a **2-unit grid**, so EVERY
  ruins model is placed at a **single consistent `scale 0.5`** (2u → 1u). Never hand-tune
  per-model scales (0.4/0.5/0.6 is what looked wrong). Pivots are centred on X/Z, base at y=0.
- **`SkeletonUtils.clone(gltf.scene)`**, never `gltf.scene.clone()` — plain clone shares the
  skeleton and stacks every body at one point (a bug already hit).
- **Corner-stone layout:** the iso camera looks from the south-east, so SOUTH/EAST faces are
  open **pillar colonnades** and only far NORTH (z=0) & WEST (x=0) are solid (backdrop). This
  removes front-wall occlusion without dynamic culling. Central **chasm (`void` tiles) + bridge**,
  throne dais + statues at the back, zoned floors (vault / library / barracks / crossroads / armory).
- After loading any model, force **`material.flatShading = true; material.needsUpdate = true`** for the stylised low-poly look.
- Color management is on by default; set **`texture.colorSpace = THREE.SRGBColorSpace`** on colour/label textures (already done for sprite labels); leave data maps (normal/roughness) linear.

---

## NON-NEGOTIABLE RULES (r0.170, this codebase)

- **Lit geometry uses `MeshStandardMaterial`** (PBR), never `MeshBasicMaterial` (ignores lights → flat). Floors are matte (`roughness 1, metalness 0`); glows use `emissive` + `emissiveIntensity`.
- **Modern API only:** `BufferGeometry` (not `Geometry`), `THREE.MathUtils` (not `THREE.Math`), `renderer.outputColorSpace = SRGBColorSpace` (not `outputEncoding`). No `physicallyCorrectLights` (default now), no `WebGL1Renderer`.
- **The grid→world mapping lives in ONE place** (`tile [x,z] → (x, 0, z)`); never inline it elsewhere.
- **Movement is tweened, never teleported** — lerp avatars toward target tiles each frame and face the travel direction.
- **The renderer reads state, never writes it.** Anything that should change the world goes through a server tool/event, not a sprite edit.
- **Dispose on teardown / when removing objects:** `geometry.dispose()`, `material.dispose()`, `texture.dispose()`; keep the single `requestAnimationFrame` loop (cancel it on teardown). Leaks here cause "fine, then chugs".
- **Keep it WebGL** unless a task explicitly migrates to WebGPU. If migrating: import from `three/webgpu`, `await renderer.init()` becomes **mandatory** (the #1 silent-failure), and post-FX must move to the WebGPU/TSL node pipeline. Decide once; don't mix.

---

## THE UPGRADE PATH — staged, ordered by visual-payoff ÷ risk

Each stage is independently shippable and reversible. Do them in order; hard-refresh and eyeball after each. Keep `renderer.info.render.calls` in the low hundreds and the frame smooth.

### Stage 1 — Bloom + tone (the 80/20 win)
Route rendering through an `EffectComposer` so torches, flame meshes, emissive OS screens, and the boot glow actually *bloom*. This single change moves the scene from "tutorial" to "atmospheric."
```js
import { EffectComposer }  from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }      from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass }      from 'three/addons/postprocessing/OutputPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W, H),
  0.55 /*strength*/, 0.7 /*radius*/, 0.85 /*threshold*/);
composer.addPass(bloom);
composer.addPass(new OutputPass());   // OutputPass now owns tone-map + sRGB
// loop:   composer.render();          // INSTEAD of renderer.render(scene, camera)
// resize: composer.setSize(W, H); bloom.setSize(W, H);
```
- **threshold ≈ 0.85** so only emissive/torch pixels bloom, not the stone; **strength 0.4–0.6** (tasteful).
- `OutputPass` does the tone-map/sRGB, so REMOVE the duplicate `renderer.toneMapping` work or you double-tone-map → washed out. If the scene brightened, lower exposure.
- Gate behind a `const BLOOM = true` so it's a one-line revert.

### Stage 2 — Lock the iso camera + presentation framing
- **Lock rotation** (`controls.enableRotate = false`) so a demo can't break the iso look; keep pan (`screenSpacePanning = true`) and zoom (clamp `minZoom/maxZoom`). Optionally add a slow idle **auto-rotation of the dungeon *group*** (a few degrees), not the camera, for a "living diorama."
- Add a one-key **cinematic toggle** that hides the HUD/sprites and slow-dollies, for clean screenshots/recordings.

### Stage 3 — Contact shadows / ambient occlusion (grounding)
Props and feet float slightly. Add **`GTAOPass`** (preferred in r0.170; `SSAOPass` as fallback) after `RenderPass`, before bloom, for soft darkening in crevices and under agents. Keep intensity/radius LOW (AO is easy to overdo) and put it behind an `AO = true` flag — it's the most expensive pass, so watch draw cost.

### Stage 4 — Tiles → `InstancedMesh` (perf headroom)
Today every floor/wall is a clone (fine at 24×20). Before growing the map or adding density, convert each **repeated tile type** to one `InstancedMesh` sized to its count; set each instance matrix via the single `tileToWorld` helper; keep unique pieces (throne, statues, bridge) as plain meshes. Enabling work, not a visual change — do it *after* bloom, *before* lots more tiles.

### Stage 5 — Material & texture polish
- Floor variation: 2–3 tint templates per zone + a low-strength normal/roughness map on the shared floor material so flagstones catch the moonlight.
- **Emissive "screen" materials** on OS modules with an animated `emissiveIntensity` pulse → they read as live tech and bloom from Stage 1.
- Torch life: a tiny additive flame sprite + the existing emissive mesh, jitter scale+intensity with `sin(t)+noise`.

### Stage 6 — The "OS coming online" set-piece (state-driven drama)
On an `os_build`/threshold event, tween a **boot sequence**: ramp module `emissiveIntensity`, briefly raise `bloom.strength`, shift fog/ambient cooler, pulse a ground ring. **Drive every value from state via tweens, never hard-cut.** This is the moment that sells "an OS is being built," and it's cheap once bloom exists.

### Later / optional — WebGPU
Only if a task demands it: `three/webgpu` + `await renderer.init()` + bloom as a TSL node (`three/examples/jsm/tsl/display/…`). Higher ceiling, real migration cost; not needed for a great WebGL demo.

---

## HOW THE SCENE CONNECTS TO STATE

```
game_state.py (truth) ──WS snapshot+events(:5175)──▶ index.html Three.js scene
        ▲                                                   │ reads, never writes
   mcp_server.py (agent loop, A*, ambient_life)             ▼ renders tiles/agents/lights/FX
```
The loop reconciles the scene to incoming events: move avatars toward target tiles, update HP/thought sprites, spawn `effect_added`, light up `os_build` modules. Intent that changes the world flows through server tools, not the renderer.

---

## DEFINITION OF DONE (self-check before claiming a visual upgrade)

1. Scene renders after a hard-refresh; no console errors; `renderer.info.render.calls` low hundreds; frame smooth.
2. If post-FX added: rendering goes through `composer.render()`; `OutputPass` owns tone-map/sRGB (no double tone-map); resize updates composer + every pass; a one-line revert flag exists.
3. Camera stays **orthographic iso**; rotation locked for presentation; pan/zoom clamped.
4. Geometry is `MeshStandardMaterial`; lights = ambient/hemi fill + moonlight key + a FEW flickering torches + fog; emissive things bloom.
5. All 6 agents distinct, on correct tiles, **tween** smoothly, keep their name/HP/thought sprites.
6. Ruins models all at **`scale 0.5`**; agents via **`SkeletonUtils.clone`**; corner-stone layout preserved (no new solid S/E walls that occlude interiors).
7. No game logic added to the renderer; it only reads state.
8. Anything removed is disposed; the single rAF loop intact.

## ANTI-PATTERNS (scan your own diff)
❌ `MeshBasicMaterial` on lit geometry · ❌ double tone-mapping (renderer **and** OutputPass) · ❌ per-model hand-tuned scales (use one `0.5`) · ❌ `gltf.scene.clone()` for agents (use `SkeletonUtils.clone`) · ❌ avatars snapping (tween) · ❌ Perspective camera · ❌ new solid S/E walls hiding rooms · ❌ dozens of point lights (keep torches sparse; use emissive + bloom instead) · ❌ materials/geometries created in the loop · ❌ `composer` without resize handling · ❌ touching `three/webgpu` without `await renderer.init()` · ❌ renderer mutating game state · ❌ r140-era API (`Geometry`/`THREE.Math`/`outputEncoding`).
