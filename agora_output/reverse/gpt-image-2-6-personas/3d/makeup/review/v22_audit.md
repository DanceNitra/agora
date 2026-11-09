AUDITOR: independent subagent, saw only the sheet and the two frames

# v22 brow audit (render v22_0057 against reference depesa_p6)

Files read: makeup/review/v22_sheet.png, beauty/depesa_p6.png, makeup/review/v22_0057.png. Pixel figures are estimates from the sheet close-up (1160 px wide). Nothing was measured with code.

Overall verdict: WRONG. The holes are gone, but the brows have overshot to the other extreme. They read as two thick, flat-black, marker-drawn blocks with a rounded hump and blunt ends. The reference shows narrower, low-set, straight-angled brows with soft heads and fine tapered tails.

| Part | Reference p6 | Render v22 | Verdict |
|---|---|---|---|
| Head near the nose (position, width, softness) | Starts close to the nose bridge, slightly inside the inner eye corner. Narrow, feathered, lighter hairs that brush upward. Skin shows through at the very front. | Starts at a similar distance from the nose. The head is a blunt, squared, fully opaque block with vertical scratch strokes and the same thickness as the body. No feathering, no gradient. | WRONG |
| Body (thickness, density, holes) | Dense, smooth, dark. Thickness at the body is about 0.2 of eye width. No holes. | No holes, fully dense. About 0.4 to 0.45 of eye width, roughly double the reference. Uniform thickness from head to tail. | WRONG |
| Top edge (straight or arched, angle) | Nearly straight line rising from head to peak at a clear upward angle, then a sharp angled break. | Smooth convex arc, a rounded hump. No straight segment and no angled corner. | WRONG |
| Arch or break point | About two thirds of the length from the head, above the outer iris edge. Sharp corner. | Highest point at about 68 to 72 % of the length, so the position is close. The peak is rounded, not angled. | CLOSE |
| Tail (length, direction, taper) | Runs past the outer eye corner toward the temple, angled down, tapering to a thin point. | Ends roughly at the outer eye corner with a thick, blunt, rounded end. Drops only slightly. No taper. | WRONG |
| Height above the eye, against the brow bone | Low-set, sits right on the brow bone close to the upper lid. Gives the intense, lowered look. | The lower edge sits close to the lid, but the extra thickness pushes the top edge far up the forehead and the hump lifts the middle. The full face reads as raised and surprised, not lowered. | WRONG |
| Spacing between the brows | Narrow gap, the heads come close together above the nose. | Gap is comparable or slightly wider. Hard to judge exactly because the head poses differ. | CLOSE |
| Texture and colour | Smooth dense hair mass, dark brown-black, soft edges, individual hairs only at the head and the lower edge. | Flat black with visible scribbly hatch strokes, ragged outline, grainy cross-hatching inside. Reads as marker or paint, not hair. Some dark strands hang below the left brow into the lid area. | WRONG |
| Symmetry | Slight asymmetry from the head tilt; same shape on both sides. | Same shape on both sides. Image-left brow is longer and more tilted, image-right is shorter and flatter. | CLOSE |

Score: 0 MATCH, 3 CLOSE, 6 WRONG.

## Three biggest differences, ordered by effect on the look

1. Thickness and the blocky silhouette. The brows are about twice as thick as the reference and the same thickness from head to tail. This alone makes the face look like it has drawn-on brows. Fix direction: halve the height of the brow mask or card strip at the body (target about 0.2 of eye width), thin the head slightly, and taper the last third of the tail down to a point.

2. Rounded hump instead of a straight angled line. The top edge is a convex arc. Fix direction: redraw the top edge as two straight segments, head to peak rising at a steady angle, then a short, sharper drop to the tail. Keep the peak at about two thirds of the length above the outer iris, and make the corner angular. Keep the lower edge low against the lid so the brow sits on the bone, not above it.

3. Texture: flat black marker with scribbles, blunt head. Fix direction: replace the hatch-stroke texture with a smooth dense hair mass in dark brown-black (not pure black). Add a soft opacity gradient at the head so it fades into upward-brushed hairs, and soften the whole outline. Remove the stray strands that hang below the left brow into the lid.

Not checked: other camera angles, animation frames, and the brows at render resolution outside frame 0057.
