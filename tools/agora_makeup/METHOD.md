# Agora Makeup: method, from research (2026-11-09)

The owner rejected renders where makeup left visible edges, did not cover the whole skin, and left the neck
and hands a different colour. This file records how professionals and MetaHuman practitioners do it, and
the method the tool follows. Every rule cites where it comes from.

## How practitioners do makeup on MetaHumans

1. Export the combined face and body mesh and the baked BaseColor and Normal of both face and body. The
   mesh carries two UDIM tiles: 1001 is the head, 1002 is the body. Paint on the whole character in 3D in
   one Substance Painter project, then export both texture sets and put them back into
   `MI_Face_Skin_Baked` (every LOD) and `MI_Body_Baked`.
   Source: Epic Developer Community tutorial "Create Custom Skin Textures For Metahumans" (FederalFatality,
   UE 5.6, 2025-07-08), video ZuqsMk4OVIY, transcript 00:22-08:02, saved in
   `agora_output/reverse/makeup_tool/research/yt_ZuqsMk4OVIY.txt`.
2. Makeup is part of the baked BaseColor; face and body use the same parent material and base texture set.
   Source: Epic documentation, "MetaHuman materials and textures".
3. The visible neck down to the collarbones belongs to the Face mesh, not the Body mesh, so neck colour and
   seams come from the face texture. Source: Unreal Engine forum, "MetaHuman UV Seam Skin Tone
   Inconsistency" and related threads (2025).
4. Remaining head/body tone differences after that come from render settings (Bent Normal is on the face
   material only), not from the textures. Source: same forum thread; Epic staff answer.
5. Studios keep head and body on one shared complexion (Cyberpunk 2077 `.mi` complexion files), and makeup
   colourisers cover "extra body parts ... evenly without any abrupt cutoffs" (Sims 4 Skin Colorizer).
   Source: NotebookLM Makeup Atlas, REDmodding wiki and The Sims Resource.

## How makeup artists build a face

- Geisha (maiko): skin prep, bintsuke wax, oshiroi over face, neck, ears, upper chest and upper back except
  the eri-ashi pattern on the nape, kona oshiroi powder, then eyes, then lips; blush (tonoko) blends the
  foundation into the skin. Sources: Wikipedia "Oshiroi"; mai-ko.com "The Makeup of the Geisha".
- Chinese opera: base mixed to a flesh tone and laid on evenly, then blush patted into the base, then powder;
  apply top to bottom and inside to outside; dan roles fade lighter toward the lower face. Stage base goes
  thin on the neck and ears as well. Sources: bangziopera.taes.tp.edu.tw d-02; Colgate global theater page;
  Wikipedia "Stage makeup".
- Everyday and editorial makeup (NotebookLM Makeup Atlas, artistry fundamentals): base evens the skin over
  the whole face and blends into the neck; every product is blended until no edge remains.

## Method the tool follows

1. One projection for the whole character. Every texel of the face texture AND the body texture is given
   its own 3D position and normal from the meshes. Zones are drawn on a frontal view of the face; a texel
   takes the zone value at its own 3D position seen from the front, weighted by how much its surface faces
   the front, so the under-chin, the sides of the head and the back fade to zero instead of copying the
   chin or leaving holes. No seams, no holes, no neck spill.
2. Base first, everywhere skin is. The base (foundation) evens the skin tone on the whole face texture and
   the whole body texture with one shared colour transform, so face, neck, chest and hands stay one
   colour. Pores and skin detail stay: only the low frequencies are evened.
3. Then, in order: concealer, sculpt (contour, bronzer), powder, blush, highlight, eyes, liner, lashes, lips.
   Each layer has soft edges and is blended out to nothing.
4. Check before Unreal: project the painted textures back onto the face from the front and from both sides,
   and look for holes, speckles, hard edges and neck or hand mismatch. Only then render.
