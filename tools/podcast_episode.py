#!/usr/bin/env python3
"""podcast_episode: one "Echoes of Tomorrow" episode from one gated article, through NotebookLM.

The mechanics only. The judgement (what the deep research adds, what survives verify-claims, the
--focus string) is Claude's, written into agora_output/derivatives/<slug>/episode.md and
verified_context.md before `audio` runs. This file runs the `nlm` CLI, faster-whisper and ffmpeg,
and refuses to master an episode whose transcript carries a number the article does not.

Stages, each a subcommand, state in agora_output/episodes/<slug>/episode.json:

    research    nlm research start --mode deep, auto-import, add the article URL as a source
    audio       nlm audio create with the focus from episode.md, wait, download episode_raw.*
    transcribe  faster-whisper (large-v3-turbo on CUDA, the dictate engine's model) -> transcript
    check       every number in the transcript exists in the article or verified_context.md
    master      ffmpeg loudnorm -16 LUFS, AAC 128k, tags, optional intro and outro -> episode.m4a
    package     spotify.md with every field the Spotify for Creators form asks for
    all         audio, transcribe, check, master, package

Every long step prints a heartbeat. NotebookLM audio takes minutes; deep research about five.

Usage:
    python tools/podcast_episode.py research <slug> [--query "..."] [--mode deep|fast]
    python tools/podcast_episode.py audio <slug> [--format deep_dive] [--length default]
    python tools/podcast_episode.py audio <slug> --artifact <id> [--notebook <id>]   (existing)
    python tools/podcast_episode.py transcribe|check|master|package|all <slug>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_post as dp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EPISODES = ROOT / "agora_output" / "episodes"
SHOW = "Echoes of Tomorrow"
ARTIST = "Agora"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", NOTEBOOKLM_HL="en-US")   # every artifact in English


def say(msg: str) -> None:
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def nlm(*args: str, timeout: int = 600) -> str:
    """Run one nlm command and return its stdout. Raises on a non-zero exit."""
    cmd = ["nlm", *args]
    say("$ " + " ".join(a if " " not in a else repr(a) for a in cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"nlm exited {p.returncode}:\n{p.stdout}\n{p.stderr}")
    return p.stdout


def folder(slug: str) -> Path:
    f = EPISODES / slug
    f.mkdir(parents=True, exist_ok=True)
    return f


def state(slug: str) -> dict:
    p = folder(slug) / "episode.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"slug": slug}


def save(slug: str, st: dict) -> None:
    (folder(slug) / "episode.json").write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def derivatives(slug: str) -> Path:
    d = dp.OUT / slug
    if not (d / "article.sha256").exists():
        raise SystemExit(f"{d} is not initialised; run: python tools/derive_post.py init {slug}")
    return d


def section(md: str, heading: str) -> str:
    m = re.search(r"^## " + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", md, re.S | re.M)
    return (m.group(1) if m else "").strip()


def article_meta(slug: str) -> dict:
    return json.loads((derivatives(slug) / "meta.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- research

def cmd_research(slug: str, query: str | None, mode: str) -> int:
    st = state(slug)
    meta = article_meta(slug)
    art = (dp.SRC / f"{slug}.en.md").read_text(encoding="utf-8")
    title = art.splitlines()[0].lstrip("# ").strip()
    q = query or title
    say(f"deep research on: {q!r}")
    out = nlm("research", "start", q, "--mode", mode, "--title", f"{SHOW}: {slug}",
              "--auto-import", "--force", timeout=1500)
    ids = UUID.findall(out)
    if not ids:
        print(out)
        raise SystemExit("no notebook id in the research output; see the output above")
    nb = ids[0]
    st.update({"notebook": nb, "research_query": q, "research_mode": mode,
               "research_output": out[-3000:]})
    save(slug, st)
    say(f"notebook {nb}; adding the article as a source: {meta['url']}")
    nlm("source", "add", nb, "--url", meta["url"], timeout=300)
    src = nlm("source", "list", nb, "--json")
    st["sources"] = json.loads(src) if src.strip().startswith("[") else src
    save(slug, st)
    n = len(st["sources"]) if isinstance(st["sources"], list) else "?"
    say(f"research done: notebook {nb}, {n} sources. Next: read the notebook, verify what you "
        f"keep into verified_context.md, write episode.md, then `audio`.")
    return 0


# ---------------------------------------------------------------- audio

def _artifact_status(nb: str, art_id: str) -> str:
    out = nlm("studio", "status", nb, "--json", "--artifact-id", art_id)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return "unknown"
    items = data if isinstance(data, list) else [data]
    for it in items:
        if it.get("artifact_id") == art_id or it.get("id") == art_id:
            return str(it.get("status", "unknown"))
    return "unknown"


def _audio_in_progress(nb: str) -> list[str]:
    out = nlm("studio", "status", nb, "--json")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [a.get("artifact_id") for a in (data if isinstance(data, list) else [data])
            if a.get("type") == "audio" and a.get("status") == "in_progress"]


def cmd_audio(slug: str, fmt: str, length: str, language: str, artifact: str | None,
              notebook: str | None) -> int:
    st = state(slug)
    nb = notebook or st.get("notebook")
    if not nb:
        raise SystemExit("no notebook yet; run `research` first or pass --notebook")
    st["notebook"] = nb
    if artifact:
        art_id = artifact
        say(f"using existing artifact {art_id}")
    else:
        # A "rate limited" error from `audio create` does not mean the job was refused: measured
        # 2026-09-17, every retry queued another generation and 36 sat in progress. Never create
        # while one is queued; attach to it instead.
        queued = _audio_in_progress(nb)
        if queued:
            say(f"an audio job is already in progress ({queued[0][:8]}); attaching to it instead of creating another")
            art_id = queued[0]
            st["artifact"] = art_id
            save(slug, st)
            return _wait_and_download(slug, st, nb, art_id)
        ep = (derivatives(slug) / "episode.md").read_text(encoding="utf-8")
        focus = section(ep, "Focus")
        if not focus or focus.startswith("("):
            raise SystemExit("episode.md has no ## Focus text; write it first (from the article "
                             "and verified_context.md only)")
        out = nlm("audio", "create", nb, "--format", fmt, "--length", length, "--language",
                  language, "--focus", focus, "-y", "--json", timeout=300)
        ids = UUID.findall(out)
        if not ids:
            print(out)
            raise SystemExit("no artifact id in the audio create output")
        art_id = ids[-1] if ids[-1] != nb else ids[0]
        st.update({"audio_format": fmt, "audio_length": length, "focus": focus})
    st["artifact"] = art_id
    save(slug, st)
    return _wait_and_download(slug, st, nb, art_id)


def _wait_and_download(slug: str, st: dict, nb: str, art_id: str) -> int:
    t0 = time.time()
    while True:
        status = _artifact_status(nb, art_id)
        say(f"artifact {art_id[:8]} status {status} ({int(time.time() - t0)} s)")
        if status.lower() in ("completed", "complete", "ready", "done"):
            break
        if status.lower() in ("failed", "error"):
            raise SystemExit("NotebookLM reported the audio as failed")
        if time.time() - t0 > 1800:
            raise SystemExit("audio not ready after 30 minutes; rerun `audio --artifact <id>` later")
        time.sleep(30)
    raw = folder(slug) / "episode_raw.m4a"
    # NotebookLM reports the artifact complete minutes before its media URL resolves; measured
    # 2026-09-17: 404 for about four minutes after "completed". Retry for up to 15 minutes.
    t1 = time.time()
    while True:
        try:
            nlm("download", "audio", nb, "--id", art_id, "--output", str(raw), "--no-progress",
                timeout=900)
            break
        except SystemExit as ex:
            if "propagating" not in str(ex) or time.time() - t1 > 900:
                raise
            say("media URL still propagating; retrying in 60 s")
            time.sleep(60)
    found = raw if raw.exists() else next(folder(slug).glob("episode_raw.*"), None)
    if not found:
        raise SystemExit("download reported success but no episode_raw.* file exists")
    st["raw"] = str(found)
    save(slug, st)
    say(f"downloaded {found} ({found.stat().st_size // 1024} KB)")
    return 0


# ---------------------------------------------------------------- transcribe

def cmd_transcribe(slug: str, model: str, language: str | None) -> int:
    st = state(slug)
    raw = Path(st.get("raw", ""))
    if not raw.exists():
        raise SystemExit("no raw audio; run `audio` first")
    from faster_whisper import WhisperModel  # the dictate engine's dependency, CUDA build
    say(f"loading faster-whisper {model} on cuda")
    try:
        wm = WhisperModel(model, device="cuda", compute_type="auto")
    except Exception as e:  # noqa: BLE001
        say(f"cuda failed ({e.__class__.__name__}); falling back to cpu int8")
        wm = WhisperModel(model, device="cpu", compute_type="int8")
    # The article's own numbers as a vocabulary hint. Measured 2026-09-17: "200,050" came out as
    # "200,000 50" without it and "200,050" with it, while a genuinely misspoken "1.8.0" stayed
    # "1.8.0" either way, so the hint sharpens recognition without hiding a wrong number.
    art = (dp.SRC / f"{slug}.en.md").read_text(encoding="utf-8")
    hint = "Numbers spoken exactly: " + ", ".join(sorted(set(dp.numbers_in(dp._strip_urls(art)[0])), key=len, reverse=True)[:60])
    segs, info = wm.transcribe(str(raw), language=language, vad_filter=True, beam_size=5, initial_prompt=hint[:800])
    lines, plain, t0 = [], [], time.time()
    for s in segs:
        lines.append(f"[{s.start:7.1f} -> {s.end:7.1f}] {s.text.strip()}")
        plain.append(s.text.strip())
        if len(lines) % 20 == 0:
            say(f"  {len(lines)} segments, at {s.end:.0f} s of audio")
    f = folder(slug)
    (f / "transcript.txt").write_text("\n".join(plain) + "\n", encoding="utf-8")
    (f / "transcript_timed.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    st.update({"transcript": str(f / "transcript.txt"), "language": info.language,
               "duration_s": round(info.duration, 1), "asr_model": model})
    save(slug, st)
    say(f"transcribed {len(lines)} segments, {info.duration:.0f} s, language {info.language}, "
        f"in {time.time() - t0:.0f} s")
    return 0


# ---------------------------------------------------------------- check

def cmd_check(slug: str) -> int:
    st = state(slug)
    tr = Path(st.get("transcript", ""))
    if not tr.exists():
        raise SystemExit("no transcript; run `transcribe` first")
    corpus, urls = dp.corpus_for(slug, derivatives(slug))
    res = dp.check_text(tr.read_text(encoding="utf-8"), corpus, urls, spoken=True)
    res["transcript_sha256"] = dp.sha(tr)
    (folder(slug) / "check.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    st["check_ok"] = res["ok"]
    save(slug, st)
    if res["ok"]:
        say("check ok: every number in the transcript exists in the article or the verified context")
        if res.get("names_warning"):
            say("  names not found (speech spelling, review by ear): " + ", ".join(res["names_warning"]))
        return 0
    say("check FAILED: numbers not in the article or verified context: " + ", ".join(res["numbers"]))
    say("  regenerate with a narrower --focus, or cut the segment; no clean transcript, no episode")
    return 1


# ---------------------------------------------------------------- master

def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg not on PATH")
    return exe


def cmd_master(slug: str, intro: str | None, outro: str | None, cover: str | None) -> int:
    st = state(slug)
    chk = folder(slug) / "check.json"
    if not chk.exists() or not json.loads(chk.read_text(encoding="utf-8")).get("ok"):
        raise SystemExit("no passing check.json for this transcript; the episode is not mastered")
    tr = Path(st["transcript"])
    if json.loads(chk.read_text(encoding="utf-8")).get("transcript_sha256") != dp.sha(tr):
        raise SystemExit("check.json is for different transcript bytes; run `check` again")
    raw = Path(st["raw"])
    ep = (derivatives(slug) / "episode.md").read_text(encoding="utf-8")
    title = section(ep, "Title") or slug
    out = folder(slug) / "episode.m4a"
    ff = _ffmpeg()
    parts = [p for p in (intro, raw, outro) if p]
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]
    n = len(parts)
    filt = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[cat];" if n > 1 else ""
    src = "[cat]" if n > 1 else "[0:a]"
    filt += f"{src}loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    cmd = [ff, "-y", *inputs, "-filter_complex", filt, "-map", "[out]",
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
           "-metadata", f"title={title}", "-metadata", f"artist={ARTIST}",
           "-metadata", f"album={SHOW}", "-metadata", f"date={date.today().year}",
           "-movflags", "+faststart", str(out)]
    say("mastering with ffmpeg loudnorm -16 LUFS, AAC 128k")
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise SystemExit(p.stderr[-3000:])
    if cover and Path(cover).exists():
        shutil.copy(cover, folder(slug) / "cover.png")
    st.update({"master": str(out), "master_sha256": dp.sha(out), "title": title})
    save(slug, st)
    say(f"mastered {out} ({out.stat().st_size // 1024} KB)")
    return 0


# ---------------------------------------------------------------- package

def cmd_package(slug: str, season: int, number: int | None) -> int:
    st = state(slug)
    if "master" not in st:
        raise SystemExit("no mastered episode; run `master` first")
    meta = article_meta(slug)
    ep = (derivatives(slug) / "episode.md").read_text(encoding="utf-8")
    desc = section(ep, "Description")
    chapters = section(ep, "Chapters")
    cover = folder(slug) / "cover.png"
    lines = [
        f"# Spotify for Creators: {SHOW}",
        "",
        "Fill the form from this file. Check every field, and that the show is "
        f"\"{SHOW}\", before Publish.",
        "",
        "| field | value |",
        "|---|---|",
        f"| audio file | `{st['master']}` (sha256 {st['master_sha256'][:12]}) |",
        f"| title | {st.get('title', slug)} |",
        f"| season | {season} |",
        f"| episode number | {number if number is not None else 'next in the show'} |",
        "| episode type | full |",
        "| explicit | no |",
        f"| publish date | {date.today().isoformat()} or later |",
        f"| cover | {'`' + str(cover) + '`' if cover.exists() else 'MISSING: generate cover.png first'} |",
        "",
        "## Description (paste as is)",
        "",
        desc or "(episode.md has no ## Description yet)",
        "",
        f"Article: {meta['url']}",
        "",
        "## Chapters",
        "",
        chapters or "(none)",
        "",
        "## Receipts",
        "",
        f"- transcript check: `{folder(slug) / 'check.json'}` (ok = {st.get('check_ok')})",
        f"- duration: {st.get('duration_s', '?')} s, language {st.get('language', '?')}",
        f"- NotebookLM notebook {st.get('notebook', '?')}, artifact {st.get('artifact', '?')}, "
        f"format {st.get('audio_format', '?')}",
    ]
    (folder(slug) / "spotify.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"package written: {folder(slug) / 'spotify.md'}")
    if not cover.exists():
        say("cover.png is missing; the package is not complete until it exists")
        return 1
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("research"); r.add_argument("slug"); r.add_argument("--query")
    r.add_argument("--mode", default="deep", choices=["deep", "fast"])
    a = sub.add_parser("audio"); a.add_argument("slug"); a.add_argument("--format", default="deep_dive")
    a.add_argument("--length", default="default"); a.add_argument("--language", default="en-US")
    a.add_argument("--artifact"); a.add_argument("--notebook")
    t = sub.add_parser("transcribe"); t.add_argument("slug")
    t.add_argument("--model", default="large-v3-turbo"); t.add_argument("--language")
    c = sub.add_parser("check"); c.add_argument("slug")
    m = sub.add_parser("master"); m.add_argument("slug"); m.add_argument("--intro"); m.add_argument("--outro")
    m.add_argument("--cover")
    p = sub.add_parser("package"); p.add_argument("slug"); p.add_argument("--season", type=int, default=1)
    p.add_argument("--number", type=int)
    al = sub.add_parser("all"); al.add_argument("slug"); al.add_argument("--format", default="deep_dive")
    al.add_argument("--length", default="default"); al.add_argument("--cover")
    ns = ap.parse_args()
    if ns.cmd == "research":
        return cmd_research(ns.slug, ns.query, ns.mode)
    if ns.cmd == "audio":
        return cmd_audio(ns.slug, ns.format, ns.length, ns.language, ns.artifact, ns.notebook)
    if ns.cmd == "transcribe":
        return cmd_transcribe(ns.slug, ns.model, ns.language)
    if ns.cmd == "check":
        return cmd_check(ns.slug)
    if ns.cmd == "master":
        return cmd_master(ns.slug, ns.intro, ns.outro, ns.cover)
    if ns.cmd == "package":
        return cmd_package(ns.slug, ns.season, ns.number)
    for step in (
        lambda: cmd_audio(ns.slug, ns.format, ns.length, "en-US", None, None),
        lambda: cmd_transcribe(ns.slug, "large-v3-turbo", "en"),
        lambda: cmd_check(ns.slug),
        lambda: cmd_master(ns.slug, None, None, ns.cover),
        lambda: cmd_package(ns.slug, 1, None),
    ):
        rc = step()
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
