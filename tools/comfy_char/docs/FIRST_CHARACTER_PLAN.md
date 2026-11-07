# First character: plan

Status 2026-11-06: the workflows are installed and checked. No character has been generated.
Findings and sources: [XRAY_LEDGER.md](XRAY_LEDGER.md).

## Round 1 results, 2026-11-07

Concept: `AGORA_CHAR_01_concept`, 919 s, 4 images, GPU total peak 23.0 GB. Image 3 chosen (horizontal arms,
separated fingers). Mesh: `AGORA_CHAR_02_character`, 150 s. Outputs: `C:\ComfyUI\output\agora_char\`.

| Check | Result | Evidence |
|---|---|---|
| Triangles | PASS, 11,911 | `check_glb.py` |
| Maps | PASS, 4 maps at 2048 | `check_glb.py` |
| Closed mesh | FAIL, but small: 2 boundary edges, 31 non-manifold edges, 2 floaters of 12 and 14 faces at button height | trimesh edge count |
| Fingers | FAIL: thumb and index separate, middle, ring, and little finger fused | Blender close-ups |
| Face texture | FAIL: a chart seam runs down the middle of the face, the mouth halves do not line up | Blender close-up |
| Body, clothing, boots, back | Shape and colours follow the source; back is plausible | Blender front/back/side |

Where the fingers are lost, measured by saving each stage:

| Stage | Fingers | 
|---|---|
| Raw TRELLIS mesh (node 46, 5.9 M faces) | all five separate |
| `RemeshMesh` udf, 768, band 1.0, smooth 20 (baseline) | fused |
| same at 1024 | fused |
| udf band 0.5 | arms dropped, 92 components |
| sdf | arms dropped, 96 components |
| no remesh, decimate raw directly | mesh shredded, 173 components |
| udf at 2048 | fused, plus texture blotches on the back |

`RemeshMesh` in udf mode offsets the surface by the band, so the narrow gaps between glove fingers close. The
raw mesh is not usable without it. Next designs, one at a time: a concept prompt with fingers spread wide
(bigger gaps survive the offset), or accept mitten hands and rig with fingers off.

## Round 2 result, 2026-11-07: concept v2, wide-spread fingers

Input `concept_v2_00003_.png`, same graph, 90 s, GPU total peak 12.5 GB. Output `C:/ComfyUI/output/agora_char/v2/`.

| Check | Result |
|---|---|
| Triangles | 11,922 |
| Components | 1 (round 1: 3) |
| Open edges | 0 boundary, 22 non-manifold (round 1: 2 and 31) |
| Fingers | PASS: five separate fingers on both hands |
| Face | no split seam this time; blurry, mouth slightly uneven, faint vertical line at the nose |
| Defects | light texture slivers between fingers, an orange spot on the back of the left glove, a hair bun on the back that the front-only source does not show |

The fix was the input image, not a node setting: gaps wide enough survive the `RemeshMesh` udf offset.
Graph: [workflows/AGORA_CHAR_02_character_v2_api.json](../workflows/AGORA_CHAR_02_character_v2_api.json).

## Round 2b, 2026-11-07: normal map and Unreal

- In Unreal the round 2 mesh showed black triangular patches on the shirt, nose, hair, and boots. A
  two-sided material did not remove them and flipping the normal map green channel made shading worse,
  so both were reverted. Blender showed the same patches on the pocket: the defect was in the baked
  normal map (0.56 % of texels with z below 0.3).
- `BakeNormalMapFromMesh` `cage_distance` 0.05 to 0.1 removed the patches in Blender and in Unreal.
  Fingers stay separate. All workflows now use 0.1.
- Unreal import: the MCP importer accepts FBX or OBJ, not GLB. Exported FBX from the owner's Blender.
  Assets saved in `/Game/AgoraChar/` (`SM_AgoraChar_v2b` is current). Scale 1.8 gives 180 cm when the
  FBX is exported without unit scaling. The metal/roughness map does not survive the Blender FBX export
  (it passes through a Separate Color node); base colour and normal do.
- A test actor `AGORA_CHAR_TEST_v2b` stands in the open level `L_Tomb_S03_Ambience` at (1800, 0, 90).
  The level is NOT saved; the owner decides whether to keep or delete the actor.
- Screenshots: `agora_output/reverse/yt_bEiW6L7Y7NM/unreal/` (local only).
- Unreal MCP client used while the session's connector stayed stale: [uemcp.py](../uemcp.py).

## Rig comparison, 2026-11-07 (in progress)

Same mesh (`v2_cage010`), same test pose from [pose_test_blender.py](../pose_test_blender.py): arms 60 degrees
down, elbows 90 degrees forward, left leg 45 degrees forward with the knee at 60 degrees, fingers curled.

**Rigify** (owner's Blender, `agora_output/reverse/yt_bEiW6L7Y7NM/blender/char_rig_compare.blend`):
- Metarig fitted from measured mesh sections; palms face forward, so arm and finger rolls are turned 90 degrees.
- Heat weights straight on the GLB failed on 128 vertices and tore the trousers: the glTF import splits the
  mesh along UV seams into hundreds of pieces (largest 300 faces). Fix: voxel proxy (5 mm, decimated to 40k,
  loose bits removed), heat weights on the proxy (0 unweighted), Data Transfer to the character.
- Result: no tears, fist closes, knee folds plausibly, inner elbow creases into facets at 90 degrees.
  73 deform bones, five 3-joint fingers per hand.

**ActionForge** (Chrome, actionforge.app):
- Network watch: upload, rig, finger detection, and bind made GET requests to actionforge.app only
  (page assets, the MediaPipe hand model, `rig-human.glb`) plus local `blob:` and `data:`. No POST, no upload.
- Dots placed by hand with mirror off: the centre dots stayed locked off the body's midline with mirror on.
- Detect Fingers failed: left hand read in 1 of 10 views, right in 0 of 10 (dark gloves). Finger bones stay
  guessed, bunched in the palm, short of the fingertips.
- Bind: 10,317 vertices weighted to 48 bones in 0.4 s. The idle clip plays with no visible tearing.
- Not yet compared in the same test pose: needs the "Character only (rest pose)" GLB export, which is a
  file download and waits for the owner's approval.

## The chain

| Stage | Tool | Our model | Output |
|---|---|---|---|
| Concept | ComfyUI, `AGORA_CHAR_01_concept` | Qwen-Image 2512 | 4 front T-pose images |
| Side and back check (optional) | ComfyUI, `BLENDER_REF_03_multiview_api` | Qwen-Image-Edit 2511, Multiple Angles LoRA, Lightning | Other views of the same design |
| Mesh + textures | ComfyUI, `AGORA_CHAR_02_character` | TRELLIS.2, DINOv3, BiRefNet | 12,000-triangle GLB, 4 maps |
| Prop (optional) | ComfyUI, `AGORA_CHAR_03_prop` | same | 2,000-triangle GLB |
| Check | `tools/comfy_char/check_glb.py` | | PASS or FAIL with numbers |
| Prop in the hand | The owner's Blender window, through the MCP | | Combined GLB |
| Rig + animation | ActionForge, in the browser | | GLB or FBX with clips |
| Game | Unreal 5.8, agent 66 | | Playable character |

## Before the first run

Five model files are missing, 8.96 GB in total. C: has 29 GB free, so about 20 GB stay free.

| File | Folder under `C:\ComfyUI\models` | Size | Source |
|---|---|---|---|
| `trellis_2_int8_convrot.safetensors` | `diffusion_models` | 5.25 GB | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2) |
| `trellis_2_shape_vae_bf16.safetensors` | `vae` | 1.10 GB | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D) |
| `trellis_2_texture_vae_bf16.safetensors` | `vae` | 0.95 GB | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D) |
| `dino_v3_L_naf_fp32.safetensors` | `clip_vision` | 1.22 GB | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D) |
| `birefnet.safetensors` | `background_removal` | 0.44 GB | [Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet) |

ComfyUI itself is not running and must be started with `run_comfyui.cmd`. GPU rules for the run:
check the queue and locks first, never fall back to CPU, and lower the priority of the real child process
([[long-training-runs-at-idle-priority-beside-trading-bots]]).

## Steps

**Round 1: technical test.** The subject is a neutral field engineer, with no weapon and no CREW cost. It
proves the chain before anyone spends on design.

1. Download the five files.
2. Run `AGORA_CHAR_01_concept`, 4 images. The owner sees them with a written difference list and picks one.
3. Copy the chosen image to `C:\ComfyUI\input\agora_char_input.png`.
4. Run `AGORA_CHAR_02_character`. Record the time and the peak VRAM.
5. Run the checker:

   ```bash
   C:/ComfyUI/venv/Scripts/python.exe tools/comfy_char/check_glb.py <final.glb> --target 12000
   ```

6. Open the GLB in the owner's Blender window through the MCP. Render front, back, both sides, and hands.
   Compare each part with the source image. Only the owner can call it a match.
7. In ActionForge, choose **+ Unrigged model** and load the GLB. Place the dots, set height 1.80 m, turn on
   **Mirror Left and Right**, set **Fingers** to Five, click **Detect Fingers**, click **Rig**. Watch the
   network tab: any upload of the GLB stops this step.
8. Export 3 clips (idle, run, one action) with **Include Character Mesh** on and **In Place** off. Choose the
   Unreal Engine 5 skeleton preset.
9. Import into Unreal 5.8 and play the clips. The Unreal MCP refused its connection on 2026-11-06, so the
   editor must be open first.

**Round 2: the real character.**

1. Get the brief from CREW OS: the character's role and the prompt from 32 Generative-Director, proportions
   from 30, engine limits from 66. State the agent cost before starting.
2. Replace the positive prompt in `AGORA_CHAR_01_concept`. Keep the pose sentences.
3. Repeat Round 1 from step 2.

## Design rules for the input image

Must have: exact front view, straight T-pose, separated fingers, empty hands, plain background, no cast
shadow, the whole body in frame, fitted clothing.

Avoid, each with its source:
- Spikes and large shoulder armour deform when the arms move (05:00, README).
- Glass and transparent objects: the author's bottle failed on the chest (13:28).
- A weapon in the hand: make it a separate prop, tagged as prop in ActionForge, or it bends with the wrist (README).

## Acceptance for Round 1

| Check | Pass | How |
|---|---|---|
| Triangles | 10,800 to 12,120 | `check_glb.py` |
| Closed mesh | watertight after welding | `check_glb.py` |
| Maps | base colour, normal, metal/rough | `check_glb.py` |
| Fingers | five on each hand, separate | render of the hands |
| Likeness | owner's verdict on front and back | renders beside the source |
| Deformation | no tearing at shoulders, elbows, or knees in 3 clips | ActionForge and Unreal |

## If a check fails

A failed check selects the next design. Change one variable at a time.

| Failure | Next design |
|---|---|
| Fingers or straps lost | Decimate target 20,000, or RemeshMesh resolution 1024 |
| Body bent or wrong shape | New structure seed, then Pixal3D multi-view fed with our Qwen views: 5.58 GB model plus MoGe 2, already supported by `Pixal3DMultiViewConditioning` |
| Texture too weak, especially the back | Texture round from our own Qwen-Image-Edit views projected in the owner's Blender window. Apache-2.0, no FLUX |
| Normal map patches | Raise `cage_distance` from 0.05 |
| Out of VRAM | Upsample 1024 |
| ActionForge uploads or its rig fails | Rigify in the owner's Blender window; retarget in Unreal |

## How the workflows were checked

- `tools/comfy_char/build_workflows.py`: every node, link type, value range, and combo against the schema of
  our 666 nodes. Six deliberate defects were all caught.
- ComfyUI's own `/prompt` validator on a CPU-only copy, port 8199, stopped afterwards. It reported exactly six
  errors: the five missing files and the missing input image.
- The frontend loaded all three workflows. Graphs 02 and 03 were reloaded from their saved UI files and
  exported again, and they matched the API graphs except for one empty frontend field on `SaveGLB`. Graph 01
  was exported, but it was not reloaded from its saved file and it was not submitted to `/prompt`, because
  its models exist and the copy would have rendered on CPU.
- `check_glb.py --self-test`: a complete mesh passes; too many faces, an open mesh, and missing textures fail.

These checks prove the graph is well formed. They do not prove the result looks good.
