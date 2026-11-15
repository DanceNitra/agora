# Acting database for Yuki: design (2026-11-15)

Owner, 2026-11-15: "treba vytiahnut kazdu emociu a prejav do presneho zapisu aby sme potom emocie vedeli odvzdat
stabu aby vedel snimi pracovat a navrhovat vlastne ... pojdeme na dalsieho spevaka a potom ... 10 najlepsich a
skopirujeme kazdy prejav do detailu a ulozime si do vlastnej hereckej databazy! aby sme neskor aplikovali vsetko na
ineho metahumana!"

Built from one CREW OS round of 12 roles: 04 Critic, 05 Skeptic, 06 Verifier, 07 Director, 10 Dramaturg, 11 Brain,
20 Creative Director, 22 Persona Architect, 27 Voice Actor, 29 Anime Director, 66 Unreal Director, 67 Scene Builder.
Their reports: `crew_<nn>_<role>.report.md` in this session's tasks folder. Brief:
`C:\Users\Danculus\crew-os\01 Projekt\YUKI HERECKA DATABAZA - brief pre stab.md`. Tears: `YUKI_TEARS_RE.md`.

Nothing in this document is measured except section 1. Proposals carry no number until a run produces one.

## 1. Where we stand (run sinead_100_60, compare.txt of 2026-11-15 15:53)

Mean correlation against the singer: upper face +0.67 (amp 1.02), mouth and jaw +0.61 (amp 0.96), 1779 of 1801
frames with both faces. Per channel, the channels that carry sadness and holding back are the weakest:

| channel | corr | amp Yuki/source | reading |
|---|---|---|---|
| browInnerUp (AU1) | +0.70 | **0.37** | timed right, 37 % of the strength |
| mouthPressLeft / Right (AU24) | +0.28 / +0.09 | 0.27 / 0.25 | lip press almost lost |
| mouthFrownLeft / Right (AU15) | n/a | **0.00** | Yuki never pulls the corners down |
| mouthStretchLeft / Right | +0.49 / +0.41 | 0.02 / 0.06 | lost |
| mouthFunnel | +0.63 | 4.22 | four times too strong |
| eyeWideLeft / Right | +0.80 / +0.62 | 3.25 / 4.39 | too strong, from a tiny source range |
| eyeBlinkLeft / Right | +0.92 / +0.79 | 0.89 / 0.87 | good |
| jawOpen | +0.84 | 1.12 | good |
| mouthUpperUpLeft / Right | +0.89 / +0.90 | 1.18 / 1.04 | good |

The brief to the crew carried four per-channel figures written from memory (46 %, 0.93, 0.87, 0.08 to 0.31) that do
not match this file. The table above replaces them. The pipeline overwrites `compare.txt` on every run, so the origin
of the old figures cannot be traced (06 Verifier).

Open question that decides the next fix: MediaPipe reads both faces. A 37 % brow can be a weak transfer or a detector
that under-reads a CG face. Section 6, step 0.3 measures which one.

## 2. The record: two layers that never mix

Every crew role asked for the same split (05, 06, 22, 29, 66, 67, 27):

- **MEASUREMENT** is what a run produced from the source. It is never edited.
- **ANNOTATION** is what a reader says the face does and why. It is never stored without a measurement under it.

Inside MEASUREMENT, **articulation** (jaw and the mouth shapes that form sounds) belongs to the song and is never
transferred to another song. The **acting layer** (brows, lids, gaze, head, lip press, chin, breath, ears) is what
the database stores and reuses (05, 27, 29, 66).

### 2.1 MEASUREMENT fields

| group | fields | source |
|---|---|---|
| provenance | `run_id` (hash of all inputs), source video id, source sha256, native fps, start and length in source seconds, git commit, UE build, MHA version, MediaPipe model sha256, yt-dlp version, `license` (`private_test_only` or `own_recording_consent`) | 06 |
| time | every time in source seconds and in render frames, with the `PRE` offset (45 frames today) | 06, 66 |
| face | 260 `CTRL_expressions_*` curves at 30 fps, raw | exists |
| head | yaw, pitch, roll in degrees relative to the camera, per frame | exists (`head.json`) |
| gaze | yaw and pitch in degrees relative to the head and to the camera, saccade events, eyes-closed spans, `gaze_target` (`camera`, `away`, `down`, `inner`) | 04, 11, 67 |
| blink | blink events with their position relative to the syllable and the phrase boundary | 07, 11 |
| ARKit | 52 MediaPipe scores for the source and for Yuki | exists |
| voice | f0 in Hz, cents off the note, loudness in dB, register (chest, mix, head, falsetto), technique (belt, cry, breathy, fry, break), vibrato rate in Hz, extent in cents and onset delay in ms, onset type (glottal, breathy, simultaneous), HNR in dB | 27 (Praat through parselmouth, free) |
| breath | start, length in ms, type (full, catch, sob, sigh), audible yes/no, nose or mouth | 27 |
| text | word, syllable and phoneme with start and end in ms, held vowels | 27, 07 |
| shot | shot size (ECU, CU, MCU), face height in px, focal length estimate, key light direction, low-key or high-key | 20, 67 |
| validity | frame ranges with a readable face (yaw under 25 degrees, no microphone, hand or hair in front) | 67 |
| fidelity | per channel correlation, amplitude ratio and lag against the source, the same against a null control (section 5, G3), share of frames with a face | 05, 06 |
| confidence | per channel flag `high`, `low`, `unusable` from the fidelity and the instrument calibration. `low` channels are never used as fact | 22, 66 |

