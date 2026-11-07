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

## Rig comparison, 2026-11-07

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
- First rig was wrong because of my dots: Hip (L) on the body's right crossed the legs, shoulders sat at
  x 0.30 and wrists at 0.60. ActionForge's L is the character's left, the screen's right when it faces you.
- Corrected dots (shoulder 0.19, elbow 0.42, wrist 0.64): Detect Fingers then read both hands in 10 of 10
  views. The earlier failure was the wrist dots, not the gloves. Bind: 10,317 vertices to 52 bones in 0.5 s.
- Export "Character only (rest pose)" GLB, 2.8 MB, owner approved the download. Its skeleton uses Unreal
  Mannequin names (`pelvis`, `spine_01`, `upperarm_l`, `lowerarm_l`, `thigh_l`, `calf_l`, fingers `_01`-`_03`).
  The glTF import leaves a pose on all 71 bones; clearing it gives back the exact rest mesh.

**Result, same test pose, edges stretched or compressed by more than 30 %** (control: rest pose = 0 on both):

| Region | Rigify | ActionForge |
|---|---|---|
| Arm and shoulder | 7.67 % | 11.89 % |
| Hand | 7.56 % | 6.60 % |
| Leg | 1.43 % | 2.78 % |
| Torso and head | 1.19 % | 1.84 % |
| Whole body | 645 of 21,830 (2.95 %) | 958 of 21,830 (4.39 %) |

By eye the two are close: both close a fist, both crease the inner elbow into facets, both fold the knee
with a dark slit. ActionForge leaves one small loose fragment near the left hand.

What the numbers do not include: Rigify's joints came from measured mesh sections and its weights needed a
proxy fix; ActionForge took about 5 minutes of dots and 0.5 s to bind, and its skeleton already carries the
Unreal names its 85 clips use. Its code is (c) CGstuff with no terms for output; its clips are CC0.

## Unreal import, 2026-11-07 (ActionForge chosen by the owner)

- Export per clip from ActionForge: FBX, Unreal units, skeleton Default, Include character mesh on, In place off.
  Files `idle_loop_unreal_fit.fbx`, `jog_fwd_loop_unreal_fit.fbx`, `fixing_kneeling_unreal_fit.fbx`, about 15 MB
  each, copied to `agora_output/reverse/yt_bEiW6L7Y7NM/actionforge_export/`. The UE5 skeleton preset exports
  animation only, retargeted to Epic's Manny (`set1_ue5_manny_anim_only.fbx`), with no character.
- Chrome blocks repeated downloads from one site until the owner allows it in the address bar.
- Unreal 5.8 (`SkeletalMeshTools.import_file`, import_animations on): `/Game/AgoraChar/AF/` holds
  `SK_AgoraChar_AF`, `SK_AgoraChar_AF_Skeleton`, `A_AgoraChar_Idle` (2.5 s), `A_AgoraChar_Jog` (0.93 s),
  `A_AgoraChar_Kneel` (5.2 s), one material and two textures. All three animations share the one skeleton.
- Checked with `CaptureAssetImage` thumbnails (no actor placed in any level).
- Incident: `save_assets` with an empty list saves EVERY dirty asset, which saved the open level
  `L_Tomb_S03_Ambience` with a test actor in it. The actor was removed and the level saved again; it is back
  to 146,598 bytes, the size of the committed version. Pass explicit asset paths to `save_assets`.

## Character Blueprint, 2026-11-07

`/Game/AgoraChar/AF/BP_AgoraChar` (parent Character), graph in [BP_AgoraChar.dsl](../BP_AgoraChar.dsl), written with
`BlueprintTools.write_graph_dsl` through [ue.py](../ue.py):
- Mesh `SK_AgoraChar_AF`, offset z -89, yaw -90, single-node animation mode. Capsule 89 / 34 cm.
- Camera boom 350 cm with pawn control rotation, follow camera, orient rotation to movement, MaxWalkSpeed 500.
- Input: `IMC_Default` and `IMC_MouseLook` added on BeginPlay; Tick reads `IA_Move`, `IA_Look`,
  `IA_MouseLook`, `IA_Jump` through the "Get IA_*" value nodes, because the DSL cannot declare Enhanced
  Input events and has no way to add function parameters.
