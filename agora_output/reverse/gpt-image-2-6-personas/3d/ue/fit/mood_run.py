"""Solve the chorus with several moods, build sequences and render each in a separate process."""
import json, os, subprocess, sys, io, contextlib
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
sys.path.insert(0, F); os.chdir(F)
import fit_lib as f, ue_py
WAV = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\lipsync\lajk_refren.wav"
MOODS = [("PLAYFULNESS", 0.9), ("CONFIDENCE", 0.9), ("HAPPINESS", 0.8)]

def run(script, timeout=900):
    p = os.path.join(F, "_ue_tmp.py"); open(p, "w", encoding="utf-8").write(open(script).read())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ue_py.run_file(p, timeout=timeout)
    return buf.getvalue()

for mood, inten in MOODS:
    name = "Depesa_lajk_" + mood.lower()
    json.dump({"name": name, "wav": WAV, "sound": "Depesa_lajk", "mood": mood, "mood_intensity": inten}, open("lipsync_cfg.json", "w"))
    out = run("ue_lipsync.py") + run("ue_lsexport.py") + run("ue_seq_kf.py")
    seq = [l.split()[1] for l in out.splitlines() if l.startswith("SEQ ")][-1]
    print(mood, "seq", seq, [l for l in out.splitlines() if l.startswith(("K CTRL_expressions_jawOpen", "CURVES"))], flush=True)
    ps = open("kf_run.ps1").read().replace("/Game/Companions/Lipsync/LS_KF_Depesa_line1_v2.LS_KF_Depesa_line1_v2", seq).replace("MRQ_kf.log", "MRQ_%s.log" % mood)
    open("mood_run.ps1", "w").write(ps)
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "mood_run.ps1"], capture_output=True, text=True)
    print(mood, r.stdout.strip().splitlines()[-1], flush=True)
    import shutil
    dst = os.path.join(F, "render_" + mood.lower())
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(os.path.join(F, "render_v5"), dst)
