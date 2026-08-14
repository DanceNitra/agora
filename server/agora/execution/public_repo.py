"""The one way a publisher commits to the public repo — scoped, branch-checked, and proven.

WHY THIS FILE EXISTS. `press.publish_piece`, `portfolio.publish` and
`research_exchange.publish_digest` each carried the same three lines:

    _git("add", <one path>)
    _git("commit", "-m", <msg>)          # NO pathspec
    _git("push", "origin", "main")

and each docstring said "commit ONLY that file". None of them did. Three defects, all confirmed
2026-08-14:

 1. `git commit -m <msg>` with no pathspec commits the ENTIRE staged index. Anything another
    process left staged — an operator's `git add`, a half-finished commit — rides out under the
    owner's approval of a track-record update. The approval authorises an ACTION, never a DIFF.
 2. The push is branch-blind. `git commit` lands on the CURRENT HEAD; this repo sits on
    `integration/dungeon-alpha-omega`, while `push origin main` sends a `main` that does not
    contain the commit. Measured: `.git/HEAD` is on the integration branch and `[branch "main"]`
    in `.git/config` has no remote/merge, so this is the ordinary state, not an edge case.
 3. The only check was `if p.returncode != 0`. `git push` exits 0 on "Everything up-to-date", which
    is exactly what (2) produces — so the record was marked `published`, a public URL was returned
    and reported to the owner, for a file that never left the machine.

So this helper refuses rather than guesses: wrong branch is an error, the commit is pathspec-scoped,
and the push is not believed until the remote ref is observed holding our commit.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def current_branch(repo: Path) -> str | None:
    r = _git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    return r.stdout.strip() or None


def commit_and_push(repo: Path, paths: list[str], message: str, branch: str = "main") -> dict:
    """Commit EXACTLY `paths` and prove the commit reached `origin/<branch>`.

    Returns {"sha": ...} on success, {"error": ...} otherwise, and {"note": "..."} when there was
    genuinely nothing to commit. Never returns success for a commit that did not land.
    """
    paths = [p for p in paths if p]
    if not paths:
        return {"error": "no paths given — refusing to commit an unspecified set"}

    here = current_branch(repo)
    if here != branch:
        return {"error": (f"on branch '{here}', but publishing targets '{branch}'. The commit "
                          f"would land on '{here}' while the push sends '{branch}' — which is how "
                          f"a publish reports success for a file that never left. Switch to "
                          f"'{branch}' and re-run.")}

    a = _git(repo, "add", "--", *paths)
    if a.returncode != 0:
        return {"error": ("git add failed: " + (a.stderr or a.stdout))[:300]}

    # `--` scopes the commit to these paths: whatever else is staged stays staged.
    c = _git(repo, "commit", "-m", message, "--", *paths)
    if c.returncode != 0:
        blob = (c.stdout or "") + (c.stderr or "")
        if "nothing to commit" in blob or "no changes added" in blob:
            return {"note": "nothing to commit (identical content already published)"}
        return {"error": ("git commit failed: " + blob)[:300]}

    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    p = _git(repo, "push", "origin", branch)
    if p.returncode != 0:
        return {"error": ("push failed: " + (p.stderr or p.stdout))[:300]}

    # Do not trust exit 0. A successful push moves the remote-tracking ref; if it does not hold our
    # commit, the push sent something else ("Everything up-to-date" is the shape that used to be
    # reported as a publish).
    remote = _git(repo, "rev-parse", f"origin/{branch}").stdout.strip()
    if remote != sha:
        return {"error": (f"push reported success but origin/{branch} is at {remote[:10]}, not our "
                          f"commit {sha[:10]} — nothing was published. (git exits 0 on "
                          f"'Everything up-to-date'.)")}
    return {"sha": sha}