- Idle/jog switch by ground speed above 20 cm/s; jog plays at rate 0.78.
- `bAutoWalkTest` (instance editable) walks forward without input, for automated tests.

Traps met: `Pawn|GetControlRotation` resolves to the Controller version unless given `:self (Pawn|GetController)`;
positional DSL arguments land on `self`, so pin keywords are needed; `write_graph_dsl` replaces only the
events it defines; `CaptureViewport` renders the editor world, not the play session, so play frames come
from `CaptureEditorImage`.

Root motion: the first jog export (In place off) carries 5.8 m of root travel per 0.93 s cycle. Setting
`bForceRootLock` through ObjectTools did not stop the mesh running ahead of the capsule. Fix: re-export
from ActionForge with "In place X Z" on, imported as `A_AgoraChar_JogInPlace`.

Test level `/Game/AgoraChar/Maps/L_AgoraChar_Test` (copy of Template_Default, 80 m floor): standing, the
capsule holds z 90.7 for 10 s; walking, measured speed 499 to 502 cm/s at z 91; play frames show the jog
staying at a constant distance from the camera. Frames: `agora_output/reverse/yt_bEiW6L7Y7NM/unreal/`.
Not tested: keyboard and mouse by hand, jump, the kneel clip (imported, not wired).

## Epic Mannequin animations on our character, 2026-11-07

Owner's verdict on the ActionForge clips in play: the idle pose is wrong, the jog looks unnatural, there is
no jump, and a jump while running plays the run. He asked to use Unreal's free animations instead.

- The project already holds Epic's Mannequin set: `ABP_Unarmed` (idle, 8-way walk and jog blend space,
  jump, fall loop, land). Usable in Unreal Engine products under Epic's terms.
- Unreal MCP cannot import `unreal`; MyProject has Python Remote Execution on, so [ue_py.py](../ue_py.py)
  runs editor scripts through Epic's `remote_execution.py`.
- [ue_retarget_setup.py](../ue_retarget_setup.py): auto IK Rigs for `SKM_Manny_Simple` (29 chains) and our
  character (21 chains), root motion bone `root` on both, IK Retargeter with default ops, all 21 target
  chains mapped, target auto-aligned. [ue_retarget_run.py](../ue_retarget_run.py): `ABP_Unarmed` plus 20
  animations and the blend space duplicated to `/Game/AgoraChar/Retarget/Anims2` (broken, see the fix below; Anims6 is current).
- First attempt collapsed every bone onto the pelvis (head and feet within 1 cm of it). Cause: the
  ActionForge FBX keeps bone translations in metres under a scaled root (pelvis local z 1.036; Manny 95.9).
  Fix: the ActionForge rest-pose GLB re-exported from the owner's Blender in centimetres (unit scale 0.01,
  model x100, scale applied) as `AgoraChar_AF_cm.fbx`, imported as `/Game/AgoraChar/AF2/SK_AgoraChar`.
- Second problem: the retargeted jog carries 12 m of root travel per 1.77 s loop, so the mesh ran up to
  8.3 m ahead of the capsule. `force_root_lock` did not stop it in play. Fix: [ue_inplace.py](../ue_inplace.py)
  zeroes the `root` track of all 20 animations; the jog pelvis then stays within 2 cm of its start.
- `BP_AgoraChar` now uses `SK_AgoraChar` (offset z -90, yaw -90, capsule 90) and `ABP_Unarmed_Agora`;
  its graph only handles input. `bJumpTest` (instance editable) triggers a jump for automated tests.
- Play test: idle upright; jump in place and while running both play the jump pose; jogging at 500 cm/s
  the pelvis stays 12 to 16 cm from the capsule and the camera 350 cm behind.
  Frames: `agora_output/reverse/yt_bEiW6L7Y7NM/unreal/abp3_*.png`.
