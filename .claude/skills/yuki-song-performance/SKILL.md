---
name: yuki-song-performance
version: 1.0.0
description: |
  Make Yuki (the MetaHuman companion in UE 5.9 MyProject) perform a song with the emotions of a real singing face.
  One command takes a video of a singer (a YouTube link or a local file, for example the owner's iPhone take),
  solves the face with MetaHuman Animator, puts the head motion on her body, renders her, and returns a side by
  side with a per-channel emotion score. Use when the owner says "vyberieme piesen", "nech Yuki spieva", "prenes
  emocie spevaka", "ako Senua", "sprav minutu z videa", or sends a singing video or link for Yuki.
---

# Yuki song performance

The emotions come from a filmed human face, never from our audio solve or a hand-written layer. Owner, 2026-11-15:
"ja chcem emocie ako senua minimalne a lepsie". The first test (Sinead O'Connor, 15 s) scored upper face corr +0.67
and mouth and jaw +0.69 against the singer, with blinks at 0.92 and upper lip at 0.91.

## Run

From `tools/tripo_char`, with the Unreal editor closed:

```bash
.venv_mp/Scripts/python.exe yuki_song_pipeline.py --tag <name> --url "<youtube link>" --auto 60
```

- `--auto D` finds the best continuous D seconds: face found, frontal, no shot cut, most brow, eye and mouth
  activity. Use `--start S --dur D` to set the window yourself, or `--video <file>` for a local clip.
- `--steps download,head,unreal,render,compare` runs a subset, for example `--steps render,compare` after a failure.
- Output: `reports/yuki_lipsync/perf/<name>/<name>_vs_yuki.mp4` (singer left, Yuki right, singer's sound) and
  `compare.txt` (correlation and amplitude per blendshape, upper face and mouth means).
- Time on this machine: solve about 1 minute per 15 s of video, render about 17 minutes per minute of video.

## Choosing the video

- The face must be frontal, large and continuous. Shot cuts, a microphone over the mouth, or a wide stage shot make
  the clip unusable; `perf_clip_pick.py` rejects them by measurement. Of six famous live clips, only one gave a
  clean minute.
- Best source: the owner's own iPhone 13 mini take. Phone in a holder at eye level, 30 to 50 cm, even front light,
  whole face with brows in frame, singing along to the track playing aloud. The iPhone's Live Link Face app records
  depth as well, which MetaHuman Animator solves more precisely (ingest with IngestLiveLinkFace instead of the mono
  ingest).
- YouTube material is for private tests only. Never publish it.

## Rules learned the hard way

- Head motion goes on the BODY. The solve's own HeadYaw/HeadPitch/HeadRoll curves turn the face mesh alone, so the
  body, the costume and its ears stay behind; they also carried a 27 to 35 degree offset with axes that did not
  match their names. `perf_head_angles.py` measures the head from the video's landmarks instead.
- Look at full-resolution frames before reporting, and say which defects remain.
- Close the editor when the work waits; hold `agora-tripo-char.lock` only while Unreal runs (the pipeline does both).
- Save Unreal assets only by explicit path; the pipeline saves only what it creates and L_Yuki_Preview.

## Files

`yuki_song_pipeline.py` (orchestrator), `perf_clip_pick.py`, `perf_head_angles.py`, `perf_emotion_match.py`,
`ue_mha_mono_solve.py`, `ue_yuki_head_additive.py`, `ue_yuki_dance_seq.py`, `render_yuki_seq.ps1`. Background and
history: `tools/tripo_char/AI_SINGER_TO_METAHUMAN_PLAN.md`, `tools/tripo_char/HANDOFF_20261112.md`.
