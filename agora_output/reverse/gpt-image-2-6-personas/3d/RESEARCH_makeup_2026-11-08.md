# Makeup deep dive for Depeša (2026-11-08, round 2)

Owner: "najlepší MAKEUP EVER ... najdôležitejšia vec", "sprav DEEPDIVE ako to robia ostatní", "namaľovať na
existujúci MetaHuman projekt, lebo sa to bude časom meniť", "tak ako to robia baby celý život", "nechoď na slepo".

## 1. How others do it
| Who | How makeup is made | Finish (gloss, matte) | Changeable? |
|---|---|---|---|
| **Real makeup artists** | Fixed order: skin prep and primer, foundation, concealer, powder, contour/bronzer, highlighter, then eyes (shadow, liner, mascara; some do eyes first to catch fallout), lips last (liner, lipstick, gloss) | product choice: matte, satin, gloss | every day |
| **Reallusion Character Creator / SkinGen** (closest production tool) | Stack of makeup layers over the skin: Foundation, Eye (7 eyeshadow sections + powder/glitter), Eyelash, Lip (Base, Heart, Contour, Highlight), Eyebrow, Misc; Photoshop-like blend modes; Flatten bakes to one image | Specular and Gloss per lip section | yes, layers stay live until flattened |
| **MetaHuman** | Makeup panel: Foundation, Eyes (shadow + liner colour, opacity, spread), Blush, Lips; the Cine/Optimized pipelines BAKE skin + makeup into one Basecolor map; custom makeup = paint into the albedo (Substance) or mask slots | roughness per layer; lips colour/roughness/metalness | preset shapes only |
| **Daz DD Makeup Editor** | makeup as shader parameters over untouched skin textures (lipstick, liner, blush, foundation) | shader | yes |
| **AR beauty apps (Perfect Corp/YouCam, Banuba, DeepAR)** | track face, region MASKS (liner wraps the upper lash line, blush follows cheekbones), colour into the mask, then shading, gloss model, blur, edge blending | 7 lipstick finishes (matte, gloss, satin, sheer, metallic, shimmer, holographic) | yes, per product |
| **Games (Hellblade II, Ninja Theory + 3Lateral)** | real makeup on the actor, then scanned; face rig via MetaHuman tools | captured | no |
| **Research** | Physically Based Cosmetic Rendering (Huang et al. 2013): Kubelka-Munk layers skin -> foundation -> blush -> eyeshadow over subsurface skin, measured real products; Li, Zhou, Lin CVPR 2015: intrinsic-layer makeup; AvatarMakeup (IEEE TIP 2026): diffusion makeup accumulated into one UV map for 3D avatars | layer optics | parametric |
| **Diffusion inpainting on UV maps** | possible, but the model does not know the UV-to-3D mapping and misplaces detail; seams need dilation | - | - |

Consensus: **makeup is a stack of masked layers over a clean skin, applied in the artist's order, with colour in the
albedo and finish in roughness/specular; masks come from face landmarks.**

## 2. What we have (SEEN in our project)
- The built face uses `MI_Face_Skin_Baked_*_VT` (parent `MI_Head_Baked_LOD0_VT`) with textures **Basecolor Baked (VT)**
  and **SRMF Baked (VT)** plus post-bake controls (Basecolor hue/value/saturation, Roughness and Specular offset and
  multiply). So makeup can be swapped AFTER the build by replacing those two textures: no new scan, no rebuild.
- `MI_Face_LacrimalFluid` (tear film / wet waterline) and `MI_Face_Eyelashes` exist in the build.
- MediaPipe finds all 478 face landmarks directly on the KeenFace UV texture (`keenface/alb_landmarks.png`), so
  every makeup mask (lash lines, lids, crease, brows, lips, cheekbones) can be drawn exactly in UV space.

## 3. Our system (proposed): "Makeup Studio" for the existing MetaHuman
- **Clean skin stays untouched.** A look is a JSON of layers, applied in the makeup artist's order:
  1. foundation/evening, 2. concealer, 3. contour + bronzer, 4. blush, 5. highlighter (also lowers roughness),
  6. brows (fill, density), 7. eyeshadow (lid, crease, outer V, lower smudge), 8. eyeliner (tightline + wing),
  9. lash line darkening (lashes themselves are grooms), 10. lip liner, 11. lipstick, 12. gloss (roughness only).
- Each layer: landmark-guided mask in UV, colour, opacity, softness, blend mode (multiply/normal/screen), and a
  finish value for the SRMF roughness channel.
- Output: composited Basecolor + SRMF; set as Basecolor Baked / SRMF Baked on the face materials; render a close-up
  beside p6. A new look = a new JSON, minutes, no scan.
- First look: **p6** (sharp dark winged liner, smoky brown lids, dense brows, warm contour, glow on cheekbones and
  nose bridge, nude-rose glossy lips).

## Sources
- Reallusion SkinGen makeup layers: https://manual.reallusion.com/Character_Creator/ENU/1/16_Makeup/The_Layers_of_Makeup.htm ,
  https://manual.reallusion.com/SkinGen-Plug-in/Content/SkinGen-1/1.0/15-SkinGen/Basic-Concepts/Skin-and-Makeup-Layers-Concepts.htm ,
  https://reallusion.com/character-creator/skingen-structure.html
- Epic Makeup Material Tools: https://dev.epicgames.com/documentation/metahuman/makeup-material-tools
- Epic MetaHuman Materials and Textures: https://dev.epicgames.com/documentation/metahuman/metahuman-materials-and-textures
- Perfect Corp, how virtual makeup renders: https://www.perfectcorp.com/business/blog/makeup/how-virtual-makeup-try-on-renders-lipstick-blush-foundation ;
  Perfect Corp API: https://yce.perfectcorp.com/ai-api/products/virtual-makeup-try-on-api ;
  Banuba comparison: https://www.banuba.com/blog/banuba-tint-makeup-sdk-vs-perfect-corp-compared-tested ;
  AR makeup patent: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11069094
- Physically Based Cosmetic Rendering: https://people.cs.nycu.edu.tw/~wclin/cosmetics.html
- Li, Zhou, Lin CVPR 2015: https://openaccess.thecvf.com/content_cvpr_2015/html/Li_Simulating_Makeup_Through_2015_CVPR_paper.html
- AvatarMakeup IEEE TIP 2026: https://doi.org/10.1109/tip.2026.3657896
- DD Makeup Editor (Daz): https://www.renderhub.com/gallery/88564/dd-makeup-editor-photorealistic-makeup-system-for-daz-studio-genesis-8-female
- Hellblade II makeup/scan: https://www.siliconera.com/ninja-theory-details-the-lengthy-process-of-creating-senuas-face-in-hellblade/
- Makeup order: https://www.charlottetilbury.com/secrets/correct-order-of-makeup-steps ,
  https://www.lorealparisusa.com/beauty-magazine/makeup/makeup-looks/makeup-order-for-application
- Substance + MetaHuman textures: https://forums.unrealengine.com/t/community-tutorial-create-custom-skin-textures-for-metahumans/2597197
- Diffusion on UV maps, caveat: https://reddit.sentinel-team.org/posts/1sgodcs/snapshots/2026-04-09T18%3A01%3A27.133764Z
