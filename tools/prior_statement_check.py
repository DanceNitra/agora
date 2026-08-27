"""Before a claim goes INTO a thread, check it against what WE already said THERE.

WHY THIS FILE EXISTS. On 2026-08-14 the most dangerous of six killed claims was
"80.7/4.1 appears nowhere in the package". It was aimed at deepseek-ai/DeepSeek-V3#1466, and our own
comment 5271557433 in that same thread, two days earlier, contains the line

    | TAT v0.9 | 80.7% | **242** | 4.10% -> ~86 | 0.738 |
    The reconstruction checks out: 242/(242+86) = 0.7378 ...

We had computed the number ourselves and were about to tell them it did not exist. Nothing in the
publish path reads our own history, so the refutation would have been public, immediate, and ours.

WHAT IT CHECKS, and why these two things. Both classes come from the six killed claims, not from
imagination:

  * NEGATIVE EXISTENCE claims -- "appears nowhere", "there is no", "has no runner", "does not exist".
    Two of the six were this shape (the 80.7 claim, and "your vectors have no runner" -- refuted by 17
    test modules that were simply not in my local copy). A negative existence claim is the only kind
    that a single overlooked artifact refutes completely, and the cheapest place an overlooked
    artifact hides is our own earlier words in the same thread.
  * SIGNIFICANT NUMBERS -- a token with a decimal point, three or more digits, or a percent sign.
    Bare one- and two-digit integers are dropped: they match everything and a check that fires on
    everything is read by nobody.

WHAT IT DOES NOT DO. It does not judge. It surfaces our prior comments that carry the same numbers or
touch the same negation, and a human reads them. A ranking would invite trusting the rank.

FAILURE MODES, deliberately separated -- a check that never sees its target must not report SAFE:

    0  CHECKED, CLEAN     the thread was read; nothing of ours overlaps
    1  OVERLAP            our own prior words touch this claim; read them before sending
    2  COULD NOT CHECK    gh missing, unauthenticated, thread unreachable, comments unreadable
    3  NOTHING TO CHECK   the draft carries no significant number and no negative-existence claim

3 is not 0. A draft with nothing to check has not been cleared by this gate; it was out of its scope,
and the caller is told so in those words rather than shown a green line.

    python tools/prior_statement_check.py <draft> --thread <issue-or-PR url> [--author LOGIN]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_AUTHOR = "DanceNitra"

# A number worth matching on: has a decimal point, or >=3 digits, or wears a percent sign.
# 80.7, 4.1, 242, 2100, 30% all survive; 4, 86, 12 do not. Widening this is not free -- the
# check is only read while it stays quiet on the ordinary.
_NUM = re.compile(r"(?<![\w.])(\d+\.\d+|\d{3,}|\d{1,2}\s*%)(?![\w])")

# Negation shapes, matched against a sentence. Each is a phrase that asserts absence; a claim of
# absence is refuted by a single instance, which is why this class gets its own pass.
_NEGATIONS = (
    "appears nowhere", "appear nowhere", "nowhere in", "nowhere does",
    "there is no", "there are no", "there was no", "there were no",
    "does not exist", "do not exist", "did not exist", "no longer exists",
    "has no", "have no", "had no", "carries no", "contains no", "provides no",
    "is absent", "are absent", "is missing", "are missing",
    "is not present", "are not present", "not present in", "not found in",
    "cannot be found", "could not be found", "never appears", "never computed",
    "no evidence", "no runner", "no test", "no such", "none of",
    "nothing in", "not covered", "uncovered by", "unmeasured", "never measured",
)

# A sentence boundary is a . ! or ? NOT between two digits -- otherwise "80.7 appears nowhere"
# splits at the decimal and the quoted claim comes back as "7 appears nowhere". Measured on the
# real fixture the first time this ran.
_SENTENCE_SPLIT = re.compile(r"(?<!\d)[.!?]+(?!\d)|\n")


def significant_numbers(text: str) -> set[str]:
    """Number tokens worth cross-checking. Percent signs normalised away."""
    return {m.group(1).replace(" ", "").rstrip("%") for m in _NUM.finditer(text)}


def _values(tokens) -> dict[float, str]:
    """token -> value, keyed by value so 4.1 and 4.10% are the same quantity."""
    out = {}
    for t in tokens:
        try:
            out.setdefault(float(t), t)
        except ValueError:
            continue
    return out


def negative_claims(text: str) -> list[str]:
    """Sentences that assert something is absent."""
    out = []
    for s in _SENTENCE_SPLIT.split(text):
        s = " ".join((s or "").split())
        if s and any(p in s.lower() for p in _NEGATIONS):
            out.append(s)
    return out


def _lines_with(body: str, values: set[float]) -> list[str]:
    """Lines of `body` carrying any of these VALUES.

    Matching is by value, never by substring: a substring test for "4.1" fires inside "24.11%",
    which it did on the first run against the real thread. A gate that cries wolf is read by nobody.
    """
    hits = []
    for ln in body.splitlines():
        if values & set(_values(significant_numbers(ln))):
            flat = " ".join(ln.split())[:200]
            if flat not in hits:
                hits.append(flat)
    return hits[:3]


def compare(draft: str, comments: list[dict]) -> dict:
    """Pure matcher. `comments` is [{id, created_at, body, url}] -- ours, oldest first.

    Kept free of I/O on purpose: the offline test runs this against a recorded snapshot of the real
    thread, so the fixture cannot go quiet because the network did.
    """
    nums = significant_numbers(draft)
    negs = negative_claims(draft)
    want = _values(nums)
    overlaps = []
    for c in comments:
        body = c.get("body") or ""
        have = _values(significant_numbers(body))
        shared_v = set(want) & set(have)
        if not shared_v:
            continue
        overlaps.append({
            "id": c.get("id"),
            "created_at": c.get("created_at"),
            "url": c.get("url"),
            "numbers": sorted(want[v] for v in shared_v),
            "lines": _lines_with(body, shared_v),
        })
    return {
        "numbers_checked": sorted(nums),
        "negative_claims": negs,
        "comments_read": len(comments),
        "overlaps": overlaps,
    }


# ----------------------------------------------------------------------------- fetching the thread
_URL = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/(?:issues|pull)/(\d+)")
# The REST path shape, as it appears in `gh api repos/o/r/issues/N/comments`.
_API_PATH = re.compile(r"repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/(?:issues|pulls)/(\d+)")
_OWNER_REPO = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def parse_thread(s: str) -> tuple[str, str, str] | None:
    """(owner, repo, number) from a thread URL, or None."""
    m = _URL.search(s or "")
    return (m.group(1), m.group(2), m.group(3)) if m else None


def canonical(t: tuple[str, str, str]) -> str:
    return "https://github.com/%s/%s/issues/%s" % t


def thread_from_command(cmd: list[str]) -> tuple[str | None, bool]:
    """(thread url or None, this command posts to github).

    WHY THIS IS NOT JUST parse_thread OVER argv. The first version of this gate looked for a full
    `github.com/o/r/issues/N` url in the publish command. Measured the same day it was written:
    of the three normal ways to post a comment, only ONE carries such a url --

        gh issue comment 7707 --repo openclaw/openclaw --body-file d.md   -> no url
        gh api repos/openclaw/openclaw/issues/7707/comments -f body=@d.md -> no url
        gh issue comment https://github.com/o/r/issues/7707 ...           -> url

    so the gate printed "NOT RUN" and let the publish through on two of three. That is the exact
    shape its own docstring warns about: a check that never sees its target reports SAFE. The second
    return value exists so the CALLER can refuse instead of proceeding when this is a post command
    whose thread could not be determined -- silence on a publish path has to fail closed.
    """
    cmd = [str(c) for c in (cmd or [])]
    posts = _is_github_post(cmd)

    for arg in cmd:                                   # (1) a full thread url anywhere
        t = parse_thread(arg)
        if t:
            return canonical(t), posts
    for arg in cmd:                                   # (2) a REST path: repos/o/r/issues/N/...
        m = _API_PATH.search(arg)
        if m:
            return canonical((m.group(1), m.group(2), m.group(3))), posts
    # (3) `gh issue comment <N> --repo owner/repo`
    owner_repo = None
    for i, arg in enumerate(cmd):
        if arg in ("--repo", "-R") and i + 1 < len(cmd):
            owner_repo = _OWNER_REPO.match(cmd[i + 1])
            break
        if arg.startswith("--repo="):
            owner_repo = _OWNER_REPO.match(arg.split("=", 1)[1])
            break
    if owner_repo:
        for arg in cmd[1:]:
            if arg.isdigit():
                return canonical((owner_repo.group(1), owner_repo.group(2), arg)), posts
    return None, posts


def _is_github_post(cmd: list[str]) -> bool:
    """Does this command write to a github thread? Errs toward True — on a publish path an
    over-broad guess costs one --ack-prior, and an under-broad one costs a post nobody checked."""
    if not cmd:
        return False
    exe = Path(cmd[0]).name.lower().removesuffix(".exe")
    if exe != "gh":
        return False
    if "comment" in cmd or "create" in cmd or "reply" in cmd:
        return True
    if "api" in cmd:
        # `gh api` defaults to GET; only a method or a field makes it a write.
        return any(a in ("-X", "--method", "-f", "-F", "--input", "--raw-field") for a in cmd) or \
            any(a.upper() in ("POST", "PATCH", "PUT") for a in cmd)
    return False


class CannotCheck(Exception):
    """The thread could not be read. Never silently a pass."""


def fetch_our_comments(owner: str, repo: str, number: str, author: str) -> list[dict]:
    if shutil.which("gh") is None:
        raise CannotCheck("gh is not on PATH")
    out = []
    # The issue body itself counts: our opening comment is where a claim most often first lands.
    for endpoint, is_issue in ((f"repos/{owner}/{repo}/issues/{number}", True),
                               (f"repos/{owner}/{repo}/issues/{number}/comments", False)):
        cmd = ["gh", "api", endpoint] + ([] if is_issue else ["--paginate"])
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise CannotCheck("gh api %s failed: %s" % (endpoint, e))
        if p.returncode != 0:
            raise CannotCheck("gh api %s exited %d: %s"
                              % (endpoint, p.returncode, (p.stderr or "").strip()[:300]))
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError as e:
            raise CannotCheck("gh api %s returned unparseable JSON: %s" % (endpoint, e))
        items = [data] if is_issue else (data if isinstance(data, list) else [])
        for c in items:
            if (c.get("user") or {}).get("login") == author:
                out.append({"id": c.get("id"), "created_at": c.get("created_at"),
                            "url": c.get("html_url"), "body": c.get("body") or ""})
    out.sort(key=lambda c: c.get("created_at") or "")
    return out


# ------------------------------------------------------------------------------------------ report
def format_report(r: dict, thread: str, author: str) -> str:
    L = ["prior-statement check -- %s (author %s)" % (thread, author),
         "  our comments read : %d" % r["comments_read"],
         "  numbers checked   : %s" % (", ".join(r["numbers_checked"]) or "(none)")]
    if r["negative_claims"]:
        L.append("  NEGATIVE EXISTENCE CLAIMS in this draft (%d) -- the class our own history"
                 " refutes:" % len(r["negative_claims"]))
        for s in r["negative_claims"][:6]:
            L.append("      - %s" % s[:180])
    if not r["overlaps"]:
        L.append("")
        L.append("  no comment of ours in this thread carries any of these numbers.")
        return "\n".join(L)
    L.append("")
    L.append("  %d comment(s) OF OURS in this thread already carry these numbers. Read them before"
             " you assert anything about them:" % len(r["overlaps"]))
    for o in r["overlaps"]:
        L.append("")
        L.append("    comment %s  %s  [%s]" % (o["id"], o["created_at"] or "?",
                                               ", ".join(o["numbers"])))
        L.append("      %s" % (o["url"] or ""))
        for ln in o["lines"]:
            L.append("      | %s" % ln)
    return "\n".join(L)


def check(draft_text: str, thread: str, author: str = DEFAULT_AUTHOR) -> tuple[int, str]:
    """-> (exit_code, report). See the module docstring for what each code means."""
    parsed = parse_thread(thread)
    if not parsed:
        return 2, "COULD NOT CHECK: %r is not a github issue/PR url" % thread
    nums = significant_numbers(draft_text)
    negs = negative_claims(draft_text)
    if not nums and not negs:
        return 3, ("NOTHING TO CHECK: this draft carries no significant number and no "
                   "negative-existence claim. That is not a pass -- it is out of this gate's scope.")
    try:
        ours = fetch_our_comments(*parsed, author=author)
    except CannotCheck as e:
        return 2, ("COULD NOT CHECK: %s\n  A thread we cannot read is not a thread we have cleared."
                   % e)
    r = compare(draft_text, ours)
    return (1 if r["overlaps"] else 0), format_report(r, thread, author)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("draft", help="path to the draft that is about to be posted")
    ap.add_argument("--thread", required=True, help="the github issue/PR url it is going to")
    ap.add_argument("--author", default=DEFAULT_AUTHOR, help="our github login")
    a = ap.parse_args(argv)
    text = Path(a.draft).read_text(encoding="utf-8", errors="replace")
    code, report = check(text, a.thread, a.author)
    print(report)
    print("")
    print({0: "CHECKED, CLEAN", 1: "OVERLAP -- read the comments above before sending",
           2: "COULD NOT CHECK -- refuse", 3: "NOTHING TO CHECK"}[code])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
