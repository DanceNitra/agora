# Lips A-F audit against p6 (independent, 2026-11-08)

Inputs: `lips_ABCDEF_sheet.png`, `lips_ABCDEF_sheet.json`, `beauty/depesa_p6.png`.
Depth is read as the lip L divided by the tile's own skin_ring L, because p6 is a much darker photo.

## Reference p6
- Colour: warm muted rose-terracotta. Hue 30.1 deg, chroma 35.8.
- Depth: lip L about 0.75 of skin L (upper 21.2, lower 26.7, skin 32.5).
- Finish: satin. Specular fraction 0.004, a soft broad sheen on the lower lip and no hard streak.
- Distribution: centre lighter than rim (+4.3 L). No visible liner (rim minus body -0.1).
- Upper vs lower: 5.5 L apart.
- Shape: closed-mouth smirk. Thin upper lip (0.087 mw), full lower lip (0.184 mw).
- Caveat: p6 is lit by a strong orange key (see the chin and collar). Part of its warm hue can come from the light and not from the lipstick.

## Per tile

| tile | hue deg | chroma | lip/skin L | specular | centre minus rim | upper vs lower L | reads as |
|---|---|---|---|---|---|---|---|
| p6 | 30.1 | 35.8 | 0.75 | 0.004 | +4.3 | 5.5 | rose-terracotta satin |
| A | 26.0 | 45.6 | 0.71 | 0.024 | -5.1 | 3.5 | raspberry-red gloss |
| B | 17.5 | 39.8 | 0.62 | 0.032 | -7.5 | 4.7 | plum-berry gloss |
| C | 32.9 | 60.7 | 0.73 | 0.021 | -4.3 | 2.3 | bright fire-engine red gloss |
| D | 29.9 | 38.1 | 0.80 | 0.000 | +4.7 | 9.8 | nude rose, satin-matte |
| E | 28.8 | 45.7 | 0.77 | 0.000 | +4.7 | 10.6 | warm coral-rose, satin-matte |
| F | 21.8 | 48.5 | 0.71 | 0.002 | +4.0 | 9.9 | deep rose-berry, satin |

- **A:** Hue is 4 deg cooler than p6, and the colour is deeper and 27% more saturated. That direction fits "more seductive". Defects: a long white specular streak along the lower lip reads as wet plastic. The centre is darker than the rim, which inverts p6's distribution. The rim is 2.1 L lighter than the body, so the edge fades into the skin with no definition.
- **B:** Hue is 12.6 deg cooler than p6, a plum or mauve family. That is the wrong lipstick for this reference. It is the deepest tile (0.62). The same gloss streak and inverted centre as A. The colour pools darker in the mouth corners.
- **C:** Hue is the closest of the glosses (32.9), but chroma is 1.7 times p6. It reads as a costume or pin-up red, not p6's lipstick. It has the hardest outer edge, close to a cut-out. Gloss streak and inverted centre as A.
- **D:** The closest saturation to p6 and the same distribution, but it is lighter than p6 relative to skin (0.80). It reads as nude. It is not more seductive than the reference. The upper lip is about 10 L darker than the lower, so the two lips look like two different products.
- **E:** The closest hue to p6 (28.8) with 28% more chroma. Satin finish and p6's centre-lighter distribution. Too light against the skin (0.77), and the lower lip leans coral or peach. Same two-tone upper vs lower lip as D.
- **F:** The deepest of the satin tiles (0.71, the same as A) and the most saturated after C. Distribution matches p6. Hue is 8 deg cooler than p6, a rose-berry rather than terracotta. Same two-tone upper vs lower lip as D.

Common to all six tiles:
- Lip geometry is identical across tiles (upper 0.098, lower 0.167 mw). No variant makes the lips fuller. The render lower lip is thinner than p6's (0.167 vs 0.184 mw), and the open smile shows teeth where p6 is closed. Fullness and shape cannot be compared fairly from this pose.
- None of the tiles has a defined lip line. p6 has none either, so this is a match, not a defect. A soft liner a shade deeper would help the "more seductive" goal.
- No colour on the teeth or on the surrounding skin is visible at this resolution. The edges of D, E, and F are soft and clean.

## Fit to the owner's words

The owner asks for lips more seductive than p6 and the right lipstick.

1. **Best base: F, with E's hue.** F gives the depth and saturation step above p6 with p6's satin finish and colour distribution. Still needed: warm the hue from 21.8 to about 26-28 deg (toward E), close the upper vs lower gap from about 10 L to about 5 L, and add a small, soft lower-lip sheen (specular about 0.005-0.01, broad, never a streak).
2. **Alternative if the owner wants gloss: A.** Hue and depth fit, and gloss reads more seductive to many viewers. Still needed: break the specular streak into a soft highlight, flip the distribution so the centre is lighter than the rim, and stop the rim fading into the skin.
3. **Reject:** B (wrong colour family), C (too saturated, costume red), and D (nude, less seductive than p6).

## What this audit cannot judge
- Lip shape and fullness with a closed mouth, because every render is an open smile and p6 is closed.
- How each lipstick reads in motion, under the film's lighting and grade, and next to the eye makeup.
- Fine texture at final resolution: the sheet tiles are about 430 px wide.
- p6's true lipstick colour without its orange key light. The target hue of 30 deg can be biased warm.
- Whether the upper vs lower gap in D, E, and F comes from the material or the lighting. A, B, and C share the same geometry and light and show a smaller gap, which points to the material.
