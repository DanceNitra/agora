# 20 Creative-Director + 32 Generative-Director: episode cover

Episode: "Echoes of Tomorrow", outside outcomes, not ranking. Date: 2026-09-28.

**Optimized for:** one shape that reads at 150 px on a dark phone screen, and that carries the finding (the lesson that helped was confirmed from outside the agent) without a literal picture of AI.

**Rejected:** the previous cover's violet side lights and model-rendered lettering, both banned by this brief, and any image of memory poisoning as the headline, because the poisoning run does not show attack detection.

**Why:** the series identity is the evidence table (steel, overhead lamp, brass markers, black glove, condensed caps). That identity holds. The layout does not repeat: identity is recognition, not copying.

## What I looked at

- Series reference, seen as an image [CLAUDE-VISION]: `agora_output/episodes/verify-agent-memory-deletion/cover.png` (3000x3000) and `cover_source.png` (1254x1254).
  - Keeps: black room, one pendant lamp, scratched steel table, brass numbered markers, gloved hand with a loupe, tall condensed uppercase title, show name tracked wide.
  - Breaks this brief: violet light strips at both edges (glow), and all lettering is baked into the model output. Only one episode cover exists, so "series" means one precedent.
- Brief bans, owner design rules (restraint, no slop tells), owner preference for dark renders.

## 1. Three cover concepts

### Concept A: the hand from outside the frame (RECOMMENDED)

- **Image in one sentence:** under a single overhead lamp, a black-gloved hand enters from beyond the top edge of the frame and presses a blind-embossed brass seal onto one white index card, among a loose row of identical unmarked cards on a steel table.
- **Why it carries this finding:** the lead is confirmation from outside. The hand is literally outside the picture; only its act reaches the card. The other cards are lessons of the same kind, from the same place, and nobody has confirmed them yet. The suspect (the ranker) is absent, which is the point: its gain cannot be told from zero.
- **150 px read:** a black square, one pool of light, one white rectangle, one dark wedge (the arm) cutting in from the top edge. Four shapes, high contrast.
- **Palette:**

  | role | hex |
  |---|---|
  | void, background | `#0B0B0C` |
  | wall | `#17171A` |
  | steel, midtone | `#6E7074` |
  | steel, highlight | `#C9CBCD` |
  | index card | `#E9E4D8` |
  | brass seal, markers | `#B8914A` |
  | glove | `#111111` |

- **Title zone:** the dark wall, top-left, from x 180 to x 1650 and y 220 to y 1150. The lamp and hand sit right of centre, so the text never collides with the subject.

### Concept B: the level ruler (the alibi)

- **Image in one sentence:** two stacks of index cards side by side under the lamp, one squared and ordered, one loose and shuffled, with a brass machinist's rule laid across both tops and lying perfectly flat.
- **Why it carries this finding:** this is the suspect's alibi. Ordering the lessons by similarity (+0.019) and drawing them at random from the same repository give tops at the same height. The ruler is the measurement, and it does not tilt.
- **150 px read:** weaker than A. Two stacks and a line; the "same height" point needs a second look.
- **Palette:** as A, the ruler is `#B8914A`, the cards `#E9E4D8`.
- **Title zone:** lower third on the table's dark front edge, left-aligned, y 2250 to y 2800.
- **Risk:** a viewer can read it as "ranking is useless". The brief bans that claim. The flat ruler says "the same within this measurement", and the copy has to carry "cannot tell from zero".

### Concept C: the flipped twin (the out-there alternative)

- **Image in one sentence:** a severe crop of the steel table edge where one white card lies face up and its twin lies face down, mirrored, half out of the lamp's light, the frame cut so that neither card is whole.
- **Why it carries this finding:** forged evidence. A lesson and its flipped twin look the same from the back.
- **150 px read:** strong: two rectangles, one bright, one dark, on a diagonal.
- **Palette:** as A, with the face-down card `#2A2A2D`.
- **Title zone:** the empty dark upper-right, where the crop leaves the void.
- **Why it is not the recommendation:** it leads with poisoning, a secondary result, and it invites the reading "we detect attacks". The brief states that the outside credit in that run was the dataset label. Shown because a cover everyone likes plays it safe; this is the braver option.

### Recommendation

Concept A. It carries the main finding, holds the series identity (lamp, steel, brass, glove), removes the two banned elements from the previous cover, and has the strongest thumbnail silhouette of the three.

## 2. Generation prompt, Concept A

32's position: this prompt is untested. No render exists. It is not "working" until a test render is on disk and the team has seen it.

### Positive prompt

```
Square photograph, film noir evidence room at night. A scratched brushed-steel examination table fills the lower half of the frame. One conical metal pendant lamp hangs just right of centre, top edge, casting a hard, narrow cone of white light onto the table; faint dust visible in the cone, no bloom. Six plain white index cards, blank on both sides, lie in a loose uneven row across the lit area of the table, slightly skewed, not aligned to a grid. A black nitrile-gloved hand and forearm reach down from beyond the top edge of the frame, right of centre, and press a small round brass embossing seal onto the fourth card; the seal leaves a blind emboss with no letters, only a raised circular ring. Two small brass tent markers, blank, stand near the left end of the row. The upper-left third of the image is a dark, plain matte charcoal wall, completely empty, falling into black at the corners. Low-key lighting, single hard light source, deep blacks, cool neutral steel, warm brass as the only colour accent. Shot on a 50mm lens at table height, slightly above, shallow depth of field on the sealed card. Restrained, editorial, still-life photography.
```

