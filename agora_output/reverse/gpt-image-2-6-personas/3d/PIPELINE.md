# Companions as real 3D mesh characters: licences and workflow

Date: 2026-11-07. Owner: "budu to kompletne vygenerovane realne Mesh 3D charaktery cez bud tripo ai alebo
hi3d ked sa overia licencie a workflow na 3D animacie sa spravi tiez! a ked sa bude renderovat 3d model
tak presne tak ako sa to ma a po castiach aby sme dosiahli uplnu rekonstrukciu!, pri 3D head veciach to
iste aby sedel aj lipsynch co najlepsie". Skin and origin: "Zmiesane".
Owner's screen check: the full body is readable at 80x160, so the device shows dance and idle as well as
the talking head.

Status: research only. Nothing generated, nothing bought.

## Licences (read from primary sources, saved in `sources/`)

| Tool | What it is | Licence fact | Tag | Source |
|---|---|---|---|---|
| Tripo AI, Free | hosted image-to-3D | Terms 5.2.1: for Free Users "Tripo retains all rights" to Inputs and Outputs. Pricing page: "Public Models, Non-Commercial Use". | SEEN | tripo3d.ai/terms, tripo3d.ai/pricing |
| Tripo AI, Pro | hosted image-to-3D, rig, animation | Terms 5.2.2: Paid Users "generally have all rights" to Inputs and Outputs; Tripo keeps a licence to use them for providing the service and says it will not train on them. Pro: 20 USD monthly or 13 USD a month billed yearly (156 USD), 3,000 credits, "Private Models, Commercial Use". | SEEN | same |
| Tripo rig and animation | API | Rig endpoint outputs rigged GLB/FBX; animation needs a rigged model; official docs list 10 credits per animation. Rig price in credits not confirmed on Tripo's own page. | SEEN / UNKNOWN | developers.tripo3d.com/en/models/rig, /animation |
| Hi3D v1.0 (open source) | REFINER: turns a coarse mesh into high-resolution geometry, conditioned on the reference image. Geometry only, no texture. | Hi3D Open License 1.0, OCEANO HK HOLDING LIMITED. Commercial use permitted (2.1). Section 9: no ownership claim on Outputs; Outputs that contain no Hi3D code or weights can be sold without "Powered by Hi3D 1.0" or a scale licence. Branding duty (7) applies only to products that integrate the model. Scale gate 200,000 MAU or 1M USD a month applies to Related Products. | SEEN | hi3d-official/Hi3Dv1.0 LICENSE, sha256 e7914ddb... |
| Hunyuan3D-2 mini | the coarse stage in Hi3D's sample code | "DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA". We are in Slovakia, so we cannot use it. | SEEN | Tencent-Hunyuan/Hunyuan3D-2 LICENSE line 3 |
| TRELLIS.2 | image-to-3D with texture; already wired in our ComfyUI (AGORA_CHAR_01-03) | Repo licence MIT. Its DINOv3 encoder carries Meta's DINOv3 License (bars trade-control and military uses). | SEEN (repo), from memory (DINOv3) | microsoft/TRELLIS.2 |
| Hi3D web platform hi3d.ai | hosted service | Ownership and commercial terms not found on the landing page. | UNKNOWN | hi3d.ai |
| GPT Image 2.6 concept art | our input images | OpenAI terms assign outputs to the user. | from memory, verify before sale | |

So "Hi3D" in practice means: TRELLIS.2 makes the coarse textured mesh locally, Hi3D v1.0 refines the
geometry locally, and the texture is baked back. Cost 0 USD, GPU time on the shared card.

## Workflow (both paths end in the same Blender stage)

1. **Concept sheet per persona** (GPT Image 2.6): full body, front view, neutral A-pose, neutral face,
   plain background, plus side and back views. Image-to-3D needs this, not the portrait prompts that
   role 32 wrote. Mixed skin and origin per the owner.
2. **Mesh**
   - Path T: Tripo Pro, image-to-3D with texture, then Tripo rig, then Tripo animations.
   - Path H: TRELLIS.2 coarse mesh, Hi3D v1.0 refine to 1024 or 1536, bake TRELLIS texture onto it.
3. **Check part by part against the concept sheet** before any rig: head, face, hands and fingers, the
   Svitok core, gear layers. The open TRELLIS defects from 11-06 (fused glove fingers, UV seam across
   the face) are tested on our characters first.
