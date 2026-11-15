# Tears for Yuki: how MetaCry works (public sources) and our own, better system

Owner, 2026-11-15: "skus ho napodobnit cez REA zisti ako na to a podme si spravit vlastny a lepsi". Rebuilt from
public material only: the forum thread, the Fab page and the published documentation (MetaCry 1.25.0). We never buy,
download or decompile the product and copy no code or assets.

Sources:
- Forum: https://forums.unrealengine.com/t/obliqpaw-metacry-procedural-tears-for-metahuman/2846918
- Fab: https://www.fab.com/listings/f9f10231-84bc-49a5-863c-38f96c976e6f (13.60 EUR before tax)
- Documentation: https://docs.google.com/document/d/e/2PACX-1vRiFZ1ex8GqNSLmRgGMNhrq1LO-DMIDUPLIEfEc3dX4Kcjm7wRIM2NTqImjukmzS-NzkubZuB-3aGlA/pub

## 1. How MetaCry works

Stated by the seller (documentation):
- One actor, BP_MetaCry (C++ class ProceduralMHTearsActor), pointed at a MetaHuman in the level.
- Binds to the face bones FACIAL_L_EyeCornerInner and FACIAL_R_EyeCornerInner; 1 to 3 outlets per lower lid.
- Needs CPU access to the LOD0 face mesh, a skin slot named "head" or "skin" with Receive Decals, and DBuffer decals.
- Drops: gravity, viscosity, adhesion, sticking pauses, path irregularity, a run-out distance after which a drop thins
  into the wet film; at most 24 moving drops; collision for detached drops; seeded.
- Wet trails: persistent decals that change only roughness and specular (at most 768 marks).
- Tear lake: a meniscus on the lower lid that fills and overflows into drops.
- Sequencer: Crying Intensity is the main key; "Bake open shot" caches the tears frame by frame.
- Unreal Engine 5.5 to 5.8, Windows only. Our project is UE 5.9, so the product would not even load.

Inferred by us (not stated): the drops walk over the CPU-read face triangles each tick, which is why it needs LOD0 CPU
access; Niagara and the Procedural Mesh Component draw the drops and the lake; the trails are DBuffer decals
projected onto the skinned face.

## 2. Our system: better on five points

1. **Tears copied from the singer.** The source video shows real tears (Sinead O'Connor cries in Nothing Compares 2
   U). We find wet streaks and drops in the source frames (bright specular streaks below the eyes, tracked over time)
   and carry their paths onto Yuki's face through the face landmarks. MetaCry only has a random generator.
2. **Driven by the emotion record.** Crying intensity comes from the performance itself: the sadness pattern in the
   solved curves (inner brow raise, brow knit, lip corner pull down, chin raise, eye squint) and the singer's measured
   tears. Sniffs, a wet and reddened eye, a reddened nose tip and lids, and lower-lid puffiness come from the same
   record.
3. **Exact, repeatable, scrubbable.** Our renders are offline (Movie Render Queue), so tears are computed per frame on
   the actually deformed face (the same per-frame face export path T used) and baked: no runtime budget of 24 drops
   or 768 marks, no cache going stale.
4. **Full look.** Drops refract and catch the light; the wet trail changes roughness and specular only; plus the eye's
   own tear film (a brighter, wetter lower-lid line and sclera highlight) and the tear lake.
5. **UE 5.9 and our pipeline.** Works in our project and inside `yuki_song_pipeline.py` as one more step.

## 3. Build plan

1. Tear paths: per frame, the deformed face mesh (GeometryScript copy, as in `ue_face_arkit_export.py STEP=setcopy`);
   drops start at the lower lid near the inner corner, move along gravity projected onto the surface, stick and slip,
   leave a trail; paths stored in face UV space so they stay on the skin as the face moves.
2. Wet map: one UV-space mask per frame (or an accumulated mask with decay) fed to the face material as a roughness
   and specular modulation (a material instance parameter on our own face material).
3. Drops: small refractive meshes, written as a geometry cache (Alembic) bound to the head, or Niagara mesh particles
   placed from the baked paths.
4. Eye and lids: tear film line on the lower lid, sclera wetness and redness, keyed from the crying curve.
5. Source tears: detector on the source video (specular streak below the eye), track, map to UV, feed step 1.
6. Gate: full-resolution crops of the cheek and eye at several frames and angles before anything is shown.

## 4. Risks

- Specular streaks in the source can be makeup or light, not tears: the detector needs a check against the sadness
  curves and a person's eye on the crops.
- Per-frame face meshes cost disk and time (19,284 vertices per frame); 60 s at 30 fps is 1,800 meshes.
- Refraction on tiny drops can read as dirt in a dark shot; the look needs the owner's eye on a test shot first.
