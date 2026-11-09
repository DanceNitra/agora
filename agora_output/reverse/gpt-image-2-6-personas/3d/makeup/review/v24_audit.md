AUDITOR: independent subagent, saw only the sheet, the two frames and the measurements

# v24 brow audit against reference p6

Image-left brow = character's right brow. Image-right brow = character's left brow. Eye width = ew.

| Part | Reference p6 | Render v24 | Verdict |
|---|---|---|---|
| Head near the nose: position | Heads close to the nose root, low, angled slightly down toward the nose, which gives the intense look | Heads start at about the same horizontal spot, but sit level or tilt up; no downward inner angle | CLOSE |
| Head: width and softness | Soft feathered head: upward strokes, skin visible through, fades into skin with no outline | Blunt rounded block with a hard filled outline; image-right head is a flat square stamp | WRONG |
| Body: thickness | About 0.2 ew in the body, thinning steadily from head to tail | About 0.2 ew in the body, but it stays full thickness almost to the tail | CLOSE |
| Body: density and holes | Dense, but single hairs readable; skin visible at the edges | No holes visible (the brow_holes figure was ignored as instructed); fill is opaque and uniform, no single hairs, no skin anywhere inside | WRONG (density too solid) |
| Top edge: shape and angle | Near-straight line rising from head to break, about 10 to 15 degrees | Image-left: a convex rounded hump, highest around 40 % of the length. Image-right: straighter, rising, closer to the reference | WRONG (image-left), CLOSE (image-right) |
| Break point: position and sharpness | About two thirds of the way out from the head, a clear but soft angle | Image-left: no break, a continuous arc. Image-right: break near 75 %, rounded, weak | WRONG |
| Tail: length, direction, taper | Long, drops gently toward the temple, tapers to a fine point | Image-left: short, hooks down steeply, blunt end. Image-right: drops more gently and tapers better, but stays thick too long | WRONG |
| Height above the eye and against the bone | Brow sits low and close to the eye; in that face the bone is just above the eye | Measured: top edge 0.067 ew above the crest, bottom edge 0.15 to 0.154 ew below it, so about two thirds of the brow hangs below the crest. Visually the brow still reads as low over the eye, and the oversized lashes reach the brow from below | CLOSE (the bottom edge is too low against the bone) |
| Spacing between the brows | Gap about 1.1 ew | Gap about 1.05 to 1.1 ew | MATCH |
| Texture and colour | Black-brown hair, slight sheen and a variation in tone, fine stroke texture, edges broken into hairs | Flat matte black with grainy noise and a spiky fringe; reads as a felt marker or a sticker | WRONG |
| Symmetry | Matching shape on both sides (asymmetry comes from the head tilt only) | Mask IoU 0.848; the two shapes differ: left is a rounded hump with a hooked tail, right is a straighter line with a break | WRONG |

## Three biggest differences, with a fix direction

1. Shape: rounded hump instead of a straight line with a break (image-left side in particular), and the tail hooks down. Fix: build the brow from three control points per side (head bottom, break at about 65 % of the length, tail tip). Make the top edge a straight segment from head to break at about 12 degrees up, then a straight segment down to the tail at about 20 degrees. Mirror the same template to both sides so the IoU rises and the image-left hook disappears. Keep the tail tip at or above the level of the head bottom edge.
2. Flat black marker look with a blunt block head. Fix: replace the opaque fill with an alpha built from strokes. Use about 60 to 70 % coverage in the body, 30 to 40 % in the head, with vertical upward strokes at the head that fade out over the first 15 % of the length and no outline. Shift the colour from pure black to a dark brown-black with a slight specular term and per-hair tone variation.
3. Thickness profile and placement against the bone. Fix: taper the width linearly from the head (about 0.2 ew) to the tail (about 0.03 ew at the tip), starting the taper at the break, not at the end. Raise the whole brow by about 0.05 to 0.08 ew so that the bottom edge sits at or slightly below the crest (target bottom_minus_crest about +0.05 to +0.08 ew instead of +0.15) and the crest falls inside the lower half of the brow.

Not judged: lashes, which are oversized and overlap the brow bottom edge in the render. They make the brow read lower than it is, so measure the brow with the lashes hidden.
