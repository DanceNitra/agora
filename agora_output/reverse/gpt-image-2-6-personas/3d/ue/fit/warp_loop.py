"""Telephoto warp-and-solve loop. Restores the preset face (face_v_state0.bin), then per round:
telephoto capture (90 cm), MediaPipe, smooth orthographic warp toward p6, MetaHuman fit_state_to_target_vertices.
Run with .venv_face python: python warp_loop.py <rounds> <alpha> <smooth>. Log: warp_loop.log."""
import json, os, shutil, subprocess, sys, time
import numpy as np
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
sys.path.insert(0, F)
os.chdir(F)
import fit_lib as f  # noqa: E402
import tele2  # noqa: E402
import mp_lm  # noqa: E402
from mp_regions import report  # noqa: E402

ROUNDS, ALPHA, SMOOTH = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
SUBSET = sys.argv[4] if len(sys.argv) > 4 else 'all'
TAG = sys.argv[5] if len(sys.argv) > 5 else 'r'
DIST, DZ, FOV_REAL = 90.0, -0.6, 12.0
REF = np.array(json.load(open("mp_ref_512x768.json")))
LOG = open("warp_loop.log", "a", buffering=1)


def log(*a):
    LOG.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")


def fit_to(path):
    if os.path.abspath(path) != os.path.abspath("face_target_v.bin"):
        shutil.copy(path, "face_target_v.bin")
    out = f.ue(open("ue_fitverts.py").read())
    return out.strip().splitlines()[-1]


def export():
    f.ue(open("ue_export.py").read())


def shoot(tag):
    p = tele2.shoot(tag, 18.0, DIST, DZ)
    cam = json.load(open(f"tele_{tag}_cam.json"))
    cam["fov"] = FOV_REAL  # the viewport keeps the first pilot FOV; measured by projection
    json.dump(cam, open(f"tele_{tag}_cam.json", "w"))
    return p


def score(p):
    pts = mp_lm.detect(p)
    if pts is None:
        return None
    r, _ = report(pts, REF)
    return {k: round(v, 2) for k, v in r.items()}


if os.environ.get("NO_RESTORE") != "1":
    log("restore preset:", fit_to("face_v_state0.bin"))
export()
p = shoot(f"{TAG}0")
log("round 0", score(p))
for r in range(1, ROUNDS + 1):
    shutil.copy("face_v.bin", f"face_v_{TAG}{r - 1}.bin")
    res = subprocess.run([sys.executable, "warp_build.py", f"tele_{TAG}{r - 1}.png", f"tele_{TAG}{r - 1}_cam.json",
                          str(ALPHA), str(SMOOTH), SUBSET], capture_output=True, text=True)
    if res.returncode:
        log("warp_build failed:", res.stderr[-600:])
        break
    rep = json.load(open("warp_report.json"))
    log(f"round {r} warp rms_cm {rep['rms_cm']:.3f} max_move {rep['max_vertex_move_cm']:.2f}")
    log(f"round {r} fit:", fit_to("face_target_v.bin"))
    export()
    p = shoot(f"{TAG}{r}")
    log(f"round {r}", score(p))
shutil.copy("face_v.bin", f"face_v_{TAG}{ROUNDS}.bin")
log("DONE")
