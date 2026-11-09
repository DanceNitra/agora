# Eyebrow animation for a MetaHuman: research deep dive (2026-11-08)

Scope: how researchers and production animators move eyebrows for emotion, speech, and singing, turned
into rules for a MetaHuman face driven by Speech2Face plus a keyed directed layer.
Method: about 40 web searches and page reads. Read-only. Each claim carries its source.
Labels used in this report:

- **[SRC]**: stated in the cited source, read in this session.
- **[SEC]**: reported by a secondary source that cites the primary work. Verify before quoting publicly.
- **[DESIGN]**: our parameter choice, derived from the sources but not stated by any of them.
- **NOT FOUND**: searched for and not found in this session.

---

## 0. Ten rules the evidence supports

1. Most pitch accents get NO brow raise. A raise marks only selected accents, usually the start of a
   new topic or an instruction. [SRC, Flecha-Garcia thesis, see 2.2]
2. When a raise happens, it starts just before the accent. The reported mean is about 60 ms before
   the nearest accent, with a very wide spread (SD 458 ms). [SEC, Flecha-Garcia 2010 as cited by Gast 2023]
3. A prominence raise is short: House et al. used 300 ms total (100 ms rise, 100 ms hold, 100 ms fall),
   at only 4% of the full brow range, and it worked as a prominence cue. [SRC, House et al. 2001]
4. Viewers tolerate about 100 ms of misalignment. Beyond that the raise attaches to the nearest other
   stressed syllable. [SRC, House et al. 2001]
5. The same rise and fall times with a long hold read as a conversational signal (interest,
   feedback), not as emphasis. Non-synchronous brows were sometimes read as irony. [SRC, House et al. 2001, stated as a plausible hypothesis, not tested]
6. In singing, brow height tracks sung pitch height. Higher notes come with higher brows and read as
   friendlier. [SRC, Huron, Dahl and Johnson 2009, abstract]
7. Spontaneous emotions (surprise, fear, pain) are symmetric. Deliberate ones (curiosity, suspicion,
   contempt) can be asymmetric. [SRC, Victor Navone, Pixar animator, blog post]
8. Brows lead: they move before the head and body, and before the rest of an expression change.
   [SRC, Navone; Animation Mentor]
9. Do not combine a full inner raise with a full brow-down. It reads as sadness or a twisted look.
   [SRC, Navone] In FACS, inner raise plus lowerer (AU1+4) is the sadness brow. [SRC, FACS table]
10. Brows travel on diagonals: up and apart, down and together. [SRC, Adrien Liv via CG Channel 2024]
    MetaHuman encodes this split: a full AU4 needs browDown plus browLateral. [SRC, Epic docs]

---

## 1. FACS: brow action units and emotion combinations

### 1.1 The three brow AUs and their muscles [SRC, Wikipedia FACS article]

| AU | Name | Muscle | MetaHuman curve [SRC, Epic MH standards docs] |
|---|---|---|---|
| AU1 | Inner brow raiser | Frontalis, pars medialis | browRaiseInL/R ("left side of FACS AU1") |
| AU2 | Outer brow raiser | Frontalis, pars lateralis | browRaiseOuterL/R |
| AU4 | Brow lowerer | Depressor glabellae (procerus), depressor supercilii, corrugator supercilii | browDownL/R (vertical part) + browLateralL/R (horizontal part) |
| AU6 | Cheek raiser | Orbicularis oculi, pars orbitalis | eyeCheekRaiseL/R |
| AU7 | Lid tightener | Orbicularis oculi, pars palpebralis | eyeSquintInnerL/R (mapping to AU7: NOT FOUND in docs; inferred from name) |
| AU12 | Lip corner puller | Zygomaticus major | mouthCornerPull (AU12 mapping: not opened this session) |
| AU14 | Dimpler | Buccinator | NOT FOUND |

Epic states that a full brow raise needs inner and outer raisers combined, and a full brow lowerer
needs browDown and browLateral combined. browDown also "pushes the eye cover fold downwards".
browLateral "pulls the left eyebrow toward the right eyebrow". [SRC, Epic docs]

