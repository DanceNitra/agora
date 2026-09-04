"""Re-derive every checkable statement in the #91188 reply from its primary source.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is the skills.

WHY IT LOOKS LIKE THIS. The letter's load-bearing facts come from three places, none of them a note
of mine: the shipped binary, our own published comment in #82056, and the live thread. So the checks
read those, in that order. An earlier version read only our own probe receipt, passed 31 of 31, and
still carried a figure that appears nowhere in the thread it was attributed to.

CONTROLS, each able to fail:
  * EVERY SOURCE MUST RESOLVE. A missing binary, comment or thread is a refusal, not a skip.
  * BEHAVIOUR, NEVER IDENTIFIERS. The same code carried different minified names across 2.1.252 and
    2.1.257 in one evening, so every binary check asserts a CONSTANT or a code SHAPE.
  * EACH ASSERTED STRING IS PAIRED WITH A NEAR MISS THAT MUST BE ABSENT, so a search that matches
    anything at all is caught.
  * THE PUBLISHED NUMBERS ARE CHECKED AGAINST WHAT WE ALREADY SAID IN PUBLIC, not against a local
    receipt, because restating our own figure differently is what costs credibility here.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "drafts", "91188_reply_units.md")
BIN = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "node_modules",
                   "@anthropic-ai", "claude-code", "bin", "claude.exe")
OUT = os.path.join(HERE, "recheck_figures_91188_units.result.json")


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def gh(path: str, jq: str) -> str:
    r = subprocess.run(["gh", "api", path, "--paginate", "--jq", jq],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        refuse("could not read %s: %s" % (path, (r.stderr or "")[:200]))
    return r.stdout


def cli_version() -> str:
    exe = shutil.which("claude.cmd") or shutil.which("claude.exe") or shutil.which("claude")
    if not exe:
        return "unknown"
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True,
                              timeout=120).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    for path, what in ((DRAFT, "draft"), (BIN, "installed CLI binary")):
        if not os.path.isfile(path):
            refuse("%s missing: %s" % (what, path))
    draft = io.open(DRAFT, encoding="utf-8").read()
    flat = " ".join(draft.split())
    data = io.open(BIN, "rb").read()
    ours = gh("repos/anthropics/claude-code/issues/82056/comments",
              '.[] | select(.user.login=="DanceNitra") | .body')
    body = gh("repos/anthropics/claude-code/issues/91188", ".body")
    by_tonydzi = gh("repos/anthropics/claude-code/issues/91188/comments",
                    '.[] | select(.user.login=="tonydzi") | .body')
    by_pm25 = gh("repos/anthropics/claude-code/issues/91188/comments",
                 '.[] | select(.user.login=="pm25coder") | .body')
    thread = body + by_tonydzi + by_pm25
    if len(ours) < 5000 or len(thread) < 5000:
        refuse("a source came back too short to be the real thing (ours=%d thread=%d)"
               % (len(ours), len(thread)))

    checks = []

    def chk(claim, phrase, ok, source):
        present = " ".join(phrase.split()) in flat if phrase else True
        checks.append({"claim": claim, "phrase_in_draft": present, "verified": bool(ok),
                       "source": source})
        print("  %-5s %-54s %s" % ("OK" if (present and ok) else "FAIL", claim, source))

    # --- the code shapes the letter describes, quoted from the shipped bundle ---
    shapes = {
        "the two fractions are declared together": b"ljo=0.8,HUn=0.7",
        "one entry per dimension, bytes": b'dimension:"bytes"',
        "one entry per dimension, lines": b'dimension:"lines"',
        "the picker keeps the largest fraction": b"n.reduce((d,p)=>p.frac>d.frac?p:d)",
        "the byte target is 0.7 of the byte cap": b"targetDesc:Ut(Math.floor(e.byteCap*HUn))",
        "the line target is 0.7 of the line cap": b"Math.floor(e.lineCap*HUn)} lines",
        "the fire gate is 0.8 of the largest fraction": b"return r<ljo?null:o",
        "capDesc renders the line cap as a label": b"capDesc:`${e.lineCap}-line`",
        "the sibling path branches on dimension": b'd.dimension==="bytes"?d.capDesc',
        "the measured value is String.length": b"byteCount:n.length",
        "the config schema accepts a per-index cap": b"promptIndexMaxBytes:A().int().positive()",
        "the caps are 200 and 25000": b"kM=200,MU=25000",
        "the mount config comes from an environment variable":
            b"process.env.CLAUDE_MEMORY_STORES",
        "the READ path compares against the hardcoded caps": b"p=o>kM,w=d>MU",
        "the truncation warning is appended to the loaded content":
            b"> WARNING: ${k}",
    }
    for claim, needle in shapes.items():
        chk(claim, "", needle in data, "in the bundle: %s" % needle.decode()[:44])
    misses = [b"ljo=0.9,HUn=0.6", b'dimension:"graphemes"', b"byteCount:n.byteLength",
              b"kM=201,MU=25001", b"promptIndexMaxLines:A()",
              b"process.env.CLAUDE_MEMORY_CAPS", b"p=o>MU,w=d>kM"]
    chk("CONTROL: near misses are absent", "", not any(m in data for m in misses),
        "absent as expected: %s" % ", ".join(m.decode()[:20] for m in misses))
    chk("the build is named, and so is the one it replaced",
        "I read the same code earlier today on 2.1.252",
        b"Version: 2.1.257" in data and b"Version: 2.1.252" not in data,
        "the binary self-reports 2.1.257")

    # --- the arithmetic the letter states, recomputed rather than recalled ---
    def kb(n):
        """The bundle's own formatter: divide by 1024, one decimal, label KB."""
        return "%.1fKB" % (n / 1024)

    chk("0.7 of 25,000 prints as 17.1KB", "prints as 17.1KB",
        kb(int(25000 * 0.7)) == "17.1KB", "floor(25000*0.7)=17500 -> %s" % kb(17500))
    chk("the byte cap itself prints as 24.4KB", "`24.4KB`", kb(25000) == "24.4KB",
        "25000/1024 -> %s" % kb(25000))
    chk("the fire and target values on the byte cap", "20,000 to fire and 17,500 to aim for",
        int(25000 * 0.8) == 20000 and int(25000 * 0.7) == 17500, "25000 x 0.8 and x 0.7")
    chk("the fire and target values on the line cap", "it is 160 and 140",
        int(200 * 0.8) == 160 and int(200 * 0.7) == 140, "200 x 0.8 and x 0.7")

    # --- our own published figures: the letter must restate them EXACTLY ---
    chk("18 of 32 below the cut", "18 of 32 sat", "18 of 32 (56%) sat below the cut" in ours,
        "quoted from our own #82056 comment")
    chk("the binomial p value", "p = 0.066", "p = 0.066" in ours,
        "our #82056 comment gives p = 0.066")
    chk("3 of 6 sessions still answered", "answered it in 3 of 6", "3 of 6 sessions" in ours,
        "our #82056 comment: answered in 3 of 6 sessions")
    chk("CONTROL: a figure we never published is absent", "",
        "19 of 32" not in ours and "19 of 32" not in draft,
        "a near-miss ratio appears in neither our comment nor the draft")

    # --- the thread: we must not hand people back their own words as news ---
    # NOT "the word is absent": the draft names the unit once, to make a DIFFERENT point about
    # which branch supplies the measured value. What it must not do is re-establish a finding
    # that is already in the thread under our own name. So assert the establishing language is
    # gone and the reference is incidental, with a control that fails if the test is vacuous.
    establishing = ["is not counted in bytes", "code points", "cuts at line", "emoji",
                    "I measured", "fixture", "canary", "established this"]
    echoed = [w for w in establishing if w.lower() in draft.lower()]
    chk("the draft does not re-establish what the thread already carries", "",
        "UTF-16 code units" in thread and not echoed and draft.count("UTF-16") <= 1,
        "tonydzi carried it there today; the draft references the unit once and proves nothing")
    chk("CONTROL: that test can fail", "",
        any(w.lower() in ours.lower() for w in establishing),
        "the establishing words do appear in our own #82056 comment, so the list is not inert")
    asked = "does your ~22KB target come from measured recall quality"
    chk("tonydzi asked it, and the draft says so",
        "@tonydzi asked @niels-roest whether that target", asked in by_tonydzi,
        "the question is in a comment authored by tonydzi")
    chk("the ~22KB target is the issue author's own",
        "@pm25coder answered for his own number",
        "~22KB target for our index" in body
        and "belongs to the issue author, not me" in by_pm25,
        "the figure is in the issue body, and pm25coder disclaims it in the thread")
    chk("CONTROL: the author split is real, not one blob", "",
        asked not in by_pm25 and asked not in body,
        "the question text appears in tonydzi's comment only")
    # Two density figures are quoted back at their authors. Verify catches attribution errors
    # only if the check knows who said what, so these are keyed to the comment author, with a
    # control that fails if the two authors' bodies were ever concatenated into one blob.
    chk("138.0 is pm25coder's own figure", "Your 138.0 and",
        "138.0" in by_pm25 and "138.0" not in by_tonydzi,
        "138.0 appears in pm25coder's comment and not in tonydzi's")
    # NOT "only tonydzi says it": pm25coder quotes the same number back at him, which is why a
    # presence-and-absence test failed here and was right to. The claim is about ORIGIN, so
    # check that tonydzi published it and that pm25coder attributes it to him rather than
    # claiming it.
    chk("117.6 originates with tonydzi, and pm25coder credits him for it",
        "@tonydzi's 117.6",
        "117.6" in by_tonydzi and "your Russian index at 117.6" in by_pm25,
        "tonydzi published it; pm25coder quotes it back as \"your\" index")
    chk("CONTROL: the two figures are not interchangeable", "",
        "138.0" not in by_tonydzi,
        "the other density appears in neither of tonydzi's comments")
    chk("the newest comment was read before sending", "you now both hold second-hand from us",
        "second-hand from here too" in by_pm25,
        "pm25coder's 18:13 comment says he holds the routing point second-hand as well")

    chk("niels-roest already published the 70 per cent himself, so we credit it",
        "the ~70% you read off it", "(~70% of the cap)" in body,
        "his issue body already states the ratio the draft derives")

    chk("the draft carries the caveat we published with those numbers",
        "we measured position and opening, never value",
        "never *value*" in ours, "our #82056 comment states that limit")
    chk("the draft does not re-endorse only-to-telemetry",
        'But "only to telemetry" is wrong',
        "only to telemetry" in by_tonydzi,
        "tonydzi wrote it, and the draft corrects it rather than agreeing")

    # --- the letter's own boundaries, which a later edit must not quietly drop ---
    recipe = [b"ljo=0.8,HUn=0.7", b"kM=200,MU=25000", b"p=o>kM,w=d>MU"]
    chk("the draft hands the reader a command instead of a link",
        "`grep -a` on your own `claude` binary",
        all(t in data for t in recipe),
        "all three strings the command names are in the binary")
    # A LINK A READER CANNOT OPEN IS WORSE THAN NO LINK. We have published probe paths that
    # 404, so this does not check that a URL is present: it FETCHES it from main and requires
    # a 200. The paired control fetches a sibling path that must NOT exist, so a fetcher that
    # returns 200 for everything is caught.
    import urllib.request

    def live(url):
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "agora-probe"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            refuse("could not reach raw.githubusercontent.com to check the cited link: %r" % e)

    RAW = "https://raw.githubusercontent.com/DanceNitra/agora/main/probes/"
    cited = live(RAW + "recheck_figures_91188_units.py")
    ghost = live(RAW + "recheck_figures_91188_units_NOT_A_FILE.py")
    chk("the cited probe resolves on main",
        "https://github.com/DanceNitra/agora/blob/main/probes/recheck_figures_91188_units.py",
        cited == 200, "raw main returns %s for the cited path" % cited)
    chk("CONTROL: the fetcher can say no", "", ghost == 404,
        "a sibling path that does not exist returns %s" % ghost)
    chk("the read method is disclosed", "by string search rather than traced in a debugger", True,
        "stated as a limit")
    chk("the sample is scoped", "One private store on Windows", True, "stated as a limit")
    chk("AI assistance is disclosed", "Written with AI assistance", True, "owner rule, permanent")

    # --- the constraint that a real send already broke once ---
    chk("pure ASCII, no dash that gh can mangle", "",
        all(ord(c) < 128 for c in draft), "every character is ASCII")

    bad = [c for c in checks if not (c["phrase_in_draft"] and c["verified"])]
    json.dump({"probe": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "draft": "drafts/91188_reply_units.md",
               "draft_bytes": len(draft.encode("utf-8")),
               "cli_version": cli_version(),
               "checks": len(checks), "failed": len(bad), "rows": checks,
               "controls": {"sources_resolve": True,
                            "near_miss_strings_absent_from_binary": True,
                            "reads_the_binary_our_comment_and_the_thread": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed." % (len(checks), len(bad)))
    for c in bad:
        print("  FAILED: %s | phrase: %s | verified: %s"
              % (c["claim"], c["phrase_in_draft"], c["verified"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
