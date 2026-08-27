"""The humanizer rule existed, the detector existed and was correct, and the send path never called it.

On 2026-08-21 @jason-sachs read a hundred of our comments on anthropics/claude-code#34556 and named
three constructions that make writing read as generated. We built `tools/humanizer_tells.py` from his
reading that same day, and the owner made a humanizer pass on every outbound draft a standing rule.

Then it was imported in exactly one place -- `probes/gate_cml311_reply.py`, a gate for one specific
draft -- and never by `tools/send_approved.py`, which is the path every outward comment actually goes
through. Measured 2026-08-23 over the 21 comments we sent in the two days after promising him the
prologue would go in front of the drafting: the detector fires on four, and one of them is the comment
sent to deepseek-ai/DeepSeek-V3#1591 at 05:45 that morning, carrying "that is the honest version of
§2.1" -- the construction he had explained eleven hours earlier.

So this probe asserts the wiring rather than the rule, and it fails if the wiring is removed:

  1. every blocking construction fires on a planted positive     (a detector that cannot fire would
     make every clean verdict below meaningless)
  2. every blocking construction stays quiet on a clean draft    (and on the legitimate uses that the
     older, wider word list rejected)
  3. the gate refuses a draft carrying a tell
  4. the same draft with the tell removed passes                 (both directions, per the rule that
     cost us three guards on their first attempt)
  5. --ack-tells waives it, and only it
  6. END TO END: the real send_approved.py CLI refuses the real bytes we sent to #1591, naming the
     tells gate as the reason -- so this measures the shipped path, not a copy of its logic

The end-to-end case deliberately uses only the REFUSING direction. A refusal returns before
`subprocess.run`, so the probe can exercise the real command-line tool without any risk of posting.
"""
import io
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.humanizer_tells import (  # noqa: E402
    BANNED_WORDS, CONSTRUCTIONS, REPORT_ONLY_CONSTRUCTIONS, find_tells,
)
import send_approved  # noqa: E402

# Verbatim from the comment we sent to deepseek-ai/DeepSeek-V3#1591 at 2026-08-23T05:45:01Z,
# comment id 5384467154. Quoted so the regression is a fixture and not a memory.
SENT_TO_1591 = (
    "One record is six characters long end to end. That is the honest version of "
    "§2.1, and it is stronger than the illustration currently in the guide."
)

# One planted positive per blocking construction. If a construction is added without a line here,
# assertion 1 fails -- which is the point: a detector nobody proved can fire is not a detector.
POSITIVES = {
    "the-honest-X": "The honest minimum is to report the range beside it.",
    "worth-saying": "It is worth noting that the two counts diverge.",
    "not-X-but-Y":  "The number is not a measurement, it is a restatement of the input.",
}

# Uses that must NOT fire. The middle one is the phrase our older word list rejected and which we
# have published and stand behind; the last is an ordinary paired parenthetical, demoted on
# 2026-08-23 after measuring 4/4 false positives on our own sent comments.
NEGATIVES = (
    "We measured 516 keys at fold 8 and 514 of them merged. Re-run it or break it.",
    "An honest null result is still a result, and people are honest even when their claims are not.",
    "The line stopped appearing — twelve comments in a row without it — and the length doubled.",
)

rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


class _Blocked(Exception):
    """Raised instead of running the publish command, so this probe can never post."""


def run_cli(argv):
    """Drive the real CLI with the publish step stubbed out. Returns (rc, stdout, attempted).

    The refusing path returns before `subprocess.run`, so exercising it is safe on its own. The stub
    is here anyway because a probe that is safe only while the code under test is correct is not
    safe -- and this one deliberately runs a mutation in which the gate does nothing.
    """
    attempted = []

    def fake_run(cmd, *a, **k):
        attempted.append(cmd)
        raise _Blocked(" ".join(map(str, cmd)))

    real_run, real_out = send_approved.subprocess.run, sys.stdout
    send_approved.subprocess.run = fake_run
    buf = io.StringIO()
    sys.stdout = buf
    try:
        rc = send_approved.main(argv)
    except _Blocked:
        rc = "WOULD HAVE PUBLISHED"
    except Exception as ex:
        rc = "raised %s" % type(ex).__name__
    finally:
        send_approved.subprocess.run = real_run
        sys.stdout = real_out
    return rc, buf.getvalue(), attempted


