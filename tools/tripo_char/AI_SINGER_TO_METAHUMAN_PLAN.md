# AI singer to MetaHuman: workflow plan (2026-11-14)

## 0. Working route (2026-11-15): pick a song, run one command

A filmed singing face goes straight into MetaHuman Animator (mono video solve, UE 5.9), the head motion goes onto
Yuki's body, and the render comes back side by side with a per-channel emotion score. No AI singing video is needed:
any real performance works, a YouTube clip for tests or the owner's iPhone take for production. Skill:
`.claude/skills/yuki-song-performance/SKILL.md`; command:

    .venv_mp/Scripts/python.exe yuki_song_pipeline.py --tag <name> --url "<link>" --auto 60

First result (Sinead O'Connor, Nothing Compares 2 U, 15 s): upper face corr +0.67, mouth and jaw +0.69 against the
singer (MediaPipe blendshapes, lag 1 frame). Path T (Tripo face copying MetaHuman motion) is stopped: it cannot beat
the MetaHuman it copies. Sections 1 to 10 below are the research that led here.

Goal: Yuki sings PUZZLE with the facial performance of a real singing face: emotion, articulation, head motion.
Route: a paid AI tool makes a singing video of Yuki's face from our vocal stem, MetaHuman Animator (MHA) solves that
video into face animation, and the curves go onto Yuki. Nothing here is bought or run yet.

## 1. The demo the owner saw

- Actress, emotions, "almost real time": State of Unreal 2023, Melina Juergens (Senua, Hellblade 2) performs "scared,
  angry, a look" to an iPhone; MHA turns it into animation in under a minute, first on her own rig, then on a
  MetaHuman and a stylized character. https://www.youtube.com/watch?v=pnaKyc3mQVk (IGN, 2.35 M views).
- Its real-time successors: Unreal Fest Orlando 2025, a performer drives MetaHuman "Blue" live from a consumer webcam
  (https://www.youtube.com/watch?v=PrJAkek0LCA, 7:14); Unreal Fest Chicago 2026 show floor, live face capture on a
  vampire from a head-mounted webcam into an Android app (https://www.youtube.com/watch?v=vlKbASuh0L4).
- Microphone only: Epic's 2026 talk says MHA "made it work without the camera, just with a microphone" and then in
  real time (https://www.youtube.com/watch?v=IsbgHRa5N3A, 3:20). In 5.8 the real-time audio model adds automatic
  emotion detection and procedural blinks. This is the audio solve we already use, so it is not the step up.
- Chicago 2026 news that matters here: MHA Markerless Motion Capture plugin (free on Fab, UE 5.8+, Windows, experimental)
  solves body, hands and face from one ordinary video; DNA and RigLogic are open source (MIT).

## 2. Why video beats our audio solve

Audio-only solving guesses the face from the sound. Our best song render (full8) measured jaw-to-lip correlation
0.741 and bilabials 27 of 29, but the upper face needed a hand-written emotion layer (`yuki_emotion_compose.py`), and
the head, blinks and gaze were invented by us. A video solve reads all of it from a performing face: brows, eyes,
cheeks, smile, blinks, gaze, head motion, plus tongue from the audio.

Verified on our UE 5.9 install (`MetaHumanPerformance.h`, toolsets):
- Input type `MonoFootage` needs no MetaHuman Identity (the Identity field is editable only for `DepthFootage`).
- Mono settings: Solve Tongue, Head Stabilization, allowed head rotation left-right and up-down (0 to 90 degrees),
  head rotation handler, Smoothing (rolling average or One Euro, per curve), Neutral Pose Calibration (frame, alpha,
  curve list), focal length estimated from the footage.
- Scriptable end to end: `CaptureManagerToolset.IngestMonoVideo(video, audio, slate, take)` and
  `MetaHumanAnimatorToolset.GenerateAnimationFromFootage(footage, params)`; `AllToolsets` is enabled in MyProject.
- Epic's capture guidelines: HD or 4K at 60 fps, H.264 CRF 18 or better (about 25 Mbps for HD), flat light with no
  shadows, stable camera, face unobstructed (hair must not cover the face), face at least 1/30 of the frame and never
  under 40x80 px.

## 3. Pipeline

| Stage | What | Tool | Check that must pass |
|---|---|---|---|
| A. Actor image | Front portrait of Yuki MetaHuman: flat light, neutral, mouth closed, hair off the brows and eyes, 1080x1920 | Unreal still (`ue_yuki_shot.py`) | MediaPipe finds all 478 landmarks; brows and lid lines visible |
| B. Audio | Clean vocal stem (no music: music under the voice makes avatars "sing along"), 1 s silent lead-in for the neutral frame | `stems/htdemucs_ft/PUZZLE/vocals.wav` | done for the test: `reports/yuki_lipsync/aisinger_test/puzzle_078_093_vocals.wav` (16.0 s, 26 words, 6 bilabials, "like a puzzle") |
| C. Singing video | Image + vocals, mood prompt per section | bake-off winner (section 4) | face sharp in every frame, no identity drift, no mouth artefacts |
| D. Video prep | Fixed face crop (no zoom or pan), Real-ESRGAN face upscale if under 720 px wide, H.264 CRF 18; test 60 fps interpolation against native fps | ffmpeg, local Real-ESRGAN | face fills 1/3 of the frame; frame count matches audio length |
| E. Solve | Ingest mono video + the WAV, solve with Tongue on, neutral calibration on frame 0 to 15 (the silent lead-in), head rotation handler on | UE 5.9 toolsets (script) | no excluded frames; brow, eye, cheek, mouth and jaw curve groups all move |
| F. Layer | Mouth, jaw, tongue: from the video solve or the audio solve, whichever measures better per phrase; upper face, blinks, gaze, head from the video | `yuki_emotion_compose.py` (curve-level, exists) | jaw lag 0 frames against the audio solve |
| G. Apply and render | Curves into the face animation, head transform scaled about 0.7 onto the neck | `ue_yuki_curves_apply.py`, `ue_yuki_dance_seq.py` | no pops (max ratio under 3) |
| H. Measure | Section 5 | `lipsync_measure.py` + new transfer check | thresholds in section 5 |

## 4. Paid singing tool: bake-off, not opinion

No public test compares these tools on singing (searched 2026-11-14; reviewers test speech). The one measured speech
test (clipia.ai, 22 to 23 Oct 2026, 15 clips per model, Laplacian sharpness and mouth-audio correlation) and the
singing reviews give this shortlist:

| Tool | Length per call | Output | Price (source) | For us |
|---|---|---|---|---|
| OmniHuman 2.0 (ByteDance; BytePlus, Dreamina, kie.ai) | 5 min | 720p, 24 fps | 0.07 USD/s (BytePlus, kie.ai): 15 s = 1.05, song = 10.3 | Reads tone and emotion from the audio; singing named in the launch; expressive; 0.6 s silent tail; reviewers: best balance for singing (OmniHuman 1.5, Jan 2026) |
| Kling AI Avatar 2.0 (Kling, fal, kie.ai) | 5 min | Pro 1072x1920, 30 fps (clipia measured) | Std 0.05, Pro 0.10 USD/s (kie.ai); fal Std 0.056: song Pro = 14.9 | Most stable on long clips (180 s, no drift); most body motion; one reviewer: exaggerated expressions; mood by prompt |
| HeyGen Avatar V (replaced IV in spring 2026) | 5 min | IV measured 714x1280, 25 fps | Creator plan 29 USD/month, about 10 min | Sharpest face, least head motion: easy to solve, less emotion |
| Hedra Character-3 | not checked | up to 720p | 0.025 to 0.0625 USD/s | Often picked for stylized singing characters |
| MiniMax H3 Max Lip Sync (fal) | 15 s | up to 2K | 0.16 USD/s at 1080p | Short calls only; seams every 15 s |
| Free, local: InfiniteTalk, LongCat-Video-Avatar 1.5 (open, singing named) | long | 720p | 0 USD, our GPU | Needs the owner's yes for a large local model; slow (InfiniteTalk 26 min per 60 s) |

Bake-off: the same actor image and the same 16 s excerpt through OmniHuman 2.0, Kling Avatar 2.0 Pro, Hedra and HeyGen
(free credits first: Dreamina gives daily free credits, Hedra and HeyGen have free tiers; Kling's free 66 credits a day
reportedly exclude Avatar). Then stages D to H on each, then section 5. Paid cost of the whole bake-off: about 3 to
4 USD. Full song with the winner: about 8 to 15 USD.

## 5. Measurement (decides the winner and every later change)

On the AI video (source) and on Yuki's render, MediaPipe Face Landmarker with blendshapes, per frame:
1. Transfer fidelity: per-channel correlation and lag between source and render for jawOpen, mouthClose,
   mouthFunnel, mouthPucker, mouthSmile L/R, browInnerUp, browDown L/R, eyeBlink L/R, eyeSquint L/R, cheekSquint.
   Target: jaw and smile 0.8 or more, brows and blinks 0.6 or more, lag 0 frames.
2. Articulation against the audio (`lipsync_measure.py`, `yuki_articulation_check.py`): bilabial closures at the
   Whisper b/p/m times at least as good as the audio solve (27 of 29 on the song), rounded and open onsets above chance.
3. Jitter: energy above 6 Hz in each curve, no worse than the audio solve.
4. Emotion per phrase: smile and brow means per sung phrase compared with the director's sheet
   (`puzzle_emotion_score.json`).
5. The owner's eye on one side-by-side: source video left, Yuki right.

## 6. Improvements beyond the tutorials

1. Yuki is her own actor: the AI animates a render of our MetaHuman, so the solver sees a MetaHuman-family face and the
   identity never changes. A version with hair pulled back keeps brows and lids visible (Epic: hair must not cover
   the face).
2. Directed emotion: generate per song section with a mood prompt from our director's sheet (verse tender, chorus
   open and joyful), 1 s overlaps, curve cross-fade with the existing composer.
3. Neutral calibration on the silent lead-in removes the AI face's resting smile or frown from the whole take.
4. Hybrid per phrase: keep the audio solve's mouth where it measures better (bilabials), take everything else from
   video. The measurement in section 5 picks per phrase, not by taste.
5. Head and shoulders: the video solve's head track replaces our still head; the free Markerless plugin can try upper
   body from the same video; if that is weak, a separate full-body singing video gives the body.
6. A human control take (optional): one webcam take of a person singing the excerpt shows how far the AI is from a
   real performance. MHA real-time also runs from a webcam (90 fps at 720p recommended by Epic).
7. Later, live: Live Link Hub with the MetaHuman Audio source (mood, lookahead 80 to 240 ms) or a webcam for the
   pocket companion.

## 7. Decisions for the owner

- Accounts: one of kie.ai or fal.ai (pay-as-you-go API, covers OmniHuman 2.0 and Kling Avatar) plus free Dreamina and
  Hedra logins. He signs in; I never type keys, passwords or card data.
- Budget: bake-off about 3 to 4 USD, full song 8 to 15 USD.
- Optional: install the free MHA Markerless Motion Capture plugin from Fab (large download; check 5.9 support on the
  listing).

## 8. Risks

- AI singing models are tested on speech; long sustained notes and fast lines are the weak spots. The bake-off uses an
  excerpt with both.
- 720p, 24 fps sources are below Epic's 60 fps recommendation; blinks and eye darts may smooth out. Stage D tests
  interpolation against native fps by measurement.
- An avatar may move the head a lot (Kling) or barely at all (HeyGen); the mono solve stabilizes the head, and the
  allowed-rotation limits drop frames turned too far.
- Content filters can refuse a render; reruns cost credits on some services.

## 9. Cheaper paths and tricks from the Tripo email (read 2026-11-14)

Source: Tripo newsletter of 2026-11-14 and its article "How to Make 3D Models with Claude Fable 5.2"
(https://www.tripo3d.ai/blog/3d-models-claude-fable). Their pipeline: Tripo P2.0 Smart Mesh character in T-pose (quad
topology, their example 28,073 faces), Tripo rig (Humanoid, Mixamo preset, 65 joints, skin weights), props generated
as separate models with PBR maps, then Claude in Blender: cleanup, 1.6 m scale, non-deforming socket bones, a small
foot and hand IK solver baked to the Mixamo bones at 30 fps, stage, effects, Eevee render 1080p (138 frames in about
13 minutes), bloom in ffmpeg. It has NO face: an independent 2026 rigging test calls Tripo's rig "biped-only; no
facial joints" with noisy jaw weights, which matches our own note of 2026-11-13. So the email alone gives no singing.

### Path 0: cheapest, no 3D
OmniHuman 2.0 directly on the concept image or a Tripo render, with the vocal stem. Free credits, or about 10 USD
for the whole song. Result is a 2D 720p video, no camera or body control. Good for a quick short or a teaser.

### Path T: Tripo body in Blender, no MetaHuman, no Unreal
1. Yuki as Tripo P2.0 Smart Mesh in T-pose (the look the owner prefers: Tripo make-up and eyes), rigged with the
   Mixamo preset (API: P2 with texture 110 credits, rig 25; Studio rig 20).
2. Face: 52 ARKit shape keys on the Tripo head, transferred from our MetaHuman. Our MetaHuman face was conformed to
   the Tripo head (surfaces within about 1 mm at the eyes, `yuki_face_bake.py`), so each ARKit pose of the MetaHuman
   head maps onto the Tripo head by nearest surface. That correspondence is ours; no paid add-on (Faceit, Shape Key
   Gen) needed.
3. Driver: MediaPipe Face Landmarker (`face_landmarker` with blendshapes, already on disk) reads 52 ARKit scores per
   frame from the AI singing video, smoothed, keyed onto the shape keys. CPU only.
4. Mouth interior: a Tripo mesh is one painted shell, with no teeth, tongue or eyeballs. Transplant the MetaHuman
   teeth, tongue and eyes, or keep the camera wide. This is the main quality limit of the path.
5. Render in Blender Eevee. Frees the GPU from Unreal, but Eevee was slower in their test (about 0.18 frames per
   second at 1080p) than our Unreal renders (3.9 frames per second).
Trade: 52 ARKit channels instead of about 260 MetaHuman curves, no wrinkle maps, no MHA tongue. Cheaper on the
machine, not better on the face. Worth one test only if the owner wants the Tripo face itself to sing.

### Tricks that go into the main path
1. Arms and upper body: free animation clips (Mixamo, free with an Adobe ID in 2026 but in maintenance mode;
   Quaternius UAL, CC0, 250+ clips) retargeted to the MetaHuman with the IK Retargeter, layered under the idle. Fixes
   the stiff arms in full8. Check the libraries for singing or talking gesture clips before choosing.
2. Tail: its own bone chain on a socket (their "attachment bones") with spring dynamics in the post-process
   animation blueprint. Fixes the rigid tail.
3. Small props (bell, choker ring) generated separately with PBR maps: normal and metal-roughness maps are what make
   metal read as metal; a base colour alone looks flat.
4. MediaPipe 52 ARKit scores from the AI video serve twice: the reference in the measurement (section 5) and a
   second, independent solve to cross-check MHA phrase by phrase.
5. Hand and foot IK baked to the bones (their small solver) for gestures that touch the body: hand to chest on a
   held note, without arms passing through the costume.

## 10. Execution order (owner 2026-11-14: "lacnejsou cestou a hlavne nasou ... postupne so vsetkym")

Our MetaHuman route, free credits only, every step measured before the next. My reading of "bez sraciek": the
Tripo-email extras with no face (Tripo rig, Eevee) stay out; the AI video is only the performance source.

| # | Step | Needs | Done when |
|---|---|---|---|
| 1 | Actor image: `reports/yuki_ue_v14/hD_face.png` (front, mouth closed, brows visible) for the first test; a flat-light 9:16 render later | nothing (exists) | uploaded |
| 2 | Free OmniHuman clip of the 16 s excerpt in Dreamina, mood prompt from the director's sheet | owner's Dreamina login (done 16:11), free credits | clip saved in `reports/yuki_lipsync/aisinger_test/` |
| 3 | MediaPipe transfer tool: 52 ARKit scores per frame from any video, compare two videos per channel | CPU | runs on the clip |
| 4 | MHA video solve script: ingest mono video + WAV, solve with tongue and neutral calibration, export the face animation | Unreal, GPU free | animation asset exists, curves move |
| 5 | Layer: video upper face + head, mouth by measurement (video or audio solve), render the 16 s, side-by-side | Unreal, GPU | numbers vs section 5 targets |
| 6 | Arms: CC0 gesture clips retargeted, layered under the idle | Unreal | no arm through the costume |
| 7 | Tail: bone chain with spring dynamics | Unreal | tail swings with the body |
| 8 | Full song: free clips in parts across days, curve cross-fade | free credits | full render measured |

GPU state at 17:2x: ComfyUI of the CREW OS icon session (driver PID 73520, lock since 17:17) holds the card; by the
shared-machine rules it outranks us and is never stopped by this session. Unreal steps wait for the owner to free it.

### Step 2 result (2026-11-14 17:3x): OmniHuman is blocked here
Dreamina, signed in (216 credits): Create, AI avatar shows "This feature is not available in your region." So
OmniHuman 2.0 through Dreamina is out for Slovakia. Free replacements:
- Hedra free tier: about 100 credits, Character-3 at about 6 credits/s, so about 16 s, watermarked (fluxnote.io,
  2026). Just covers our 16 s excerpt. Needs the owner's login.
- HeyGen free tier: 3 videos a month, 1 min, 720p, watermark; whether Avatar IV is included is disputed.
- LongCat-Video-Avatar 1.5 (Meituan, MIT, singing named, up to minutes): runs on our card in INT8 (16 GB VRAM by its
  model page). Hugging Face repo 74.9 GB in total; the INT8 model is 15.9 GB, the DMD LoRA 2.5 GB, Whisper large-v3
  3.1 GB, plus the base text encoder and VAE from LongCat-Video (size not checked). Free, no watermark, unlimited,
  ours. Needs the owner's yes for the download and a free GPU.