### 2.2 ANNOTATION fields

| field | meaning | source |
|---|---|---|
| `intent` | one verb aimed at someone: `prosi`, `obvinuje`, `spomina`, `zadrziava`, `vzdava_sa`. The database is searched by verb, never by emotion adjective | 04, 07, 10, 20, 22, 27 |
| `obstacle` | what the singer holds back (crying, anger, shame) | 10 |
| `emotion_visible`, `emotion_suppressed` | each with strength 0 to 1 per frame. Senua works because two emotions fight on one face | 10, 04 |
| `suppression` | 0 to 1: how hard the hold is | 07, 11 |
| `valence`, `arousal` | -1 to 1 and 0 to 1, as a viewer would rate them | 07, 11 |
| `beat` | `onset_f`, `peak_f`, `hold_f`, `release_f`, each with a source key frame image | 07, 29, 67 |
| `trajectory` | state A, turn frame with its trigger (word, breath, note), state B | 10 |
| `function` | onset, escalation, turn, peak, release, after-ring | 10, 11 |
| `music_position` | verse, chorus, held note, after a breath, key change | 10 |
| `key_poses` | extremes picked from the curves (frame, region, value) | 29 |
| `ma_before`, `ma_after` | stillness in frames around a peak | 29 |
| `imperfections` | chin tremble, broken breath, asymmetric smile, each with a time. Never smoothed away | 20 |
| `truth` | the director's verdict 1 to 5 | 07 |
| `readability` | result of the grey silent test (section 5, G8) | 20 |
| `annotators` | two independent readers and their agreement. A model's label is marked `[NAVRH]` until a person confirms it | 05, 06, 10 |

### 2.3 Stylization layer (Yuki only)

Yuki is a stylized character with cat ears. The singer's record is realistic. Between them sits a layer that the
database stores per character, not per singer (29): overshoot 1.0 for a realistic MetaHuman and 1.3 to 1.6 for
Yuki, holds and stepped timing (on 1s, 2s, 3s) per section, pupil size, eye highlight tremble, cheek blush, and an
`ears` channel (pose up, forward, back, flat, twitch, angle in degrees) derived from emotion and brows.

## 3. Units

| unit | length | definition |
|---|---|---|
| `CLIP` | the source | one run, one immutable folder |
| `SONG` | the arc | list of phrases, a valence and arousal curve |
| `PHRASE` | 2 to 8 s | breath to breath; one intent against one obstacle (10, 27, 66) |
| `MOVE` (herecky tah) | 0.5 to 4 s | one onset, peak and release; anchored on a voice event (breath, onset, peak, break, decay) |
| `PROFILE` | per singer | statistics of all their moves (22) |

- A move is a reference into its clip (`clip_id`, `f_from`, `f_to`), never a copy. Curve slices are generated (66,
  67).
- Every move records its start and end state, so the crew can search for moves that chain (10).
- Name, ASCII: `<singer>_<song>_F07_T03_<verb>_<visual-signature>`, for example
  `soc_nc2u_F07_T03_zadrziava_oci-zavrete-na-vrchole`.
- Tags come only from a controlled vocabulary (`vocab.yaml`): `intent:`, `emo:`, `tech:`, `beat:`, `func:`, `shot:`,
  `int:`. Free text in tags breaks search (29, 06).
- Index lives outside Unreal (JSON lines or SQLite). The same tags are written onto Unreal assets with
  `EditorAssetLibrary.set_metadata_tag`, so the Content Browser finds them too (66).

### 3.1 Profiles

- **Singer profile** (22): core, top 10 signature moves (frequency times distinctness), tempo (median onset to peak
  in ms), restraint index (mean over peak), derailer (for example melodrama from the brows), antipersona (AUs the
  singer never uses), `tear_threshold`.