FACS intensity letters: A trace, B slight, C marked, D severe, E maximum. [SRC, Wikipedia]

### 1.2 Emotion prototypes (EMFACS-style) [SRC, Wikipedia FACS table; variants in the FACS Investigator's Guide per PMC7264164 table 3]

| Emotion | AUs | Brow part |
|---|---|---|
| Happiness (Duchenne) | 6+12 | none required |
| Surprise | 1+2+5B+26 | full symmetric raise |
| Sadness | 1+4+15 | inner raise + lowerer (oblique "grief" brow) |
| Fear | 1+2+4+5+7+20+26 | raise + lowerer together (flat, tense) |
| Anger | 4+5+7+23 | lowerer |
| Disgust | 9+15+17 | none (AU4 often secondary, NOT FOUND as prototype) |
| Contempt | R12A+R14A (unilateral) | none; the asymmetry is in the mouth |

- Ekman 1979: sadness, fear, and surprise brows are raised; anger brows are lowered; anger, fear, and
  sad brows (not surprise) may include corrugator. [SEC, Frontiers 2013 review citing Ekman 1979 "About brows"]
- Ekman 1979 treats the brow raise as having a widely shared meaning, one reading being "I want to know
  more". [SEC, same]
- Ekman's baton / underliner / question-mark brow categories: NOT FOUND in a readable source this session.
- Compound "happily surprised" (Du, Tao and Martinez 2014, PNAS): press summary says ~93% of participants
  produced wide surprise eyes plus happy raised cheeks. Exact AU list NOT FOUND (paper tables not opened).

### 1.3 Asymmetric and single-brow expressions

- Contempt is a unilateral expression (lip corner raise and tightening on one side), recognized across
  cultures. [SRC, Matsumoto 1992 abstract]
- Asymmetric expressions (smirks) signal contempt, skepticism, defiance. [SRC, Affectiva smirk paper]
- A one-sided AU2 as a FACS-defined "skepticism" signal: NOT FOUND. Navone (Pixar) states that
  deliberate expressions such as curiosity, suspicion, and contempt can be asymmetric. [SRC]
- Bloop Animation tip: when the character looks left, raise the left brow slightly higher. [SRC, tutorial, not research]

### 1.4 Flirt, interest, seductive

- Eyebrow flash (AU1+2, Grammer et al. 1987): about one fifth of a second (~200 ms); longer at the
  opening of conversations; a greeting/approach signal. Flirt-specific duration NOT FOUND. [SEC, Wikipedia]
- Most effective female flirt expression (Haj-Mohamadi, Gillath and Rosenberg 2020, FACS-coded):
  head turned to one side and tilted slightly down, slight smile, eyes forward to the target; 77% and
  71% of men identified the top two images as flirtatious. Brow AUs NOT FOUND in the summaries. [SEC, ScienceDaily / Psychology Today]
- Sexual excitement (Fernandez-Dols et al., 100 videos): frequent AUs include closed or slit eyes,
  brow lowering, cheek raise. This is arousal, not seduction display. [SEC, Improbable Research]
- A FACS study of eyebrows specifically in seduction: NOT FOUND.

---

## 2. Brows, speech prosody, and singing

### 2.1 Coupling with F0 is partial, not automatic
- Cave et al. 1996 (ICSLP): rapid rise-fall brow movements coincided with F0 rises in only 71% of
  cases. The authors argue against a muscular coupling and for a communicative choice.
  https://www.isca-archive.org/icslp_1996/cave96_icslp.html [SEC, abstract via search]
- Same group: brow movements occur right before or after turn onset and with F0 changes. [SEC]
- House et al. 2001 cite the view that a direct F0-to-brow coupling "is very unnatural", while
  prominence and brow movement may co-occur. [SRC]
- Cvejic, Kim and Davis 2011: brow raise and head tilt timing was not aligned with auditory cues and
  occurrence was inconsistent. [SEC, ISCA abstract via search]

