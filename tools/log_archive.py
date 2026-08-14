"""Compress rolled logs and, optionally, back them up to GitHub — without breaking GitHub's rules.

    python tools/log_archive.py                      # compress rolled segments, report, stop
    python tools/log_archive.py --upload owner/repo  # ...then upload as Release assets
    python tools/log_archive.py --prune-days 90      # drop local archives older than N days

WHAT GITHUB ACTUALLY ALLOWS, and why this uses Releases rather than commits:

  * a file over 100 MB is REJECTED by a push outright, and over 50 MB warns;
  * a repository is expected to stay near 1 GB and 5 GB is the practical ceiling;
  * git history is FOREVER. A compressed log committed once is in every clone of the repo for the
    rest of its life, and removing it later means rewriting history for everyone. Our two rolled
    logs are 2.4 GB raw today. Committing them, even compressed, would be an irreversible way to
    ruin the repo — so this tool NEVER stages a log, and refuses to be pointed at git.
  * a RELEASE ASSET is stored outside the git object store: it does not enter history, `git clone`
    never downloads it, and the per-file ceiling is 2 GB. That is the mechanism that fits.

THE DECISION THIS TOOL REFUSES TO MAKE FOR YOU. `DanceNitra/agora` is PUBLIC. Measured 2026-08-14,
these logs contain no token, key or bearer credential (a scan for the literal values of all 17
`.env` entries and for token-shaped patterns found nothing) — but they DO quote research findings
and vault-derived note text, and CLAUDE.md rule 1 makes the vault private. So an upload target is
checked with `gh repo view --json visibility` and a PUBLIC one is refused. Pass an explicit private
repo, or accept that publishing operational logs of a private vault is a disclosure decision that
belongs to the owner, not to a cron job.

The secret scan runs on every upload regardless, and refuses on a hit. It checks the LITERAL values
in the .env files rather than only token-shaped regexes, because the regex for "our token" is "our
token" — a pattern-only scan cannot know what our secrets look like.

Only ROLLED segments are touched (`*.1`, `*.gz`). A live log is never renamed or truncated: the
writers hold positional handles, so rotation belongs to the launcher, before the process opens the
file. See tools/logroll.py.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "agora_output" / "log_archive"
# Rolled segments the launchers produce. Live logs are deliberately absent from this list.
ROLLED = ["server/_brain.log.1", "server/_brain.err.1",
          "agora-game-server/_dungeon.log.1", "agora-game-server/_dungeon.err.1"]
# Well under the 2 GB asset ceiling, and small enough that a failed upload is cheap to retry.
PART_BYTES = 1024 * 1024 * 1024
_SECRET_SEGMENTS = {"TOKEN", "KEY", "APIKEY", "SECRET", "PASSWORD", "PASS", "PAT", "CREDENTIAL",
                    "CREDENTIALS", "AUTH"}
_TOKENISH = (re.compile(r"\b\d{9,11}:[A-Za-z0-9_-]{30,}"),        # telegram bot token
             re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),          # github pat
             re.compile(r"\bsk-[A-Za-z0-9]{20,}"),                 # openai-style key
             re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"))


def env_secrets() -> list[str]:
    """Literal values from the gitignored .env files. Never printed, only searched for."""
    out = []
    for rel in ("server/.env", "agora-game-server/.env"):
        p = ROOT / rel
        if not p.exists():
            continue
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                v = v.strip().strip('"').strip("'")
                # Only genuinely secret-shaped keys: a model name or a vault path is config, and
                # treating it as a secret makes the scan cry wolf until nobody reads it.
                #
                # Matched on key SEGMENTS, not substrings. A substring test flags AGORA_VAULT_PATH,
                # because "_PATH" contains "_PAT" — the same false positive an ad-hoc scan produced
                # an hour before this file was written, and which was written into it anyway. The
                # test is what caught it the second time.
                if len(v) >= 16 and (_SECRET_SEGMENTS & set(k.upper().strip().split("_"))):
                    out.append(v)
    return out


def scan_secrets(path: Path) -> list[str]:
    """-> human-readable reasons the file must not leave the machine. Empty means clean."""
    secrets, hits = env_secrets(), []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            s = chunk.decode("utf-8", "replace")
            for v in secrets:
                if v in s:
                    hits.append("a literal value from a .env TOKEN/KEY entry")
            for rx in _TOKENISH:
                if rx.search(s):
                    hits.append(f"a credential-shaped string matching {rx.pattern[:28]}…")
    return sorted(set(hits))


def compress(src: Path) -> Path:
    """gzip src -> ARCHIVE/<name>.<utc>.gz, then remove src. Returns the archive path."""
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    dst = ARCHIVE / f"{src.name}.{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.gz"
    tmp = dst.with_suffix(dst.suffix + ".part")
    with open(src, "rb") as fi, gzip.open(tmp, "wb", compresslevel=6) as fo:
        shutil.copyfileobj(fi, fo, length=8 * 1024 * 1024)
    tmp.replace(dst)                       # only becomes an archive once it is complete
    src.unlink()
    return dst


def split_if_needed(p: Path) -> list[Path]:
    """Split into <=PART_BYTES pieces so no asset can approach GitHub's 2 GB ceiling."""
    if p.stat().st_size <= PART_BYTES:
        return [p]
    parts, i = [], 0
    with open(p, "rb") as fh:
        while True:
            blob = fh.read(PART_BYTES)
            if not blob:
                break
            i += 1
            q = p.with_name(f"{p.name}.part{i:02d}")
            q.write_bytes(blob)
            parts.append(q)
    p.unlink()
    print(f"  split into {len(parts)} part(s) — reassemble with `cat *.part* > {p.name}`")
    return parts


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=900)