- **Character key** (07, 20, 22): Yuki's own core ("zadrziava, kym to ide"), 2 to 3 signature traits that repeat,
  what she never does (for example a smirk on a sad line). Every borrowed move passes through it, so Yuki is not a
  collage of ten singers.
- **MetaHuman calibration** (66, 05, 07, 11, 22): for each target face, render each curve at 0, 0.25, 0.5, 1 and
  measure the real response. The result is a gain and an offset per channel. Without it "plays on any MetaHuman" is
  true technically and false visually.

## 4. Composing a new performance

1. **Emotional score of the new song** (10, 07): every phrase gets a verb, a target strength and an arousal curve.
   One payoff, usually the last chorus or the key change. Each chorus stronger than the one before.
2. **Script breakdown** (27): Cartwright notation (`|` short pause, `||` long pause, a line over a stretched vowel,
   intent and attitude in the margin). From the audio: breaths, held vowels, peak notes.
3. **Mood strip** (20, 67): 8 to 12 key frames of the peaks on the target MetaHuman, from locked camera poses, with
   framing and light. Signed off before the full render. Correlation cannot judge a new song, because there is no
   source to compare against; this strip is the gate that replaces it (67).
4. **Casting moves** (07, 27): candidates by verb, function, technique, vowel, note length and tempo. One singer per
   phrase as the source (04). The same move does not repeat within 4 phrases without a change of strength (10, 20).
5. **Layers** (29, 66, 27): mouth and jaw from the solve or lipsync of the new song. Lip closure on m, b, p comes
   from the phoneme layer of the new audio, never from a copied move (66). Upper face, gaze, head, breath and ears
   come from the database.
6. **Timing**: only held vowels stretch, consonants never (27). Moves anchor on syllables and voice events.
   Transitions 4 to 8 frames, through a breath or neutral (07, 29, 66).
7. **Character key and calibration**: every move passes the character key, then the target's calibration gains.
8. **Build** (66): Python, curve by curve, because Sequencer blends whole poses. Blink takes the maximum, emotion
   adds, everything clamps to the control range. Output is one AnimSequence on the Face track
   (`AnimationLibrary.add_float_curve_keys`) and head as an additive row on Body, as `ue_yuki_dance_seq.py` does today.
   The existing `yuki_emotion_compose.py` already blends solves and a performance layer; it is the starting point.
9. **Variants** (20, 27): two to three per phrase, a faithful one and a bolder one. The owner picks.
10. **Gaze blocking** (07): eyes to the camera in 2 to 3 key moments only.

## 5. Quality gates

| gate | test | source |
|---|---|---|
| G1 integrity | source sha256 matches, face in at least 95 % of frames | 06 |
| G2 reproducibility | a second solve from the same inputs gives the same curves | 06 |
| G3 null control | correlation against the singer shifted by 10 s and against another phrase. A score counts only above this line | 05, 06 |
| G4 instrument | calibration of MediaPipe on Yuki (section 6, step 0.3), plus a second detector. OpenFace is free but needs a download, so it waits for the owner's yes | 05, 06 |
| G5 per channel | judged per channel, never by the mean. The mean amp 0.96 hides 4.22 and 0.02 | 06, 22 |
| G6 annotation | two independent readers, Cohen's kappa. Disagreement marks the move `unclear`, not false | 05, 06, 10 |
| G7 golden set | the Sinead minute is a fixture. Every pipeline change re-runs it; a drop in any gated channel means the change is reverted | 06, 66, 67 |
| G8 blind silent test | Yuki clips without sound, grey MetaHuman, at 270x480 and 1080x1920. A reader picks the verb or emotion from 5 to 6 options. 05 predicts 30 to 45 % today, chance is 20 % | 04, 05, 10, 20, 29 |
| G9 held-out song | one fixed song never used for training. The system improves only when G8 rises on it after a new singer. More moves is not improvement | 05 |
| G10 falseness checklist | dead eyes, lips that do not close on p, b, m, perfect symmetry, a body without breath, a tear without redness, a transition without a reason | 04 |
| G11 viewer response (later) | a webcam reads the viewer's AU4 and AU12 while watching; free with MediaPipe | 11 |

## 6. Build order

Every step in phase 0 and 1 is free and runs on what is installed.

**Phase 0: make the instrument honest (before any new singer).**
- 0.1 Run registry: one folder per `run_id`, never overwritten; `compare.txt` moves into it.
- 0.2 `perf_emotion_match.py` adds the `eyeLook*` channels (today it measures no gaze at all, 04) and the null
  control G3.
