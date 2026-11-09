# Photo to beautiful MetaHuman: how it is done in late 2026

Date: 2026-11-08. Trigger: owner rejected the landmark-fit Depeša ("PREDPOTOPNA METODA").

## Why our method failed
We bent a preset (Vivian) toward 2D landmarks of p6 and kept the preset's generic skin texture. Beauty in p6
lives in three things we never transferred: the 3D volumes (cheeks, nose bridge, lips), the skin and makeup
texture, and the brows and eye shape. Every current pipeline below transfers all three.

## What current pipelines do (sources at the end)
1. **A real 3D head first, from several views.** Single photo works but every vendor recommends a front view
   plus about 40-45 degree turns to each side (KeenFace: 2-15 images; Meshy: multi-view Image to 3D).
2. **Wrap MetaHuman topology onto that head**, so the rig survives (KeenFace exports it directly; Meshy route uses
   Faceform Wrap or Blender Shrinkwrap plus Character DNA Pro).
3. **Project the photo texture**: 4K base colour + normal (+ SRMF) from the photos, applied in MetaHuman Creator
   under Texture & Material Overrides. This is where likeness and beauty come from.
4. **Conform from Template / Mesh**, auto-rig, assemble. Our API already has `enable_texture_overrides`,
   `texture_overrides`, `conform_to_target_meshes`, `fit_state_to_target_vertices`, auto-rig and build.
5. Lip-sync: MetaHuman Audio Driven Animation, which we already have working (332 frames from Slovak Piper).

## Candidate head sources
| Tool | What you get | Cost | Notes |
|---|---|---|---|
| KeenFace (KeenTools, cloud) | MetaHuman-topology head FBX + 4K albedo, normal, SRMF; PBR cleanup removes baked light | 150 credits = 15 EUR per head; new account 450 free credits = 3 heads | Licence terms NOT yet read. Bald head, no eyes/teeth (we have those from MH). |
| Meshy (multi-view Image to 3D + AI texturing 8K) | dense mesh + texture, needs wrap + DNA convert | paid plan for private output; free = public CC BY 4.0 | Wrap step is manual and slow. |
| Rodin Gen-2 | most cited for realistic faces in 2026 roundups | highest price tier | No rigorous face benchmark found. |
| Research (Any3DAvatar 2604.13856, PercHead, SEGA, VASA-3D) | Gaussian heads, some audio-driven | free code where released | Gaussians, not engine meshes; no code/licence found for Any3DAvatar. Not for the device pipeline. |

## Proposed plan (not started)
1. Make 2 extra views of p6 with GPT Image 2.6 edits (left and right 3/4, same face, same light), about 0.10 USD.
2. KeenFace with the free 3-head trial on p6 + those views (owner creates the account; I may not).
3. Import the MetaHuman template + 4K maps, conform, texture override, auto-rig, build, render the same lip-sync
   line. Owner judges beauty on that render, side by side with p6.

## Sources
- KeenFace review, Digital Production, 2026-10-22: https://digitalproduction.com/2026/10/22/keenface-photos-3d-heads/
- Meshy to MetaHuman 2026 workflow: https://www.meshy.ai/tutorials/meshy-to-metahuman-blender-workflow
- KeenTools MetaHuman solution: https://cloud.keentools.io/solutions/metahumans
- MetaHuman 5.7 release notes: https://dev.epicgames.com/documentation/metahuman/metahuman-5-7-release-notes
- Any3DAvatar: https://arxiv.org/abs/2604.13856 ; VASA-3D: https://arxiv.org/pdf/2512.14677
- 2026 image-to-3D roundups: https://www.rapiddirect.com/blog/best-8-ai-3d-model-generators/ , https://fuser.studio/articles/best-ai-3d-model-generators
