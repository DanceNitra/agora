"""Fits MH_Depesa's 81 face landmarks (X and Z, the image plane of the front camera) so that the tracked
eye, lip and nasolabial curves match the reference portrait. Finite-difference Jacobian, damped least
squares, 3 iterations. Writes progress to fit_run.log and keeps the best state."""
import json, sys, time, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *

ref = json.load(open(F + r"\ref_landmarks.json"))
KEYS = sorted(ref)
REF = flat(ref, KEYS)
STEP = 0.6
LOG = open(F + r"\fit_run.log", "a", buffering=1)


def log(*a):
    LOG.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")


def translate(idx, dx, dz):
    ue(f'''import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
mhs.translate_face_landmarks(ch, {list(idx)}, [unreal.Vector(x, 0.0, z) for x, z in {[[float(a), float(b)] for a, b in zip(dx, dz)]}])''')


def measure(tag):
    lm = track(capture(tag), tag)
    if sorted(lm) != KEYS or any(len(lm[k]) != len(ref[k]) for k in KEYS):
        return None, 1e9
    err, aligned = aligned_error(lm, ref)
    return aligned, err


n = 81
cur, err0 = measure("fit_it0")
log("start err", round(err0, 3))
best = err0
for it in range(1, 4):
    J = np.zeros((REF.size, 2 * n))
    for p in range(2 * n):
        i, axis = p // 2, p % 2
        dx, dz = (STEP, 0.0) if axis == 0 else (0.0, STEP)
        translate([i], [dx], [dz])
        a, e = measure("fd")
        translate([i], [-dx], [-dz])
        if a is not None:
            J[:, p] = (a - cur).reshape(-1) / STEP
        if p % 20 == 0:
            log("it", it, "jacobian col", p, "of", 2 * n)
    r = (REF - cur).reshape(-1)
    lam = 0.05 * np.trace(J.T @ J) / (2 * n) + 1e-6
    d = np.linalg.solve(J.T @ J + lam * np.eye(2 * n), J.T @ r)
    d = np.clip(d, -2.0, 2.0)
    translate(range(n), d[0::2], d[1::2])
    new, err = measure(f"fit_it{it}")
    log("it", it, "err", round(err, 3), "max step cm", round(float(np.abs(d).max()), 3))
    if err > best:  # undo a step that made it worse and stop
        translate(range(n), -d[0::2], -d[1::2])
        log("it", it, "worse, undone; stop")
        break
    best, cur = err, new
log("DONE best err", round(best, 3), "from", round(err0, 3))
