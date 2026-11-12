# Tripo to Unreal Engine: character workflow and milestone plan

Status 2026-11-11: research and plan only. Nothing was generated, bought, installed, or imported.
`TRIPO_API_KEY` is not set in this setup and the `tripo` CLI is not installed.

Account, read in the owner's Chrome on 2026-11-11 at <https://developers.tripo3d.ai/en/billing>: the owner's
Tripo developer account exists, with one active key named `hermesino` created 2026-11-03. Available credits
0.00, frozen 0.00, no top-up on record, no task on record. So this account carries no free API credits. A key
is shown only once, at creation, so this project needs either the stored `hermesino` key or a new key.

Every claim carries its source. `UNKNOWN` marks what the sources do not say. `OURS` marks a fact measured in our
own earlier work, recorded in [tools/comfy_char/docs/FIRST_CHARACTER_PLAN.md](../tools/comfy_char/docs/FIRST_CHARACTER_PLAN.md).

## 1. Summary

- The article describes a Tripo Studio (web UI) character route plus Claude Code driving Unreal through the
  Unreal MCP. The same character steps exist in the Tripo API, except Text to Motion, which the API docs do not
  list.
- One test character through the API costs about 145 credits (1.45 USD): P2 model with standard texture 110,
  rig 25, one preset animation 10. API credits cost 0.01 USD each and do not expire.
- The API and Tripo Studio have separate wallets. A Studio subscription does not pay for API calls.
- Tripo can rig a humanoid with Unreal Mannequin bone naming (`spec: "unreal"`). What that skeleton contains
  (root bone, twist bones, IK bones, finger count, rest pose) is UNKNOWN until we measure one file.
- The Unreal side is already solved once in our own work: Manny animations retargeted to a foreign skeleton and
  to a MetaHuman by script, with measured checks. The Tripo character plugs into that route.
- Direction of 2026-11-11: characters are realistic and period-correct. The main route is section 5.5 (route M):
  Tripo generates the body shape and the costume, MetaHuman Creator's **From Custom Mesh** tool (UE 5.8) turns
  the body into a rigged MetaHuman, and the costume becomes a garment with weights transferred from that body.
  Cost 60 to 100 credits for each character. Fab body animations reach it through Epic's retargeter.
- Risk carried over from 2026-11-07: the owner rejected a generated one-shell character because it deformed
  poorly under every rig. Tripo P2 output is the same class of mesh. Milestone 1 measures this before anything
  else is bought.

## 2. What the article does

Source: <https://www.tripo3d.ai/blog/claude-opus-5-5-tripo> (updated 2026-10-27), read in full.

| Step | What the article does | Tool |
|---|---|---|
| Setup | Empty UE5 level, Third Person feature pack, Claude Code plugin `unreal-engine-skills-for-claude-code`, UE plugins ModelContextProtocol and AllToolsets, console command `ModelContextProtocol.StartServer` | Unreal, Claude Code |
| First contact | A read-only prompt: report level name, main actors, whether a Third Person character and Player Start exist | Unreal MCP |
| 1 | One prompt builds a playable grey-box level: height-map terrain, PCG vegetation, three collectibles, HUD counter, completion state, restart | Unreal MCP |
| 2.1 | Three reference views of one character, P2 model, check quad topology (example: 27,458 faces, 25,621 vertices) | Tripo Studio |
| 2.2 | Smart UV; check islands and utilization (example 79.9 %). Saving a new UV layout can remove textures, so UV comes before texture | Tripo Studio |
| 2.3 | Texture with Remove Lighting on | Tripo Studio |
| 2.4 | Rigging: Humanoid, Skeleton Preset UE5 Mannequin, Auto Rig; check joint positions | Tripo Studio |
| 2.5 | Preview one animation, optional Text to Motion, export FBX with Export Skeleton, one animation, "Animation stay in Place" | Tripo Studio |
| 3 | Scene assets: split the environment into single assets, test one, batch the rest, retry failures one by one | Tripo CLI or API |
| 4 | Import the FBX as Skeletal Mesh. First import creates a new Skeleton; later imports use Import Only Animations on that Skeleton | Unreal |
| 5 | Replace the Third Person mesh, build an Animation Blueprint from the character's own animations, refine forest and town in small batches | Unreal MCP |

Statements in the article that matter for us:

- "A successful tool call does not necessarily mean that the level, materials, collision, or runtime result is
  correct." The result is checked in the editor after each batch.
- The article claims the UE5 Mannequin preset is "broadly compatible with the default UE5 skeleton, reducing the
  need for retargeting". It does not show a test of this. We treat it as unverified.
- The article's character uses its own Tripo animations in its own Animation Blueprint. It does not retarget
  Manny or MetaHuman animations. That part is our addition (section 5).
- The completion checklist leaves camera collision, foot sliding, collision boundaries, and frame rate untested.

Linked pages read:

- Scene workflow: <https://www.tripo3d.ai/blog/gpt-6-astra-3d-game-scene-workflow>. Order: asset list from one
  reference image, blockout from basic shapes, one hero asset as a settings test, batch generation, swap assets
  into the blockout, lighting and fog, walk test. H3.1 for hero buildings (high poly, Nanite), P2.0 for distant
  buildings and props (500 to 50,000 faces). Rules for every asset: no people, no background, flat bottom.
  Install: `npm install -g tripo-cli`; `tripo auth whoami`, `tripo account balance`.
- Smart UV: <https://www.tripo3d.ai/blog/smart-uv>. Limit 80,000 triangles or 40,000 quads.
- Rigging and animation: <https://www.tripo3d.ai/blog/rigging-animation>. Five presets: UE5 Mannequin, Mixamo,
  VRM 1.0, Unity Humanoid, ActorCore. Full-body and hand bones. Text to Motion: 1 to 10 seconds, up to five
  segments. Limits: humanoid up to 100,000 triangles, T-pose or A-pose before rigging. Studio prices: rig 20,
  Text to Motion 20, preset animations free.
- Vibe Gaming Playbook: <https://www.tripo3d.ai/tutorials/vibe-gaming>. One prompt for a browser game built in
  stages (design document first, stop after each stage). Only the top of the page was readable as text; the rest
  is UNKNOWN. It targets browser games, not Unreal.