- 0.3 Calibration of Yuki: each acting curve at 0, 0.25, 0.5, 1, rendered, read by MediaPipe. One experiment answers
  two questions: is the 37 % brow the detector or the transfer, and what is Yuki's gain per channel.
- 0.4 Voice track on the Sinead minute with parselmouth: f0, loudness, breath events.
- 0.5 Phoneme alignment check on 20 hand-labelled words (27): free aligners are trained on speech and slip on held
  vowels.

**Phase 1: the first real records (Sinead).** Phrases from breath events, moves from onset, peak and release in the
curves, annotation by two readers (agents mark `[NAVRH]`, the owner confirms), the first singer profile, Yuki's
character key written with 07, 22 and 29.

**Phase 2: the first composed performance.** Sinead's moves on the held-out song, mood strip signed by 07 and 20,
then G8 and G10.

**Phase 3: tears.** `YUKI_TEARS_RE.md` plus section 7.

**Phase 4: the learning loop.** The owner's list of 10 singers, ordered by the gaps in the coverage matrix (intent and
emotion by strength by technique by register), not by fame. Each singer runs `yuki_song_pipeline.py`, then phase 1
steps, then G7 to G9.

**Phase 5: transfer.** Calibration of a second MetaHuman, the same moves on both, G8 on both.

## 7. Tears

All 12 roles agree on the model; it replaces the plain "crying intensity" key of MetaCry:

- **Reservoir per eye** (11, 10, 22, 07): level = integral of (sadness times suppression) with a slow decay. It fills
  over several phrases, never at once.
- **Stages** (10, 22, 29): 0 dry, 1 glassy eye and gloss, 2 lake on the lower lid, 3 one drop, 4 run and wet trail,
  5 sob. A stream is banned for Yuki (29).
- **When a drop falls** (07, 10, 11, 27, 29): at a release, a turn or a pause after the peak, or pushed out by a
  blink or eyes closing. Never on the peak and never during a belt; on the peak it reads as melodrama. The strongest
  image is a tear held back that does not fall (20).
- **Physiology with it** (04, 11, 20, 27): red lid rims, nose tip and sclera, swollen lids, clumped lashes, chin
  tremble (AU17), a wet sniff after the phrase. A tear without redness reads as glycerin (04).
- **Trail** (07, 10, 22): dries over seconds and stays to the end of the scene; it must survive a cut (continuity).
- **Light** (20, 29): the highlight matters more than refraction; a tear without a highlight is invisible.
- **Record**: tears are `AUTHORED`, not captured, because MediaPipe cannot see them (05, 06). Their timing in the
  Sinead clip is annotated by hand from the video.
- **Sequencer channels per eye** (66, 67, 07): `tear_level`, `drop_events[] {frame, side, size_mm}`, `trail_wet`
  with `wet_decay_s`, `sclera_red`, `lid_red`, `eye_gloss`.
- **Rendering**: offline bake per frame on the deformed face (`YUKI_TEARS_RE.md`, section 3). 66 proposes Niagara on
  the skinned face with a UV render target for the wet map, which is the runtime alternative; both are unmeasured in
  UE 5.9.
- **Acceptance** (67, 05): a locked light rig, three close-ups (lake, drop leaving, trail), the highlight visible at
  1080p, nothing passes through the lid on a blink, a blind comparison with MetaCry's public demo before we call it
  better. Clean room: public videos and documentation only (06).

## 8. Risks

1. **Correlation becomes the goal** (29, 67, 11). Every exaggeration, hold and ear move lowers it, so tuning for it
   pushes Yuki to realism and kills her anime identity. Correlation gates the measurement layer only; G8 gates acting.
2. **Sadness and holding back do not survive** (all 12). AU1 at 37 %, AU24 near zero, AU15 at zero. Without a fix the
   database stores open emotion and loses the suppressed one, which is the Senua level the owner asked for.
3. **Averaging and the Frankenstein** (07, 20, 27, 04). Ten singers blended give one mush near 0.6 strength with no
   imperfections. Moves keep their singer's identity and are never averaged.
4. **Lip closure on m, b, p** (66, 04). The mono solve catches it weakly; borrowed moves would look dubbed.
5. **Transfer to another MetaHuman is unverified** (05, 06). Only Yuki is measured.
6. **Rights** (05). YouTube clips are private tests, but curves derived from them would be published through Yuki.
   05 recommends production only from own recordings with consent (the owner's iPhone takes) and only statistics
   (timing, order of moves) from foreign clips. This is the owner's decision and a legal question, not ours.
