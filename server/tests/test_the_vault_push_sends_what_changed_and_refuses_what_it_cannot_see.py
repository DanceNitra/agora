"""`tools/safe_vault_push.py` pushes the owner's edits, follows no links, and still refuses deletions.

WHY THIS FILE EXISTS. safe_vault_push is the only sanctioned way to push the vault — a private
Obsidian repo of ~5,800 notes, ~380 of them with NTFS-illegal `:` in the filename, which a normal
`git add` stages as deletions (that is how 376 real notes were destroyed once). It had no tests.

An adversarial review on 2026-08-14 found three defects, and the first one is the reason a test
module now exists rather than a comment:

  * "changed" was decided by LOCATION — a file counted as modified only under
    `Concepts/Agora Agents/` or if it contained the AutoLinker marker. Every other note the owner
    edited kept its BASE blob, so the push silently omitted his work. The 0-deletion guard is blind
    to it, because a stale blob is not a `D`.
  * symlinks and NTFS junctions were followed, so content outside the vault could be hashed into
    the private repo and force-pushed.
  * `--force-with-lease` carried no value, so a concurrent pusher's success renewed the lease it
    was meant to trip.

Every test below runs against a THROWAWAY repo in tmp_path with its own bare origin. Nothing here
touches C:/Users/Danculus/my-second-brain, and nothing here runs git inside the real vault.

The tests are paired on purpose. It is not enough to prove the new content comparison pushes an
edit; the original guarantee — a file missing from the working tree is KEPT, and a real deletion
ABORTS — has to keep holding, or the fix has traded one silent loss for another.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "safe_vault_push.py"
AGENTS = "04 Resources/Concepts/Agora Agents/2026-08-14"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stderr}"
    return r.stdout


def _load(vault: Path):
    """Fresh import with VAULT pointed at the throwaway repo (it is read at module scope)."""
    os.environ["VAULT"] = str(vault)
    spec = importlib.util.spec_from_file_location("safe_vault_push_under_test", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["safe_vault_push_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """A vault clone with a bare origin, seeded to look like the real one."""
    origin, wt = tmp_path / "origin.git", tmp_path / "vault"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], capture_output=True)
    subprocess.run(["git", "clone", str(origin), str(wt)], capture_output=True)
    _git(wt, "config", "user.email", "t@t.local")
    _git(wt, "config", "user.name", "test")
    for rel, body in [
        ("04 Resources/Concepts/Antifragility.md", "# Antifragility\noriginal owner text\n"),
        (f"{AGENTS}/agent-note.md", "# Agent note\n"),
        ("04 Resources/attachments/diagram.canvas", '{"nodes":[]}\n'),
        ("Daily/2026-08-14.md", "# Daily\n"),
    ]:
        p = wt / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "seed")
    _git(wt, "push", "-u", "origin", "main")
    return wt


def _pushed(vault: Path, rel: str) -> str:
    """The content of `rel` as it now exists on origin/main."""
    return _git(vault, "show", f"origin/main:{rel}")


def _run(vault: Path):
    mod = _load(vault)
    mod.main()
    _git(vault, "fetch", "origin", "main", "-q")
    return mod


# ------------------------------------------------------- the defect this module exists for
def test_an_edit_outside_the_agent_folder_is_actually_pushed(vault: Path):
    """The regression pin. If anyone reverts to deciding 'changed' by folder name or by the
    AutoLinker marker, this note stops being pushed and this test fails."""
    note = vault / "04 Resources/Concepts/Antifragility.md"
    note.write_text("# Antifragility\nEDITED BY THE OWNER\n", encoding="utf-8")
    _run(vault)
    assert "EDITED BY THE OWNER" in _pushed(vault, "04 Resources/Concepts/Antifragility.md"), (
        "the owner's edit to a note outside 'Agora Agents/' was not pushed — the modified set is "
        "location-based again")


def test_a_non_markdown_file_is_pushed_too(vault: Path):
    """The old enumeration was rglob('*.md'), so an edited attachment could never be sent at all."""
    p = vault / "04 Resources/attachments/diagram.canvas"
    p.write_text('{"nodes":[{"id":"a"}]}\n', encoding="utf-8")
    _run(vault)
    assert '"id":"a"' in _pushed(vault, "04 Resources/attachments/diagram.canvas")


def test_an_unchanged_file_keeps_its_base_blob(vault: Path):
    """The other half. A tool that re-hashes everything would pass the two tests above while
    producing a whole-vault diff on every run."""
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nnew line\n", encoding="utf-8")
    mod = _run(vault)
    changed = [ln for ln in _git(vault, "diff", "--name-only", "HEAD~1", "HEAD").splitlines() if ln]
    assert changed == [f"{AGENTS}/agent-note.md"], f"unchanged files were rewritten: {changed}"
    assert mod.hashed == 1, f"expected 1 blob written into the tree, got {mod.hashed}"


# ------------------------------------------------- the original guarantee must not regress
def test_a_file_missing_from_the_working_tree_is_kept_not_deleted(vault: Path):
    """The whole reason this tool exists: the ~380 ':' notes cannot be checked out on NTFS, so they
    are absent from the working tree and must survive every push."""
    missing = vault / "Daily/2026-08-14.md"
    missing.unlink()                                    # stands in for a ':' note git cannot check out
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    _run(vault)
    assert _pushed(vault, "Daily/2026-08-14.md") == "# Daily\n", (
        "a file absent from the working tree was dropped — this is the 376-note failure")


def test_the_deletion_guard_still_aborts(vault: Path, monkeypatch):
    """A deletion reaching the diff must still stop the push. Forced by making the merge drop an
    entry, since an absent file is (correctly) kept and can never produce a D on its own."""
    mod = _load(vault)
    real_merge = mod.merge

    def dropping_merge(base_sha, dir_rel):
        sha = real_merge(base_sha, dir_rel)
        if dir_rel == "":
            entries = mod.ls_tree(sha)
            entries.pop("Daily", None)                  # simulate a lost subtree
            return mod.mktree(entries)
        return sha

    monkeypatch.setattr(mod, "merge", dropping_merge)
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert _git(vault, "rev-parse", "refs/heads/main").strip() == \
        _git(vault, "rev-parse", "origin/main").strip(), "the ref moved despite the abort"


# ----------------------------------------------------------------- links are never followed
@pytest.mark.skipif(os.name == "nt" and not os.environ.get("CI"),
                    reason="creating a symlink on Windows needs Developer Mode or admin")
def test_a_symlinked_directory_is_not_walked_into(vault: Path, tmp_path: Path):
    """A link inside the vault used to be walked as a real subtree, so everything behind it was
    hashed into the private repo and force-pushed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("must never reach the vault repo\n", encoding="utf-8")
    try:
        (vault / "04 Resources/linked").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted in this environment")
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    _run(vault)
    tree = _git(vault, "ls-tree", "-r", "--name-only", "origin/main")
    assert "linked" not in tree, f"content behind a symlink was committed:\n{tree}"