4. **Rig and animate**: Tripo rig + animation (Path T) or Blender in the owner's window (both paths):
   idle loop, dance loops synced to beat tempo, reactions. No third-party animation packs.
5. **Face for lip-sync**: nine viseme shape keys per head in Blender (Rhubarb set A-H plus X), plus
   blink and three emotion keys. Rhubarb's phonetic recogniser drives them from the Slovak audio.
   NVIDIA Audio2Face-3D (ARKit blendshapes) is an option only after its licence text is read; sources
   conflict on commercial use.
6. **Render to the device**: Blender, orthographic camera, 80x160 frames rendered at 8x (640x1280) and
   reduced, sprite sheets for idle, dance, talk (mouth layer) and emotions. Every frame set is compared
   part by part with the concept sheet and the previous approved set before it goes to the device.

## Run 1: Busola on TRELLIS.2 (2026-11-07)

Concept `concepts/busola_front_v1.png` (Sunburst, 0.0359 USD). Graph AGORA_CHAR_02 unchanged, 227 s,
VRAM baseline 17.3 GB (other programs), peak 23.6 GB of 24.6. Outputs in `meshes/`.

| Mesh | Faces | Hands | Face | Antenna and flag | Core at throat | Texture |
|---|---|---|---|---|---|---|
| high-poly (node 61) | 3,597,832 | five separate fingers | detailed, neutral | present | disc present | none (geometry only) |
| final (remesh + decimate + bake, node 74) | 11,353 | cones, no fingers | red smear over the mouth, eyes smudged | missing | smeared | baked, crumpled look |

Both: the cap has two ring-shaped dials, one on each side; the concept has one ring and one foil patch.
Conclusion: TRELLIS.2 geometry holds; the 12k game budget destroys it. Sprites are pre-rendered, so the
triangle budget does not apply to us. Next: bake the texture onto a 150k-300k decimation instead of 12k.

## Run 2: same shape, texture baked at 200k faces (2026-11-07)

Changes: `62.target_face_count=200000`, `64.resolution=4096`, `70.texture_size=4096`,
`71.resolution=4096`. 74 s (shape stages cached), VRAM baseline 11.9 GB, peak 17.8 GB. Result
196,608 faces, 116 components, 52 MB GLB, all four maps. Views in `review/busola_v2_*.png` (Chrome,
model-viewer 4.0.0, neutral environment).

| Part | Concept v1 | Mesh v2 | Verdict |
|---|---|---|---|
| Hands | five spread fingers | five separate fingers, skin texture | holds |
| Antenna and pennant | brass mast, cobalt pennant | present, pennant has a pink tint at the mast | holds, small colour drift |
| Cap front | one compass ring, one foil patch | two mirrored white dials like goggles | wrong |
| Cap back | not shown | invented brass wiring and orange tubes | invented, not wrong |
| Face | freckles, open eyes, neutral mouth | eyes are dark smudges, freckles faint, mannequin look | wrong for a talking head |
| Gorget and core | brass crescent with cobalt enamel, amber oval | blue band on the shirt collar, amber disc at the throat | partly |
| Jacket, shorts, leggings, boots, map case | as concept | as concept; back of jacket has an invented leather patch | holds |

Conclusion: the full body is usable for idle and dance sprites. The face is not usable for lip-sync;
the talking head needs its own head pass (head-only concept, higher-resolution head mesh, or a
dedicated face texture).

## Run 3: Depeša head from the frontal portrait (2026-11-07)

Input `beauty/depesa_frontal_e2.png`. Graph AGORA_CHAR_02 with upsample 1024, 200k faces, 4K maps.
2,766 s (texture bake 26 min, normal bake about 10 min), VRAM baseline 15.9 GB, peak 21.8 GB.
High-poly 244 MB. Final 176,535 faces, 460 components. Views `review/depesa_head_v1_*.png`.

Result: FAIL. The face is shattered into flat shards, the eyes are metallic fragments, the texture is
smeared across the cuts. The owner predicted it ("to bude napicu"). TRELLIS from one portrait does not
carry a face; it is not a route to a beautiful 3D face.

## Open before any spend

- Path T costs at least 20 USD for one month. Path H costs 0 USD but uses the shared GPU under the
  compute rules (WATCH and ComfyUI first; lock file in C:\Users\Danculus\.claude\compute\).
- The 32 prompts contradict bio v2 in 7 places and are portrait prompts; the concept sheets of step 1
  need new prompts.
