AUDITOR: independent subagent, saw only the sheet, motion strip, frame, measurements and the v30 audit

# v31 brow audit against reference p6

Image-left brow = character's right brow. Image-right brow = character's left brow. ew = eye width. In the sheet close-up one render eye is about 200 px wide. On the full frame v31_0057.png one eye is about 100 px wide. The reference face is rolled and turned, so angles carry about plus or minus 5 degrees and spacing about plus or minus 0.1 ew. brow_holes was ignored as instructed. I could not zoom, so details under 0.03 ew are read at sheet resolution only.

| Part | Reference p6 | Render v31 | Verdict | vs v30 |
|---|---|---|---|---|
| Head: position | Low at the nose root, inner end slants down toward the nose | Both heads low, at the right height. The vertical cut from v30 is gone. Image-left head now curls down into a rounded hook (sheet x about 470 to 490, down to y about 555), lower than the body line. Image-right head is rounded, not slanted | CLOSE | improved (no vertical cut), new hook shape |
| Head: width and softness | Narrowest part, about 0.12 to 0.15 ew, feathered, upward strokes, skin showing | Still about 0.25 ew tall, as tall as the body or taller. Image-right head is lighter and greyer than its body. Neither is the narrowest part | WRONG | same |
| Body: thickness | About 0.18 to 0.2 ew, thickest just before the break | Measured top 0.162 to 0.165 ew above the crest plus bottom 0.097 to 0.098 ew below it = 0.26 ew. v30 was 0.25. The bottom edge moved down by about 0.027 ew | WRONG | worse |
| Body: density and holes | Dense, single hairs readable, skin visible at the edges | Dense black, hatch strokes readable, a little skin in image-right head and inner body | CLOSE | same |
| Body: bottom edge | Soft, broken by hairs, follows the top edge | Cleaner, smooth curved line on both sides, no straight hard segment as in v30. But it is a crisp clipped outline, not broken by hairs, and it sits lower | CLOSE | improved (shape), worse (position) |
| Top edge: shape and angle | Near-straight rise of about 15 to 20 degrees to a clear angle | Sheet: rise reads about 15 to 20 degrees from the head on image-right, steeper near the image-left head. Full frame: about 9 to 10 degrees on both sides. Both still roll into a broad rounded crest, an arch, not a straight line to a corner | WRONG | improved (steeper rise) |
| Break: position and sharpness | About 65 to 70 % of the length from the head, defined but soft angle | Position about 55 to 60 % on both sides, now slightly too far inward (v30 was 75 to 85 %). Still rounded, no angle | WRONG | improved (position), same (sharpness) |
| Tail: length, direction, taper | Long, drops gently toward the temple, fine point | Image-right: about 0.7 ew after the crest, drops, tapers to a point, partly lost in purple light. Image-left: ends in a blunt, almost square end about 0.15 ew thick, nearly flat, little drop | WRONG (image-left), CLOSE (image-right) | worse (image-left), improved (image-right) |
| Height against the brow bone | Low over the eye, bone close above the eye | top -0.162 / -0.165 ew, bottom 0.097 / 0.098 ew. The brow centre moved about 0.025 ew down toward the eye, symmetric | CLOSE | same position, lower edge worse |
| Spacing | About 1.0 to 1.1 ew | About 1.0 ew in the close-up and on the frame | CLOSE | same |
| Texture | Black-brown hair, sheen, tone variation, broken edges | Hatch strokes inside, but the outline is now a hard, clean template cut, which reads as a stamp or marker, not hair. Flat black, no brown variation; purple light sheen on image-right only | WRONG | worse (edges), same (tone) |
| Symmetry | Same shape both sides; differences from head pose only | Mask IoU 0.887 (v30 0.874). Visually: image-left has a hooked head and blunt tail, image-right a rounded head and pointed tail | WRONG | improved (number), same (visually) |
| Motion through the blink | No motion reference; a real blink drops the brow very slightly and the brow stays attached | Brows stay fully attached in still, before, during and after. No sliding, tearing or seam. They do not move at all. A dark smear on the image-left outer lid during the blink belongs to the lashes or liner, not the brow | CLOSE | same |
| Brown patch under the heads | None | No straight-edged rectangle visible any more. A soft brown shade remains under the image-left head and merges into its downward hook, so the head reads lower and heavier | CLOSE | improved |

## Three biggest remaining differences, with a concrete fix

1. **The brow got thicker, not thinner: 0.26 ew against about 0.19 ew, and the head is still as tall as the body.** The bottom edge moved down by 0.027 ew since v30. Fix: raise the template bottom edge so bottom_minus_crest goes from 0.097 to about 0.03 ew (body about 0.19 ew). Taper the first 20 % of the length from 0.12 ew at the inner end to full width, slanted down toward the nose at about 45 degrees, and remove the downward hook on the image-left head.
2. **The clip to the template made a hard stamped outline and a blunt image-left tail.** The reference outline is broken by single hairs and the tail ends in a fine point. Fix: replace the hard clip with a feathered mask that fades hair alpha to zero over about 0.03 ew outside the outline, and let 20 to 30 % of edge hairs cross it. In the last 25 % of the length, ramp density and hair width down so both tails end in a point under 0.03 ew. Extend the image-left tail and drop it to match image-right.
3. **The arch is still rounded, and the break now sits too far inward.** Fix: put the break at 0.67 of the length on both sides, make head-to-break one straight line at about 17 degrees in the front view, and set the corner radius under 0.05 ew. Check it on the full frame, where the rise still reads only 9 to 10 degrees.

Not judged: lashes (still oversized and reaching into the brow zone), skin, lighting, hair colour, approved brow colour and density.
