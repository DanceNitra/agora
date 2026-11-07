# Handoff: first game character, 2026-11-07

Session `4d84810e`. The owner paused this work until the heavy renders in other sessions finish and Claude
Code is restarted for an upgrade. Read this file first, then [docs/FIRST_CHARACTER_PLAN.md](docs/FIRST_CHARACTER_PLAN.md).

## Where it stands

- The pipeline works end to end in ComfyUI 0.36 with native nodes only. Image to a 12,000-triangle textured
  GLB takes 150 s on the RTX 3090 (shape cached runs: 70 to 90 s).
- Round 1 character exists: `C:\ComfyUI\output\agora_char\character\final_00001_.glb`. 11,911 triangles and
  4 maps at 2048 pass. Fingers and the face fail.
- **Fingers:** the raw TRELLIS mesh (node 46) has all five fingers separate. `RemeshMesh` in udf mode
  offsets the surface by its band and fuses middle, ring, and little finger. Tried and rejected: resolution
  1024 and 2048, band 0.5, sdf mode, and decimating the raw mesh without a remesh. Table in the plan.
- **Face:** a UV chart seam runs down the middle of the face and the two halves of the mouth do not line
  up. Not worked on yet.
- **Owner's choice, 2026-11-07:** new concept with fingers spread wide, so the gaps survive the remesh
  offset. Concept v2 prompt: thin tight-fitting work gloves, "all five fingers spread wide apart like a
  starfish with a clear gap of background visible between every finger", same seed 2026110601. Graph:
  [workflows/AGORA_CHAR_01_concept_v2_spread_fingers_api.json](workflows/AGORA_CHAR_01_concept_v2_spread_fingers_api.json).

## Running when this was written

- ComfyUI on `127.0.0.1:8188`, started by this session, server PID 24592 at Idle priority, log
  `C:\ComfyUI\_agora_char_20261107.err`. Concept v2 (prompt `29584cb2`) was at step 10 of 50 at about
  12:20 and finishes on its own; output `C:\ComfyUI\output\agora_char\concept_v2_0000{1..4}_.png`.
  An interrupt was refused by the permission classifier, so it was left to finish.
- Blender 5.2, PID 56516, started by this session on the owner's word. Unsaved scene with the test
  objects `AGORA_CHAR_*` and helper empties `TMP_*` used as close-up targets.
- Unreal was NOT started. The owner asked for it, then paused everything. Project
  `C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject`, MCP autostart is on
  (`bAutoStartServer=True`), port 8000. Start it only when the GPU is free; the concept graph peaks at 23 GB.

## Next steps

1. Check `C:\Users\Danculus\.claude\compute\` for locks and the ComfyUI queue. Shorts-studio renders
   have priority.
2. Look at the 4 concept v2 images part by part, write a difference list, and pick the one with the widest
   finger gaps.
3. Copy it to `C:\ComfyUI\input\agora_char_input.png` and run the baseline graph:
   `python -X utf8 tools/comfy_char/run_graph.py tools/comfy_char/workflows/AGORA_CHAR_02_character_api.json`
4. Measure with `check_glb.py`, then compare hands in Blender close-up (import the GLB, frame the
   `TMP_hand_R` empty at 0.18 m). Compare raw (save node 46 with an extra SaveGLB) against final.
5. If fingers survive: face seam, then rig in ActionForge, then Unreal. If not: mitten hands and rig
   with fingers off.

## Measured costs

| Step | Time | GPU total peak |
|---|---|---|
| Concept, 4 images, 50 steps, 1328 px | 919 s | 23.0 GB |
| Mesh graph, cold | 150 s | 13.8 GB |
| Mesh graph, shape cached, remesh 768 to 2048 | 70 to 425 s | 9.8 to 21.0 GB |

## Traps met

- `watch` skill fails on this ffmpeg: `Unrecognized option 'vsync'`.
- Remesh variants with band 0.5 or sdf drop whole arms; check `extent_xyz` x is about 0.95 first.
- A `look` close-up needs a target object; empty `TMP_*` objects at hand, head, and feet work.
- `run_graph.py` measures whole-GPU VRAM, not ComfyUI alone.
