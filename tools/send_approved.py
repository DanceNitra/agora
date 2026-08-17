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

SECOND GATE, added 2026-08-14: WHAT WE ALREADY SAID IN THAT THREAD. Approval binds the bytes; it says
nothing about whether the claim inside them is refuted by our own earlier comment. On 2026-08-14 the
draft "80.7/4.1 appears nowhere in the package" was aimed at a thread where WE had computed 80.7/4.1
two days earlier. `tools/prior_statement_check.py` reads our own history in the target thread and this
path refuses on an overlap unless `--ack-prior` says a human read it. Wired here, not remembered --
that is the half of the construction-gate lesson that repeats.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

# Direct-script runs put tools/ on sys.path automatically; an import from a test does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prior_statement_check as psc  # noqa: E402


def digest(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def _thread_in(cmd) -> str | None:
    """The github thread this command posts to, canonicalised. See psc.thread_from_command."""
    return psc.thread_from_command(cmd)[0]


def _gh_exe(cmd) -> bool:
    return bool(cmd) and Path(cmd[0]).name.lower().removesuffix(".exe") == "gh"


def bind_payload(draft: str, cmd: list) -> tuple[list, bytes] | str:
    """Rewrite the publish command so the bytes it sends ARE the bytes that were hashed.

    WHY THIS EXISTS, and it is the second half of this file's own lesson. Until 2026-08-14 the
    digest bound the FILE and nothing bound the PAYLOAD: nothing between the hash check and
    `subprocess.run(cmd)` asserted that `cmd` had anything to do with `a.file`. So

        post draft.md --sha <correct digest of draft.md> -- gh issue comment N -R o/r --body "..."

    printed "approved digest matches; publishing" and posted text nobody had hashed. That is not an
    exotic attack — `--body` is the most idiomatic gh form, and the argv here is composed by a
    model, so the binding failed exactly when nobody was trying to defeat it. The docstring above
    promised "approval is bound to bytes here instead". It was bound to a filename.

    The fix is to stop letting the command source its own body: we read the approved bytes ONCE,
    into memory, refuse every command shape that could get a body from anywhere else, and hand the
    bytes to gh on stdin. That also closes the read-again window (the file was re-read by the
    prior-statement gate and again by gh, with two `gh api --paginate` calls in between).

    Flag shapes verified against `gh help issue comment` and `gh api --help` on 2026-08-14, not
    from memory -- note the collision: `-F` is `--body-file` for `issue comment`/`pr comment` and
    `--field` for `gh api`.

    Returns (rewritten_cmd, stdin_bytes), or a refusal string explaining what to do instead.
    """
    if not _gh_exe(cmd):
        return ("only a `gh` command can be bound to the approved bytes; got %r. Another transport "
                "may source its body anywhere, so the digest would guarantee nothing." % (cmd[:1],))

    is_api = "api" in cmd
    want = Path(draft).resolve()
    body_flags = ("--input",) if is_api else ("--body-file", "-F")
    stdin_token = "-"

    # 1. An inline body cannot be bound to anything. Refuse before looking further.
    for i, arg in enumerate(cmd):
        if arg in ("--body", "-b") or arg.startswith("--body="):
            return ("the command carries an inline body (%s). An inline body is never the approved "
                    "file, so the digest cannot bind it. Use --body-file %s instead." % (arg, draft))
        if is_api and arg in ("-f", "-F", "--raw-field", "--field") and i + 1 < len(cmd):
            v = cmd[i + 1]
            if v.startswith("body=") and not v.startswith("body=@"):
                return ("the command carries an inline body (%s %s). Use `--input %s` or "
                        "`-F body=@%s`." % (arg, v, draft, draft))

    # 2. Find the one flag that sources the body from a file, and check it IS the approved file.
    out = list(cmd)
    found = None
    for i, arg in enumerate(cmd):
        if arg in body_flags and i + 1 < len(cmd):
            found, out[i + 1] = cmd[i + 1], stdin_token
            break
        if any(arg.startswith(f + "=") for f in body_flags):
            f, v = arg.split("=", 1)
            found, out[i] = v, f + "=" + stdin_token
            break
        if is_api and arg in ("-f", "-F", "--raw-field", "--field") and i + 1 < len(cmd):
            v = cmd[i + 1]
            if v.startswith("body=@"):
                found, out[i + 1] = v[len("body=@"):], "body=@-"
                break
    if found is None:
        return ("the command names no body file, so there is nothing to bind the approved bytes to."
                " Use `--body-file %s`%s." % (draft, " or `--input <file>`" if is_api else ""))
    if found != stdin_token and Path(found).resolve() != want:
        return ("the command sends %s but the approved digest is of %s. Approve the file you are "
                "actually sending." % (found, draft))

    return out, Path(draft).read_bytes()


def _prior_gate(path: str, cmd: list, declared: str | None, ack: bool) -> int | None:
    """Run the prior-statement check. Returns an exit code to refuse with, or None to proceed.

    The thread is derived from the COMMAND. A `--thread` given on our own argv is treated as an
    assertion to cross-check, never as an override: the first version preferred the declared value,
    so a caller could aim the check at a quiet thread while the command posted to a loud one, and
    get a green report naming the thread it did not post to.
    """
    from_cmd, posts = psc.thread_from_command(cmd)
    if declared and from_cmd:
        d = psc.parse_thread(declared)
        if not d or psc.canonical(d) != from_cmd:
            print("REFUSED: --thread %s does not match the thread this command posts to (%s)."
                  % (declared, from_cmd))
            print("  These must agree; the check is worthless if it can be aimed elsewhere.")
            return 2
    thread = from_cmd or declared
    if not thread:
        if posts:
            # Fail CLOSED on a publish path. "I could not tell where this goes" must not read as
            # "nothing of ours is there" -- that is the shape this whole file exists against.
            print("REFUSED: this command posts to github but no thread could be determined from it.")
            print("  Pass --thread <issue url> so the check has a target, or use a command form")
            print("  that names the thread. A thread we cannot read is not a thread we cleared.")
            return 2
        print("prior-statement check: NOT RUN -- this command does not post to a github thread.")
        print("  Reported, not assumed clean.")
        return None
    code, report = psc.check(Path(path).read_text(encoding="utf-8", errors="replace"), thread)
    print(report)
    print("")
    if code in (0, 3):
        return None
    if ack:
        print("--ack-prior given: a human states they have read the comments above. Proceeding.")
        return None
    print("REFUSED: %s" % ("our own words in this thread touch this claim" if code == 1
                           else "the thread could not be read"))
    print("  Read them, then either fix the draft (which changes the hash, so it is re-approved) or")
    print("  pass --ack-prior to record that they were read and are not a contradiction.")
    return 1 if code == 1 else 2


def _survive_a_narrow_console() -> None:
    """A console that cannot render a character must not silence the gate that protects a send.

    MEASURED 2026-08-17, and it is the fourth instance of this class in one day. `show --thread`
    printed the sha256, then raised UnicodeEncodeError on a U+2192 in the draft -- crashing INSIDE
    the prior-statement check, after the hash and before the verdict. So the one output that says
    "we already contradicted this upthread" never appeared, and the run still looked like it had
    produced its answer.

    That is worse than the CLI instance this repo fixed earlier today. There the crash followed a
    successful write; here it replaces a SAFETY VERDICT with silence, on the exact path that exists
    because I once sent something the owner had not approved.

    backslashreplace rather than replace: a mangled draft digest or a mangled quote from our own
    prior comment would be a wrong answer instead of an unreadable one.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if (getattr(stream, "encoding", "") or "").lower() not in ("utf-8", "utf8"):
                stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def _thread_url_from(cmd, thread):
    """The thread we are ACTUALLY posting to, taken from the publish command when possible.

    Not from --thread: that argument is optional and describes the thread the operator MEANT. The
    command is what the network will do. `gh issue comment <n> --repo <owner/name>` and
    `gh pr comment` both carry the real destination.
    """
    if thread:
        m = re.search(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)", thread)
        if m:
            return f"{m.group(1)}/{m.group(2)}", m.group(3)
    parts = list(cmd)
    if "gh" in parts[0] and len(parts) > 2 and parts[1] in ("issue", "pr") and parts[2] == "comment":
        num = parts[3] if len(parts) > 3 else None
        repo = parts[parts.index("--repo") + 1] if "--repo" in parts else None
        if num and repo:
            return repo, num
    return None, None


def _thread_moved_gate(path, cmd, thread, acked):
    """HAS THE CONVERSATION MOVED SINCE THIS DRAFT WAS WRITTEN?

    MEASURED 2026-08-17, and this gate exists because it was missing. A draft was approved, gated on
    its bytes, gated against our own prior comments -- and posted into an issue a maintainer had
    CLOSED four hours and thirty-eight minutes earlier, after two substantial comments from another
    participant that the draft therefore answered none of. Every existing check passed. They were all
    checks on US: our hash, our history, our numbers. Nothing read the room.

    A reply is a claim about a conversation, so the conversation's current state is part of what has
    to be true for the claim to hold. Two things are checked here, both cheap:

      * the thread is still OPEN -- posting into a closed thread is sometimes right and always a
        decision, never a default;
      * no comment by anyone else has landed since this draft was last written.

    The draft's own mtime is the reference point rather than a stored timestamp, because that is the
    moment the text stopped being able to account for anything new.
    """
    repo, num = _thread_url_from(cmd, thread)
    if not repo or not num:
        print("NOTE: no github thread could be identified, so the thread-state gate did not run.")
        print("      That is UNVERIFIED, not clear. Pass --thread if this is a reply.")
        return None

    try:
        raw = subprocess.run(
            ["gh", "issue", "view", num, "--repo", repo, "--json", "state,closedAt,comments"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        data = json.loads(raw.stdout)
    except Exception as ex:                                        # noqa: BLE001
        print("REFUSED: could not read the thread's state (%s). A gate that cannot see its target "
              "must not pass it." % type(ex).__name__)
        return 2

    drafted = dt.datetime.fromtimestamp(Path(path).stat().st_mtime, dt.timezone.utc)
    me = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True
                        ).stdout.strip()
    newer = [c for c in data.get("comments", [])
             if c.get("author", {}).get("login") != me
             and dt.datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00")) > drafted]

    problems = []
    if data.get("state") == "CLOSED":
        problems.append("the thread is CLOSED (since %s)" % data.get("closedAt"))
    if newer:
        problems.append("%d comment(s) by others landed after this draft was written:" % len(newer))
        for c in newer[-4:]:
            problems.append("    %s  %s  %s" % (c["createdAt"], c["author"]["login"], c["url"]))

    if not problems:
        return None
    print("\nTHREAD-STATE GATE")
    for p in problems:
        print("  " + p)
    if acked:
        print("  --ack-thread given: a human states they have read the above and still want this "
              "text sent as written. Proceeding.")
        return None
    print("  REFUSED. Read them, then either revise the draft (which invalidates the approved hash,")
    print("  as it should) or pass --ack-thread to send it unchanged deliberately.")
    return 3


def main(argv=None):
    _survive_a_narrow_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("show", "post"))
    ap.add_argument("file")
    ap.add_argument("--sha", help="the digest the owner approved (post only)")
    ap.add_argument("--thread", help="github issue/PR url, so `show` can run the prior-statement "
                                     "check while the owner is deciding")
    ap.add_argument("--ack-prior", action="store_true",
                    help="record that a human read our own prior comments in that thread")
    ap.add_argument("--ack-thread", action="store_true",
                    help="record that a human read what happened in the thread SINCE this draft was "
                         "written, including a close, and still wants it sent unchanged")
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
        if a.thread:
            print("")
            print(psc.check(body, a.thread)[1])
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

    # Bind the payload BEFORE the prior-statement check: the check costs two network calls, and
    # refusing afterwards would mean the operator waits for a gate to run against a draft the
    # command was never going to send.
    bound = bind_payload(a.file, cmd)
    if isinstance(bound, str):
        print("REFUSED: %s" % bound)
        return 2
    cmd, stdin = bound

    refuse = _thread_moved_gate(a.file, cmd, a.thread, a.ack_thread)
    if refuse is not None:
        return refuse

    refuse = _prior_gate(a.file, cmd, a.thread, a.ack_prior)
    if refuse is not None:
        return refuse

    print("approved digest matches; publishing %d bytes from memory (stdin), not from the file"
          % len(stdin))
    return subprocess.run(cmd, input=stdin).returncode


if __name__ == "__main__":
    sys.exit(main())
