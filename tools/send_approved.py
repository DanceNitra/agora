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

THIRD GATE, added 2026-08-23: HOW IT READS. The owner's standing rule since 2026-08-21 is a humanizer
pass on EVERY outbound draft, after @jason-sachs read a hundred of our comments on claude-code#34556
and named the constructions that make them read as generated. We built `tools/humanizer_tells.py` from
his reading the same day -- and then imported it in exactly ONE place, a gate for one specific draft,
never here. Measured 2026-08-23 across the 21 comments we sent in the two days after promising him
"the prologue goes in front of the drafting from here on": the tool fires on four of them, and one is
the comment we sent to DeepSeek-V3#1591 at 05:45 that morning, carrying "that is the honest version
of §2.1" -- the exact construction he had explained eleven hours earlier. The rule existed, the
detector existed, the detector was correct, and nothing ran it. Same shape as the two gates above, so
it gets the same remedy: wired, not remembered.

`show` prints the report before the owner ever sees the draft, which is where a tell costs nothing to
fix. `post` refuses on a blocking hit unless --ack-tells says a human looked and kept the wording. This module is NOT the humanizer skill; it is a
regex over a fraction of it, and `post` refuses unless --humanizer-skill-ran says the real
skill (.claude/skills/humanizer/SKILL.md) was run on the draft.

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
import humanizer_receipt as hr  # noqa: E402
import humanizer_tells as ht  # noqa: E402
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


def _tells_gate(body: str, acked: bool, skill_ran: bool) -> int | None:
    """Refuse a draft carrying a construction that reads as generated. None means proceed.

    Deliberately NOT waivable by the digest: the hash proves the owner saw these bytes, and he saw
    them because we handed them over. He is not the reader this gate is for. The acknowledgement is
    a separate flag so that keeping a wording is a decision somebody made, not a step nobody took.
    """
    # THIS MODULE IS NOT THE HUMANIZER, and saying so is half of what this gate is for. On
    # 2026-08-23 I wrote tools/humanizer_tells.py, wired it in here INSTEAD of
    # .claude/skills/humanizer/SKILL.md, and then reported its green result as "humanizer clean"
    # on three drafts that shipped. The skill is 622 lines over 33 pattern classes; this file is a
    # regex over a handful of them and cannot see a negative parallelism, an announcement opener,
    # or a voice mismatch against a sample. So the gate refuses to be mistaken for it.
    if not skill_ran:
        print("REFUSED: the humanizer SKILL has not been run on this draft.")
        print("  This module is a regex over a handful of that skill's 33 pattern classes.")
        print("  It is NOT the humanizer, and a green result here is not a humanizer pass.")
        print("  Run .claude/skills/humanizer/SKILL.md on the draft, then pass")
        print("  --humanizer-skill-ran to record that it was actually run.")
        return 1
    hits = ht.find_tells(body)
    if not hits:
        return None
    print("The draft carries %d construction%s that read as generated:"
          % (len(hits), "" if len(hits) == 1 else "s"))
    for name, got, off in hits:
        i = max(0, off - 55)
        ctx = " ".join(body[i:off + len(got) + 55].split())
        print("  line %-4d %-14s %r" % (ht.line_of(body, off), name, got))
        print("            ...%s..." % ctx)
    print("")
    print("  %s" % ht.report(body).splitlines()[0])
    if acked:
        print("--ack-tells given: a human read these and is keeping the wording. Proceeding.")
        return None
    print("  REFUSED. Rewrite them -- which invalidates the approved hash, so re-show the draft --")
    print("  or pass --ack-tells to record that a human read them and chose to keep them.")
    return 1


