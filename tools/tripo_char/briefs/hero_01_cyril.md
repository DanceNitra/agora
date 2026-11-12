# Hero 01: Cyril, present day (draft for the owner)

Status 2026-11-11: draft. Nothing is rendered. The owner approves or changes this brief before step 2 of
section 5.5 in `docs/TRIPO_UE_WORKFLOW.md`.

## Idea

The owner's idea: Cyril and Methodius reincarnated as two heroes in the present day. The setting of the world
(Renaissance, fantasy, cyberpunk) is open and changes only the wardrobe.

Cyril is the first run because a slim, average build is the easiest fit for **From Custom Mesh**. Methodius
follows as the second hero with a broader build.

## Proposed look (all of it is a proposal, none of it is a historical claim)

| Item | Proposal |
|---|---|
| Age | Early thirties |
| Build | Slim, average height (target 178 cm), narrow shoulders, upright posture |
| Face | Calm and attentive, short dark beard, short dark hair; no likeness to a living person |
| Present-day dress | Dark fitted trousers, plain fitted long-sleeve shirt, short fitted jacket, ankle boots |
| Signature item | A small book or notebook, as a separate prop on a hand socket, not part of the body |
| Colours | Muted: charcoal, off-white, one deep blue accent |

Contrast planned for Methodius: about ten years older, broad and solid, shorter hair, fuller beard, practical
work clothing.

## Rules the images must meet (from Epic's From Custom Mesh page)

- A pose: arms straight, about 45 degrees down from horizontal, palms toward the thighs, fingers apart.
- Legs straight, feet apart at hip width, both feet flat.
- Exact front view, whole body in frame, plain light grey background, even light, no cast shadow.
- Image (a), the body: tight short underlayer only, bare arms and legs, bare feet, no loose cloth, no folds,
  no accessories, hair short and close to the head.
- Image (b), the dress: the same person and pose, made by an image edit of (a), so the proportions stay equal.

## Images

| Image | Workflow | Model |
|---|---|---|
| (a) body | `workflows/HERO_01_body_api.json` | `qwen_image_2512_fp8_e4m3fn` |
| (b) dressed | built after the owner picks one (a) | `qwen_image_edit_2511_fp8mixed` |

## Open

- The owner's changes to the look.
- Whether the face should echo the statue under the castle.