def main():
    # 1 -- every blocking construction fires on its planted positive
    for name, text in POSITIVES.items():
        hits = [n for n, _, _ in find_tells(text)]
        ck(name in hits, "control: %s fires on a planted positive" % name, ",".join(hits) or "NOTHING")
    missing = sorted(set(CONSTRUCTIONS) - set(POSITIVES))
    ck(not missing, "control: every blocking construction has a planted positive", ",".join(missing))
    ck(BANNED_WORDS and find_tells("However, the result is crucial."),
       "control: the banned-word list fires too")
    ck("em-dash-gloss" in REPORT_ONLY_CONSTRUCTIONS and "em-dash-gloss" not in CONSTRUCTIONS,
       "em-dash-gloss is reported, not blocked (4/4 false positives on our sent comments)")

    # 2 -- and stays quiet where it should
    for text in NEGATIVES:
        hits = find_tells(text)
        ck(not hits, "clean text stays clean: %r" % text[:46],
           "; ".join("%s=%r" % (n, g) for n, g, _ in hits))

    # 3 + 4 -- the gate refuses, and the same draft without the tell passes. Both directions.
    ck(send_approved._tells_gate(SENT_TO_1591, acked=False) == 1,
       "the gate REFUSES the clause we actually sent to #1591")
    rewritten = SENT_TO_1591.replace("the honest version of", "a truer statement of")
    ck(send_approved._tells_gate(rewritten, acked=False) is None,
       "the same sentence passes once the construction is gone")

    # 5 -- the acknowledgement waives that gate and nothing else
    ck(send_approved._tells_gate(SENT_TO_1591, acked=True) is None,
       "--ack-tells waives it for a human who read the hits")

    # 6 -- END TO END through the shipped CLI, on the refusing path only (it returns before any
    #      subprocess.run, so nothing can be posted). This is what fails if the wiring is reverted.
    with tempfile.TemporaryDirectory() as td:
        draft = pathlib.Path(td) / "draft.md"
        draft.write_text(SENT_TO_1591, encoding="utf-8")
        sha = send_approved.digest(str(draft))
        # --body-file is required: bind_payload refuses any shape that could source a body from
        # somewhere other than the approved bytes. A probe using an unbindable shape refuses at an
        # earlier gate and never reaches the one under test, which is how the first run of this
        # file "passed" its mutation control for the wrong reason.
        argv = ["post", str(draft), "--sha", sha, "--",
                "gh", "issue", "comment", "1", "-R", "example/does-not-exist",
                "--body-file", str(draft)]
        rc, out, attempted = run_cli(argv)
        ck(rc == 1, "end to end: the real CLI refuses these bytes", "rc=%s" % rc)
        ck("read as generated" in out,
           "end to end: it is the TELLS gate refusing, not an earlier one",
           " / ".join(out.strip().splitlines()[:2])[:120])
        ck("the honest version" in out,
           "end to end: the refusal names the construction and its context")
        ck(not attempted, "end to end: no publish was attempted", "attempts=%d" % len(attempted))

    # the mutation this probe exists to catch: unwire the gate and case 6 must stop refusing
    saved = send_approved._tells_gate
    try:
        send_approved._tells_gate = lambda body, acked: None      # the state before 2026-08-23
        with tempfile.TemporaryDirectory() as td:
            draft = pathlib.Path(td) / "draft.md"
            draft.write_text(SENT_TO_1591, encoding="utf-8")
            sha = send_approved.digest(str(draft))
            argv = ["post", str(draft), "--sha", sha, "--",
                    "gh", "issue", "comment", "1", "-R", "example/does-not-exist",
                    "--body-file", str(draft)]
            rc, out, _ = run_cli(argv)
            ck("read as generated" not in out,
               "mutation control: with the gate unwired these bytes are NOT refused for their wording",
               "rc=%s" % rc)
    finally:
        send_approved._tells_gate = saved

    print("== the humanizer gate runs on the send path ==")
    for ok, label, detail in rows:
        print("  %s  %s%s" % ("PASS" if ok else "FAIL", label, ("   [%s]" % detail) if detail else ""))
    bad = sum(1 for ok, _, _ in rows if not ok)
    print("\n  %d checks, %d failed" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
