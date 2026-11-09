"""Try MetaHuman eye makeup variants on MH_DepesaKF: apply, build, render (separate process), crop the eyes."""
import json, os, subprocess, sys, io, contextlib, shutil
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
M = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\makeup"
sys.path.insert(0, F); os.chdir(F)
import fit_lib as f, ue_py

def run(script, timeout=1500):
    p = os.path.join(F, "_ue_tmp.py"); open(p, "w", encoding="utf-8").write(open(script).read())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ue_py.run_file(p, timeout=timeout)
    return buf.getvalue()

L = json.load(open(os.path.join(M, "look_p6.json"), encoding="utf-8"))
brown, black = [0.05, 0.026, 0.016, 1.0], [0.002, 0.002, 0.002, 1.0]
VARS = {
    "cat_eye": {"eyes.type": "CAT_EYE", "eyes.primary_color": brown, "eyes.secondary_color": black, "eyes.opacity": 0.9, "eyes.metalness": 0.18, "eyes.roughness": 0.5},
    "soft_smokey": {"eyes.type": "SOFT_SMOKEY", "eyes.primary_color": brown, "eyes.secondary_color": black, "eyes.opacity": 0.75, "eyes.metalness": 0.12, "eyes.roughness": 0.5},
    "thin_liner": {"eyes.type": "THIN_LINER", "eyes.primary_color": brown, "eyes.secondary_color": black, "eyes.opacity": 0.95, "eyes.metalness": 0.1, "eyes.roughness": 0.5},
}
for name, eyes in VARS.items():
    mm = dict(L["metahuman_makeup"]); mm.update(eyes)
    json.dump({"bc_png": os.path.join(M, "look_p6_BC.png"), "asset_name": "T_DepesaKF_Look_p6_v4", "metahuman_makeup": mm},
              open(os.path.join(M, "apply_cfg.json"), "w"), indent=1)
    o = run(os.path.join(M, "ue_apply_look.py")) + run("ue_build_kf.py")
    print(name, [l for l in o.splitlines() if l.startswith(("LOOK", "BUILT"))][:2], flush=True)
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "look_run.ps1"], capture_output=True, text=True)
    print(name, r.stdout.strip().splitlines()[-1], flush=True)
    dst = os.path.join(F, "render_eye_" + name)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(F, "render_v5"), dst)
    json.dump(mm, open(os.path.join(M, f"eyes_{name}.json"), "w"), indent=1)
