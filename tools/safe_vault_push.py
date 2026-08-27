#!/usr/bin/env python3
"""
safe_vault_push — push working-tree changes to a vault repo WITHOUT losing files
that Windows can't check out (e.g. names containing ':').

Those files can never live in a git index on Windows, so any `git add`/`reset`
based push silently drops them. This tool instead builds the new commit tree by
RECURSIVELY MERGING the working tree over the remote base tree via pure plumbing
(ls-tree / hash-object / mktree / commit-tree) — for every path:
  * file present in the working tree AND changed  -> working-tree blob
  * file missing from the working tree (the ':' ones) -> kept from base
  * unchanged file                                -> kept from base (no re-hash)

It verifies the resulting diff is additions/modifications only (zero deletions)
before updating the ref, then force-pushes.

THREE DEFECTS FIXED 2026-08-14, all found by an adversarial review of this file. The three lines
above were the SPEC; they were not what the code did.

 1. "changed" was decided by LOCATION, not content: a file counted as modified only if it sat under
    `Concepts/Agora Agents/` or contained the AutoLinker marker. Every other note the owner had
    edited was `name in base` and kept its BASE blob, so the commit carried the pre-edit content and
    the push silently omitted his work. The 0-deletion guard cannot see this — a stale blob is not a
    `D`. The enumeration was also `rglob("*.md")`, so attachments, .canvas files, PDFs and images
    were never eligible at all. Now every working-tree file is hashed and compared to the base blob,
    in ONE batched `hash-object` call, which is both correct and faster than a per-file subprocess.
 2. Symlinks and NTFS junctions were FOLLOWED. `Path.is_dir()`/`is_file()` resolve links, and
    nothing tested for one, so a directory link inside the vault was walked as a real subtree and
    everything behind it was hashed into the private repo and force-pushed. The asymmetry hid it:
    `rglob` does not descend into symlinked directories, so the linked content never appeared in the
    "files to push" count the operator reads. Links are now skipped, and the base entry is preserved
    rather than replaced.
 3. `--force-with-lease` carried NO VALUE, so the lease was taken from `refs/remotes/origin/main`
    as it stood AT PUSH TIME rather than from the `base` this tree was built on. A concurrent
    pusher's success renews the lease it was supposed to trip, so the second push force-overwrites
    the first one's commit. The lease is now pinned to `base`, `update-ref` is compare-and-swap, and
    a local `main` carrying commits that `origin/main` does not is a refusal rather than a silent
    reset.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(os.environ.get("VAULT", "C:/Users/Danculus/my-second-brain"))
BASE_REF = os.environ.get("BASE_REF", "origin/main")
# (The AutoLinker marker constant that used to live here is gone with build_modified_set. It was
#  half of the location heuristic that decided "changed" without looking at content.)


def git(*args: str, _input: str | None = None) -> str:
    r = subprocess.run(["git", "-C", str(VAULT), "-c", "core.quotepath=false", *args],
                       input=_input, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def ls_tree(tree_sha: str) -> dict[str, tuple[str, str, str]]:
    out = git("ls-tree", "-z", tree_sha)
    entries: dict[str, tuple[str, str, str]] = {}
    for rec in out.split("\0"):
        if not rec:
            continue
        meta, name = rec.split("\t", 1)
        mode, typ, sha = meta.split(" ")
        entries[name] = (mode, typ, sha)
    return entries


def mktree(entries: dict[str, tuple[str, str, str]]) -> str:
    lines = [f"{mode} {typ} {sha}\t{name}" for name, (mode, typ, sha) in entries.items()]
    return git("mktree", "-z", _input="\0".join(lines) + ("\0" if lines else "")).strip()


_isjunction = getattr(os.path, "isjunction", lambda _p: False)


def is_link(p: Path) -> bool:
    """A symlink or an NTFS junction. Neither may be followed.

    `is_symlink()` alone is not enough on Windows: a junction keeps S_IFDIR in its lstat mode, so
    it reads as an ordinary directory and gets walked. os.path.isjunction exists from 3.12; the
    getattr keeps this working on older interpreters rather than crashing the vault push.
    """
    try:
        return p.is_symlink() or _isjunction(p)
    except OSError:
        return True          # cannot classify it -> do not walk into it


def walk_worktree() -> list[str]:
    """Every regular file under VAULT, relative posix, links never followed.

    Deliberately not `rglob("*.md")`: the old modified-set was markdown-only, which is why an
    edited attachment or .canvas file could never be pushed at all.
    """
    out: list[str] = []
    root = VAULT.resolve()

    def rec(d: Path, rel: str) -> None:
        try:
            names = os.listdir(d)
        except OSError:
            return
        for name in names:
            if name == ".git":
                continue
            full = d / name
            r = f"{rel}/{name}" if rel else name
            if is_link(full):
                continue
            try:
                if full.is_dir():
                    # Containment: a link we failed to classify must still not take us outside.
                    if full.resolve().is_relative_to(root):
                        rec(full, r)
                elif full.is_file():
                    out.append(r)
            except OSError:
                continue

    rec(VAULT, "")
    return out


def hash_many(rels: list[str]) -> dict[str, str]:
    """rel -> blob sha for every path, in ONE `git hash-object` call.

    `-w` writes the objects, which is a no-op for content already in the store, so the changed
    files end up present without a second pass. One subprocess instead of ~6000: a per-file spawn
    on Windows would turn this into minutes and is what made a content comparison look expensive
    enough to replace with a folder-name heuristic in the first place.
    """
    if not rels:
        return {}
    out = git("hash-object", "-w", "--stdin-paths", _input="\n".join(rels) + "\n")
    shas = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(shas) != len(rels):
        raise RuntimeError(f"hash-object returned {len(shas)} shas for {len(rels)} paths")
    return dict(zip(rels, shas))


WT_HASH: dict[str, str] = {}
hashed = 0


def merge(base_tree_sha: str | None, dir_rel: str) -> str:
    """Return the merged tree sha for directory `dir_rel`."""
    global hashed
    base = ls_tree(base_tree_sha) if base_tree_sha else {}
    result = dict(base)                      # start from base → preserves missing files
    wt_path = VAULT / dir_rel if dir_rel else VAULT
    try:
        names = os.listdir(wt_path)
    except Exception:
        names = []
    for name in names:
        if name == ".git":
            continue
        full = wt_path / name
        rel = f"{dir_rel}/{name}" if dir_rel else name
        # A link is never followed and never replaces the base entry: skipping leaves whatever the
        # base tree held at this name, which is the conservative outcome in both directions.
        if is_link(full):
            continue
        if full.is_dir():
            sub = base.get(name)
            sub_sha = sub[2] if (sub and sub[1] == "tree") else None
            result[name] = ("040000", "tree", merge(sub_sha, rel))
        elif full.is_file():
            # AutoLinker pending/report files are regenerated every cycle (working artifacts) and
            # caused 600+/600- line churn commits — never push their changes (keep base, skip new).
            if name.startswith(("autolinker_pending_", "autolinker_report_")):
                continue
            cur = WT_HASH.get(rel)
            if cur is None:
                continue                       # not enumerated / unreadable -> keep base entry
            prev = base.get(name)
            # A git symlink (mode 120000) that this Windows checkout materialised as a plain text
            # file containing the target path. Measured on the real vault 2026-08-14: all 671
            # symlink entries are regular files here, and 10 of the first 400 differ from their
            # blob by a trailing newline alone -- so a content comparison would "update" them and
            # the symlink target would become "…/Note.md\n", broken on every Linux checkout. This
            # defect did not exist before the content comparison; it is one the fix introduced, and
            # the read-only dry run against the real vault is the only reason it was caught.
            if prev is not None and prev[0] == "120000" and not full.is_symlink():
                continue
            if prev is not None and prev[1] == "blob" and prev[2] == cur:
                continue                       # genuinely unchanged -> keep base entry, no churn
            # Preserve the base entry's mode. Hardcoding 100644 rewrote a symlink entry (120000)
            # as a regular file, and would drop the executable bit on anything that carried one.
            mode = prev[0] if (prev is not None and prev[1] == "blob") else "100644"
            result[name] = (mode, "blob", cur)
            hashed += 1
    return mktree(result)


def local_main() -> str | None:
    """refs/heads/main, or None when it does not exist."""
    r = subprocess.run(["git", "-C", str(VAULT), "rev-parse", "--verify", "-q", "refs/heads/main"],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() or None


def is_ancestor(a: str, b: str) -> bool:
    return subprocess.run(["git", "-C", str(VAULT), "merge-base", "--is-ancestor", a, b],
                          capture_output=True).returncode == 0


def main() -> None:
    global WT_HASH
    base = git("rev-parse", BASE_REF).strip()
    print(f"base {BASE_REF} = {base[:10]}")

    # Refuse rather than silently reset. The commit below is parented on `base`, and update-ref
    # then moves refs/heads/main onto it -- so any local commit that origin/main does not already
    # contain would be dropped from the branch (reflog-only). That is exactly the class of quiet
    # loss this tool exists to prevent, so it aborts instead of being clever about it.
    head = local_main()
    if head and head != base and not is_ancestor(head, base):
        print(f"ABORT — local refs/heads/main ({head[:10]}) carries commits that {BASE_REF} "
              f"({base[:10]}) does not.")
        print("  Pushing would drop them from the branch. Push or rebase them first, then re-run.")
        sys.exit(1)

    files = walk_worktree()
    WT_HASH = hash_many(files)
    print(f"working tree: {len(files)} file(s) hashed and compared against base")

    base_root = git("rev-parse", f"{base}^{{tree}}").strip()
    new_root = merge(base_root, "")
    print(f"new root tree = {new_root[:10]} (hashed {hashed} blobs)")

    msg = sys.argv[1] if len(sys.argv) > 1 else "vault update (safe push)"
    commit = subprocess.run(
        ["git", "-C", str(VAULT), "-c", "user.name=Agora Agents",
         "-c", "user.email=agents@agora.local", "commit-tree", new_root, "-p", base],
        input=msg, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    # Verify: additions/modifications only, ZERO deletions
    stat = git("diff", "--name-status", base, commit)
    dels = [ln for ln in stat.splitlines() if ln.startswith("D")]
    adds = [ln for ln in stat.splitlines() if ln.startswith("A")]
    mods = [ln for ln in stat.splitlines() if ln.startswith("M")]
    print(f"diff vs base: {len(adds)} A, {len(mods)} M, {len(dels)} D")
    if not adds and not mods and not dels:
        print("no real changes — nothing to push")
        return
    if dels:
        print("ABORT — deletions present:")
        for d in dels[:10]:
            print("  ", d)
        sys.exit(1)

    print(f"commit {commit[:10]} OK — updating ref + pushing")
    # Compare-and-swap: if another pusher moved local main since we read it, this fails instead of
    # overwriting. (git takes the expected old value as the third argument.)
    if head:
        git("update-ref", "refs/heads/main", commit, head)
    else:
        git("update-ref", "refs/heads/main", commit)
    # The lease is pinned to the base this tree was built on. A valueless --force-with-lease reads
    # refs/remotes/origin/main AT PUSH TIME, which a concurrent pusher's own success has already
    # advanced -- so the lease it was meant to trip has been renewed by the very event it guards
    # against, and the second push discards the first one's commit.
    out = subprocess.run(["git", "-C", str(VAULT), "push",
                          f"--force-with-lease=main:{base}", "origin", "main"],
                         capture_output=True, text=True)
    print(out.stdout + out.stderr)
    if out.returncode != 0:
        print("PUSH FAILED — the ref moved under us (that is the lease doing its job) or the "
              "remote refused. Nothing was lost; re-run to rebuild against the new base.")
        sys.exit(1)


if __name__ == "__main__":
    main()