- Not checked: hand test with keyboard and mouse, 8-way strafing look, foot sliding at 500 cm/s.

### Owner hand test: crooked body, broken feet. Fixed in Anims6, 2026-11-07

The owner's screenshots: the body leaned forward and the feet stood twisted and tilted. My frame checks before
had looked at the whole character from 350 cm and never at the feet. Four separate defects, each measured
against Epic's source clip with [ue_check_anims.py](../ue_check_anims.py) (it runs on Anims2 as the control and
fails all 20 clips there):

| Defect | Measured | Cause | Fix |
|---|---|---|---|
| Body tipped forward | idle pelvis-to-head 24.6 degrees forward, Manny 8.2 | our `root` has a -13.3 degree roll in the reference pose; `ue_inplace.py` wrote identity | root keys = reference transform |
| Soles tilted | 10-12 degrees off flat in idle, Manny 2-3 | auto-align turns thigh and calf, the foot inherits it | [ue_retarget_feet.py](../ue_retarget_feet.py): foot offset keeps the reference sole orientation |
| Toes splayed | 12 degrees further out than Manny per foot | our rest pose | same script turns each foot about the vertical to Manny's toe direction |
| Head hung, spine too upright | neck-to-head 45 degrees forward, Manny 23; spine 4-6 degrees more upright | auto-align leaves neck and spine line alone | [ue_retarget_spine_neck.py](../ue_retarget_spine_neck.py) aims spine_01 and neck_01 at Manny's lines, head stays level |

Result in `/Game/AgoraChar/Retarget/Anims6`, used by `BP_AgoraChar` through
[ue_use_anims.py](../ue_use_anims.py): all 20 clips within 5.5 degrees body lean, 0.0 degrees sole tilt and 3.5
degrees neck of Epic's; knee bend in the jog within 9 degrees; stride range -68 to 34 cm against Manny's -67 to
41. Ankles sit 2-3 cm lower than Manny's in stance (thicker boots), so the mesh is raised 3 cm (offset z -87).

Video: [ue_record_play.py](../ue_record_play.py) renders the play session through Unreal itself at time
dilation 0.1 and captures each frame (a desktop grab picked up another window on top of the editor).
`agora_output/reverse/yt_bEiW6L7Y7NM/unreal/agora_char_play_2026-11-07.mp4`, 6.7 frames per second real time.

Second hand test, same day: one boot still stood sideways. Side by side in play, Epic's own `MM_Idle` has the
right foot turned 47 degrees out (toe yaw 137, forward 90) and the left straight; we had copied it exactly.
[ue_idle_feet.py](../ue_idle_feet.py) turns the whole right leg about the vertical through the hip in
`MM_Idle_Agora` so the toes point 10 degrees out; ankle height and sole tilt unchanged, the Epic stance kept as
`MM_Idle_Agora_EpicStance`. [ue_turntable.py](../ue_turntable.py) shows the result from 8 directions. The feet
stay staggered about 30 cm front to back, as in Epic's stance; from the side the rear boot shows behind the front leg.

Fifth hand test: still hunched from the side. The plumb line was fine; the body was not square. Epic's idle turns
hips and shoulders 20-23 degrees from the facing direction (with the right foot turned out to match); with the feet
straightened, the legs were twisted under a turned body. [ue_idle_neutral.py](../ue_idle_neutral.py) supersedes
`ue_idle_feet.py` and `ue_idle_stand.py`: from the untouched `MM_Idle_Agora_EpicStance` it turns the body square
(hip line 0.6 degrees, shoulders 3.7 in play), plants the feet symmetric 12 cm either side of the centre line,
toes 8 degrees out, and solves both legs; Epic's breathing stays. In play: head 9 cm, pelvis 1.4 cm in front of
the ankles. Its first version deleted and recreated the clip, which cleared the AnimBP and blend space references
and blocked Play with a compile-error dialog; [ue_relink_idle.py](../ue_relink_idle.py) restored them and the
script now writes in place.