### 2.2 Frequency and placement
- Flecha-Garcia (Edinburgh thesis; Speech Communication 2010, 52(6):542-554): most pitch accents had
  no brow raise. Raises tended to immediately precede an accent, with raise start aligned to accent
  start. Instructions had more and longer raises. The first utterance of a high-level discourse
  segment had more and longer raises. Queries did NOT have more raises than other utterances.
  https://era.ed.ac.uk/items/c1dfbb39-7eef-4b4d-aec0-8102dcc50453 [SRC, abstract]
- Exact percentage of accents with a raise: NOT FOUND.
- Kim, Cvejic and Davis 2014 (Speech Communication 57:317-330): brows and head moved more often under
  narrow focus and echoic questions than under broad focus; brow movement was larger early in the
  utterance. [SEC, abstract]

### 2.3 Timing numbers
| Quantity | Value | Source |
|---|---|---|
| Brow raise lead before nearest pitch accent | ~60-63 ms mean, SD 458 ms | [SEC] Flecha-Garcia 2010 as cited by Gast 2023 and a Lund paper |
| Brow action window before a prominent word (focus, echoic question) | ~250 ms | [SEC] Kim et al. as cited by Gast 2023 |
| Raise onset before brow peak | ~270 ms | [SRC] Gast 2023, https://pmc.ncbi.nlm.nih.gov/articles/PMC9854528 |
| Raise extent around peak | ~300-600 ms (10-20 frames at 30 fps) | [SRC] Gast 2023 |
| Pitch stays elevated after a high raise (>1.5 SD) | ~670 ms | [SRC] Gast 2023 |
| Pitch contour before the peak predicts raise height | phase r=0.24, p=0.019 in combined model | [SRC] Gast 2023 |
| Synthetic prominence raise | 300 ms: 100 rise / 100 hold / 100 fall, 4% of full range | [SRC] House et al. 2001 |
| Perceptual timing tolerance | ~100 ms (one syllable, 100-200 ms) | [SRC] House et al. 2001 |
| Effect of a brow raise on prominence judgments | +24% (L1 listeners), +39% (L2) | [SRC] Granstrom, House and Lundeberg 1999, cited in House 2001 |
| Pitch vs brow weight in focus perception | pitch effect much larger; brows matter most when pitch is ambiguous | [SEC] Krahmer et al. 2002 |

House et al. 2001 PDF: https://www.isca-archive.org/eurospeech_2001/house01_eurospeech.pdf
Krahmer et al. 2002: https://www.isca-archive.org/icslp_2002/krahmer02_icslp.html
Note: in House 2001, head nods beat brows as a prominence cue when the two conflict. [SRC]

### 2.4 Questions
- European Portuguese: brow raising is the dominant visual cue for questions in production, but
  listeners still rely mainly on intonation. [SEC, Cruz, Swerts and Frota]
- English: Srinivasan and Massaro found the visual question cue weak against the auditory one. [SEC]
- Navone: for a question whose answer the speaker knows, raise the brows; for a truly unknown answer,
  lower them. Trends, not rules. [SRC]
- Slovak-specific brow data: NOT FOUND.

### 2.5 Singing
- Huron, Dahl and Johnson 2009 (Empirical Musicology Review): 44 participants sang low, moderate, and
  high pitches; strong correlation between brow position and sung pitch; high-pitch faces judged
  friendlier, also with only the eye region visible. [SRC, abstract via search]
  https://doaj.org/article/6876121d77644b20ba64f9d8bd6273f8
- Thompson and Russo 2007; Thompson, Russo et al. 2010: singers' facial movements scale with the size
  of the sung interval and change listeners' interval judgments. [SEC]
- Sci. Rep. 2021 (s41598-021-01797-z): head and facial (brow, lip) movement extent correlates with
  interval size or pitch height. [SEC]
- Numeric brow displacement per semitone: NOT FOUND.

---

## 3. Production tools and animator practice

