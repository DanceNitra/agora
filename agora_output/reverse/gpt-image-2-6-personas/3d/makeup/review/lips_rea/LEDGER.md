# REA ledger: how the p6 lipstick is built

Example: `beauty/depesa_p6.png` (1024x1536). Instrument: `makeup/lip_measure.py` on the MediaPipe landmarks in `makeup/p6_landmarks.json`. Output: `p6.json`.

p6 is a darker image than our render (skin ring L 32.5 against 59.6), so every comparison is relative to the skin.

| Question | Tag | Evidence | Limit | Next check |
|---|---|---|---|---|
| Lip depth against skin | SEEN | lip L 24 / skin L 32.5 = 0.74 | One image | Same ratio on the D-F renders |
| Hue | SEEN | lower lip hue 30 deg (warm rose-red), chroma 35.8 against skin 25 | | |
| Ombre | SEEN | lower-lip core +4.3 L and chroma 35 against rim 27 | | |
| Hard dark liner | SEEN: none | rim L minus body L = -0.1 | | |
| Upper lip deeper than lower | SEEN | -5.5 L | Part shading, part pigment: UNKNOWN which | |
| Finish | SEEN: satin | 0.4 % specular pixels on the lower lip; renders A, B show 2.4-3.2 % | | |
| Fullness | SEEN | lower lip 0.184 mouth widths, upper 0.087, ratio 2.1; render 1.7 | Mouth open in render frame 57 | |
| Overline in p6 | UNKNOWN | landmarks follow the painted edge, so an overline cannot be told from the real edge | | |

## Variants

- D: p6 match. Warm rose, ombre centre, soft deeper edge, satin (roughness 0.35), no overline.
- E: more seductive. Deeper rose-red, lower lip overlined at the centre (2.5 % mouth width), raised cupid's bow, stronger ombre, soft gloss (0.15).
- F: deep berry-red, blurred edge, centre glow, overline, wet gloss (0.08).

Painted in UV by `makeup/lip_paint.py` from `makeup/lips_{D,E,F}.json`; MetaHuman lip layer at opacity 0.2 sets roughness only.

## Deep dive 2: how MetaHuman builds and renders the lips (2026-11-08)

Source: UE 5.8.4 engine headers (`MetaHumanCharacterEditorSubsystem.h`, `MetaHumanCharacterMakeup.h`) and the live material `MI_Face_Skin_Baked_LOD1_VT` read by `ue/fit/_q24.py` (`ue/fit/kf_mat_*.json`).

| Layer | What controls it | Tag | Evidence |
|---|---|---|---|
| Lip shape | Face identity state; 81 sculpt landmarks, moved by `translate_face_landmarks`, or `set_face_model_coefficients`, or `fit_state_to_target_vertices` | SEEN | header lines 1276-1319, 1414 |
| Lip landmarks | corners 48/32, bow peaks 47/31, upper centre 5, lip line 50 + 49/34, lower lip 9/16 and 4 | INFERRED from 3D positions (`ue/fit/kf_landmarks3d.json`) | test move confirms |
| Expressions after a shape change | rig must be rebuilt: `request_auto_rigging` (JOINTS_AND_BLEND_SHAPES), then texture sources, then build | SEEN | `ue/fit/ue_rigtex_kf.py` already used |
| Lip colour in render | `Basecolor Baked VT` (our patched texture) | SEEN | material dump |
| Lip gloss in render | `SRMF Baked VT` = T_Head_LOD1_SRMF_VT (roughness baked at build). The MetaHuman lip makeup roughness only reaches the render through this bake | SEEN (texture), INFERRED (makeup path) | material dump |
| Lip lines | pore normals `Rot/Scale/Intensity Lips` (1.5 / 0.5) + baked normal | SEEN | material dump |
| Lip wrinkles when moving | wrinkle maps `wm1/wm3 ... lips_UL/UR/DL/DR`, `purse_*` | SEEN | material dump |

## Shape: p6 against our face with the mouth closed (clip frame 0), in eye-distance units

| Measure | p6 | ours | Note |
|---|---|---|---|
| Mouth width | 1.667 | 1.445 | p6 15 % wider; part of it is the smirk stretch |
| Upper lip height at centre | 0.149 | 0.181 | ours fuller upper lip |
| Lower lip height | 0.313 | 0.320 | equal |
| Lower / upper | 2.1 | 1.8 | p6 reads pouty because the upper lip is thin and the lower lip full |
| Cupid's bow dip | 0.054 | 0.052 | equal |
| Corners | lifted (smirk) | neutral | smile task, not shape |

Overlay: `review/lips_rea/shape_overlay_p6_vs_clip0000.png` (green p6, magenta ours).

## Colour G (render frame 57) against p6

lip/skin L 0.75 (p6 0.74), hue 27 deg (p6 30), upper-lower -5.5 L (p6 -5.5), specular 0.7 % (p6 0.4 %).
