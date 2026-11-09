# MetaHuman brief: Depeša (18-24), beauty first

Owner, 2026-11-07: "krasa cloveka musi byt na prvom mieste", "10/10 modely". Bio: crew/22-personas-v2.report.md
section 4.4. Critic fix: crew/04-critic.report.md 3.4 (her look was "the most common cyberpunk woman").
Tool: MetaHuman Creator inside Unreal 5.8 (plugins MetaHumanCharacter and MetaHumanGenerator enabled in
MyProject by the REA session). Licence: free under 1M USD revenue, renders royalty-free (metahuman.com/license,
read 2026-11-07). Status: brief only; Unreal belongs to the REA session until it says the editor is free.

## 1. Beauty (judged first, by the owner, before any technical check)

- **Who she is in one look:** a 23-year-old night courier who laughs easily and runs everywhere. Beauty
  comes from life in the face: a dry, warm half-smile, alert eyes, healthy skin. Not a model's pose.
- **Face:** soft oval with defined cheekbones, straight nose, full but natural lips, slightly wide-set
  almond eyes in warm dark brown with clear catchlights, straight dark brows with a natural arch.
- **Skin:** light olive, real texture and pores, a little warmth on the cheeks, no heavy make-up, no
  glamour retouching.
- **Hair:** long straight black hair, glossy from the rain, one side tucked behind the ear to show the
  data earring. No shaved side (critic: stock cyberpunk look). The asymmetry lives in the gear.
- **Proportions:** clearly adult, athletic runner's build, practical posture.
- **Not allowed:** sexualised styling, cleavage, glamour lighting on wet skin, childlike features.

## 2. Gear (the five world layers, readable in a head-and-shoulders crop)

| Layer | Item |
|---|---|
| Hull (used-future) | old fleet radio earpiece on the left ear |
| Machine (robotics) | small servo inside the long data earring |
| Craft (hand-painted enamel) | cherry-red enamel on the left shoulder plate of her courier jacket |
| Myth | one line of gold-leaf verse along the jacket collar, unreadable at screen size |
| Night (neon) | a thin light thread along the jacket seam and the wet sheen of rain |

- Jacket zipped to the collar. Svitok core: oval amber with a dark fleck, at the throat, on a brass
  crescent gorget resting on the collarbones, never a collar around the neck.
- Guild colour: cherry red.

## 3. Light and frame (world signature)

Amber low sun from the left, rose-violet night sky from the right, light rain. Head-and-shoulders for the
talking head; full body for idle and dance. Render at 640x1280 and reduce to 80x160.

## Unreal rules from the REA session (2026-11-07)

- Wait for its message that the editor (PID 42280) is free; it is building a MetaHuman soldier now.
- Our assets only under `/Game/Companions/`; theirs are under `/Game/AgoraChar/`.
- `save_assets` with an empty list saves every dirty asset: always pass explicit paths.
- Never delete or recreate an asset an AnimBP references: Play then opens a modal dialog that freezes MCP.
- Measure the character in Play, not only as assets. Backup of the project file:
  `MyProject.uproject.bak-before-metahuman-20261107`.

## 4. Technical checks (only after the owner says the face is beautiful)

1. Facial rig: blink, the nine Rhubarb mouth shapes, three emotions.
2. Lip-sync: MetaHuman Animator from a Slovak audio line (Piper "lili") versus Rhubarb shape keys.
   Which language the audio solver handles well is UNKNOWN; this test answers it.
3. Gear: the jacket, earring, gorget and core are not in the MetaHuman library; source them as our own
   meshes (TRELLIS.2 from our concepts) and fit them to the body.
4. 80x160 readability, the same calibrated test the owner already passed.
