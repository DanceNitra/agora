# Agora Makeup

A makeup library and painter for MetaHumans in Unreal Engine 5.8. It paints a look onto the baked face
textures of any built MetaHuman in a few seconds, without rebuilding the character.

## What is in it

- `agora_makeup/zones.py`: 30 face zones (under-eye triangle, T-zone, cheek hollow, temples, jaw, nose
  contour, 5 blush placements, 7 highlight spots, lid, crease, outer V, lower lash line, aegyo-sal,
  inner corner, winged liner, lips with overline, lip liner, ombre centre, gloss band) as soft masks in
  MetaHuman head UV. Every MetaHuman shares that UV, so the zones fit any of them.
- `agora_makeup/paint.py`: layers in artist order, with blend modes (tint, multiply, screen, colour),
  glitter, and roughness changes for matte, satin, dewy, glass and gloss finishes.
- `agora_makeup/library.py`: 23 base looks from the trend research (latte, espresso, Douyin doll,
  aegyo-sal, Y2K, Y3K, siren, office siren, clean girl, cold girl, mob wife, glazed, runway looks,
  K-beauty, smoky, berry, sunkissed, editorial glass) and a generator of 4,968 variants:
  3 intensities x 9 lip palettes x 8 eye palettes per look.
- `cli.py`: list, describe and paint looks from the command line.
- `preview.py`: paint looks onto an albedo and write a contact sheet, without Unreal.
- `unreal_plugin/AgoraMakeup`: the Unreal plugin. Copy it into `<Project>/Plugins/`.

## Use in Unreal

1. Select a built MetaHuman in the level.
2. Open **Tools > Agora Makeup**, pick a family and a look at soft, standard or glam intensity.
3. To undo, click **Reset makeup on selected**.

Any variant by id, from the Python console:

```python
import agora_makeup_ue.core as c
c.apply("latte__glam__classic_red__espresso")
c.apply("luvpauli_doll", folder="/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face")
c.reset()
```

The first apply exports the original baked textures to `<Project>/Saved/AgoraMakeup/<key>/`, so looks
never stack. Results go to `/Game/AgoraMakeup/<key>/` under fixed names and are overwritten on each
apply, so memory and disk do not grow with every try.

## Sources

The looks come from the NotebookLM notebook "Makeup Atlas" (d99dde93-a6d4-406c-bc16-620c9854757d,
about 75 sources on 2025-2026 trends, game and MetaHuman makeup, and artistry rules) and from the
@luvpauli tutorial breakdown in `agora_output/reverse/makeup_tool/video_luvpauli/BREAKDOWN.md`.

## Limits

- Brows are not painted: the Depesa brows are grooms, and the tool leaves brows alone.
- The editor's Python has no OpenCV, so painting runs in an external Python set in
  `unreal_plugin/AgoraMakeup/Content/Python/agora_makeup_ue/config.json`.
