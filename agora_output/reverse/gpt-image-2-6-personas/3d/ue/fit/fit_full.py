"""Full-face fit of MH_Depesa to the p6 frontal reference.

Measures 467 MediaPipe points (jaw oval, brows, eyes, irises, nose, lips, cheeks; the forehead rim under
the hair is left out) on the Unreal capture and on the reference, aligns them by a weighted similarity
transform, and moves the 81 MetaHuman sculpt landmarks in X and Z (the image plane) to reduce the error.
Finite-difference Jacobian once, then damped Gauss-Newton steps with a step-size search and Broyden
updates; the Jacobian is rebuilt when a step fails. Every accepted state is saved as 3D landmarks so it
can be restored. Run with .venv_face python. Progress goes to fit_full.log.
"""
import json, sys, time
import numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import F, ASSET, ue, capture  # noqa: E402
from PIL import Image  # noqa: E402
import mp_lm  # noqa: E402
from mp_regions import report, USED, W  # noqa: E402

REF = np.array(json.load(open(F + r"\mp_ref_512x768.json")))
SQW = np.sqrt(W[USED])[:, None]
N = 81
STEP = 0.6           # cm, finite-difference step
CLIP = 1.5           # cm, largest move of one landmark per step
MAX_STEPS = 8
LOG = open(F + r"\fit_full.log", "a", buffering=1)

def log(*a):
    LOG.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")

PRE = f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
'''

def translate(idx, dx, dz):
    moves = [[float(a), float(b)] for a, b in zip(dx, dz)]
    ue(PRE + f"mhs.translate_face_landmarks(ch, {list(idx)}, "
             f"[unreal.Vector(x, 0.0, z) for x, z in {moves}])")

def save_state(tag):
    out = ue(PRE + 'print("LMK" + json.dumps([[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]))')
    L = json.loads(out.split("LMK", 1)[1].strip().splitlines()[0])
    json.dump(L, open(F + rf"\state_{tag}.json", "w"))
    return np.array(L)

def measure(tag):
    im = capture(tag)
    w, h = im.size
    cw = int(h * 512 / 768)
    x0 = (w - cw) // 2
    im = im.crop((x0, 0, x0 + cw, h)).resize((512, 768), Image.LANCZOS).convert("RGB")
    path = F + rf"\{tag}.png"
    im.save(path)
    pts = mp_lm.detect(path)
    if pts is None:
        return None, 1e9, {}
    reg, full = report(pts, REF)
    res = (SQW * (REF[USED] - full[USED])).reshape(-1)  # weighted residual
    return full[USED], float(np.sqrt((res ** 2).mean())), reg

def fmt(reg):
    return " ".join(f"{k}={v:.2f}" for k, v in reg.items())

def jacobian(cur):
    J = np.zeros((cur.size, 2 * N))
    for p in range(2 * N):
        i, ax = p // 2, p % 2
        dx, dz = (STEP, 0.0) if ax == 0 else (0.0, STEP)
        translate([i], [dx], [dz])
        a, _, _ = measure("ff_fd")
        translate([i], [-dx], [-dz])
        if a is not None:
            J[:, p] = (SQW * (a - cur)).reshape(-1) / STEP
        if p % 20 == 0:
            log("jacobian col", p, "of", 2 * N)
    return J

save_state("ff0")
cur, err, reg = measure("ff_0")
_, err_b, _ = measure("ff_0b")
log("start err", round(err, 3), "| repeat", round(err_b, 3), "| noise", round(abs(err - err_b), 3), "|", fmt(reg))
J, fails, step_no = None, 0, 0
while step_no < MAX_STEPS:
    if J is None:
        J = jacobian(cur)
        log("column norm median", round(float(np.median(np.linalg.norm(J, axis=0))), 3))
    r = (SQW * (REF[USED] - cur)).reshape(-1)
    lam = 0.05 * np.trace(J.T @ J) / (2 * N) + 1e-6
    d = np.clip(np.linalg.solve(J.T @ J + lam * np.eye(2 * N), J.T @ r), -CLIP, CLIP)
    best = None
    for s in (1.0, 0.5, 0.25):
        translate(range(N), s * d[0::2], s * d[1::2])
        new, e, rg = measure(f"ff_try")
        log(f"  try scale {s} err {e:.3f}")
        if e < err:
            best = (s, new, e, rg)
            break
        translate(range(N), -s * d[0::2], -s * d[1::2])
    if best is None:
        fails += 1
        log("step failed", fails)
        if fails >= 2:
            break
        J = None  # rebuild the Jacobian at this point
        continue
    s, new, e, rg = best
    step_no += 1
    fails = 0
    # Broyden rank-1 update with the observed change
    dd = s * d
    dy = (SQW * (new - cur)).reshape(-1)
    J += np.outer(dy - J @ dd, dd) / (dd @ dd)
    cur, err = new, e
    measure(f"ff_{step_no}")
    save_state(f"ff{step_no}")
    log("step", step_no, "err", round(err, 3), "max move cm", round(float(np.abs(dd).max()), 3), "|", fmt(rg))
log("DONE err", round(err, 3))
