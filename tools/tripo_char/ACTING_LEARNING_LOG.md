# Acting learning log

One entry per audited run, written by `perf_audit.py`. A row marked `new` is seen in this run only (the singer's); a row seen in other runs is Yuki's or the pipeline's and is fixed first. Nothing here is a visual verdict: frames are checked by eye before any claim.

## 2026-11-15 18:17 sinead_100_60 (Sinead O'Connor, Nothing Compares 2 U, 1990)

Frames 1801, both faces 1779. Means over channels that move in the singer, with the null control (Yuki shifted 10 s) in brackets:
- upper: 9 channels, corr +0.67 (null 0.09), amp 1.02
- mouth_jaw: 17 channels, corr +0.60 (null 0.11), amp 0.96
- gaze: 8 channels, corr +0.47 (null 0.04), amp 0.68
- brow shape, inner to outer movement: singer 0.53, Yuki 0.13 (Yuki tilts the brow the other way)

Composite checks correlate after removing the 3 s trend.

| check | corr | amp | verdict | seen in other runs |
|---|---|---|---|---|
| sad_brow_oblique (AU1 without AU2) | +0.42 | 1.81 | OVER | new |
| brow_knit (AU4) | +0.59 | 0.57 | WEAK | new |
| sad_mouth (AU15 against AU12) | +0.84 | 0.44 | WEAK | brel_nmqp |
| lip_press (AU24) | +0.26 | 0.28 | TIMING | new |
| smile_asymmetry L-R | +0.17 | 0.51 | TIMING | new |
| blink_asymmetry L-R | -0.01 | 0.42 | TIMING | brel_nmqp |
| brow_asymmetry L-R | -0.18 | 0.52 | TIMING | brel_nmqp |
| gaze_horizontal | +0.33 | 0.40 | TIMING | brel_nmqp |
| gaze_vertical | +0.84 | 0.88 | OK | brel_nmqp |
| browDownLeft | +0.71 | 0.47 | WEAK | new |
| browDownRight | +0.60 | 0.68 | WEAK | new |
| browInnerUp | +0.70 | 0.37 | WEAK | brel_nmqp |
| browOuterUpRight | +0.35 | 1.99 | TIMING | new |
| eyeLookInLeft | +0.42 | 0.33 | WEAK | new |
| eyeLookInRight | -0.08 | 0.37 | TIMING | brel_nmqp |
| eyeLookOutLeft | -0.01 | 0.42 | TIMING | brel_nmqp |
| eyeLookOutRight | +0.34 | 0.35 | TIMING | brel_nmqp |
| mouthFunnel | +0.63 | 4.22 | OVER | new |
| mouthLowerDownLeft | +0.85 | 0.45 | WEAK | brel_nmqp |
| mouthLowerDownRight | +0.84 | 0.59 | WEAK | brel_nmqp |
| mouthPressLeft | +0.28 | 0.28 | TIMING | new |
| mouthPressRight | +0.09 | 0.25 | TIMING | new |
| mouthPucker | +0.42 | 2.08 | OVER | brel_nmqp |
| mouthRollLower | +0.34 | 0.47 | TIMING | new |
| mouthRollUpper | +0.28 | 0.85 | TIMING | new |
| mouthShrugLower | +0.67 | 0.37 | WEAK | new |
| mouthSmileLeft | +0.86 | 0.44 | WEAK | brel_nmqp |
| mouthSmileRight | +0.85 | 0.45 | WEAK | brel_nmqp |
| mouthStretchLeft | +0.49 | 0.02 | DEAD | new |

Fixes:
- sad_brow_oblique (AU1 without AU2): OVER. Too strong: damp the channels that form it.
- brow_knit (AU4): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- sad_mouth (AU15 against AU12): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- lip_press (AU24): TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- smile_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- blink_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- brow_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- gaze_horizontal: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- fit gains for yuki_expr_fit.py: browDownLeft x2.153, browDownRight x1.471, browInnerUp x2.703, eyeLookInLeft x3.0, mouthFunnel x0.33, mouthLowerDownLeft x2.249, mouthLowerDownRight x1.704, mouthPucker x0.48, mouthShrugLower x2.677, mouthSmileLeft x2.268, mouthSmileRight x2.229

## 2026-11-15 18:22 brel_nmqp (Jacques Brel, Ne me quitte pas, TV 1966)

Frames 1800, both faces 1800. Means over channels that move in the singer, with the null control (Yuki shifted 10 s) in brackets:
- upper: 9 channels, corr +0.75 (null 0.10), amp 1.27
- mouth_jaw: 14 channels, corr +0.57 (null 0.08), amp 1.40
- gaze: 8 channels, corr +0.42 (null 0.09), amp 0.71
- brow shape, inner to outer movement: singer 1.44, Yuki 0.74 (Yuki tilts the brow the other way)

Composite checks correlate after removing the 3 s trend.

| check | corr | amp | verdict | seen in other runs |
|---|---|---|---|---|
| sad_brow_oblique (AU1 without AU2) | +0.23 | 0.86 | TIMING | new |
| brow_knit (AU4) | +0.44 | 1.43 | OK | new |
| sad_mouth (AU15 against AU12) | +0.76 | 0.64 | WEAK | sinead_100_60 |
| lip_press (AU24) | +0.56 | 0.38 | WEAK | new |
| smile_asymmetry L-R | +0.67 | 0.84 | OK | new |
| blink_asymmetry L-R | +0.12 | 0.86 | TIMING | sinead_100_60 |
| brow_asymmetry L-R | +0.11 | 0.92 | TIMING | sinead_100_60 |
| gaze_horizontal | +0.03 | 0.68 | TIMING | sinead_100_60 |
| gaze_vertical | +0.87 | 0.81 | OK | sinead_100_60 |
| browDownRight | +0.84 | 1.43 | OVER | new |
| browInnerUp | +0.81 | 0.65 | WEAK | sinead_100_60 |
| eyeLookInLeft | +0.06 | 0.50 | TIMING | new |
| eyeLookInRight | +0.02 | 0.72 | TIMING | sinead_100_60 |
| eyeLookOutLeft | -0.08 | 0.90 | TIMING | sinead_100_60 |
| eyeLookOutRight | +0.04 | 0.40 | TIMING | sinead_100_60 |
| eyeSquintLeft | +0.58 | 1.87 | OVER | new |
| eyeSquintRight | +0.37 | 1.46 | TIMING | new |
| jawOpen | +0.68 | 0.52 | WEAK | new |
| mouthDimpleLeft | +0.48 | 4.86 | OVER | new |
| mouthLowerDownLeft | +0.42 | 0.57 | WEAK | sinead_100_60 |
| mouthLowerDownRight | +0.46 | 0.64 | WEAK | sinead_100_60 |
| mouthPressLeft | +0.54 | 0.58 | WEAK | new |
| mouthPressRight | +0.58 | 0.23 | WEAK | new |
| mouthPucker | +0.55 | 1.65 | OVER | sinead_100_60 |
| mouthRollLower | +0.47 | 2.05 | OVER | new |
| mouthSmileLeft | +0.80 | 0.68 | WEAK | sinead_100_60 |
| mouthSmileRight | +0.79 | 0.61 | WEAK | sinead_100_60 |
| mouthStretchRight | +0.47 | 0.08 | DEAD | new |
| mouthUpperUpLeft | +0.64 | 3.15 | OVER | new |
| mouthUpperUpRight | +0.67 | 3.06 | OVER | new |

Fixes:
- sad_brow_oblique (AU1 without AU2): TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- sad_mouth (AU15 against AU12): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- lip_press (AU24): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- blink_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- brow_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- gaze_horizontal: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- fit gains for yuki_expr_fit.py: browDownRight x0.698, browInnerUp x1.532, eyeSquintLeft x0.534, jawOpen x1.938, mouthDimpleLeft x0.33, mouthLowerDownLeft x1.746, mouthLowerDownRight x1.569, mouthPressLeft x1.728, mouthPressRight x3.0, mouthPucker x0.607, mouthRollLower x0.488, mouthSmileLeft x1.478, mouthSmileRight x1.632, mouthUpperUpLeft x0.33, mouthUpperUpRight x0.33

## 2026-11-15 18:45 brel_nmqp_fit (Jacques Brel, Ne me quitte pas, TV 1966)

Frames 1800, both faces 1800. Means over channels that move in the singer, with the null control (Yuki shifted 10 s) in brackets:
- upper: 9 channels, corr +0.75 (null 0.11), amp 1.28
- mouth_jaw: 14 channels, corr +0.55 (null 0.09), amp 1.34
- gaze: 8 channels, corr +0.43 (null 0.09), amp 0.70
- brow shape, inner to outer movement: singer 1.44, Yuki 1.00

Composite checks correlate after removing the 3 s trend.

| check | corr | amp | verdict | before (base run) |
|---|---|---|---|---|
| sad_brow_oblique (AU1 without AU2) | +0.52 | 0.69 | WEAK | +0.23 / 0.86 TIMING |
| brow_knit (AU4) | +0.43 | 1.44 | OVER | +0.44 / 1.43 OK |
| sad_mouth (AU15 against AU12) | +0.76 | 1.16 | OK | +0.76 / 0.64 WEAK |
| lip_press (AU24) | +0.44 | 0.44 | WEAK | +0.56 / 0.38 WEAK |
| smile_asymmetry L-R | +0.58 | 1.42 | OK | +0.67 / 0.84 OK |
| blink_asymmetry L-R | +0.13 | 0.99 | TIMING | +0.12 / 0.86 TIMING |
| brow_asymmetry L-R | +0.05 | 0.87 | TIMING | +0.11 / 0.92 TIMING |
| gaze_horizontal | +0.03 | 0.68 | TIMING | +0.03 / 0.68 TIMING |
| gaze_vertical | +0.87 | 0.79 | OK | +0.87 / 0.81 OK |
| browDownLeft | +0.83 | 1.48 | OVER | +0.83 / 1.42 OK |
| browDownRight | +0.85 | 1.39 | OK | +0.84 / 1.43 OVER |
| browInnerUp | +0.92 | 0.82 | OK | +0.81 / 0.65 WEAK |
| eyeLookInLeft | +0.08 | 0.48 | TIMING | +0.06 / 0.50 TIMING |
| eyeLookInRight | +0.01 | 0.74 | TIMING | +0.02 / 0.72 TIMING |
| eyeLookOutLeft | -0.05 | 0.87 | TIMING | -0.08 / 0.90 TIMING |
| eyeLookOutRight | +0.02 | 0.39 | TIMING | +0.04 / 0.40 TIMING |
| eyeSquintLeft | +0.55 | 1.89 | OVER | +0.58 / 1.87 OVER |
| eyeSquintRight | +0.30 | 1.42 | TIMING | +0.37 / 1.46 TIMING |
| jawOpen | +0.73 | 0.65 | WEAK | +0.68 / 0.52 WEAK |
| mouthDimpleLeft | +0.36 | 4.61 | TIMING | +0.48 / 4.86 OVER |
| mouthLowerDownLeft | +0.39 | 0.60 | TIMING | +0.42 / 0.57 WEAK |
| mouthLowerDownRight | +0.45 | 0.70 | WEAK | +0.46 / 0.64 WEAK |
| mouthPressLeft | +0.32 | 0.70 | TIMING | +0.54 / 0.58 WEAK |
| mouthPressRight | +0.58 | 0.21 | WEAK | +0.58 / 0.23 WEAK |
| mouthPucker | +0.63 | 1.56 | OVER | +0.55 / 1.65 OVER |
| mouthRollLower | +0.42 | 0.89 | OK | +0.47 / 2.05 OVER |
| mouthRollUpper | +0.43 | 0.42 | WEAK | +0.45 / 0.92 OK |
| mouthSmileLeft | +0.78 | 1.17 | OK | +0.80 / 0.68 WEAK |
| mouthSmileRight | +0.80 | 1.19 | OK | +0.79 / 0.61 WEAK |
| mouthStretchRight | +0.43 | 0.11 | DEAD | +0.47 / 0.08 DEAD |
| mouthUpperUpLeft | +0.66 | 3.09 | OVER | +0.64 / 3.15 OVER |
| mouthUpperUpRight | +0.66 | 2.81 | OVER | +0.67 / 3.06 OVER |

Fixes:
- sad_brow_oblique (AU1 without AU2): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- brow_knit (AU4): OVER. Too strong: damp the channels that form it.
- lip_press (AU24): WEAK. Strength missing: raise the channels that form it (fit gains) and check the shape on frames.
- blink_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- brow_asymmetry L-R: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- gaze_horizontal: TIMING. Timing or detection does not follow the singer; check the solve on frames before any gain.
- fit gains for yuki_expr_fit.py: browDownLeft x0.676, eyeSquintLeft x0.53, jawOpen x1.547, mouthLowerDownRight x1.434, mouthPressRight x3.0, mouthPucker x0.641, mouthRollUpper x2.383, mouthUpperUpLeft x0.33, mouthUpperUpRight x0.356
