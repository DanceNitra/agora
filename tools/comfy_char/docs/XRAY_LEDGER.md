# X-ray + REA: "Local AI Now Makes Game-Ready 3D Characters (Fully Animated!)"

Source: https://www.youtube.com/watch?v=bEiW6L7Y7NM, channel PixelArtistry, published 2026-11-06, 24:12.
The segment 9:32 to 11:17 is a paid VARCO 3D advertisement.

Evidence, all in this folder:
- `download/video.mp4`, sha256 `c54d5c7a346ce0c5134f63a1f10ec7059a4412ebde7e8ed6f13307418ee5659d`.
- `transcript.txt`: full auto captions, read in full. `sheets/`: 145 frames at 1 per 10 s. `keyframes/`.
- `repo/`: the author's public repo (MIT for his files), commit `77f1462`, read and never run.
- `wf_character_dump.txt`: every node, value, and note of his workflow.
- `object_info_0.36.json`: schema of the 666 built-in nodes of our ComfyUI 0.36.0.

Question: which steps turn one image into a playable character, and which of them run on our machine,
under our licence rules, with our models?

## Answer

The author's installer cannot run here, but ComfyUI's own native nodes cover the same mesh steps. We need
no custom node pack, no torch downgrade, and no `blender -b`. Rebuild:
[FIRST_CHARACTER_PLAN.md](FIRST_CHARACTER_PLAN.md). It passes schema and frontend checks. It has not
generated a character yet, because five model files are missing and the download needs approval.

## The pipeline as seen

| # | Step | What it does | Tag | Evidence |
|---|---|---|---|---|
| 1 | Input image | Full body, front, T-pose, empty hands, plain background, fitted clothes; no spikes or big shoulder armour, because they deform | SEEN | 04:42-05:00, README "How to use" |
| 2 | Shape | TRELLIS.2 or Pixal3D, one switch. Structure 12 steps, shape 20, upsample 12 at 1536 | SEEN | wf nodes 3, 18, 23, 94, 316 |
| 3 | Watertight | Quad Reconstruct, then WTiVo, then LODTailor at 6M faces | SEEN | wf nodes 325-328 |
| 4 | Low poly | LODTailor to 12,000 triangles, prop 2,000, UV `pec`, smooth normals | SEEN | wf nodes 335, 337, 338 |
| 5 | Normal bake | Bake Forger, 2048, cage 0.0019 | SEEN | wf node 341 |
| 6 | Texture | UltraTex: FLUX.2 Klein + LoRA paints 12 colour views and 6 metal/rough views, projected onto the mesh at 2048 | SEEN | wf nodes 358, 364, 377 |
| 7 | Prop | Second workflow; the sword is placed in the hand in Blender and exported with Limit to Selected | SEEN | 11:17-14:30 |
| 8 | Rig | ActionForge in the browser: orange dots, height, Mirror, Fingers Five, Detect Fingers, Rig; tag the prop, Bind and Wear | SEEN | 15:05-16:10, sheet_04 |
| 9 | Animation | 85 clips by Quaternius (CC0); 9 clips exported as one GLB, Include Character Mesh on, In Place off | SEEN | 15:10, 17:28, godot guide stage 0 |
| 10 | Game | Godot 4.7: CharacterBody3D, collision, hitbox, camera on a spring arm, Claude-written `player.gd` with exact clip names | SEEN | 18:44-21:56, `docs/godot-ai-guide.md` |

Author's measurement, RTX 5080 16 GB: 572 s, 11,976 triangles, sword 463 s, 2,000 triangles (README). Not re-measured.

## Claims checked against the evidence

| Claim in the video | Finding | Tag |
|---|---|---|
| "all locally" | Shape and texture yes. Rigging is a website; its page says "nothing you make is uploaded" and the UI says "never uploaded". We have not watched the network traffic | SEEN statement, traffic UNKNOWN |
| TRELLIS.2 "guaranteed" to stand straight | One sentence, then he says he switched to Pixal3D for this run, and the repo default is Pixal3D. No comparison is shown | Overclaim, UNKNOWN |
| "way better textures" from UltraTex | No side-by-side in this video. His own result has a failed glass bottle on the chest, 13:28 | Unmeasured |
| 6 to 8 GB VRAM works | The workflow note says "No GPU benchmark was run on this package" | Unmeasured |
| Runs on Python 3.12 + torch 2.8 only for WTiVo | Confirmed by `docs/COMPATIBILITY.md`; other torch versions are derived from binaries, not run | SEEN |
| Note says the seed is randomized | Same workflow fixes it at 56. Internal contradiction in the notes | SEEN |