def repo_is_private(repo: str) -> bool | None:
    r = _gh("repo", "view", repo, "--json", "visibility")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout).get("visibility", "").upper() == "PRIVATE"
    except Exception:
        return None


def upload(repo: str, files: list[Path]) -> int:
    tag = "logs-" + time.strftime("%Y-%m", time.gmtime())
    priv = repo_is_private(repo)
    if priv is None:
        print(f"REFUSED: cannot read {repo}'s visibility. A destination we cannot classify is not "
              f"a destination we have cleared.")
        return 2
    if not priv:
        print(f"REFUSED: {repo} is PUBLIC. These logs quote research findings and vault-derived "
              f"note text, and CLAUDE.md rule 1 makes the vault private. Publishing them is a "
              f"disclosure decision for the owner, not for this tool. Point --upload at a private "
              f"repo.")
        return 2
    for f in files:
        reasons = scan_secrets(f)
        if reasons:
            print(f"REFUSED: {f.name} contains " + "; ".join(reasons) + ". Nothing uploaded.")
            return 2
    if _gh("release", "view", tag, "--repo", repo).returncode != 0:
        r = _gh("release", "create", tag, "--repo", repo, "--title", f"Logs {tag[5:]}",
                "--notes", "Compressed operational logs. Release assets stay out of git history.")
        if r.returncode != 0:
            print("REFUSED: could not create the release: " + (r.stderr or r.stdout)[:300])
            return 2
    sent = 0
    for f in files:
        r = _gh("release", "upload", tag, str(f), "--repo", repo, "--clobber")
        if r.returncode != 0:
            print(f"  FAILED {f.name}: " + (r.stderr or r.stdout)[:200])
            continue
        # Verify by reading the asset back, not by trusting the exit code — `gh` has reported
        # success for a publish that did not land before (see public_repo.commit_and_push).
        v = _gh("release", "view", tag, "--repo", repo, "--json", "assets")
        ok = False
        try:
            for a in json.loads(v.stdout).get("assets", []):
                if a.get("name") == f.name and int(a.get("size", 0)) == f.stat().st_size:
                    ok = True
        except Exception:
            ok = False
        if not ok:
            print(f"  FAILED {f.name}: uploaded, but the asset does not read back at the right "
                  f"size — keeping the local copy.")
            continue
        print(f"  uploaded + verified {f.name} ({f.stat().st_size / 1048576:.1f} MB)")
        f.unlink()
        sent += 1
    print(f"{sent}/{len(files)} archive(s) backed up to {repo} release {tag}, local copies removed")
    return 0 if sent == len(files) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--upload", metavar="OWNER/REPO", help="private repo to back the archives up to")
    ap.add_argument("--prune-days", type=int, default=0,
                    help="delete local archives older than N days (only after a successful upload "
                         "would have removed them anyway)")
    a = ap.parse_args(argv)

    made = []
    for rel in ROLLED:
        p = ROOT / rel
        if not p.exists() or p.stat().st_size == 0:
            continue
        before = p.stat().st_size
        gz = compress(p)
        after = gz.stat().st_size
        print(f"compressed {rel}: {before / 1048576:.1f} MB -> {after / 1048576:.1f} MB "
              f"({before / max(after, 1):.1f}x)  -> {gz.relative_to(ROOT)}")
        made.extend(split_if_needed(gz))
    if not made:
        print("nothing rolled to archive (this is the normal state between rotations)")

    pending = sorted(ARCHIVE.glob("*.gz*")) if ARCHIVE.exists() else []
    total = sum(p.stat().st_size for p in pending)
    print(f"local archive: {len(pending)} file(s), {total / 1048576:.1f} MB in "
          f"{ARCHIVE.relative_to(ROOT)}")

    rc = 0
    if a.upload:
        rc = upload(a.upload, pending)
    elif pending:
        print("NOT uploaded — pass --upload <private-owner/repo>. These are never committed to git: "
              "history is permanent and a log in it cannot be taken back out.")

    if a.prune_days > 0:
        cutoff = time.time() - a.prune_days * 86400
        for p in list(ARCHIVE.glob("*.gz*")) if ARCHIVE.exists() else []:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                print(f"pruned {p.name} (older than {a.prune_days} days)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