@pytest.mark.skipif(os.name != "nt", reason="NTFS junctions are a Windows construct")
def test_an_ntfs_junction_is_not_walked_into(vault: Path, tmp_path: Path):
    """The case that actually matters on this box, and the one the symlink test above cannot cover
    here: `mklink /J` needs no Developer Mode and no admin, so a junction into a shared folder is
    the realistic way outside content ends up inside an Obsidian vault. It is also the harder case
    — a junction keeps S_IFDIR in its lstat mode, so `is_symlink()` alone does not catch it and
    `rglob` DOES descend into it, unlike a symlink."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("must never reach the vault repo\n", encoding="utf-8")
    link = vault / "04 Resources" / "linked"
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"could not create a junction: {r.stdout}{r.stderr}")
    assert (link / "secret.md").exists(), "the junction fixture did not take — nothing was tested"

    mod = _load(vault)
    assert mod.is_link(link) is True, "a junction was not recognised as a link"
    assert not any(r_.startswith("04 Resources/linked") for r_ in mod.walk_worktree()), \
        "the walk descended into a junction"

    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    _run(vault)
    tree = _git(vault, "ls-tree", "-r", "--name-only", "origin/main")
    assert "linked" not in tree, f"content behind a junction was committed:\n{tree}"


def test_a_windows_materialised_symlink_is_never_rewritten(vault: Path):
    """The real vault holds 671 mode-120000 entries, and this Windows checkout has materialised
    every one of them as a plain text file containing the target path. 10 of the first 400 differ
    from their blob by a trailing newline alone, so a naive content comparison "updates" them and
    the symlink target becomes "…/Note.md\\n" — broken on every Linux checkout.

    This defect did not exist before the content comparison. It is one the fix introduced, and only
    a dry run against the real vault surfaced it, so it gets a pin of its own.
    """
    mod = _load(vault)
    # A symlink entry written straight into the tree via plumbing (no symlink support needed).
    blob = mod.git("hash-object", "-w", "--stdin", _input="target/Note.md").strip()
    entries = mod.ls_tree(_git(vault, "rev-parse", "origin/main^{tree}").strip())
    entries["link.md"] = ("120000", "blob", blob)
    tree = mod.mktree(entries)
    commit = _git(vault, "commit-tree", tree, "-p",
                  _git(vault, "rev-parse", "origin/main").strip(), "-m", "add symlink entry").strip()
    _git(vault, "update-ref", "refs/heads/main", commit)
    _git(vault, "push", "-f", "origin", "main")
    _git(vault, "fetch", "origin", "main", "-q")

    # Windows materialises it as a regular file — with a trailing newline the blob does not have.
    (vault / "link.md").write_text("target/Note.md\n", encoding="utf-8")
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    _run(vault)

    raw = _git(vault, "ls-tree", "origin/main", "link.md")
    assert raw.startswith("120000"), f"the symlink entry lost its mode: {raw.strip()}"
    assert _git(vault, "show", "origin/main:link.md") == "target/Note.md", (
        "a Windows-materialised symlink was rewritten with a trailing newline — the target is now "
        "broken on any Linux checkout")


def test_the_walk_skips_links_without_following_them(vault: Path, tmp_path: Path):
    """`is_link` is the load-bearing predicate; pin it directly so the test still measures something
    on a host where creating a symlink is not permitted."""
    mod = _load(vault)
    assert mod.is_link(vault / "04 Resources/Concepts/Antifragility.md") is False
    rels = mod.walk_worktree()
    assert "04 Resources/Concepts/Antifragility.md" in rels
    assert not any(r.startswith(".git/") for r in rels), "the walk descended into .git"


# --------------------------------------------------------- concurrency and local-branch safety
def test_a_local_main_ahead_of_origin_is_a_refusal(vault: Path):
    """update-ref would move main onto a commit parented on origin/main, dropping the local ones.
    It must refuse rather than reset."""
    (vault / "Daily/extra.md").write_text("local work\n", encoding="utf-8")
    _git(vault, "add", "-A")
    _git(vault, "commit", "-m", "unpushed local commit")
    mod = _load(vault)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "extra.md" in _git(vault, "show", "--name-only", "HEAD"), "the local commit was lost"


def test_the_push_lease_names_the_base_it_was_built_on(vault: Path, monkeypatch):
    """A valueless --force-with-lease reads the tracking ref at push time, which a concurrent
    pusher has already advanced. Pin that the lease carries the base sha."""
    mod = _load(vault)
    seen: list[list[str]] = []
    real_run = mod.subprocess.run

    def spy(cmd, *a, **k):
        if isinstance(cmd, list) and "push" in cmd:
            seen.append(cmd)
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(mod.subprocess, "run", spy)
    (vault / f"{AGENTS}/agent-note.md").write_text("# Agent note\nedit\n", encoding="utf-8")
    mod.main()
    assert seen, "no push was issued"
    lease = [a for a in seen[-1] if a.startswith("--force-with-lease")]
    assert lease and lease[0] != "--force-with-lease", "the lease carries no value"
    assert lease[0].startswith("--force-with-lease=main:"), f"unexpected lease form: {lease[0]}"
    assert len(lease[0].split(":")[1]) == 40, "the lease value is not a full sha"