def _the_gate(path: str) -> int | None:
    """The owner's gate, and it is not a script I wrote. None means proceed.

    "a pod branou sa myslia veci ako Validate, storm ak je treba, redteam a podobne!!!!!" -- and
    then, the same day, "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO HOVEN". Both were said
    because I kept running `probes/gate_*.py`, a file I wrote that morning, and calling it the gate.
    That file recomputes figures against receipts. It is ONE check inside VALIDATE. It is not the
    frame, and it never was.

    The frame is the SKILLS: verify-claims (validate the facts), stress-claim (red-team the claim),
    and humanizer (how it reads). Storm when the claim rests on literature. Until today the send
    path asked for `--humanizer-skill-ran`, which is a bare flag -- exactly as strong as
    remembering, and on 2026-08-26 I passed it for a draft whose skeptic and validator had never
    run. So each skill now leaves a RECEIPT bound to the draft's content sha256, an edit
    invalidates it, and this refuses without all three.
    """
    m = hr.missing(path)
    if not m:
        return None
    print("REFUSED: the gate has not run on this draft. Missing: %s" % ", ".join(m))
    print("  The gate is the SKILLS, not a probes/*.py I wrote:")
    print("    verify  -> .claude/skills/verify-claims/SKILL.md    (every number vs its artifact)")
    print("    redteam -> .claude/skills/stress-claim/SKILL.md     (the claim, before the prose)")
    print("    humanizer -> .claude/skills/humanizer/SKILL.md      (how it reads)")
    print("  Then record each one against THESE bytes:")
    for skill in m:
        print("    python tools/humanizer_receipt.py record %s --skill %s --found \"...\""
              % (path, skill))
    return 1


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


def _creates_a_thread(cmd) -> bool:
    """`gh issue create` / `gh pr create` -- a destination that does not exist yet."""
    p = list(cmd)
    return (bool(p) and Path(p[0]).name.lower().removesuffix(".exe") == "gh"
            and len(p) > 2 and p[1] in ("issue", "pr") and p[2] == "create")


