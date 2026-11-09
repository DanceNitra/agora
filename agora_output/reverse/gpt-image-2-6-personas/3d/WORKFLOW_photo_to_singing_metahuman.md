# Workflow: photo -> beautiful MetaHuman that talks and sings (proved 2026-11-08)

Owner verdict on the result: "VYBORNE". This file is the recipe. Every script named here lives in
`ue/fit/` beside this file; run Unreal-side scripts with `python -X utf8 -c "import fit_lib as f; print(f.ue(open('X').read()))"`
or, for long ones, through `ue_py.run_file(path, timeout=...)` as in the loops below.

Proved outputs: `lipsync/depesa_kf_lipsync_line2.mp4` (speech, 5.5 s), `lipsync/depesa_kf_spieva_aj_jeden_lajk.mp4`
(singing, 16 s, chorus of DANCHI "Aj jeden lajk").

## 0. Preconditions
- UE 5.8.4, project `C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject`, plugins MetaHumanCharacter,
  MovieRenderPipeline (enabled 2026-11-07, backup `MyProject.uproject.bak-before-mrq-20261107`).
- Owner's OK before starting or stopping the editor. Our assets only under `/Game/Companions`.
- Epic login in the editor (auto-rig and texture download are Epic cloud services).

## 1. Face reference (beauty is decided here, in 2D)
- Beauty portrait first (GPT Image 2.6 Sunburst, `gen_concept.py`), owner picks.
- Three capture views from it with `images.edit`: front, 40 degrees left, 40 degrees right; neutral face, hair in a
  low bun, ears free, no jewellery, soft even light, grey background. Prompts: `keenface/kf_*.md`. Cost 0.14 USD.

## 2. Head from KeenFace (keenface.ai, owner's account)
- Upload the 3 views. Scan Reconstruction **Off** (References mode; generated views are not geometrically exact).
- 150 credits per head (new account 450 free). Licence 8 Oct 2026: owner keeps rights, may publish, no training.
- Download **MetaHuman ZIP** (head.fbx in MetaHuman topology, 24,408 verts + 4K Color/Normal/SRMF) and GLB.

## 3. MetaHuman from the template (`ue_kf_import.py`)
- Import head.fbx as StaticMesh, import the 3 maps (Normal: TC_NORMALMAP, sRGB off; SRMF sRGB off).
- Duplicate a preset (Vivian) to `/Game/Companions/MetaHuman/MH_<Name>`, `import_from_template` -> SUCCESS.
- Skin: `enable_texture_overrides`, face BASECOLOR + NORMAL = KeenFace maps. The editable preview does NOT show
  overrides; only the build does.
- Eyes and makeup with `ue_beauty.py` + `beauty_cfg.json` (iris u=0.95 v=0.75 = amber; thin dark liner; lips and
  blush NONE because the texture carries them).
- Grooms via the wardrobe (`ue_build.py` sets internal AND preview collection): WI_Hair_L_Straight,
  WI_Eyebrows_M_FlatThick, WI_Eyelashes_L_ThickCurl; colours via instance parameters (`groomcolor_cfg.json`,
  Melanin 1, Redness 0-0.05, Lightness 0). Never hand-build a GroomBindingAsset: it crashed the editor.

## 4. Rig, textures, build (`ue_rigtex_kf.py`, then RESTART, then `ue_build_kf.py`)
- `request_auto_rigging` JOINTS_AND_BLEND_SHAPES (about 30 s), `request_texture_sources` (2k, about 10 s), save.
- **Restart the editor before the build.** Building in the same session right after rig/textures crashes
  (EXCEPTION_ACCESS_VIOLATION 0x470, TextureGraphEngine). CINEMATIC crashed; OPTIMIZED works.
- Build OPTIMIZED to `/Game/Companions/MetaHuman/BuiltKF`, then `save_directory` (build output is in memory only;
  an editor quit once lost it).

## 5. Voice
- Speech: Piper `sk_SK-lili-medium` (CC0) in `lipsync/.venv_tts`, ONLY through the Python API
  (`PiperVoice.synthesize_wav`) and print `phonemize()` first. The Windows CLI with a text file on stdin mangled the
  diacritics and the voice spoke nonsense (owner: "uplne nezmysly").
- Singing: any vocal works; we used the chorus 6.0-22.4 s of the master WAV, mono 44.1 kHz, full mix (no stem
  separation yet).

