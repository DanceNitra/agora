# -*- coding: utf-8 -*-
"""Is any file TRACKED by git despite a .gitignore rule that names it?

.gitignore governs untracked files only. Once a path is in the index, the rule beside it is inert,
and it stays inert silently: `git status` is clean, `git check-ignore` on the working tree says
nothing, and the rule reads as protection to everyone who opens the file.

Measured 2026-09-10 on this repo. Rules to keep a co-author's unsubmitted manuscript out of a
PUBLIC repository had been at .gitignore lines 295 to 317 with their reason written beside them.
Twenty-one of the paths they name were tracked, and manuscript.tex answered HTTP 200 with 40383
bytes on raw.githubusercontent.com. The rule had never applied to a single one of them.

This is the same shape as every expensive day here: a check that never sees its target reports SAFE.

THE CONTROL. The probe stages a file that a rule names, and requires the check to report it. If
that does not fire, the check is reading something other than the index and its green means
nothing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Paths whose rules exist to keep someone else's unpublished work out of a PUBLIC repository. A
# tracked file here is the failure this probe was written for; everything else is reported only.
SENSITIVE_PREFIXES = (
    "agora_output/edrn_submission/",
    "agora_output/edrn_final/",
)


def _is_sensitive(path):
    return any(path.startswith(pfx) for pfx in SENSITIVE_PREFIXES)


def run(args, **kw):
    return subprocess.run(["git"] + args, cwd=ROOT, capture_output=True, text=True, **kw)


def tracked_but_ignored(ref=None):
    """Every path that git tracks AND .gitignore names. Empty is the healthy answer."""
    if ref:
        listing = run(["ls-tree", "-r", "--name-only", ref])
    else:
        listing = run(["ls-files"])
    if listing.returncode != 0:
        sys.exit("cannot list tracked files: %s" % listing.stderr.strip())
    # Strip the carriage return. Windows git hands these back with \r attached, and a path with a
    # stray \r is a DIFFERENT path: git quotes it, the rule stops matching, and the canary the
    # control stages is never recognised. The first run of this probe reported 345 hits with a
    # control that did not fire, which is the signature of an instrument measuring its own noise.
    paths = [p.rstrip("\r") for p in listing.stdout.splitlines() if p.strip()]
    if not paths:
        sys.exit("the instrument found no tracked files at all, which cannot be right")
    # BYTES, not text. With text=True Python translates "\n" to "\r\n" on the way INTO the child on
    # Windows, so git receives "path\r", treats the CR as part of the name, quotes it, and the rule
    # stops matching. That is what produced the first run's 345 hits beside a control that could not
    # fire: the instrument was measuring its own line endings.
    hit = subprocess.run(["git", "check-ignore", "--no-index", "--stdin"], cwd=ROOT,
                         input=("\n".join(paths) + "\n").encode("utf-8"),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # exit 0 means at least one matched, 1 means none matched; anything else is a broken run
    if hit.returncode not in (0, 1):
        sys.exit("check-ignore failed: %s" % hit.stderr.decode("utf-8", "replace").strip())
    out = hit.stdout.decode("utf-8", "replace")
    return sorted(p for p in out.splitlines() if p.strip()), len(paths)


def control_fires():
    """Stage a path that a rule names and require the check to see it."""
    rules = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    if "*.env.bak-*" not in rules and ".env.*" not in rules:
        return False, "no rule available to build a control on"
    canary = os.path.join(ROOT, ".env.probe-canary")
    open(canary, "w", encoding="utf-8").write("canary\n")
    try:
        add = run(["add", "-f", "--", ".env.probe-canary"])
        if add.returncode != 0:
            return False, "could not stage the canary: %s" % add.stderr.strip()
        seen, _ = tracked_but_ignored()
        return ".env.probe-canary" in seen, "canary staged and %sseen" % ("" if ".env.probe-canary" in seen else "NOT ")
    finally:
        run(["rm", "--cached", "-q", "--", ".env.probe-canary"])
        if os.path.exists(canary):
            os.remove(canary)


def main():
    here, n_here = tracked_but_ignored()
    on_main, n_main = tracked_but_ignored("origin/main")
    fired, why = control_fires()

    # WHAT BLOCKS AND WHAT ONLY REPORTS. 440 paths here are tracked despite a rule naming them, and
    # almost all are harmless: old handoffs and benchmark data whose rules were written afterwards.
    # Failing on all of them would make this wallpaper, and wallpaper is how the one that mattered
    # went unnoticed. So the exit code answers the question that has actually cost us: is anything
    # tracked under a rule written to keep someone else's unpublished work out of a public repo?
    sensitive_here = [p for p in here if _is_sensitive(p)]
    sensitive_main = [p for p in on_main if _is_sensitive(p)]

    result = {
        "tracked_files_checked_here": n_here,
        "tracked_but_ignored_here": len(here),
        "tracked_but_ignored_on_origin_main": len(on_main),
        "tracked_files_checked_on_origin_main": n_main,
        "sensitive_tracked_here": sensitive_here,
        "sensitive_tracked_on_origin_main": sensitive_main,
        "reported_not_blocking_here": here,
        "control_fires": fired,
        "control_note": why,
        "verdict": "PASS" if (not sensitive_here and not sensitive_main and fired) else "FAIL",
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           os.path.basename(__file__).replace(".py", ".result.json")),
              "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)

    print("tracked files checked, here:", n_here, "| on origin/main:", n_main)
    print("control fires:", fired, "-", why)
    print("tracked despite a rule, here: %d | on origin/main: %d (reported, not blocking)"
          % (len(here), len(on_main)))
    print("SENSITIVE, here: %d | on origin/main: %d (blocking)"
          % (len(sensitive_here), len(sensitive_main)))
    for q in sensitive_here + sensitive_main:
        print("   ", q)
    print("verdict:", result["verdict"])
    if result["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