## Our machine

| Item | Value | Effect | Tag |
|---|---|---|---|
| ComfyUI | 0.36.0, `C:\ComfyUI`, not running since 2026-11-03 | Start before the first run | SEEN |
| Python, torch | 3.12.10, 2.14.0+cu130 | WTiVo blocked: it needs torch 2.8 + CUDA 12. CuMesh wheels stop at torch 2.10 | SEEN |
| GPU | RTX 3090, 24 GB, `sm_86` | WTiVo's `cellocut_gpupr_fast` lists only `sm_100` and `sm_120`, so it might not run even after a downgrade | INFERRED; check is not worth running |
| Disk C: | 29 GB free | 8.96 GB fits; his 26 GB would leave 3 GB | SEEN |
| `custom_nodes/ComfyUI-Trellis2-GGUF` + `models/Trellis2` (16 GB) | Import fails: `No module named 'cumesh'` (log 2026-11-03) | Those weights are in a format for the broken pack, so we still need the Comfy-Org files | SEEN failure; format mismatch INFERRED |
| Native nodes | Every node type in our three graphs exists, including `RemeshMesh`, `DecimateMesh`, `UnwrapMesh`, `BakeNormalMapFromMesh` | The rebuild needs no custom node | SEEN |
| ComfyUI's template `3d_pixal3d_trellis2_image_to_model` | Shipped in our venv; the author's workflow is built on it | Source of our sampler values | SEEN |

## Why not the author's chain

| His part | Problem for us | Our replacement |
|---|---|---|
| WTiVo + Quad Reconstruct | Blocked by torch; downgrading the shared venv risks MiniMax H3 and everything else on it | Native `RemeshMesh` |
| LODTailor, Bake Forger | Each runs `blender --background` (`__init__.py` line 989). Banned: [[blender-work-only-in-the-owners-window]] | Native `DecimateMesh`, `UnwrapMesh`, `BakeNormalMapFromMesh` |
| UltraTex with FLUX.2 Klein | "FLUX Non-Commercial License" (Hugging Face card, repo README); UltraTex weights licence UNKNOWN. Banned: [[textures-are-our-own-from-comfyui-no-third-party-licences]] | Native TRELLIS.2 texture stage, then `BakeTextureFromVoxel` |
| Godot | Not installed; we work in Unreal 5.8. The author says the method is not tied to Godot (23:30) | ActionForge export with its Unreal Engine 5 skeleton preset; 66 owns the import |

The price of this choice: texture quality may be lower than UltraTex. That is the first thing the held-out
test measures, and the next design is in the plan.

## Licences read this session

| Part | Licence | Source | Note |
|---|---|---|---|
| TRELLIS.2 weights | MIT | Hugging Face cards, `microsoft/TRELLIS.2-4B`, `Comfy-Org/TRELLIS.2` | |
| BiRefNet | MIT | Hugging Face card | |
| DINOv3 image encoder | DINOv3 License, not MIT | `ai.meta.com/resources/models-and-libraries/dinov3-license` | Royalty-free and no revenue cap. "Built with DINOv3" applies when we distribute the model. Forbids uses barred by trade controls, "including those related to military or warfare purposes". The Comfy-Org repo tags the file MIT, which does not match Meta's licence. Owner decision before a war-themed product |
| Qwen-Image 2512, Edit 2511, Lightning, Multiple Angles LoRA | Apache-2.0 | Hugging Face cards | |
| ActionForge code | "© CGstuff", no terms of service for output | site page | Ask the author before a commercial release |
| Quaternius animations | CC0 | site page, 15:10 | Owner's no-CC0 rule was stated for textures; decision needed for animation |
| WTiVo, LODTailor, Bake Forger, UltraTex nodes | GPL-3.0 | GitHub API | Not used |

## Unresolved

- Whether native `RemeshMesh` at 768 keeps fingers and straps through 12,000 triangles. Measured by the held-out test.
- Whether TRELLIS.2's own texture is good enough on the back of the body.
- ActionForge's real network behaviour and its finger detection on our mesh.
- The run time on our RTX 3090.
