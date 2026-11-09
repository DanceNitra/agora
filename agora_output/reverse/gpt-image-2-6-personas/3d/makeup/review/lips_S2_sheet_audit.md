# Lips S2 audit (independent)

Date: 2026-11-09. Inputs: `lips_S2_sheet.png`, `lips_rea/shape_overlay_S2.png`, `beauty/depesa_p6.png`, `lips_S2_sheet.json`. Pixel means are my own crops of the sheet (approximate boxes).

## Verdict

Not ready to show. Shape moved toward p6 on width and on the upper-to-lower ratio, and it is fuller than p6, which fits the "more seductive" brief. Two defects block it: teeth show through a slit in the closed mouth, and the corners stay level where p6 curls up into a smirk. The lipstick colour did not change between the two smile tiles.

## Shape (units: inner-eye-corner distance)

| measure | p6 | before closed | new closed | new vs p6 |
|---|---|---|---|---|
| width | 1.667 | 1.445 | 1.573 | -5.6 % (before -13.3 %) |
| upper | 0.150 | 0.181 | 0.206 | +37 % |
| lower | 0.312 | 0.320 | 0.395 | +27 % |
| lower/upper | 2.088 | 1.772 | 1.913 | closer (before 1.772) |

Moved toward p6:
- Width: the gap to p6 fell from 13 % to 6 %. The left corner now sits on the green outline.
- Lower-to-upper balance: 1.77 to 1.91, against 2.09 in p6.

Moved away or still off:
- Corners: p6's right corner lifts high and outward (green reaches about 70 px further right and higher on the overlay). The new right corner ends lower and short. The new mouth reads neutral. p6 reads as a closed-lip smirk, and that lift is most of its seductive look.
- Upper lip: 37 % taller than p6, so the ratio still falls short. p6's upper lip is thin with a soft, low cupid's bow. The new one has two pronounced bow peaks that sit above the green line.
- Lower lip: 27 % fuller than p6. Within the "more seductive" brief I accept this, but the volume is centred. p6's lower lip is deepest right of centre, following the smirk.

## Colour and finish (smile tiles only)

- Before smile lower lip: RGB about 190, 75, 73. New smile: 187, 69, 66. The difference is under 4 %, so S2 did not change the lipstick.
- Against p6 (118, 44, 43 under dark warm light) the hue and saturation match closely; the brightness gap comes from lighting, so I cannot call the colour wrong from these images. Under neutral light the new shade reads as bright coral-red. p6 reads as a muted brick-rose. If "the right lipstick" means p6's shade, deepen it one step toward brick (less orange, slightly darker).
- Finish: new is wet gloss with a broad highlight band on the lower lip. p6 is satin-wet with visible vertical lip lines. Add lip-line detail to the normal or roughness map, and narrow the highlight.

## Defects

1. Teeth visible in the closed pose: a pale slit of teeth across the centre between the lips. "Before, closed" had no gap. p6's lips are sealed. Must fix: close the lip seam (jaw or lip-press blend) or darken the mouth interior in that pose.
2. Midline split on the upper lip: a hard vertical change at the centre (left half about 182, 69, 61; right half about 128, 46, 49). It is also in "before". Part of it is the pink light from the right (the nose shows the same tint), but the edge is too sharp for light alone. Check for a mirrored-UV or normal seam.
3. Left/right asymmetry of the lower lip: left about 211, 94, 81, right about 163, 62, 65. Likely lighting. Confirm with a neutral, frontal light render.
4. Edges: no colour bleed visible. The edges are soft at this resolution; I cannot judge liner sharpness.

## Directions for S3

1. Seal the closed mouth (no teeth).
2. Lift both corners, the right one more, toward the green outline; push the lower lip's deepest point slightly right of centre.
3. Reduce upper-lip height about 15 to 20 % and soften the cupid's bow peaks; keep the lower lip as it is or reduce it about 5 %.
4. Widen another about 4 % to reach p6.
5. Deepen the shade toward brick-rose; add lip-line texture; narrow the gloss highlight.

## Cannot judge from these images

- True lipstick colour, because p6 and the render use different light. A side-by-side under matched light is needed.
- Profile pout and lip projection: all tiles are frontal.
- Motion: seam or teeth behaviour between the closed and smile poses.
- Fine edge sharpness, because the tiles are soft at this size.
