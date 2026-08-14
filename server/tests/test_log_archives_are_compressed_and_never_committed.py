"""Logs are rolled, compressed, kept out of git, and refused an outward destination we cannot clear.

WHY. `_dungeon.err` had reached 1,022 MB and `server/_brain.log.1` 1,384 MB — 2.4 GB — because the
brain's launcher rolled its logs at 25 MB since 2026-08-06 and the dungeon's launcher never did. A
rotation policy present in one of two launchers is a rotation policy for one of two logs.

The backup destination is the part worth testing hardest, because getting it wrong is irreversible
in two different ways:

  * COMMITTING a log is forever. Git history cannot be trimmed without rewriting every clone, and
    GitHub rejects any file over 100 MB outright. So archives live under a gitignored directory and
    travel as RELEASE ASSETS, which are stored outside the object store (2 GB per asset, absent
    from `git clone`).
  * PUBLISHING a log is forever too. `DanceNitra/agora` is PUBLIC, and these logs quote research
    findings and vault-derived note text while CLAUDE.md rule 1 makes the vault private. A scan on
    2026-08-14 found no token, key or bearer credential in them — but "no credential" is not "safe
    to publish", and that judgement is the owner's.

So the tests below are mostly about REFUSALS, and each is paired with the case that must still work.
"""
from __future__ import annotations

import gzip
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("log_archive_under_test", ROOT / "tools/log_archive.py")
la = importlib.util.module_from_spec(spec)
sys.modules["log_archive_under_test"] = la
spec.loader.exec_module(la)


# ------------------------------------------------------------------------ never touch a live log
def test_only_rolled_segments_are_listed():
    """A live log is held open by its writer with a POSITIONAL handle: renaming fails and
    truncating corrupts. Rotation belongs to the launcher, before the process opens the file."""
    assert all(name.endswith(".1") for name in la.ROLLED), f"a live log is in ROLLED: {la.ROLLED}"
    for live in ("server/_brain.log", "agora-game-server/_dungeon.err"):
        assert live not in la.ROLLED


def test_the_archive_directory_is_gitignored():
    """The tool's whole premise. Asked of git, not asserted."""
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "agora_output/log_archive/"],
                       capture_output=True)
    assert r.returncode == 0, "agora_output/log_archive/ is committable — a log could enter history"


# ------------------------------------------------------------------------------ compression works
def test_compression_round_trips_and_removes_the_source(tmp_path, monkeypatch):
    monkeypatch.setattr(la, "ARCHIVE", tmp_path / "arch")
    src = tmp_path / "_brain.log.1"
    payload = b"a log line that repeats\n" * 5000
    src.write_bytes(payload)
    gz = la.compress(src)
    assert not src.exists(), "the source segment was left behind, so nothing was reclaimed"
    assert gzip.open(gz, "rb").read() == payload, "the archive does not round-trip"
    assert gz.stat().st_size < len(payload) / 5, "no meaningful compression"
    assert not list((tmp_path / "arch").glob("*.part")), "a partial archive was left as an archive"


def test_a_large_archive_is_split_below_the_asset_ceiling(tmp_path, monkeypatch):
    monkeypatch.setattr(la, "PART_BYTES", 1024)
    p = tmp_path / "big.gz"
    p.write_bytes(b"x" * 3000)
    parts = la.split_if_needed(p)
    assert len(parts) == 3 and not p.exists()
    assert b"".join(q.read_bytes() for q in parts) == b"x" * 3000, "the parts do not reassemble"


def test_a_small_archive_is_not_split(tmp_path):
    p = tmp_path / "small.gz"
    p.write_bytes(b"x" * 10)
    assert la.split_if_needed(p) == [p]


# --------------------------------------------------------------------------------- the refusals
def test_a_public_destination_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(la, "repo_is_private", lambda _r: False)
    assert la.upload("DanceNitra/agora", [tmp_path / "x.gz"]) == 2
    assert "PUBLIC" in capsys.readouterr().out


def test_an_unreadable_destination_is_refused(tmp_path, monkeypatch, capsys):
    """Not "assume private and proceed": a destination we cannot classify is not one we cleared."""
    monkeypatch.setattr(la, "repo_is_private", lambda _r: None)
    assert la.upload("who/knows", [tmp_path / "x.gz"]) == 2
    assert "cannot read" in capsys.readouterr().out


def test_a_secret_in_the_archive_refuses_the_whole_upload(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(la, "repo_is_private", lambda _r: True)
    f = tmp_path / "log.gz"
    with gzip.open(f, "wb") as fh:
        fh.write(b"INFO starting\nAuthorization: Bearer abcdefghijklmnopqrstuvwxyz012345\n")
    assert la.upload("owner/private", [f]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "Nothing uploaded" in out
    assert f.exists(), "the archive was deleted despite the refusal"


def test_a_clean_archive_passes_the_scan(tmp_path):
    """The other half — a scanner that flags everything protects nothing, because it gets ignored."""
    f = tmp_path / "clean.gz"
    with gzip.open(f, "wb") as fh:
        fh.write(b"INFO [plan] Sage Mira: 3 grounded quest(s)\nINFO tick 41\n")
    assert la.scan_secrets(f) == []


def test_the_secret_list_ignores_ordinary_config(tmp_path, monkeypatch):
    """A model name and a vault path are config, not credentials. Treating them as secrets makes the
    scan cry wolf until nobody reads it — and both appear in these logs constantly."""
    monkeypatch.setattr(la, "ROOT", tmp_path)
    (tmp_path / "server").mkdir()
    (tmp_path / "server/.env").write_text(
        'AGORA_LLM_MODEL=deepseek-v4-flash:0731-cloud\n'
        'AGORA_VAULT_PATH=C:/Users/Danculus/my-second-brain\n'
        'HERMES_TELEGRAM_BOT_TOKEN=1234567890:AAquiteLongEnoughToCountAsASecret\n',
        encoding="utf-8")
    vals = la.env_secrets()
    assert vals == ["1234567890:AAquiteLongEnoughToCountAsASecret"], vals
