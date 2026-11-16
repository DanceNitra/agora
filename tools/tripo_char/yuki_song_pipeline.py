"""Song to Yuki: one command from a video of a singing face to Yuki performing it, side by side, measured.

    .venv_mp/Scripts/python.exe yuki_song_pipeline.py --tag NAME (--url URL | --video FILE)
        (--start S --dur D | --auto D) [--steps download,head,unreal,render,compare,audit]
    .venv_mp/Scripts/python.exe yuki_song_pipeline.py --tag NAME --steps fit,render,compare,audit --fit-train RUN1,RUN2

Steps (run in this order; --steps runs a subset, for example after a failure):
 1. download  yt-dlp fetches [start, start + dur] at up to 1080p with sound. With --auto D the whole video is first
              fetched at 360p and perf_clip_pick finds the best continuous D seconds (face found, frontal, no shot cut,
              most brow, eye and mouth activity). YouTube material is for private tests only.
 2. head      perf_head_angles: the performer's head yaw, pitch and roll at 30 fps (drives Yuki's neck and head).
 3. unreal    starts the editor (own PID), solves the face with MetaHuman Animator (ue_mha_mono_solve), builds the
              body head additive (ue_yuki_head_additive), opens L_Yuki_Preview, builds the sequence and its render
              config (ue_yuki_dance_seq), then closes the editor.
 4. render    render_yuki_seq.ps1 renders the sequence in a separate -game process.
 5. compare   side by side (performer left, Yuki right, the performer's sound) and perf_emotion_match per channel.
 6. audit     perf_audit: per channel and shape checks against the singer, appended to ACTING_LEARNING_LOG.md.
 fit          (instead of unreal, after a solve exists) dumps the solved face, applies the gains yuki_expr_fit learns
              from the audits of --fit-train, saves A_P_<tag>_face_fit and a sequence LS_Yuki_Dance_P_<tag>_fit. With
              fit in the steps, render, compare and audit work on the fitted variant (render_fit/, *_fit files).

Work folder reports/yuki_lipsync/perf/<tag>/ (source.mp4, head.json, render/, <tag>_vs_yuki.mp4, compare.txt).
Unreal assets /Game/AgoraChar/Tripo/Yuki/MHA/A_P_<tag>_face_nohead and A_P_<tag>_head, sequence
LS_Yuki_Dance_P_<tag>. A compute lock (agora-tripo-char.lock) is held while Unreal runs."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / "comfy_char" / "ue_py.py"
UE_EXE = r"C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe"
UPROJECT = r"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject"
LOCK = Path(r"C:\Users\Danculus\.claude\compute\agora-tripo-char.lock")
MHA = "/Game/AgoraChar/Tripo/Yuki/MHA"
IDLE = "/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Stand_Idle_Loop"
PROP_ADD = "/Game/AgoraChar/Tripo/Yuki/Anim/A_Yuki_ProportionsAdd"
FFMPEG, YTDLP = "ffmpeg", "yt-dlp"

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--url")
ap.add_argument("--video")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--dur", type=float, default=15.0)
ap.add_argument("--auto", type=float, default=0.0)
ap.add_argument("--steps", default="download,head,unreal,render,compare,audit")
ap.add_argument("--variant", default="", help="render, compare and audit a face variant, for example fit")
ap.add_argument("--fit-train", default="", help="runs whose audits train yuki_expr_fit, comma separated")
ap.add_argument("--label", default="", help="singer, song and year for the learning log")
a = ap.parse_args()
steps = a.steps.split(",")
W = ROOT / "reports" / "yuki_lipsync" / "perf" / a.tag
W.mkdir(parents=True, exist_ok=True)
if "fit" in steps and not a.variant:
    a.variant = "fit"
SFX = f"_{a.variant}" if a.variant else ""
SRC, HEAD, RDIR = W / "source.mp4", W / "head.json", W / f"render{SFX}"
NAME = "P_" + a.tag
NAMEV = NAME + SFX


def run(cmd, **kw):
    print(">>", " ".join(map(str, cmd))[:300], flush=True)
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode != 0:
        raise SystemExit(f"step failed ({r.returncode}): {cmd[0]}")
    return r


def ue(code, tag):
    p = W / f"_ue_{tag}.py"
    p.write_text(code, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines() if line.strip() and "DeprecationWarning" not in line)
    print(out[-3000:], flush=True)
    if "FAILED" in out or r.returncode != 0:
        raise SystemExit(f"unreal step {tag} failed")
    return out


def wrap(args, script):
    return f"ARGS = dict({args})\n" + (ROOT / script).read_text(encoding="utf-8")


if "download" in steps:
    if a.video:
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", a.start, "-i", a.video, "-t", a.dur, "-c:v", "libx264",
             "-crf", "16", "-c:a", "aac", SRC])
    else:
        start, dur = a.start, a.dur
        if a.auto:
            prev = W / "preview.mp4"
            run([YTDLP, "--no-warnings", "-q", "-f", "bv*[height<=360][ext=mp4]/bv*[height<=360]", "-o", prev, "--force-overwrites", a.url])
            run([sys.executable, ROOT / "perf_clip_pick.py", W / "picks.json", a.auto, 0.03, prev])
            picks = json.load(open(W / "picks.json"))
            best = next(iter(picks.values()))
            if not best:
                raise SystemExit("no continuous window of that length with a frontal face; try a shorter --auto")
            start, dur = best[0]["start"], a.auto
            print("AUTO window", start, "s, length", dur, flush=True)
        run([YTDLP, "--no-warnings", "-q", "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]", "--download-sections",
             f"*{start}-{start + dur}", "--force-keyframes-at-cuts", "--force-overwrites", "-o", SRC, a.url])
    json.dump({"url": a.url, "video": a.video, "start": a.start, "dur": a.dur, "auto": a.auto}, open(W / "source.json", "w"))

if "head" in steps:
    run([sys.executable, ROOT / "perf_head_angles.py", SRC, HEAD])

LVL = "import unreal\nunreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview')\n"


def with_editor(what, body):
    """Starts the editor (own PID), waits until it answers, runs body(), closes the editor and drops the lock."""
    LOCK.write_text(f"agora tripo_char: yuki_song_pipeline {a.tag}, Unreal 5.9 editor, {what}, "
                    f"scope=gpu ttl=60m started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    ed = subprocess.Popen([UE_EXE, UPROJECT, "-AutoDeclinePackageRecovery"])  # a killed editor leaves a restore prompt that blocks the next start
    print("EDITOR PID", ed.pid, flush=True)
    try:
        ready = "import unreal\nprint('READY', unreal.SystemLibrary.get_engine_version())\n"
        for _ in range(40):
            p = W / "_ue_ready.py"
            p.write_text(ready)
            r = subprocess.run([sys.executable, "-I", str(RUNNER), str(p)], capture_output=True, text=True)
            if "READY" in r.stdout:
                break
        else:
            raise SystemExit("the editor did not answer")
        body()
    finally:
        ed.kill()
        LOCK.unlink(missing_ok=True)
        print("EDITOR closed", flush=True)


def sequence(face):
    N = len(json.load(open(HEAD))["yaw"])
    ue(LVL + wrap(f"ANIM='{IDLE}', FACE='{face}', ADD=['{MHA}/A_{NAME}_head', '{PROP_ADD}'], Z_OFF=29.5, "
                  f"PRE=45, TAG='{NAMEV}', RANGE=(0, {N - 1}), FOCAL=150.0, CAM_Z=126.0, OUT=r'{RDIR.as_posix()}'",
                  "ue_yuki_dance_seq.py"), "sequence")


if "unreal" in steps:
    def solve():
        ue(wrap(f"VIDEO=r'{SRC.as_posix()}', NAME='{NAME}'", "ue_mha_mono_solve.py"), "solve")
        ue(wrap(f"JSON=r'{HEAD.as_posix()}', DST='{MHA}/A_{NAME}_head'", "ue_yuki_head_additive.py"), "head")
        sequence(f"{MHA}/A_{NAME}_face_nohead")
    with_editor("MetaHuman Animator solve", solve)

if "fit" in steps:
    CUR = W / "curves"
    CUR.mkdir(exist_ok=True)

    def fit():
        base = f"{MHA}/A_{NAME}_face_nohead"
        ue(wrap(f"ANIMS=['{base}'], OUT=r'{CUR.as_posix()}'", "ue_yuki_curves_dump.py"), "dump")
        run([sys.executable, ROOT / "yuki_expr_fit.py", "--train", a.fit_train, "--dump", CUR / f"A_{NAME}_face_nohead",
             "--out", CUR / f"face{SFX}"])
        ue(wrap(f"SRC='{base}', DST='{MHA}/A_{NAME}_face{SFX}', STEM=r'{(CUR / f'face{SFX}').as_posix()}'", "ue_yuki_curves_apply.py"), "apply")
        sequence(f"{MHA}/A_{NAME}_face{SFX}")
    if not a.fit_train:
        raise SystemExit("fit needs --fit-train RUN1,RUN2")
    with_editor("face fit", fit)

if "render" in steps:
    LOCK.write_text(f"agora tripo_char: yuki_song_pipeline {a.tag}{SFX}, render, scope=gpu ttl=60m started {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    try:
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ROOT / "render_yuki_seq.ps1", "-tag", NAMEV, "-out", RDIR])
    finally:
        LOCK.unlink(missing_ok=True)

if "compare" in steps:
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(SRC)],
                        capture_output=True, text=True).stdout.strip().split(",")
    w_, h_ = int(pr[0]), int(pr[1])
    s_ = min(w_, h_)
    left = f"[0:v]fps=30,crop={s_}:{s_}:{(w_ - s_) // 2}:{(h_ - s_) // 2},scale=900:900[l]"
    for crop, out, audio in (("700:700:190:330", W / f"{a.tag}{SFX}_vs_yuki.mp4", True), ("520:520:315:400", W / f"_tight{SFX}.mp4", False)):
        cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", SRC, "-framerate", 30, "-start_number", 45, "-i", RDIR / "%04d.png",
               "-filter_complex", f"{left};[1:v]crop={crop},scale=900:900[r];[l][r]hstack=inputs=2[v]", "-map", "[v]"]
        cmd += (["-map", "0:a", "-c:a", "aac"] if audio else []) + ["-c:v", "libx264", "-crf", 18, "-pix_fmt", "yuv420p", "-shortest", out]
        run(cmd)
    with open(W / f"compare{SFX}.txt", "w", encoding="utf-8") as f:
        r = subprocess.run([sys.executable, str(ROOT / "perf_emotion_match.py"), str(W / f"_tight{SFX}.mp4")], capture_output=True, text=True)
        f.write(r.stdout)
    print("\n".join(line for line in r.stdout.splitlines() if "UPPER" in line or "MOUTH" in line or "lag" in line), flush=True)
    print("DONE", W / f"{a.tag}{SFX}_vs_yuki.mp4", flush=True)

if "audit" in steps:
    run([sys.executable, ROOT / "perf_audit.py", W, "--label", a.label] + (["--variant", a.variant] if a.variant else []))
