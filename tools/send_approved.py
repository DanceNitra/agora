"""Post outward ONLY the exact bytes the owner approved. Not a reminder: a check that fails.

WHY THIS EXISTS. The PreToolUse guard already says "that token asserts the OWNER approved THIS EXACT
DRAFT. If he has not seen it, stop." It is a warning, and on 2026-08-13 I read it and posted anyway: the
owner had approved a draft, I then appended a paragraph, and I sent the edited version under his
approval of the earlier one. Twice in one session I posted content he had not seen in final form. He has
the rule in my memory and in a hook, and I did it regardless, because both are things I have to CHOOSE
to honour at the moment I am least likely to.

So approval is bound to bytes here instead. Two steps:

    python tools/send_approved.py show <file>
        prints the draft's sha256. Paste the draft to the owner WITH that hash.

    python tools/send_approved.py post <file> --sha <the hash he approved> -- gh issue comment ...
        recomputes the hash and REFUSES if a single byte changed since he saw it.

Editing after approval is exactly the failure mode, so an edit invalidates the approval by construction
rather than by my remembering that it should.
"""
import argparse
import hashlib
import io
import subprocess
import sys


def digest(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("show", "post"))
    ap.add_argument("file")
    ap.add_argument("--sha", help="the digest the owner approved (post only)")
    # The publish command is split off BEFORE argparse sees it. `nargs=REMAINDER` after a positional
    # swallows later options too, so `post f --sha X -- gh ...` lost the --sha and the tool refused a
    # correctly approved draft. A gate that fails closed on its own argument parsing is still a gate
    # that does not work.
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = []
    if "--" in args:
        i = args.index("--")
        args, cmd = args[:i], args[i + 1:]
    a = ap.parse_args(args)
    a.rest = cmd

    now = digest(a.file)
    if a.action == "show":
        body = io.open(a.file, encoding="utf-8").read()
        print("sha256 : %s" % now)
        print("bytes  : %d" % len(body.encode("utf-8")))
        print("words  : %d" % len(body.split()))
        print("\nShow the owner this draft together with the hash above, and pass it back as --sha.")
        return 0

    if not a.sha:
        print("REFUSED: --sha is required. Run `show` first and get the owner's approval on that hash.")
        return 2
    if a.sha.strip().lower() != now:
        print("REFUSED: the file changed since it was approved.")
        print("  approved : %s" % a.sha.strip().lower())
        print("  current  : %s" % now)
        print("  Re-show the draft and get approval on the new hash. An edit after approval is the")
        print("  exact failure this exists to stop, so it cannot be waived here.")
        return 1

    cmd = list(a.rest)
    if not cmd:
        print("REFUSED: no publish command given after --")
        return 2
    print("approved digest matches; publishing")
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