Fourth hand test: the standing pose looked hunched (owner: "ohnuta jak quasimodo"). Measured in play beside Manny:
pelvis 7.4 cm behind the feet (Manny 3.3 in front), right shin leaning 15 degrees back (Manny 17 forward), knees
15-21 degrees. [ue_idle_stand.py](../ue_idle_stand.py), run after `ue_idle_feet.py`, moves the pelvis 9.8 cm forward
and 1.8 cm up as one constant offset (the breathing motion stays) and solves both legs onto the unchanged feet:
pelvis 2.0 cm in front of the feet, knees 9.8 degrees, shins within 6 degrees of vertical, feet moved at most 0.2 cm.

Third hand test: in play the left foot pointed backward (172 degrees from the actor's forward) while the clip
itself had it forward. Cause: `ABP_Unarmed` ends in a Control Rig node running `CR_Mannequin_FootIK`, built for
Manny's bones; our skeleton has no `ik_foot_*` bones. It reversed the left foot, pulled both feet about 6 cm down
and crouched the jog into a shuffle. Every check on the clips missed it because they evaluated the clips without
the AnimBP. Fix: the node's Alpha set to 0 in `Anims6/ABP_Unarmed_Agora` (MCP `set_pin_value`). In play the toes
then point 6.6 and 9.9 degrees out, as in the clip. Lesson: measure the character in play, not only the assets.

Skin weights tried in Blender the same day (test pose plus a 25 degree spine bend and a right leg swung back;
edges stretched or squashed over 30 percent): ActionForge 5.57 % overall, torso 9.07, hips 16.44; heat weights on a
voxel proxy 5.51, 10.38, 10.28, but fused left fingers and tore the inner thighs; ActionForge with far and
wrong-side weights removed 5.04, 8.21, 16.83, faceted. None clearly better, none applied.

Shirt crease fixed the same day. Down the back centre line the ActionForge weights put 0.3-0.5 on each clavicle
from 112 to 132 cm and almost nothing on spine_01-03, and the thighs pulled the belt line, so swinging arms dragged
the shirt into a V. The jog was exported from Unreal and copied bone by bone onto the Blender rig (all bones within
3 cm) to reproduce the crease; the torso band (96-146 cm, arms and shoulder tips excluded) was then reweighted along
the spine, pelvis to spine_03 by height, blended into the original weights at its edges. Exported as
`AgoraChar_AF_cm_w5.fbx` and reimported over `SK_AgoraChar` by [ue_reimport_mesh.py](../ue_reimport_mesh.py);
the previous mesh is kept as `SK_AgoraChar_AFweights`, the Blender original as `UEX_AgoraChar_Mesh_AFweights`.
In play the hem stays straight.

Shoulders, same day. On the shoulder top the clavicle held the skin out to 24 cm from the centre line (the joint is
at 19 cm), and lowerarm reached into the middle of the upper arm (0.11-0.34). The arm band was reweighted along the
arm: clavicle to upperarm from 15 to 27 cm, upperarm alone to 37, upperarm to lowerarm from 37 to 46 (elbow at 42);
under 26 cm only the shoulder cap above 139-145 cm changes, so the chest, back and armpit keep their weights. Edges
stretched or squashed over 20 % across 8 jog frames: shoulder 26.5 % to 20.3 %, elbow 23.7 % to 17.7 %. Two
variants were rejected on the play video: one that reached the armpit, and one that smoothed weights over the whole
mesh; both drew a diagonal crease across the back that the edge metric did not show. The kept version smooths only
the 1,127 vertices it changed and leaves every other vertex identical. Exported as `AgoraChar_AF_cm_w8.fbx`;
`SK_AgoraChar_W5torso` and `SK_AgoraChar_W6arms` are the earlier meshes in Unreal. The deep-knee jog is Epic's `MF_Unarmed_Jog_Fwd` itself; knees match it.

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
