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