- Unreal Bridge: the article links only a download,
  `https://tripo-public.tripo3d.ai/plugins/ue-bridge/Tripo3d_UE_Bridge-latest.zip`. Not downloaded. Its
  documentation is UNKNOWN. The Studio pricing page lists DCC Bridge under the paid plans
  (<https://www.tripo3d.ai/pricing>). Our route does not need it: the API returns an FBX file.

## 3. Tripo API reference for a game character

Base URL `https://openapi.tripo3d.ai/v3`, header `Authorization: Bearer <key>`. Every call creates a task; poll
`GET /v3/tasks/{task_id}` until `success`, then download `output.model_url`. Index of all pages:
<https://developers.tripo3d.ai/llms.txt>. All 43 doc pages were downloaded on 2026-11-11. The pages cited in this
section were read in full. The SDK, ComfyUI, Codex plugin, webhook, migration, error-code, Gaussian splat, and
image-generation pages were only searched for the terms used here.

### 3.1 Rules that apply to every call

| Rule | Source |
|---|---|
| Task states: `queued`, `running`, `success`, `failed`, `cancelled`. Poll every 1 to 2 seconds, time out at about 5 minutes | <https://developers.tripo3d.ai/en/docs/task-lifecycle> |
| Credits freeze at creation and are deducted only on success. Failed and cancelled tasks cost nothing | <https://developers.tripo3d.ai/en/docs/billing> |
| Model URLs expire after 5 minutes. Download at once | <https://developers.tripo3d.ai/en/docs/quick-start> |
| Balance: `GET /v3/account/balance` returns `balance` and `frozen` | <https://developers.tripo3d.ai/en/docs/account> |
| Usage: `GET /v3/account/usage/history` lists tasks and credits for up to 31 days | <https://developers.tripo3d.ai/en/docs/changelog> |
| Upload: `POST /v3/files`, multipart. Images JPEG or PNG up to 20 MB, models GLB, GLTF, FBX, OBJ, STL up to 150 MB | <https://developers.tripo3d.ai/en/docs/files> |
| Concurrency per account: H series 10, P series 5, image generation 1, animation 10, model processing 5, mesh operations 10. Over the limit returns HTTP 429 | <https://developers.tripo3d.ai/en/docs/rate-limits> |
| `credits_consumed`, `balance`, `frozen` are decimals, not integers | <https://developers.tripo3d.ai/en/docs/changelog> |
| Requests per minute | UNKNOWN: the page gives headers, no numbers |

### 3.2 Generation

Endpoints `POST /v3/generation/text-to-model`, `/image-to-model`, `/multiview-to-model`. `model` is required.
Sources: <https://developers.tripo3d.ai/en/docs/generation-image-to-model/p>,
<https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p>,
<https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard>,
<https://developers.tripo3d.ai/en/docs/models-and-versions>.

| Model ID | Use | Face limit |
|---|---|---|
| `P2-20260801` | Game characters and props, native quads | 48 to 50,000 triangles, or 48 to 25,000 quads with `quad: true` |
| `P1-20260311` | Low poly | 50 to 20,000 |
| `v3.1-20260211` (H3.1) | High detail, static assets | up to 1,500,000 triangles, 2,000,000 with `geometry_quality: "detailed"` |

Parameters for a character (P2):

| Parameter | Value | Note |
|---|---|---|
| `input` | `file_token`, URL, or an image task ID | PNG, JPEG, WebP; at least 256 x 256; clean background |
| `inputs` (multiview) | objects keyed `front`, `left`, `back`, `right` | Front is required, at least 2 views |
| `quad` | `true` | P2 only |
| `face_limit` | for example 12000 | Adaptive when omitted |
| `texture`, `pbr` | default `true` | PBR gives base colour, metallic, roughness, normal |
| `texture_quality` | `fast`, `standard`, `detailed`, `extreme` (8K) | `fast` needs texture version `v3.5-20260815` |
| `texture_version` | `v3.5-20260815` | Needed for `delight` |
| `delight` | default `true` | Removes baked lighting; this is the article's Remove Lighting |
| `model_seed`, `texture_seed` | integers | Same seed and input give the same mesh |
| `auto_size` | default `false` | `true` scales the model to real-world metres |
| `export_orientation` | leave unset | The docs warn: setting it before post-processing can give a wrongly oriented result with no error. Convert the orientation in the last step |

Not available on P models: `smart_low_poly`, `generate_parts`, `geometry_quality`
(<https://developers.tripo3d.ai/en/models/p2>). `generate_parts` (H series) cannot be combined with texture.

Image helpers: `POST /v3/generation/text-to-image`, `/image-to-image`, `/image-to-multiview` (10 credits, returns
front, left, back, right), `/edit-multiview` (<https://developers.tripo3d.ai/en/docs/generation-image-to-multiview>).
We have our own free image and multiview workflows in ComfyUI, so these are optional.

### 3.3 Texture, UV, retopology, parts

| Endpoint | What it does | Key parameters | Source |
|---|---|---|---|
| `POST /v3/models/texture` | New textures for an existing model | `texture_prompt` (`text`, `image`, or `images`, optional `style_image`), `pbr`, `texture_quality`, `delight`, `part_names` | <https://developers.tripo3d.ai/en/docs/models-texture> |
| `POST /v3/mesh/uv` | Smart UV: new UV layout, remaps textures, rig, and animation; returns a UV atlas preview | Input at most 80,000 equivalent triangles | <https://developers.tripo3d.ai/en/docs/mesh-uv> |
| `POST /v3/mesh/decimate` | Retopology. `v3.0`: 500 to 20,000 triangles or 500 to 10,000 quads, optional `smart_uv` | `model`, `face_limit`, `quad`, `bake` | <https://developers.tripo3d.ai/en/docs/mesh-decimate> |
| `POST /v3/mesh/segment` | Splits a model into parts (`tripo_part_N`); v2 is beta with semantic labels | `model`, `segmentation_granularity` | <https://developers.tripo3d.ai/en/docs/mesh-segment> |
| `POST /v3/mesh/complete` | Closes the holes of segmented parts | `completion_mode`: `ai_completion` or `quick_cap` | <https://developers.tripo3d.ai/en/docs/mesh-complete> |
| `POST /v3/mesh/smartsegment` | Segmentation with auto modelling from an image or a GLB | `seg_type`, `granularity`, `hint` | <https://developers.tripo3d.ai/en/docs/mesh-smartsegment> |
| `POST /v3/models/import` | Brings an external model in; returns `normalize_scale` and `normalize_translation` | GLB, GLTF, FBX, OBJ, STL up to 150 MB | <https://developers.tripo3d.ai/en/docs/models-import> |

Stylization: the v2 `stylize_model` and `refine_model` types appear only in the migration table. The official
ComfyUI node package marks both as no longer supported from 2.0.0
(<https://developers.tripo3d.ai/en/docs/comfyui-nodes>). Treat stylization through the API as not available.

### 3.4 Rigging and animation

Sources: <https://developers.tripo3d.ai/en/docs/animations-rig-check>,
<https://developers.tripo3d.ai/en/docs/animations-rig>, <https://developers.tripo3d.ai/en/docs/animations-retarget>.

| Endpoint | Parameters | Output |
|---|---|---|
| `POST /v3/animations/rig-check` | `input` (task ID, file token, or URL; GLB, FBX, OBJ, STL) | `riggable`, `rig_type` (`biped`, `quadruped`, `hexapod`, `octopod`, `avian`, `serpentine`, `aquatic`). Free |
| `POST /v3/animations/rig` | `model`: `v3.0-20260909` for humanoids (the default is still `v1.0-20240301`, so set it). `rig_type`. `spec`: `tripo`, `mixamo`, `actorcore`, `unity`, `unreal`, `vrm` (biped only). `out_format`: `glb` or `fbx` | Rigged model |
| `POST /v3/animations/retarget` | `input`: task ID of the rigged model. `animation` or `animations` (at most 5). `out_format`. `export_with_geometry` (default `true`). `animate_in_place` (default `false`) | Animated model |

Preset animations for a v3.0 biped rig: `preset:idle`, `walk`, `run`, `dive`, `climb`, `jump`, `slash`, `shoot`,
`hurt`, `fall`, `turn`. The 90+ `preset:biped:*` clips work only on the v1.0 rig, which does not offer the
`unreal` spec.

Despite the name, the retarget endpoint only applies Tripo's presets. It does not accept our own animation.

UNKNOWN in the docs:

- The bone list of the `unreal` spec: whether it has `root`, twist bones, `ik_foot_*` and `ik_hand_*` bones, and
  how many finger joints. The blog says "full-body and hand bones".
- The rest pose of the output (T-pose or A-pose) and the unit and scale of the FBX.
- How a request with several `animations` packs the clips in one FBX.
- Text to Motion and multi-stage motion: present in Studio, absent from the API reference.
- Face bones or blend shapes: no page mentions them. Assume none.

### 3.5 Format conversion and export

`POST /v3/models/convert` (<https://developers.tripo3d.ai/en/docs/models-convert>).

- Formats: `GLTF`, `FBX`, `USDZ`, `OBJ`, `STL`, `3MF`. Generation returns GLB by default.
- `with_animation` (default `true`), `animate_in_place`, `export_orientation` (`+x`, `-x`, `+y`, `-y`).
- `fbx_preset`: `blender`, `3dsmax`, `mixamo`, `bake_scale` (bakes the scale into the geometry instead of the node).
- `texture_packaging`: `embedded` or `zip` (FBX with a separate texture folder).
- `scale_factor`, `pivot_to_center_bottom`, `texture_size` (default 4096), `texture_format`, `flatten_bottom`.
- Rig and retarget can return FBX directly through `out_format`, so a convert call is needed only for the options
  in this list.

### 3.6 Prices

API price list: <https://developers.tripo3d.ai/en/pricing>. 1 credit = 0.01 USD.

| Call | Credits |
|---|---|
| P2 text, image, or multiview to 3D: no texture, standard, detailed, 8K | 100, 110, 120, 130 |
| P1 image or multiview to 3D: no texture, standard | 40, 50 |
| H series image or multiview to 3D: no texture, standard | 20, 30 |
| H series add-ons: HD texture +10, 8K texture +20, HD geometry +20, quad +5, smart low-poly +10, parts +20 | |
| Texture: fast or standard 10, HD 20, 8K 30 | |
| Convert: basic 5, advanced 10 (any of `quad`, `face_limit`, `flatten_bottom`, `texture_size`, `texture_format`, `pivot_to_center_bottom`, `scale_factor`) | |
| Retopology: v1.0 10, v2.0 30, v3.0 triangles 35, v3.0 quads 40 | |
| Smart UV 20; segmentation 40; part completion 50 (quick cap 30); smart segmentation 85 (image) or 55 (model) | |
| Rig check free; auto rig 25; animation retarget 10 for each animation | |
| Image to multiview 10; text to image 5 to 50 by model and size | |

UNKNOWN: whether `quad: true` on P2 adds the 5-credit quad add-on. The price list names it only under H series.

Account facts:

- Credits do not expire. API and Studio are billed separately. Failed tasks are not charged. Inputs and outputs
  are not used for training. Source: FAQ at <https://developers.tripo3d.ai/en>.
- Top-up through Stripe, "any amount from $1", preset amounts 50, 100, 250 USD
  (<https://developers.tripo3d.ai/en/pricing>).
- "New accounts receive free credits" (<https://developers.tripo3d.ai/en/docs/codex-plugin>). The amount is UNKNOWN.
- From 2026-12-01 the console shows USD instead of credits. API fields stay in credits
  (<https://developers.tripo3d.ai/en/docs/billing>).

Studio (web UI), for comparison (<https://www.tripo3d.ai/pricing>): Free 200 credits a month, 1 task at a time,
public models, non-commercial use; Pro 20 USD a month, 3,000 credits, private models, commercial use, DCC Bridge.
Studio costs: HD generate 15, Smart Mesh 35 (P2.0 +65), texture 10, auto rig 20.

### 3.7 Licence

Terms of service, last updated 2025-07-11: <https://developers.tripo3d.ai/en/terms>.

- Section 5.2.1: for users who use the service free of charge, Tripo retains all rights in inputs and outputs.
- Section 5.2.2: paid users "generally have all rights" in their inputs and outputs, including commercial use,
  and Tripo does not use them as training data.
- Section 3.2: outputs must not be used to build models or services that compete with Tripo.
- Outputs are not exclusive: another user can receive a similar or identical result.
- UNKNOWN: whether a model made with the free sign-up API credits counts as a free-user output. Assume it does.
  Anything that goes into the game is generated with paid credits.

### 3.8 Ways to call the API

| Way | Note | Source |
|---|---|---|
| REST from our own Python script | Recommended. We log every `task_id` and `credits_consumed` and save `task.json` beside each file | <https://developers.tripo3d.ai/en/docs/quick-start> |
| `tripo-cli` 0.9.0 (npm, Node 20+) | `tripo make hero.png --then texture,rig,convert:fbx`, `tripo balance`, `tripo usage`, `--dry-run` plans without spending, `tripo batch run` for resumable batches. Anonymous usage analytics are on by default | <https://developers.tripo3d.ai/en/docs/cli> |
| ComfyUI-Tripo 2.0.0 | Official nodes for generation, texture, rig, retarget, convert, Smart UV. Not installed here | <https://developers.tripo3d.ai/en/docs/comfyui-nodes> |
| Official SDKs | JavaScript, Python, Go, Rust, Java | <https://developers.tripo3d.ai/en/docs/sdk> |

## 4. The API call chain for one character

This replaces the article's Studio clicks. Prices are from section 3.6.

| # | Call | Body | Credits |
|---|---|---|---|
| 0 | `GET /v3/account/balance` | | 0 |
| 1 | `POST /v3/files` | The front T-pose image (and back, left, right if we have them) | 0 |
| 2 | `POST /v3/generation/image-to-model` or `/multiview-to-model` | `model: "P2-20260801"`, `quad: true`, `face_limit: 12000`, `pbr: true`, `texture_version: "v3.5-20260815"`, `delight: true` | 110 (115 if quad is charged) |
| 3 | `POST /v3/animations/rig-check` | `input: <task 2>` | 0 |
| 4 | `POST /v3/animations/rig` | `model: "v3.0-20260909"`, `rig_type: "biped"`, `spec: "unreal"`, `out_format: "fbx"` | 25 |
| 5 | `POST /v3/animations/retarget` (optional) | `input: <task 4>`, `animation: "preset:walk"`, `out_format: "fbx"`, `animate_in_place: true` | 10 |
| 6 | `POST /v3/models/convert` (only if step 4 output imports with wrong scale or axis) | `format: "FBX"`, `fbx_preset: "bake_scale"`, `export_orientation`, `texture_packaging: "zip"` | 5 to 10 |

Differences from the article: Smart UV is skipped at first, because generation already unwraps UVs
(`export_uv` defaults to `true`). It is added (20 credits) only if the UV layout puts a seam on the face.

Download every `model_url` within 5 minutes and also save the GLB of step 2, so that a failed rig does not cost a
second generation: steps 4 to 6 accept an uploaded file.

## 5. Unreal Engine side

### 5.1 Import

- FBX import options, from Epic's reference
  (<https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine>):
  Skeletal Mesh on; Skeleton empty on the first import, which creates a new one; Import Animations on when the
  file carries a clip; Convert Scene converts the FBX axes to Unreal's; Convert Scene Unit converts FBX units to
  centimetres; Import Uniform Scale scales the mesh.
- Animation-only import needs an existing Skeleton; bones are matched by name and hierarchy. The legacy FBX
  pipeline imports one animation for each file
  (<https://dev.epicgames.com/documentation/unreal-engine/fbx-animation-pipeline-in-unreal-engine>). So we request
  one preset for each retarget call until we have measured how Tripo packs several.
- OURS: the Unreal MCP importer accepts FBX and OBJ, not GLB. `SkeletalMeshTools.import_file` with
  `import_animations` on worked in UE 5.8 on 2026-11-07.
- OURS, the trap to test first: an FBX whose bone translations are in metres under a scaled root imported fine
  and then collapsed every bone onto the pelvis after retargeting (pelvis local z 1.036 against Manny's 95.9).
  The check is one number: pelvis local z of the imported skeleton must be near 90 to 100, not near 1. Tripo
  levers if it fails: `fbx_preset: "bake_scale"` and `scale_factor` in the convert call.
- Materials: check that base colour, normal, and the metallic/roughness map all arrive. OURS: a metal/roughness
  map was lost in one FBX export path before. `texture_packaging: "zip"` gives the maps as separate files.
- Character height: with `auto_size: false` the size is UNKNOWN. Measure the bounds and scale to the target
  height (Manny is about 180 cm).

### 5.2 Skeleton: Tripo, Manny, MetaHuman

What Epic documents:

- IK Rig retargeting transfers animation "between skeletons with varying numbers of bones, bone names, and
  orientations" (<https://dev.epicgames.com/documentation/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine>).
- Auto retargeting: right-click an Animation Sequence, **Retarget Animation Assets**, set the target mesh. With
  **Auto Generate Retargeter** on, Unreal creates the IK Rigs and the IK Retargeter. The templates cover "UE4 and
  UE5 Mannequins", "MetaHumans", and Stack O Bot. Chains are matched by bone name and exact names are not
  required (<https://dev.epicgames.com/documentation/unreal-engine/auto-retargeting-in-unreal-engine>).
- Retarget op stack in 5.8: the default ops are Pelvis Motion, FK Chains, Root Motion, Remap Curves, and Run IK
  Rig. FK Chains in One to One mode "typically is the best choice for finger chains". Root Motion either copies
  the source root or generates it from the target pelvis. Floor Constraint and Stride Warp adjust feet
  (<https://dev.epicgames.com/documentation/unreal-engine/retargeting-operation-stack-in-unreal-engine-5-8>).
- IK Retargeter assets can be created and batch-run from Python
  (<https://dev.epicgames.com/documentation/unreal-engine/using-python-to-create-and-edit-ik-retargeter-assets-in-unreal-engine>).
- MetaHuman: Epic ships `RTG_MH_IKRig` for MetaHuman bodies; a Retarget Pose From Mesh node can drive a MetaHuman
  from a Manny at run time, with a 2 cm offset note; the retarget component route is experimental
  (<https://dev.epicgames.com/documentation/metahuman/runtime-retargeting>).

What we measured ourselves (OURS, MyProject, UE 5.8, 2026-11-07):

- Manny (`SKM_Manny_Simple`) gives 29 retarget chains. A MetaHuman body mapped 29 of 29 and all 20 `ABP_Unarmed`
  clips passed the pose checks without correction. A foreign 52-bone skeleton with Mannequin names mapped 21
  chains and needed four corrections (root roll, sole tilt, toe direction, spine and neck line).
- So bone names alone do not make a skeleton compatible. Rest pose and bone roll decide.

Routes for the Tripo character:

| Route | How | When |
|---|---|---|
| A. Retarget (recommended) | Import with its own Skeleton. Build IK Rigs and one IK Retargeter Manny to Tripo with our scripts. Export retargeted copies of the clips we use | Default. Works whatever the Tripo skeleton contains |
| B. Shared skeleton | Import the Tripo mesh onto Manny's Skeleton asset, so every Manny animation and Animation Blueprint plays directly | Only if the bone list and hierarchy equal Manny's. This is the article's "reduces retargeting" claim. Test once in milestone 1, do not rely on it |
| C. Run-time retarget | Retarget Pose From Mesh node from a hidden Manny or MetaHuman | Later, for many characters sharing one Animation Blueprint |

The link to the animation training: animations are authored and trained on Manny or the MetaHuman. Each new clip
reaches a Tripo character through the same IK Retargeter (route A, batch export) or live (route C). The direction
Tripo to Manny also works through a second retargeter, if a Tripo preset is worth keeping.

### 5.3 What breaks, and the check for each

| Area | Failure | Check |
|---|---|---|
| Scale | Bones collapse after retarget when the FBX is in metres under a scaled root (OURS) | Pelvis local z near 90 to 100 |
| Root bone | No `root`, or a rolled root: root motion and body lean go wrong (OURS: 24.6 degrees lean against Manny's 8.2) | Bone list; pelvis-to-head angle in idle against Manny |
| Root motion | Clips with travel run ahead of the capsule (OURS: 12 m for each loop) | `animate_in_place: true` for Tripo presets; root track check for retargeted clips |
| Twist bones | If the Tripo rig has no `upperarm_twist`, `lowerarm_twist`, `thigh_twist`, `calf_twist`, forearms and shoulders pinch when they rotate. Retargeting ignores unmapped bones | Bone list; forearm roll test pose |
| IK bones | `ABP_Unarmed` ends in `CR_Mannequin_FootIK`, built for Manny's `ik_foot_*` bones. On a skeleton without them it reversed a foot and crouched the jog (OURS) | Set the node's alpha to 0, or add virtual IK bones |
| Fingers | Fewer joints or fused finger geometry | Bone list; fist pose close-up. Map finger chains FK One to One |
| Face | No face rig: no blinking, no speech | Accept for stylized characters. A talking hero stays a MetaHuman |
| Feet | Tilted soles and splayed toes after auto-align (OURS: 10 to 12 degrees) | `ue_check_anims.py`: sole tilt and toe yaw against Manny |
| Skin weights | Shirt drags, elbows crease, shoulders collapse on a one-shell mesh (OURS) | Share of edges stretched over 30 % in the standard test pose: our Rigify result 2.95 %, ActionForge 4.39 % |
| Clothing | Painted-on clothes cannot move apart from the body | Visible in the play video only |
| Evaluation | Clip checks miss Animation Blueprint effects (OURS) | Measure the character in play, not only the assets |

### 5.4 What the Unreal MCP can automate

OURS, from the 2026-11-07 work in MyProject and the 2026-11-09 work in NitraHrad. The Unreal MCP tool list was
not queried on 2026-11-11, because the castle session is using the editor.

| Task | Through the MCP or script | Needs the editor UI or the owner |
|---|---|---|
| FBX import of mesh, skeleton, animation | `SkeletalMeshTools.import_file` | |
| Bounds, bone list, triangle count | Mesh tools, Python | |
| IK Rigs, IK Retargeter, batch retarget, pose corrections | Python through Remote Execution (`ue_py.py`, `ue_retarget_setup.py`, `ue_retarget_run.py`). The MCP itself cannot `import unreal` | Remote Execution must be on. In NitraHrad it is UNKNOWN (no setting found in `Config/`) |
| Character Blueprint, input, camera | `BlueprintTools.write_graph_dsl` | The DSL cannot declare Enhanced Input events |
| Animation Blueprint pin values | `set_pin_value` | Building a new state machine is not tested through the MCP |
| Thumbnails, viewport captures, play frames, play video | `CaptureAssetImage`, `CaptureEditorImage`, `ue_record_play.py` | |
| Saving | `save_assets` with explicit paths. An empty list saves every dirty asset | |
| Third Person feature pack | UNKNOWN through the MCP | **Add** > **Add Feature or Content Pack** |
| MetaHuman cloud auto-rig | Script | The owner signs in once |
| Hand test with keyboard and mouse, and the verdict on how it looks | | Owner |

### 5.5 Realistic character: Tripo shape on a MetaHuman rig (route M)

Owner's direction of 2026-11-11: the character must be realistic and period-correct, fitted onto a MetaHuman,
well rigged, and able to play animations from Fab. Route M answers that. It does not use the Tripo rig: Tripo
supplies the shape and the costume, and the MetaHuman supplies topology, skin weights, face rig, and skeleton.

What Epic documents:

- UE 5.8 added **Import** > **From Custom Mesh** in MetaHuman Creator: "Convert any human character mesh with
  arbitrary topology into a fully-rigged MetaHuman in a single workflow", head and body in one step, "ideal for
  characters created from scans, external GenAI/DCC tools". Limit: "humanoid characters only; the resulting
  character will adopt the MetaHuman topology and rig"
  (<https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine>).
- Input rules of the tool
  (<https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine>):
  A pose, human proportions, static or skeletal mesh, one connected component, no holes, no stray vertices. The
  solver does not repair meshes. A textured source helps the face trace. Tight clothing gives plausible results;
  loose clothing "produces a body fitted to the clothing silhouette", so robes, coats, and folds must not be on
  the body mesh. Fingers and toes are the hardest areas and often need keypoints.
- Steps of the tool: load the mesh into **Full Character**, **Auto Solve**, add keypoint correspondences where
  the fit misses, solve again; manual order is **Trace Facial Features**, keypoints, **Body Solve**, **Head
  Solve**, **Refine Vertices**. The output is standard MetaHuman topology in the MetaHuman A pose with the
  proportions of the source. The source texture is not transferred.
- Rigging and assembly run from Python: `conform_to_target_meshes`, `request_auto_rigging` (cloud; "the editor
  must be signed in to an Epic account with MetaHuman Cloud access"), `build_meta_human`
  (<https://dev.epicgames.com/documentation/metahuman/metahuman-creator-python-scripting-in-unreal-engine>).
  5.8 also ships a MetaHumanGenerator toolset for the Unreal MCP server; its tool list is UNKNOWN until queried.
- Clothing: a MetaHuman wears a Chaos Outfit (parametric, resizes with the body) or a Skeletal Mesh (fixed size)
  (<https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items>). A cloth asset is
  built from a plain render mesh; the **TransferSkinWeights** Dataflow node copies the skin weights from the
  MetaHuman body mesh, and "skinning is not required" on the garment itself
  (<https://dev.epicgames.com/documentation/metahuman/building-a-metahuman-parametric-outfit-with-a-render-mesh>).
  Tearing at armpits and thighs is corrected with a painted weight map.
- Animations: all MetaHumans share one skeleton. Body clips made for Manny reach a MetaHuman through an IK
  Retargeter (auto retargeting has a MetaHuman template; section 5.2) or at run time through Retarget Pose From
  Mesh, as in Epic's Game Animation Sample
  (<https://dev.epicgames.com/documentation/en-us/unreal-engine/adding-a-metahuman-to-the-game-animation-sample-project-in-unreal-engine>).
  MetaHumans assembled in 5.6 or later have no +2 cm floor offset; a -2 offset lines them up with Manny
  (<https://dev.epicgames.com/documentation/en-us/metahuman/base-skeleton-offset-update>).
- Compatible Skeletons share clips without retargeting only between "nearly identical skeleton hierarchy
  structures and naming conventions" with similar proportions
  (<https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletons-in-unreal-engine>). We do not rely on
  it for Manny and MetaHuman.

OURS: a MetaHuman body mapped 29 of 29 retarget chains and all 20 `ABP_Unarmed` clips passed the pose checks
without correction (MyProject, UE 5.8, 2026-11-07). That result is why route M carries the lowest rig risk.

The procedure, one character:

| # | Step | Tool | Cost | Check before the next step |
|---|---|---|---|---|
| 1 | Period brief: who, which century, which garments, from sources on Nitra | CREW OS, owner approves | 0 | Owner's yes on the brief |
| 2 | Two images of the same person, A pose, front and back, plain background: (a) body in a tight underlayer, hands open, feet apart; (b) the same body in the full costume | Our ComfyUI | 0 | Part-by-part look at both; same proportions in (a) and (b) |
| 3 | Body mesh from (a): `multiview-to-model`, H3.1, standard texture. Quads and P2 are not needed, because the topology is replaced | Tripo API | 30 credits | In Blender: one component, no holes, fingers separate, height scaled to the brief |
| 4 | Dressed mesh from (b), same settings | Tripo API | 30 credits | Same proportions as step 3 within a tolerance we set after the first measurement |
| 5 | Split the costume from the dressed mesh: `POST /v3/mesh/segment`; a manual cut in Blender is the free fallback | Tripo API or Blender | 40 credits or 0 | Each garment is its own mesh, with no body faces left inside |
| 6 | Clean in Blender: fill holes, remove stray vertices, export the body as OBJ or FBX in centimetres | Blender MCP | 0 | Vertex count; one connected component |
| 7 | **From Custom Mesh**: **Full Character**, **Auto Solve**; keypoints for fingers and toes; solve again | MetaHuman Creator in MyProject | 0 | Overlay of the MetaHuman mesh on the source; surface distance by region |
| 8 | Skin, eyes, teeth, hair from the MetaHuman tools; face likeness judged against image (a) | MetaHuman Creator | 0 | Difference list against the image; owner sees the face |
| 9 | Auto-rig and assemble | `request_auto_rigging`, `build_meta_human`; the owner signs in to Epic once | 0 | Skeletal mesh on the MetaHuman skeleton; face rig present |
| 10 | Fit the garments to the conformed body in Blender (offset, no intersections, clearance at armpits and between thighs) | Blender MCP | 0 | Zero body faces showing through in A pose |
| 11 | Garment to cloth asset: **TransferSkinWeights** from the conformed body, then Outfit Asset and wardrobe item. Hats, belts, and weapons are static meshes on sockets | Dataflow Editor | 0 | Standard test pose: stretched-edge share, clipping count by region |
| 12 | Animations: batch retarget of the 20 Manny clips with our scripts and Epic's MetaHuman retargeter | `ue_retarget_run.py`, `ue_check_anims.py` | 0 | Lean, sole tilt, toe yaw, neck line against Manny |
| 13 | One Fab pack on the same retargeter | Fab, a free pack first | 0 | Same checks; listing's skeleton and licence recorded |
| 14 | Play test and video: idle, walk, run, jump; close-ups of face, hands, feet, costume | `ue_record_play.py` | 0 | Difference list; owner's hand test |

What "all Fab animations work" means, stated without overclaiming:

- A body clip authored for the UE5 Manny or Quinn skeleton, or for the UE4 Mannequin, retargets to a MetaHuman
  with Epic's shipped assets. Each Fab listing names its skeleton; read it before download.
- Clips that need checking one by one: root motion with travel, two-handed weapons and props (hand IK targets),
  mounted or paired animations, and clips that rely on a pack's own Animation Blueprint or Control Rig.
- Facial animation is a separate track on the face rig. Body packs do not contain it.
- A paid pack is priced and approved before purchase, and its licence is read first.

What is UNKNOWN in route M until M1 measures it:

- How well **Auto Solve** fits a Tripo body, mainly hands and feet.
- Whether segmentation returns a clean garment, or whether the cut is done by hand in Blender.
- How a generated garment deforms with transferred weights: long skirts, cloaks, and sleeves are the risk. Chaos
  cloth simulation is the lever if skinning alone is not enough.
- Whether **From Custom Mesh** needs the Epic sign-in. The auto-rig does.
- Whether a face made this way reaches the likeness of the concept image. The texture is not transferred, so
  the skin comes from the MetaHuman tools.

The heroes, owner's idea of 2026-11-11 (the setting is not decided): Cyril and Methodius reincarnated as two
heroes in the present day. The world around them may later move to a Renaissance, fantasy, or cyberpunk
variant.

- Route M fits this idea: each hero is one MetaHuman body and face, made once. Each setting is a set of wardrobe
  items on that same body, so a new setting costs garments (30 to 70 credits for each costume), not a new
  character.
- Present-day clothing (trousers, shirt, jacket) is close-fitting, so the first hero in present-day dress is the
  low-risk first run of the 14 steps. Long robes come later, as a costume variant with cloth simulation.
- Faces: no portrait from the 9th century exists. The heroes may echo the statue under the castle, which is an
  artistic reading of 1990 (Ľudmila Cvengrošová), not a historical source. The owner approves the two concept
  faces in step 2.
- Two heroes share the step chain; the second repeats steps 2 to 14 with the settings found in the first.

The statue of Cyril and Methodius under the castle is a static scene object, not a character. It is modelled in
Blender from photographs and drone frames by the reference-fidelity method, then imported as a static mesh. It
is not generated, because it is a real object that must match. It belongs to the town build, and no work on it
starts from this plan.

Route M against the Tripo rig (routes A and B of section 5.2):

| | Route M: MetaHuman rig | Routes A, B: Tripo `unreal` rig |
|---|---|---|
| Skin weights, twist bones, fingers | Epic's, measured by us | UNKNOWN until measured |
| Face rig, speech, blinking | Yes | No |
| Clothing | Separate garment with transferred weights | Painted onto the body shell |
| Animation from Fab | Epic's retargeter, 29 of 29 chains | Our own retargeter, corrections likely |
| Cost for each character | 60 to 100 credits | 135 credits |
| Fits | Realistic humans | Stylized figures, creatures, crowd extras |

## 6. Where Tripo fits beside what we already have

| Need | First choice | Why |
|---|---|---|
| Realistic period human: hero, named NPC | Route M (section 5.5): Tripo body and costume on a MetaHuman rig | Owner's direction of 2026-11-11; 29 of 29 chains, passes checks without fixes |
| Stylized figure, crowd extra | Tripo P2 with `unreal` rig, if the M1 comparison passes | Quad mesh made for rigging; 1.35 USD for each character |
| Creature (four legs, wings, snake, fish) | Tripo rig v2.5 or v3.0 non-biped | We have no other creature rig. Only a walk or march preset exists for each type |
| Props and set dressing | Tripo H3.1 (30 credits) or our free ComfyUI TRELLIS graph | Static meshes have no deformation risk |
| Body animation | Epic's Manny set and our trained clips, retargeted | Free, already measured |
| Castle geometry | The survey build in NitraHrad | Never replaced by generated meshes |

## 7. Milestones

Each milestone ends with a difference list, the named artifact, and a git tag. A failed check selects the next
design; it does not end the work. No paid call runs before the owner has seen its price and the balance.

Versioning: scripts, documents, task logs, and measurement reports live in git under `tools/tripo_char/`.
Generated models and Unreal assets are large binaries; where they live is open decision 6.

### M0. Plan (this document)

- Artifact: `docs/TRIPO_UE_WORKFLOW.md`.
- Cost: 0.
- Closes with: the commit of this file on branch `docs/tripo-ue-workflow`; tag `tripo-m0-plan` after the owner
  has decided section 8.

### M1. One test character, end to end

Goal, revised 2026-11-11 after the owner's direction: one realistic period character, shaped and dressed by
Tripo, runs on the MetaHuman rig in Unreal and plays the 20 Manny clips and one Fab pack. The procedure is the
14-step table of section 5.5; each step ends with its check and a commit of the report.

Sub-tags, so each proven step is versioned: `tripo-m1a-body` (steps 1 to 6), `tripo-m1b-metahuman` (7 to 9),
`tripo-m1c-costume` (10 and 11), `tripo-m1d-animation` (12 to 14).

Cost of route M: 60 credits with a manual garment cut, 100 with API segmentation. One regeneration adds 30.

Comparison branch, optional, 135 credits, only if the owner wants it: the Tripo `unreal` rig on a P2 mesh, by
the steps listed next. It removes the UNKNOWNs of section 3.4 and tells us whether crowd extras can skip the
MetaHuman. Steps 1 to 3 (key, script, balance and approval) apply to both branches.

Steps of the comparison branch:

1. The owner creates the Tripo API account and key himself and puts the key into a gitignored `.env` as
   `TRIPO_API_KEY`. Claude never types a key.
2. Write `tools/tripo_char/tripo.py`: balance, upload, create task, poll, download, with a `--dry-run` that
   prints each call and its price. Test it with a fake server first. Every real run writes `task.json` with
   `task_id` and `credits_consumed`.
3. Read the balance. Show the owner the balance, the planned calls, and the total. Wait for his yes.
4. Input image: `concept_v2_00003_.png`, the T-pose with spread fingers that already exists. It makes the result
   comparable with the TRELLIS character. Cost 0.
5. Run the chain of section 4, steps 0 to 4. Stop after step 2: inspect the GLB part by part (face, hands, feet,
   back) in a viewer and write the difference list against the image. The owner decides whether to rig it.
6. Measure the rigged FBX before Unreal: bone list, hierarchy, rest pose, units, finger joints, twist and IK
   bones. Write `reports/m1_skeleton.md`. This removes the UNKNOWNs.
7. Check machine load and the compute locks. Import into Unreal (open decision 5 names the project). Checks:
   height, pelvis local z, three texture maps present.
8. Route B test: import a copy onto Manny's Skeleton. Record whether Unreal accepts it and whether `MM_Idle`
   plays without distortion. One attempt, no fixing.
9. Route A: `ue_retarget_setup.py` and `ue_retarget_run.py` for Manny to Tripo. Run `ue_check_anims.py` on the
   20 clips. Foot IK node alpha 0.
10. Deformation: the standard test pose, share of edges stretched over 30 %, by region, beside the 2.95 % and
    4.39 % of the earlier rigs.
11. Optional, 10 credits: one `preset:walk` retarget in FBX, to learn how Tripo delivers a clip.
12. Play test in the test level with `BP_AgoraChar` input and camera. Record the play video with
    `ue_record_play.py`: idle, jog, jump, and a close-up of feet and hands.

Artifacts: `m1_skeleton.md`; the check table from `ue_check_anims.py`; the deformation table; the play video;
`task.json` files with the credits spent; the owner's hand test.

Cost of the comparison branch: 135 credits (1.35 USD) without the preset clip, 145 with it, 150 if quad is
charged. One regeneration adds 110. Cap for M1, both branches: 300 credits (3.00 USD). Suggested top-up: 5 USD.

Pass, route M: all 20 clips within our existing limits (lean, sole tilt, neck), no collapsed or reversed bone in
play, no body showing through the costume in the test poses, and the owner's verdict on the video. A missed
check selects the next design for that step (keypoints, manual solve, cloth simulation, a hand-cut garment).

Closes with: tag `tripo-m1-test-character`.

### M2. Character set

Goal: the cast the game needs, on one shared pipeline.

Steps:

1. CREW OS brief for the cast: roles, style, proportions. The owner approves the list and the style.
2. Concept images in our own ComfyUI (free), front T-pose plus back and side views; the owner picks from four
   for each character.
3. `tools/tripo_char/batch.yaml` with one row for each character. Generate one, inspect, then the rest. Retry
   failures one by one.
4. One IK Retargeter for each distinct skeleton; if all bipeds share the Tripo `unreal` skeleton, one retargeter
   and one skeleton serve all of them.
5. One creature as a rig test (`rig_type` from rig-check), with its walk preset.
6. Each character passes the M1 checks and gets a turntable and a play video.

Cost: 135 credits for each humanoid, about 145 for a creature with one preset. Six characters: about 820
credits (8.20 USD); with a 50 % retry reserve about 12 USD.

Closes with: tag `tripo-m2-character-set`.

### M3. Courtyard restyle

Starts only when the castle session reports the courtyard complete. The survey level is never edited.

Steps:

1. The owner picks the style: fantasy, futuristic, or other. One reference image for the courtyard.
2. Duplicate the level (or use a data layer) as `NitraHrad_<style>`. The survey geometry stays the collision and
   scale reference.
3. Asset list from the reference image, by the scene article's method: hero pieces, props, distant silhouettes;
   which parts are only material and light changes on the existing walls.
4. One hero asset as the settings test (H3.1, 30 credits; Nanite), then the batch. Rules: one object, no
   background, flat bottom. Our free ComfyUI graph is tried first for simple props.
5. Place in small batches through the MCP; after each batch a capture from fixed cameras and a difference list.
6. Lighting, sky, fog for the style. Walk test along the planned route; fix blocked paths and floating objects.

Artifacts: asset table with task IDs and credits; before and after captures from the same cameras; a walk video.

Owner's direction of 2026-11-11: the period look and the real Nitra come first. The town is assembled as it
was; colour and light are adjusted afterwards "as needed". So M3 is a grade of the survey build, not a
replacement: materials, light, fog, and period props that sources support. The candidates listed next stay as
ideas for a later variant, and nothing in them overrides the survey geometry or the period.

Style candidates, none decided.

| Candidate | Status |
|---|---|
| Stylized fantasy village | The owner's idea of 2026-11-11 ("to je len napad"), one reference image |
| Futuristic | Named by the owner, no reference yet |
| Other | Open |

Candidate "stylized fantasy village". Reference:
`C:\Users\Danculus\blender-fidelity\subjects\nitra-drone\reference\style\podhradie_style_idea_20261111.webp`,
meant for the podhradie (the area below the castle). Seen in the image: a wide paved street of large stone slabs
with grass in the joints; two-storey half-timbered houses with cream plaster, dark beams, red tile roofs, dormers,
tall chimneys, and ivy; a small church with a clock and a cross closing the street; market stalls with striped
and plain awnings, a broken cart, barrels, crates, wheels, clay pots, fruit and vegetable displays; dark blue
bunting across the street; birds; a pale grey-green hazy sky; soft warm light with long soft shadows. Shapes are
slightly exaggerated and the textures look hand-painted, with little fine detail and no visible specular shine.

What this look needs from Tripo:

- Props in one consistent style: stalls, awnings, carts, barrels, crates, wheels, pots, produce displays, bunting
  posts, lanterns, signs. About 20 to 30 unique props, repeated with rotation and scale.
- The API has no stylize call (section 3.3). Consistency therefore comes from the inputs: every reference image
  is drawn in one style by our own ComfyUI workflow, with one fixed style sentence and palette, before any Tripo
  call. One prop is generated and judged before the batch.
- `delight: true` with texture version `v3.5-20260815`, so no baked light fights the scene light. For a prop
  whose texture drifts, `POST /v3/models/texture` with `texture_prompt.text` and one shared `style_image`
  (10 credits).
- P2 for props (clean low-poly shapes suit the look; 110 credits) or H3.1 with `smart_low_poly` (40 credits).
  Which one holds the style better is UNKNOWN; the first prop is made both ways and compared (150 credits).
- Characters in the same style: stylized proportions from the same concept workflow, P2 with the `unreal` rig,
  through the M1 and M2 pipeline. A MetaHuman beside these would not fit the look, so this candidate moves the
  hero to a Tripo character and depends on M1 passing.
- Half-timbered houses and the church are not Nitra's buildings. Two ways, the owner chooses: keep the survey
  buildings and restyle only their materials, or dress their fronts with generated facade pieces. Generated whole
  houses would replace the survey geometry, which the plan does not allow.

What this look needs from Unreal:

- Materials: one master material for the whole scene, with roughness high and near constant, no metallic,
  weak normal maps, a shared colour tint and saturation control. Hand-painted base colour carries the detail.
  Plaster, timber, roof tile, and paving as tiling materials on the survey walls and ground.
- Ground: the slab paving as a material on the terrain mesh, grass tufts in the joints placed by PCG or foliage.
- Lighting: a low warm Directional Light with soft shadows, Sky Atmosphere and Sky Light, light Exponential Height
  Fog with a grey-green tint so the far end of the street fades, as in the scene article's lighting step.
- Post Process Volume: slightly lifted shadows, muted contrast, warm tint; no film grain or lens effects.
- Foliage: stylized trees and ivy with simple leaf cards and a wind animation.
- Small life: birds as a Niagara effect, bunting with a simple wind sway.
- Nanite and Lumen stay usable; the look comes from materials and light, not from a custom toon shader.

Cost: 30 credits for each static asset. Thirty assets: 900 credits (9 USD); 8K texture adds 20 for each.

Closes with: tag `tripo-m3-courtyard-<style>`.

### M4. The game (outline only)

Built last, on real results from M1 to M3.

- Vertical slice first, as in the article: one route through the courtyard, one goal, three collectibles, HUD
  counter, completion state, restart.
- Third Person template logic, our Character Blueprint, the M2 cast as player, NPCs, and enemies.
- Then, in separate small steps: camera collision, foot sliding, collision boundaries, frame rate, save and load,
  menu, sound, packaging.
- Each step ends with a recorded play video and a tag `game-v0.x`.

## 8. Open decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| 1 | API credits or a Studio subscription | API, pay as you go: 5 USD covers M1 with a reserve, credits do not expire, and scripts can run it. Studio Pro costs 20 USD a month and its credits cannot pay for API calls |
| 2 | Model for the test character | P2 with quads (110 credits). It is the model the article uses and the one made for rigging |
| 3 | Skeleton spec | `unreal`, rig model `v3.0-20260909` |
| 4 | Test subject | The existing `concept_v2_00003_.png`, so the result compares directly with the rejected TRELLIS character |
| 5 | Unreal project for M1 and M2 | MyProject. It holds Manny, the MetaHuman, the retarget scripts, the test level, and Remote Execution. NitraHrad stays untouched for the castle session; characters migrate there in M3 or M4 |
| 6 | Where the binaries are versioned | Scripts and reports in git now. A private GitHub repository with Git LFS for the Unreal game project, created at M3. Until then models stay in a dated local folder outside Temp |
| 7 | Role of Tripo characters | Directed 2026-11-11: realistic period characters through route M (Tripo shape and costume, MetaHuman rig). The Tripo rig stays for creatures and, if the comparison branch passes, crowd extras |
| 8 | Animations | Epic's Manny set and our trained clips through the retargeter. Buy one Tripo preset in M1 only to learn the format |
| 9 | Courtyard and podhradie style | Directed 2026-11-11: period-correct and real first, assembled before any grading; colour and light adjusted afterwards. The candidates in M3 are ideas for a later variant |
| 11 | First character | Owner's idea of 2026-11-11: Cyril and Methodius reincarnated as present-day heroes. We recommend the first hero in present-day dress as the M1 character. A garrison soldier of 1663 to 1674, a bishop of the 1730s, and a townsperson stay as later period NPCs |
| 13 | Setting of the game world | Open by the owner's word: Renaissance, fantasy, or cyberpunk. It changes costumes and the M3 grade, not the characters' bodies or rigs, so M1 does not wait for it |
| 12 | Run the comparison branch (Tripo rig, 135 credits) in M1 | Not now. Route M first; the branch is bought only if crowd extras are needed |
| 10 | Free sign-up credits | Use them for the M1 test if they exist; generate everything meant for the game with paid credits (section 3.7) |

## 9. Sources not reached

- The body of the Vibe Gaming Playbook page beyond its first screen.
- Any documentation of the Tripo Unreal Bridge plugin.
- The two other blog posts linked under "Continue Reading" (a Unity and Blender game build, and a P2 against
  Claude comparison). They do not describe a step of this workflow.
- The live tool list of the Unreal MCP in NitraHrad.
