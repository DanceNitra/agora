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
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(os.environ.get("VAULT", "C:/Users/Danculus/my-second-brain"))
BASE_REF = os.environ.get("BASE_REF", "origin/main")
MARK = "## Related (AutoLinker)"


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


def hash_file(relpath: str) -> str:
    return git("hash-object", "-w", "--", relpath).strip()


def build_modified_set() -> set[str]:
    """Files we intend to push: anything with the AutoLinker section + agent outputs."""
    mod: set[str] = set()
    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT).as_posix()
        if "Concepts/Agora Agents/" in rel:
            mod.add(rel)
            continue
        try:
            if MARK in p.read_text(encoding="utf-8", errors="replace"):
                mod.add(rel)
        except Exception:
            pass
    return mod


MODIFIED: set[str] = set()
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
        if full.is_dir():
            sub = base.get(name)
            sub_sha = sub[2] if (sub and sub[1] == "tree") else None
            result[name] = ("040000", "tree", merge(sub_sha, rel))
        elif full.is_file():
            # AutoLinker pending/report files are regenerated every cycle (working artifacts) and
            # caused 600+/600- line churn commits — never push their changes (keep base, skip new).
            if name.startswith(("autolinker_pending_", "autolinker_report_")):
                continue
            if rel in MODIFIED or name not in base:
                blob = hash_file(rel)
                if blob:
                    result[name] = ("100644", "blob", blob)
                    hashed += 1
            # else: unchanged → keep base entry already in result
    return mktree(result)


def main() -> None:
    global MODIFIED
    base = git("rev-parse", BASE_REF).strip()
    print(f"base {BASE_REF} = {base[:10]}")
    MODIFIED = build_modified_set()
    print(f"files to push (modified/new): {len(MODIFIED)}")

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
    git("update-ref", "refs/heads/main", commit)
    out = subprocess.run(["git", "-C", str(VAULT), "push", "--force-with-lease",
                          "origin", "main"], capture_output=True, text=True)
    print(out.stdout + out.stderr)


if __name__ == "__main__":
    main()