## 6. Lip-sync (`lipsync_cfg.json` {name, wav} -> `ue_lipsync.py` -> `ue_lsexport.py`)
- MetaHumanPerformance, input AUDIO, `set_blocking_processing(True)`, `start_pipeline()`.
- Export onto `/MetaHumanCharacter/Face/Face_Archetype_Skeleton` with `show_export_dialog False`; without the target
  skeleton the export is EMPTY (length 0). Check: 260 curves, `CTRL_expressions_jawOpen` range (speech 0.43, song 0.69).

## 7. Sequence (`ue_seq_kf.py`)
- `export_level_sequence` with the built BP as spawnable, audio track, control rig track; new name each run
  (`LS_KF_<name>_vN`; deleting a loaded sequence raises an Ensure dialog).
- Adds spawnable CineCamera 85 mm, filmback 24x32, f/16, focus distance-12 cm, manual exposure bias 2,
  physical camera exposure OFF (otherwise black), plus 3 spawnable point lights. Everything sits at
  (0, 300000, 100000), away from the level.

## 8. Render (`kf_run.ps1` pattern, preset `/Game/Companions/Lipsync/MRQ_Depesa_portrait`)
- Render in a SEPARATE `-game` process: `UnrealEditor.exe <uproject> /Game/Maps/L_Tomb_S03_Ambience -game
  -LevelSequence=<seq> -MoviePipelineConfig=<preset> -windowed -resx=540 -resy=720 -log=... -Unattended`.
  Tell the owner first: a second Unreal window appears.
- The first render compiles hair and face shaders and looks frozen for minutes; with the cache warm, 332 frames take
  70 s. Do not kill it as hung within the first minutes; watch frame count, stop only if 0 frames for 3+ minutes.
- Compute lock `C:\Users\Danculus\.claude\compute\pocket-companion.lock` during renders.

## 8b. Emotion and direction (owner: "Sedí", 2026-11-08)
- Solve the same audio once per mood (`mood_run.py`; mood + mood_intensity in `ue_lipsync.py`), export a sequence
  per mood. The model takes ONE mood and ONE intensity per clip (see RE_metahuman_audio2face_2026-11-08.md).
- Export a fresh base sequence (`ue_seq_kf.py`, never duplicate one: the copy loses control-rig keys), write its path
  to `arc_target.json`, then `ue_arc2.py`: per-line mood blend from the line timings (0.25 s fades), jaw x1.12,
  lipsTogether x1.3, positive blink x4.
- `ue_smile.py`: additive directed layer per line (cornerPull, dimple, cheekRaise, squintInner, brow raiseIn/Out,
  0.3 s ramps). Key times are DISPLAY-rate frames (30 fps): use `get_display_rate()`, never tick resolution.
- Proven result: `lipsync/depesa_spieva_rezia.mp4`.

## 8c. Look and device export (2026-11-08)
- Skin: grade the KeenFace albedo (Lab L-10, a+3, b+6 -> `Head_Color_olive.jpg`), set it as the BASECOLOR override,
  body skin u=0.42 v=0.5 (`ue_olive.py`), `request_texture_sources`, RESTART, build.
- Dosvit light (`ue_dosvit.py`): amber key camera-left low, rose-violet rim behind right, weak cool fill.
- Device framing (`ue_devcam.py`): filmback 16x32 (1:2), 85 mm, camera 105 cm, z +158; preset
  MRQ_Depesa_device 640x1280 -> `render_dev`. After an editor restart re-run the CONFIDENCE solve before exporting
  a sequence (processed results do not survive a restart; the export returns None).
- 80x160: INTER_AREA + light unsharp, 4x4 Bayer dither to RGB565 little-endian, frames concatenated:
  `device/depesa_lajk_80x160.rgb565` (491 frames, 12.6 MB) + `.json`; preview `lipsync/depesa_80x160_nahlad_x4.mp4`.

## 9. Video
`ffmpeg -framerate 30 -i render_v5/%04d.png -i <audio> -c:v libx264 -pix_fmt yuv420p -crf 18 -vf scale=720:960 -c:a aac -shortest out.mp4`

## Open improvements
Olive skin tone and warm Dosvit lighting, black wet hair, smile/mood in the audio solve, whiter teeth, vocal stem
separation for songs, 80x160 sprite export for the device.