def _new_thread_gate(path, cmd, acked):
    """FOR A NEW ISSUE, the question is not "what did we already say here" -- nothing was said here,
    the thread does not exist. It is "is there already a thread for this".

    This exists because the gate refused an issue creation outright: the prior-statement check needs
    a thread to aim at, could not find one, and failed closed. Failing closed was right for a reply
    and wrong for a creation, and the difference is not a special case to wave through -- it is that
    the same worry (are we talking into a conversation we have not read) takes a different form when
    the conversation is the thing being started. Here it is duplicate detection.

    Non-blocking by design where it cannot be sure: it PRINTS the candidates and requires
    --ack-thread only when something looks like a real duplicate, because a title-word overlap is a
    weaker signal than a closed thread and a gate that cries wolf gets waived by reflex.
    """
    if not _creates_a_thread(cmd):
        return None
    p = list(cmd)
    repo = p[p.index("--repo") + 1] if "--repo" in p else None
    title = p[p.index("--title") + 1] if "--title" in p else ""
    if not repo:
        print("REFUSED: `gh issue create` without --repo; the destination must be explicit.")
        return 2

    words = {w.lower().strip("`(),:") for w in title.split() if len(w) > 4}
    try:
        raw = subprocess.run(["gh", "issue", "list", "--repo", repo, "--state", "all",
                              "--limit", "60", "--json", "number,title,state,url"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=60)
        issues = json.loads(raw.stdout)
    except Exception as ex:                                        # noqa: BLE001
        print(f"REFUSED: could not list issues on {repo} ({type(ex).__name__}). A duplicate check "
              "that cannot see the tracker has not run.")
        return 2

    scored = []
    for i in issues:
        overlap = words & {w.lower().strip("`(),:") for w in i["title"].split() if len(w) > 4}
        if len(overlap) >= 2:
            scored.append((len(overlap), i, sorted(overlap)))
    print(f"\nNEW-THREAD GATE -- {repo}: {len(issues)} issue(s) read, "
          f"{len(scored)} sharing 2+ title words")
    for n, i, ov in sorted(scored, reverse=True, key=lambda t: t[0])[:5]:
        print(f"  [{i['state']}] #{i['number']}  {i['title'][:64]}")
        print(f"        shared: {', '.join(ov)}  {i['url']}")
    if scored and not acked:
        print("  REFUSED. Read them. If none is a duplicate, pass --ack-thread.")
        return 3
    if scored:
        print("  --ack-thread given: a human states none of the above is a duplicate. Proceeding.")
    else:
        print("  no candidate duplicate found.")
    return None


def _thread_url_from(cmd, thread):
    """The thread we are ACTUALLY posting to, taken from the publish command when possible.

    Not from --thread: that argument is optional and describes the thread the operator MEANT. The
    command is what the network will do. `gh issue comment <n> --repo <owner/name>` and
    `gh pr comment` both carry the real destination.

    MEASURED 2026-08-17, on a real send. This function used to re-implement the parse, and knew only
    the long `--repo`; the send used `-R`, so it returned (None, None) and the gate printed "no
    github thread could be identified" and did not run -- on the most idiomatic gh form there is.
    A gate defeated by a short flag is the same defect it was built to prevent: a check that never
    sees its target reports safe. `prior_statement_check.thread_from_command` already handles every
    posting form (`--repo`, `-R`, `--repo=`, a full url, a REST path) and is tested against them, so
    the duplicate is deleted rather than patched -- two derivations of one fact, where one is a
    subset of the other, is the bug.

    The command is also consulted FIRST now. The old code returned the declared `--thread` when it
    was present, which contradicted this docstring; `_prior_gate` refuses a mismatch before we get
    here, but the order should say what it means.
    """
    for candidate in (psc.thread_from_command(list(cmd))[0], thread):
        if not candidate:
            continue
        m = re.search(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)", candidate)
        if m:
            return f"{m.group(1)}/{m.group(2)}", m.group(3)
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
    import owner_spoke as osp   # lives beside this file

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
    ap.add_argument("--humanizer-skill-ran", action="store_true",
                    help="record that .claude/skills/humanizer/SKILL.md was actually RUN on this "
                         "draft. This module is not that skill and refuses to run without it.")
    ap.add_argument("--ack-tells", action="store_true",
                    help="record that a human read the flagged constructions and is keeping them")
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
        raw = Path(a.file).read_bytes()
        body = io.open(a.file, encoding="utf-8").read()
        # RAW bytes, because that is what digest() hashes and what bind_payload sends. This line
        # used to re-encode the TEXT, which on Windows silently dropped every CR: it showed the
        # owner 5,911 for a payload of 5,994. The digest was never wrong -- the number printed
        # beside it was, and a figure shown next to a hash is read as describing that hash.
        print("sha256 : %s" % now)
        print("bytes  : %d" % len(raw))
        print("words  : %d" % len(body.split()))
        # Before the owner sees it, because this is the only point where a tell costs nothing to
        # fix: rewriting after approval invalidates the hash by design.
        print("")
        print(ht.report(body))
        if a.thread:
            print("")
            print(psc.check(body, a.thread)[1])
        # Record that this hash was DISPLAYED, so `post` can require that a person spoke
        # The record holds a time, never a verdict.
        # No state file any more: the anchor is the harness's own record of the line above.
        # A file this session writes was forgeable, and an audit showed backdating one line
        # satisfied the check for every hash at once.
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

    # THE DIGEST IS MINE. I compute it, print it and pass it back, so "the owner approved
    # this" has been my own assertion wearing a hash. This establishes the one fact I cannot
    # author: after the hash was displayed, a real message from a person arrived in the
    # harness-written transcript. It cannot know the message means yes. It can prove that
    # nobody said anything at all.
    spoke_ok, spoke_why = osp.check(now)
    if not spoke_ok:
        print("REFUSED: no owner message follows the moment this hash was shown.")
        print("  " + spoke_why)
        print("  A task notification is recorded as a user message and is not consent.")
        return 1
    print("owner-spoke check: " + spoke_why)

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

    # Local and free, so it runs before the gates that cost network calls: being refused on the
    # wording after waiting for two `gh api --paginate` round trips is how a gate earns a reputation
    # for being in the way. Gates the PAYLOAD, not the file, for the same reason bind_payload exists.
    # THE GATE FIRST, before anything cheap or expensive. It is the three skills, and it is not
    # waivable by any flag on this command line: the receipts are bound to the draft's bytes.
    refuse = _the_gate(a.file)
    if refuse is not None:
        return refuse

    refuse = _tells_gate(stdin.decode("utf-8", "replace"), a.ack_tells, a.humanizer_skill_ran)
    if refuse is not None:
        return refuse

    refuse = _new_thread_gate(a.file, cmd, a.ack_thread)
    if refuse is not None:
        return refuse
    if _creates_a_thread(cmd):
        # The prior-statement and thread-state gates below both need a thread to aim at, and a
        # thread being CREATED does not have one. Refusing here was the gate failing closed on a
        # question that cannot apply -- correct for a reply, wrong for a new issue. The duplicate
        # check above is the form those questions take when the destination does not exist yet.
        print("approved digest matches; publishing %d bytes from memory (stdin), not from the file"
              % len(stdin))
        return subprocess.run(cmd, input=stdin).returncode

    refuse = _thread_moved_gate(a.file, cmd, a.thread, a.ack_thread)
    if refuse is not None:
        return refuse

    refuse = _prior_gate(a.file, cmd, a.thread, a.ack_prior)
    if refuse is not None:
        return refuse

    print("approved digest matches; publishing %d bytes from memory (stdin), not from the file"
          % len(stdin))
    rc = subprocess.run(cmd, input=stdin).returncode
    if rc == 0:
        _verify_landed(stdin, a.thread)
    return rc


def _verify_landed(stdin: bytes, thread: str) -> None:
    """Fetch what actually landed and compare it byte for byte with what we sent.

    Every gate above this line checks the payload BEFORE it leaves. None of them can see the
    transport. Measured 2026-08-24 on anthropics/claude-code#82056: `gh issue comment
    --body-file -` decoded our UTF-8 stdin as the Windows ANSI codepage, so the em dash inside a
    VERBATIM QUOTE of the CLI's own output was published as `a<euro>"`. 2,333 bytes in, 2,338 out,
    exit 0, no warning anywhere. In a comment whose whole subject is exact strings.

    It is not a blanket failure, which is why nothing caught it: a comment sent an hour earlier
    the same way, carrying both an em dash and an en dash among a lot of CJK, round-tripped
    byte-identical. Whatever heuristic picks the decoding, it is data-dependent, so the only
    reliable check is to read back what landed.

    Reports rather than raises: the comment is already public by this point, and the operator
    needs the diff and the repair recipe, not a traceback. The repair is a PATCH whose body is
    JSON with ensure_ascii=True, so nothing multibyte ever crosses a codepage boundary.
    """
    import json as _json
    import re as _re
    m = _re.search(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)", thread or "")
    if not m:
        print("NOTE: no thread url given, so what landed was not read back. "
              "Pass --thread to enable the transport check.")
        return
    owner, repo, num = m.groups()
    out = subprocess.run(["gh", "api", f"repos/{owner}/{repo}/issues/{num}/comments",
                          "--paginate"], capture_output=True)
    try:
        me = subprocess.run(["gh", "api", "user", "--jq", ".login"],
                            capture_output=True, text=True).stdout.strip()
        mine = [c for c in _json.loads(out.stdout.decode("utf-8"))
                if (c.get("user") or {}).get("login") == me]
        landed = mine[-1]["body"].encode("utf-8")
        cid = mine[-1]["id"]
    except Exception as e:                                          # noqa: BLE001
        print(f"NOTE: could not read the comment back ({type(e).__name__}); transport unchecked.")
        return
    if landed == stdin:
        print(f"transport verified: comment {cid} is byte-identical to what was approved.")
        return
    print(f"!! WHAT LANDED IS NOT WHAT WAS SENT. comment {cid}: "
          f"{len(stdin)} bytes sent, {len(landed)} bytes live.")
    a, b = stdin.decode("utf-8", "replace"), landed.decode("utf-8", "replace")
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print(f"   first difference at character {i}:")
            print(f"     sent : {a[max(0, i - 40):i + 20]!r}")
            print(f"     live : {b[max(0, i - 40):i + 20]!r}")
            break
    print("   REPAIR: write {\"body\": <text>} with json.dump(..., ensure_ascii=True) to a file,")
    print(f"   then: gh api --method PATCH repos/{owner}/{repo}/issues/comments/{cid} --input FILE")


if __name__ == "__main__":
    sys.exit(main())
