AUDITOR: independent subagent, saw only the sheet, the two frames, the measurements and the v24 audit

# v25 brow audit against reference p6

Image-left brow = character's right brow. Image-right brow = character's left brow. Eye width = ew. Pixel estimates come from the sheet close-up, where one eye is about 200 px wide in the render strip and about 150 px wide in the reference strip. The reference face is tilted and turned, so angles and spacing carry roughly plus or minus 5 degrees and 0.1 ew of uncertainty.

| Part | Reference p6 | Render v25 | Verdict | vs v24 |
|---|---|---|---|---|
| Head: position | Low, at the nose root, the inner end angles DOWN into the nose, which gives the intense look | Image-left: the top edge now dips toward the nose, so the head is lower than the body. Image-right: the head sits low, but its end is a rounded lower corner and does not angle into the nose | CLOSE | improved |
| Head: width and softness | Soft, feathered, upward strokes, skin visible, no outline | Image-left head ends in a ragged hair fringe, less of a stamp than v24. Image-right head is still a rounded, filled blob. Both heads are as opaque as the body, with no lighter zone and no upward strokes | WRONG | slightly improved |
| Body: thickness | About 0.3 ew at the thickest, then thins steadily from the break to the tail | About 0.3 ew, comparable, but stays at full thickness until about 85 % of the length | CLOSE (profile WRONG, see tail) | stayed |
| Body: density and holes | Dense, single hairs readable, skin visible at the edges | Opaque, nearly uniform black fill; a few faint streaks, no skin visible inside; fringe only at the outline. brow_holes ignored as instructed | WRONG | stayed |
| Top edge: shape and angle | Near-straight rise from head to break, about 15 to 20 degrees in this tilted view | Both sides now a fairly straight rise, the v24 hump on image-left is mostly gone. Rise is flatter, about 8 to 12 degrees | CLOSE | improved |
| Break point: position and sharpness | About 65 % of the length, clear but soft angle | Both sides break at about 80 to 85 %, rounded; the break is now present on both sides | WRONG (too far out) | improved |
| Tail: length, direction, taper | Long, drops gently toward the temple, tapers to a fine point | Image-left: short, drops steeply, ends in a ragged blunt end. Image-right: almost no tail, the brow stops shortly after the break with a hairy blunt end. No taper to a point on either side | WRONG | stayed |
| Height above the eye and against the bone | Low over the eye; bone sits just above the eye | Measured: top 0.187 to 0.189 ew above the crest, bottom 0.051 to 0.052 ew below it; the crest falls in the lower third of the brow, which was the v24 target (+0.05 to +0.08). The eye-to-brow gap is larger than in the reference, as intended by the brief | MATCH (against the bone), larger gap above the eye by design | improved |
| Spacing between the brows | About 1.1 ew | About 0.95 to 1.0 ew in the close-up, about 1.2 ew in the full frame; the difference comes from the measurement, not from the render. Inside tolerance | CLOSE | stayed |
| Texture | Black-brown hair, sheen, tone variation, fine strokes, edges broken into hairs | Flat matte black, spiky fringe on the outline, no sheen, no tone variation inside; still reads as a marker stroke | WRONG | stayed |
| Symmetry | Same shape both sides (differences come from head tilt) | Mask IoU 0.885 (v24: 0.848). The shapes are closer, but the heads differ (image-left angles into the nose, image-right is a rounded blob) and so do the tails (short hook against nearly none) | CLOSE | improved |

## Three biggest remaining differences, with a fix direction

1. Tail and break: the brow ends almost where the reference tail only begins. Fix: move the break inward to about 65 % of the head-to-tip length on both sides, then extend a straight tail segment by about 0.35 to 0.45 ew toward the temple at about 20 degrees down. Taper the width linearly from the break (about 0.3 ew) to about 0.03 ew at the tip, and keep the tip at or slightly above the head bottom edge. Use the same template, mirrored, on both sides.
2. Opaque marker fill and blob heads. Fix: build the alpha from strokes, not from a filled shape. Target about 60 to 70 % coverage in the body and 30 to 40 % in the first 15 % of the length, with near-vertical upward strokes at the head and no outline. The image-right head needs the same downward angle into the nose as the image-left head: cut the rounded lower corner into a slanted, feathered edge.
3. Flat black texture with no hair structure inside the shape. Fix: draw individual hairs inside the body following the growth direction (up at the head, diagonal up-out in the body, down-out in the tail), with per-hair tone variation from dark brown to black and a slight specular term, so that skin shows between hairs. Keep the approved overall colour and density as the average. The spiky fringe on the outline then becomes the natural end of these hairs instead of noise on a solid edge.

Not judged: lashes (oversized, they reach the brow from below and make the brow read lower), skin tone, lighting (the purple rim light tints the image-right brow), hair colour.