### 3.1 MetaHuman
- Brow curves: browDown, browLateral, browRaiseIn, browRaiseOuter (L/R); eye curves include
  eyeSquintInner, eyeCheekRaise, eyeWiden, eyeBlink, eyeFaceScrunch (experimental, needs Hierarchical
  Solve). All are "driven by MetaHuman Animator". [SRC, https://dev.epicgames.com/documentation/metahuman/mh-standards-docs/mha_index]
- Value range of the CTRL_* board controls: NOT FOUND in docs. Verify in the editor (read min/max of
  CTRL_L_brow_raiseIn etc. through the Control Rig) before writing values.
- Forehead joints: FACIAL_C_Forehead, FACIAL_L/R_ForeheadIn, ForeheadMid, ForeheadOut. [SRC, MetaHuman DNA docs]
  The mapping of each control to those joints: NOT FOUND.
- RigLogic maps the semantic channels (for example inner brow up/down) to joints, corrective blend
  shapes, and wrinkle triggering. [SRC, Epic DNA docs]
- Animated wrinkle maps: 3 color + 3 normal variants, masked by RGB channels. [SRC, Polyhammer docs]
  Which wrinkle map the forehead raise uses: NOT FOUND.
- What Speech2Face outputs on brow curves specifically: NOT FOUND. Measure it by reading the baked curves.

### 3.2 NVIDIA Audio2Face-3D
- Separate upper-face and lower-face controls: upper face strength (default 1.0, range 0-2), upper face
  smoothing (0.001 in the 1.3 config), face mask level (0.6, boundary between regions), face mask
  softness (0.0085). Emotion strength multiplier (0.6 in 2.0 docs); preferred emotion blend (0.5:
  0 = audio-inferred only, 1 = preferred only); cap on simultaneous emotions (3 or 6 by version).
  [SEC, NVIDIA ACE docs via search: https://docs.nvidia.com/ace/audio2face-3d-microservice/1.3/text/deployment/container-config.html]
- Emotion list and brow behaviour per emotion: NOT FOUND (tuning page returned 403).
- Design lesson [DESIGN]: they treat the upper face as its own channel with its own gain and smoothing.
  We do the same.

### 3.3 Speech Graphics SGX
- Extracts pitch, intensity, prosody, word and pause timing; "Bi-Tonal Modes" modulate expression from
  pitch and intensity changes; auto behaviour modes for positivity, negativity, effort, laughter; also
  breaths, blinks, eye darts, head motion. [SEC, 80.lv interviews; vendor claims]
  https://80.lv/articles/a-deep-dive-into-speech-graphics-facial-animation-solutions
- Their brow rules and numbers: NOT FOUND.

### 3.4 JALI
- JALI (SIGGRAPH 2016) covers jaw and lip only. A 2020 talk on Cyberpunk 2077 covers "paralingual"
  motion. Brow rules: NOT FOUND. https://www.dgp.toronto.edu/~elf/jali.html

### 3.5 ML research 2022-2026
- Deterministic speech-to-face models produce "no/muted motion in the upper region of the face".
  [SRC, FaceTalk, arXiv 2312.08459, as quoted in search]
- VOCA fails to synthesize realistic upper-face motion. [SEC]
- Some diffusion methods add blink and upper-face diversity with weak or no audio correlation. [SEC, 3DiFACE arXiv 2509.26233]
- EmoTalk neglects "subtle eyebrow raises"; EmoDiffusion (arXiv 2503.11028) models the upper face with
  its own VAE. [SEC]
- EMOTE (arXiv 2306.08990): emotion-controllable; FaceFormer has no emotion control. [SEC]
- Conclusion [DESIGN]: audio alone gives a weak brow signal. A separate, directed brow layer is what
  research systems and production tools both do. This supports our two-layer plan.

### 3.6 Animator practice
- Navone (Pixar): brows lead head and body; spontaneous = symmetric, deliberate = asymmetric; brows up
  with pitch up, down with pitch down (a trend); corrugator furrow for intense states; inner raise +
  furrow = sad; match upper-lid shape to brow shape. https://animationhelper.blogspot.com/2012/05/brows-have-it-victor-navone.html [SRC]
- Animation Mentor: "thought drives action"; do not change pose for every new emphasis; brows almost
  always lead an expression change. [SEC via search]
- Adrien Liv (DreamWorks): hit some accents ahead of the line and some behind it; brows move on
  diagonals. https://www.cgchannel.com/2024/10/10-subtle-tricks-to-improve-your-character-animation/ [SEC via search]
- Osipa, Stop Staring: for eyes and brows, emotion has priority over function. [SEC, O'Reilly TOC]
- A written "eyebrow dancing" rule with numbers: NOT FOUND. The research equivalent is rule 1.

---

## 4. Anatomy summary
- Frontalis medial fibres raise the inner brow (AU1); lateral fibres raise the outer brow (AU2). [SRC, FACS]
- Corrugator supercilii pulls brows down and together (vertical glabella lines); procerus / depressor
  glabellae and depressor supercilii pull the medial brow down. All code as AU4. [SRC, FACS]
- Orbicularis oculi orbital part = AU6 cheek raise (Duchenne marker); palpebral part = AU7 lid tightener. [SRC, FACS]
- AU1+4 together produce the oblique sad brow and forehead centre wrinkles. [SRC for the AU combo; wrinkle shape NOT FOUND]

---

## 5. Recommended algorithm for our pipeline [DESIGN unless marked]

### 5.1 Inputs
- F0 track (10 ms hop), RMS energy, phoneme and syllable timing (forced alignment), word list with
  stress, phrase boundaries (pauses > 200 ms [DESIGN]), and a mood tag per line
  (confident / seductive / warm / question / tease).
- Per singer: F0 range (5th to 95th percentile over the song).

### 5.2 Layers (added on top of Speech2Face, then clamped)
**A. Baseline (mood pose), slow.** Held per line, blended in over 300-500 ms [DESIGN].

| mood | raiseIn | raiseOut | down | lateral | cheekRaise | squintInner | cornerPull |
|---|---|---|---|---|---|---|---|
| confident | 0.00 | 0.05 | 0.05 | 0.05 | 0.25 | 0.15 | 0.25 |
| seductive | 0.00 | 0.08 one side, 0.02 other | 0.10 | 0.05 | 0.30 | 0.30 | 0.20, one side +0.05 |
| warm | 0.08 | 0.10 | 0.00 | 0.00 | 0.40 | 0.20 | 0.40 |

All values [DESIGN], on an assumed 0-1 control range (verify range first, section 3.1). Reasoning:
seductive borrows the slightly lowered lid and mild brow-down of the arousal data and the head-tilt /
slight-smile / direct-gaze flirt data (section 1.4), plus deliberate asymmetry (Navone). Warm and
Duchenne use AU6+12 (section 1.2). Keep raiseIn low in seductive and confident: AU1 is the sadness and
fear component (section 1.2).

**B. Prominence accents, fast.**
1. Candidates: stressed syllables whose F0 peak is at least 2 semitones above the phrase's running
   median AND energy above the phrase median [DESIGN].
2. Select at most ONE per intonation phrase (the highest-scoring one), plus the first accent of a new
   section or verse. Basis: most accents get no raise; raises cluster at topic starts and instructions
   (Flecha-Garcia) [rule SRC, numbers DESIGN].
3. Cooldown: no new accent raise within 1.2 s of the last peak [DESIGN].
4. Shape: onset 60 ms before the accented syllable's vowel onset (Flecha-Garcia mean); rise 100-150 ms,
   hold 100 ms, fall 150-250 ms (House 300 ms total; Gast 300-600 ms extent) [SRC basis, values DESIGN].
   Jitter onset by +/-40 ms so it stays inside the 100 ms tolerance (House) [DESIGN].
5. Amplitude: raiseOut 0.15-0.30 and raiseIn 0.5x of raiseOut, scaled by the F0 excursion in semitones
   (Gast: pre-peak pitch shape predicts raise height) [DESIGN]. House used only 4% of range and it was
   visible in motion, so start low.
6. Symmetry: symmetric by default; in seductive or tease mood, 70% on one side [DESIGN, from Navone's
   deliberate-asymmetry rule].
7. Probability gate: even a selected accent gets a raise only 60% of the time; otherwise give it a
   head nod instead (House: head nods are the stronger prominence cue) [DESIGN].

**C. Singing pitch-height track, slow.** For sung lines only: raiseOut += k * (F0 position in singer
range, 0 at median, 1 at the 95th percentile), k = 0.15, low-passed at 1.5-2 Hz (attack ~250 ms,
release ~400 ms), only on notes held longer than 300 ms [DESIGN, basis Huron 2009]. Large ascending
intervals (>= 5 semitones) add a one-off accent raise (basis Thompson and Russo) [DESIGN].

**D. Questions.** Yes/no or echoic questions: hold a raise (raiseIn 0.2, raiseOut 0.25) from 250 ms
before the question's last stressed word to the end of the phrase (Kim et al. ~250 ms window) [SEC basis].
Rhetorical or teasing questions: one-sided raise. Real uncertainty: slight down 0.1 (Navone trend).

**E. Listening and holds.** Between lines (silence > 600 ms [DESIGN]): optional eyebrow flash
(raiseIn+Out 0.3, total ~200 ms, Grammer/Eibl-Eibesfeldt) at a phrase start addressed to camera, at most
once per 8-10 s [DESIGN]. Long holds read as conversational signals (House), so use holds for attitude,
short shapes for emphasis.

### 5.3 Combination and limits
- Sum Speech2Face brow curves + A + B + C + D, then clamp. Max total raiseIn 0.45, raiseOut 0.55,
  down 0.4 [DESIGN; prevents surprise read, which is the full symmetric AU1+2].
- Mutual exclusion: if down > 0.15, scale raiseIn by (1 - down) so the sad AU1+4 brow does not appear by
  accident (Navone; FACS sadness) [rule SRC, formula DESIGN].
- Couple lateral to down: lateral = 0.6 x down (Epic: full AU4 = down + lateral; Liv: brows go down
  and together) [rule SRC, ratio DESIGN].
- Brows lead: brow keys start 2-4 frames (at 30 fps) before matching head motion (Navone) [rule SRC, frames DESIGN].
- Duchenne: whenever cornerPull > 0.2, cheekRaise >= 0.6 x cornerPull and squintInner 0.1-0.3
  (AU6+12) [rule SRC, ratios DESIGN]. Without AU6 the smile reads as non-Duchenne.
- Upper lid follows brow: on a raise, reduce squint slightly; on brow-down, add squint (Navone: match lid
  shape to brow) [rule SRC].

### 5.4 Avoid
- A raise on every accent or every F0 peak (Flecha-Garcia; Cave 71%; Cvejic 2011).
- Direct F0 -> brow mapping in speech ("very unnatural", House 2001 citing Cave). Use the continuous
  pitch track (layer C) only for sustained sung notes.
- Symmetric full AU1+2 in a confident or seductive line: reads as surprise or fear.
- Inner raise plus brow-down: reads as sadness.
- Brow raise out of sync by more than ~100 ms: moves the emphasis to the wrong word (House).
- Long uniform holds of a raised brow: read as a question, interest, or irony (House).

### 5.5 How to verify (proposal)
- Render the same line three ways: Speech2Face only, + layer A, + layers A-D. Owner picks.
- Measure: raises per phrase (target <= 1), raise onset vs accent vowel onset (target -100..+40 ms),
  share of frames with raiseIn > 0.3 and down > 0.15 simultaneously (target 0).

---

## 6. Gaps (NOT FOUND this session)
- MetaHuman CTRL_* min/max ranges and control-to-joint mapping.
- Speech2Face brow output behaviour.
- Audio2Face per-emotion brow behaviour and emotion list.
- Ekman's baton/underliner/question-mark brow taxonomy (in Ekman 1979, not opened).
- Brow AUs in the flirt study; any FACS study of eyebrows in seduction.
- Brow displacement per semitone in singing; any Slovak-language brow data.
- Exact percentage of accents accompanied by a brow raise.

## 7. Source list
- House, Beskow, Granstrom 2001, Eurospeech: https://www.isca-archive.org/eurospeech_2001/house01_eurospeech.pdf
- Cave et al. 1996, ICSLP: https://www.isca-archive.org/icslp_1996/cave96_icslp.html
- Flecha-Garcia thesis: https://era.ed.ac.uk/items/c1dfbb39-7eef-4b4d-aec0-8102dcc50453 ; 2010 paper doi 10.1016/j.specom.2009.12.003
- Gast 2023, Behavioral Sciences 13(1):52: https://pmc.ncbi.nlm.nih.gov/articles/PMC9854528
- Krahmer et al. 2002: https://www.isca-archive.org/icslp_2002/krahmer02_icslp.html
- Swerts and Krahmer 2007 AVSP: https://www.isca-archive.org/avsp_2007/swerts07_avsp.html
- Kim, Cvejic, Davis 2014: https://researchnow.flinders.edu.au/en/publications/tracking-eyebrows-and-head-gestures-associated-with-spoken-prosod/
- Cvejic et al. 2011: https://www.isca-archive.org/interspeech_2011/cvejic11_interspeech.html
- Cruz, Swerts, Frota (Portuguese questions): https://www.cambridge.org/core/services/aop-cambridge-core/content/view/5B46DA30CB51F113DE55CF42ED031707/S1866980824000632a.pdf/talking-heads-in-portuguese-sign-and-spoken-languages.pdf
- Huron, Dahl, Johnson 2009: https://doaj.org/article/6876121d77644b20ba64f9d8bd6273f8
- Singing face substitution 2021: https://pmc.ncbi.nlm.nih.gov/articles/PMC8599708
- FACS: https://en.wikipedia.org/wiki/Facial_Action_Coding_System ; mapping table https://pmc.ncbi.nlm.nih.gov/articles/PMC7264164/table/T3
- Ekman 1979 secondary: https://www.frontiersin.org/articles/10.3389/fpsyg.2013.00115/full
- Matsumoto 1992 contempt: https://www.davidmatsumoto.com/content/1992%20More%20Evidence%20for%20the%20Universality%20of%20a%20Contempt%20Expression.pdf
- Affectiva smirk paper: https://www.affectiva.com/wp-content/uploads/2017/03/Smile_or_Smirk_Automatic_Detection_of_Spontaneous_Asymmetric_Smiles_to_Understand_Vi.pdf
- Eyebrow flash: https://en.wikipedia.org/wiki/Eyebrow_flash
- Flirt study: https://www.sciencedaily.com/releases/2020/09/200914112143.htm
- Sexual excitement AUs: https://improbable.com/2011/12/28/frowns-scowls-and-grimaces/
- Epic MetaHuman curves: https://dev.epicgames.com/documentation/metahuman/mh-standards-docs/mha_index ,
  .../browRaiseInL , .../browDownL , .../browLateralL , .../eyeCheekRaiseL
- MetaHuman DNA: https://dev.epicgames.com/documentation/metahuman/metahuman-dna-rig-definition-and-rig-operation
- Wrinkle maps: https://docs.polyhammer.com/character-dna/terminology
- Audio2Face config: https://docs.nvidia.com/ace/audio2face-3d-microservice/1.3/text/deployment/container-config.html
- Speech Graphics: https://80.lv/articles/a-deep-dive-into-speech-graphics-facial-animation-solutions ; https://80.lv/articles/leveraging-voice-analysis-for-immersive-interactions-with-speech-graphics-metadata
- JALI: https://www.dgp.toronto.edu/~elf/jali.html
- EMOTE: https://arxiv.org/pdf/2306.08990 ; FaceTalk: https://arxiv.org/html/2312.08459v2 ; 3DiFACE: https://arxiv.org/html/2509.26233v1 ; EmoDiffusion: https://arxiv.org/pdf/2503.11028
- Navone: https://animationhelper.blogspot.com/2012/05/brows-have-it-victor-navone.html
- CG Channel 2024 (Liv): https://www.cgchannel.com/2024/10/10-subtle-tricks-to-improve-your-character-animation/
- Osipa, Stop Staring: https://www.oreilly.com/library/view/stop-staring-facial/9780471789208/pt03.html