### Negative prompt

```
text, letters, words, numbers, typography, logo, watermark, signature, caption, writing on cards, writing on the seal, face, head, person visible, brain, robot, circuit board, circuitry, glow, neon, purple light, violet light, blue rim light, bloom, lens flare, light rays, gradient background, abstract blob, sci-fi hologram, screens, monitors, clutter, many objects, extra hands, deformed fingers, cartoon, illustration, 3D render look, oversaturated colour, red
```

### Settings

| setting | value |
|---|---|
| aspect ratio | 1:1 |
| native size | the model's largest square (for example 2048x2048), then upscale to 3000x3000 with a photographic upscaler, not a generative one that invents detail |
| empty zone for type | upper-left, x 180 to 1650, y 220 to 1150 at 3000 px; must be flat dark wall |
| lettering | none; any stray glyph fails the render |

### Model notes

- **GPT-image and Imagen** take no negative field. Append this line to the positive prompt: `Avoid: any text, letters or numbers; faces; glow, neon or coloured light; lens flare; clutter.`
- **Flux dev** (guidance-distilled) ignores a negative prompt at CFG 1. Use the same "Avoid:" line, or run with true CFG if the workflow supports it.
- Blank cards and markers are the weak point: models like to print numbers on markers and scribbles on cards. If the test render prints glyphs, change ONE variable: remove the tent markers first.

### Test-render protocol (32)

- Fix the seed, size and model for the test. Change one variable per retry, never prompt and seed together.
- Check the render at 150 px and in greyscale before judging colour (20's black-and-white gate: the card, arm and title zone must separate in grey at 150 px).
- Stop after 3 failed tests and report what failed, instead of tuning further.
- Log the winning prompt, seed and model under `crew-os::prompt::<model>::agora::eot-outside-outcomes`.

## 3. Typography spec (overlay, not model-rendered)

Type belongs to 18 Subtitle-Designer; this is the art-direction slot and it defers to 18 on kerning.

| element | typeface (Google Fonts, SIL OFL) | size at 3000 px | colour | placement |
|---|---|---|---|---|
| title `{TITLE}` | Oswald Medium 500, uppercase | 300 px font size (cap height about 240 px), leading 0.95, tracking +10 | `#E9E4D8` | left-aligned at x 200; first baseline at y 520; max width 1450 px; at most 3 lines |
| show name `ECHOES OF TOMORROW` | IBM Plex Mono Medium 500, uppercase | 64 px, tracking +400 | `#B8914A` | left-aligned at x 206, baseline 110 px under the last title line |
| brand line `AGORA` | IBM Plex Mono Regular 400, uppercase | 44 px, tracking +300 | `#8C8F93` | bottom-left, x 206, baseline y 2860 |

- **Title length:** at most 22 characters per line, at most 3 lines. At 150 px thumbnail size the cap height is 12 px, which stays legible; smaller sizes do not.
- **Layout test string only (titles come from the titles role):** `WHO WROTE / THE LESSON`.
- **Contrast, measured with the WCAG formula:** title on `#0B0B0C` 15.5:1, on `#17171A` 14.1:1; brass on `#0B0B0C` 6.7:1; grey `#8C8F93` on `#17171A` 5.5:1. All pass 20's 4.5:1 gate.
- **No effects:** no drop shadow, no glow, no gradient fill, no outline. If the wall behind the title is lighter than `#1E1F22` anywhere, darken the render locally rather than adding a shadow.
- **Placement is off-centre on purpose:** the previous cover centred the title. Moving it to the upper-left keeps the series type and breaks the repeat.
- **Brand mark:** the inspeximus three-bar mark is optional and is 24 Brand-Guardian's call. If used: 120 px wide, bottom-right at x 2680, y 2800, lower bars `#E9E4D8` at 26 % and 50 % opacity, top bar `#3FAE7D`.

## 4. OG image variant, 1200x630

- **Do not crop the square.** A 1.91:1 band from the square loses either the lamp and the type zone (band low) or the card (band high).
- **Generate a sibling:** same prompt, same model and seed, aspect 16:9 or the model's closest wide size (for example 1920x1008), with one prompt change: "the lamp, hand and cards occupy the right half of the frame; the left half is plain dark wall". Scale to 1200x630.
- **Type on the OG image:** left 50 % of the frame, x 64, title Oswald 500 at 88 px (3 lines max, `#E9E4D8`), show name Plex Mono 22 px tracking +400 `#B8914A` under it. Keep 48 px safe margins; social platforms crop edges.
- **Fallback if the sibling fails:** extend the square canvas left with a flat `#0B0B0C` field to 3000x1575 (outpaint only the wall, never the table), then scale.

## 5. Flags for the curator

- **Series title clash:** our role memory (rule P17, 2026-09-25) records that "Echoes of Tomorrow" is also a DANCHI track whose cover the owner drew himself, and that his own art is never redrawn. This cover does not touch that art. If the show art on Spotify is his drawing, the owner decides whether episode covers may diverge from it. I did not check the Spotify show page.
- **The previous cover breaks this brief** (violet glow, model lettering). If the owner wants the series consistent, the fix is to re-set that cover's type as an overlay; that is his call.
- **No render exists.** Nothing in this file is verified visually beyond the two existing covers.
