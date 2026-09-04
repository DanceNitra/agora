"""VOID. 417.8 units per line was never our figure, so there was nothing to retract.

CORRECTED 2026-09-04. This probe shipped as `our_published_units_per_line_belongs_to_no_file_here.py`
and opened with "WHAT WE PUBLISHED. anthropics/claude-code#91188, comment 5538716005". Comment
5538716005 was posted by `pm25coder`, resolved from the live GitHub API. It is not our account:
`gh auth status` on this host holds exactly one token, `DanceNitra`.

So the question the file asks, "which file did OUR published 417.8 units per line describe", has a
false subject. The answer "no file on this machine" is trivially true of another person's
measurement of another person's file.

WHAT SURVIVES, and it is the useful half. The measurement of our own index is sound and was run
against dated backups: 221 lines, 28,384 bytes, 28,233 UTF-16 units, 127.8 units per line on
2026-09-04, and 25 snapshots from 17 August spanning 80.2 to 163.6 units per line. That series is
real and re-runnable. Our index sits near the 125 crossover; it is not immune to it.

WHAT DOES NOT SURVIVE. The framing, the sibling `.result.json` verdict, and the retraction built on
top of them, which is parked as `drafts/91188_correction.md.DEAD-false-premise-pm25coder-is-not-us`.

WHY THE FILE STAYS. Commit ff71101 cites it by its old name and repeats the false premise in its own
message. See `probes/who_actually_posted_it_resolved_from_the_live_api.py` for the check that makes
this class of error non-repeatable.

The original docstring follows, unedited.

ORIGINAL, FALSE:

    Which file did our published 417.8 units per line describe?

    WHAT WE PUBLISHED. anthropics/claude-code#91188, comment 5538716005, 2026-09-04 09:48 UTC:

        MEMORY.md, English/CJK index, right now
          21 lines
          11,132 UTF-8 bytes
           8,774 UTF-16 units   (0 astral)
           1.269 bytes per unit
          417.8 units per line
          21 CRLF pairs / 0 LF-only

    and the conclusion drawn from it: "At 417.8 u/l our unit cap binds at ~line 60 and the line cap is
    decoration; no newline convention moves us across 125, so our binding dimension is stable by two
    orders of margin."

    WHY IT MATTERS. The other participant is building an argument on that contrast, that his file sits
    in an unstable band near the 125 crossover while ours is immune. If our index is also in that band,
    the contrast is not there, and our own data supports his claim instead of bounding it.

    WHAT THIS MEASURES, and it is deliberately narrow:
      1. The agora memory index now, raw and with newlines collapsed, because the thread's whole
         subject is that those differ.
      2. Every archived copy of it, which gives a time series rather than the two points he has.
      3. A search of every file named memory*.md under the profile for the published figures.

    THE FIGURES ARE THE CLAIM, so the search has to be able to find a match if one exists. Its control
    is that the SAME search finds the current file by its own figures. Without that, "no file matches"
    would be indistinguishable from a broken search, which is the failure this repository keeps paying
    for.

      * CONTROL A: searching for the current file's own byte count must return the current file.
      * CONTROL B: the archived copies must actually differ from each other, or the "time series" is
        one measurement repeated and says nothing about drift.
      * CONTROL C: the crossover arithmetic is recomputed here, not quoted: 25000 / 200 = 125.
"""
from __future__ import annotations

import datetime
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "our_published_units_per_line_belongs_to_no_file_here.result.json")

MEM = os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory")
PROFILE = os.path.expanduser("~")
LINE_CAP, UNIT_CAP = 200, 25000

# The figures we put in the comment. Every one of them is searched for below.
PUBLISHED = {"lines": 21, "bytes": 11132, "units": 8774, "bpu": 1.269, "upl": 417.8, "crlf": 21}


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def measure(path):
    raw = io.open(path, "rb").read()
    t = raw.decode("utf-8", errors="replace")
    collapsed = t.replace("\r\n", "\n").replace("\r", "\n")
    def units(s):
        return sum(2 if ord(c) > 0xFFFF else 1 for c in s)
    lines = t.count("\n") + (0 if t.endswith("\n") else 1)
    u = units(t)
    return {"path": path, "lines": lines, "bytes": len(raw), "units": u,
            "units_collapsed": units(collapsed),
            "crlf": t.count("\r\n"), "astral": sum(1 for c in t if ord(c) > 0xFFFF),
            "non_ascii": sum(1 for c in t if ord(c) > 127),
            "bpu": len(raw) / u, "upl": u / lines,
            "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(" ")[:16]}


def main():
    live = os.path.join(MEM, "MEMORY.md")
    if not os.path.isfile(live):
        refuse("no memory index at %s, so there is nothing to compare the published figures with"
               % live)
    now = measure(live)
    crossover = UNIT_CAP / LINE_CAP
    if abs(crossover - 125.0) > 1e-9:
        refuse("the crossover recomputes to %.4f, not 125, so every margin below is wrong"
               % crossover)

    print("  our index, now")
    print("     %d lines, %d bytes, %d units raw, %d collapsed, %d CRLF, %d non-ascii, %d astral"
          % (now["lines"], now["bytes"], now["units"], now["units_collapsed"], now["crlf"],
             now["non_ascii"], now["astral"]))
    print("     %.3f bytes per unit, %.1f units per line, crossover %.0f, margin %+.1f"
          % (now["bpu"], now["upl"], crossover, now["upl"] - crossover))
    print("     the unit cap binds at line %.1f; the line cap binds at line %d"
          % (UNIT_CAP / now["upl"], LINE_CAP))

    hist = sorted((measure(p) for p in glob.glob(os.path.join(MEM, "MEMORY.md.bak-*"))),
                  key=lambda m: m["mtime"])
    if len(hist) < 5:
        refuse("only %d archived copies, too few to call anything a time series" % len(hist))
    upls = [h["upl"] for h in hist] + [now["upl"]]
    if max(upls) - min(upls) < 1.0:
        refuse("every copy has the same units per line to within 1.0, so these are one measurement "
               "repeated and say nothing about drift")
    print()
    print("  %d archived copies, %s to %s" % (len(hist), hist[0]["mtime"][:10], now["mtime"][:10]))
    print("     units per line: min %.1f, max %.1f, now %.1f"
          % (min(upls), max(upls), now["upl"]))
    inside = [h for h in hist + [now] if abs(h["upl"] - crossover) <= 10]
    print("     %d of %d snapshots sit within 10 units of the crossover"
          % (len(inside), len(upls)))
    for h in hist[-4:] + [now]:
        print("       %s  %3d lines  %6d B  %6.1f u/l  %+6.1f from crossover"
              % (h["mtime"], h["lines"], h["bytes"], h["upl"], h["upl"] - crossover))

    # THE SEARCH, with its own positive control.
    print()
    cands = []
    for dp, dn, fn in os.walk(PROFILE):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__", "AppData")
                 or dp.count(os.sep) < 4]
        for f in fn:
            if f.lower().startswith("memory") and f.lower().endswith(".md"):
                p = os.path.join(dp, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    cands.append(measure(p))
                except Exception:
                    continue
    print("  searched %d files named memory*.md under the profile" % len(cands))
    if not any(c["bytes"] == now["bytes"] and c["lines"] == now["lines"] for c in cands):
        refuse("the search cannot find the CURRENT index by its own byte and line count, so a "
               "'no match' verdict below would only mean the search is broken")
    print("  CONTROL: the search finds the current index by its own figures")

    def near(c):
        return (abs(c["lines"] - PUBLISHED["lines"]) <= 2
                and abs(c["bytes"] - PUBLISHED["bytes"]) <= 400)
    matches = [c for c in cands if near(c)]
    bpu_match = [c for c in cands if abs(c["bpu"] - PUBLISHED["bpu"]) < 0.02]
    print()
    print("  files within 2 lines and 400 bytes of the published figures: %d" % len(matches))
    print("  files whose bytes-per-unit is within 0.02 of the published 1.269: %d" % len(bpu_match))
    for c in bpu_match[:4]:
        print("     %s" % c["path"][-84:])

    verdict = ("NO_FILE_HERE_MATCHES" if not matches
               else "A_FILE_MATCHES_AFTER_ALL")
    print()
    if matches:
        print("  A file does match. The published figures are not orphaned and this probe's "
              "premise is wrong:")
        for c in matches[:3]:
            print("     %s" % c["path"])
    else:
        print("  VERDICT: no file named memory*.md on this machine carries those figures. Our own")
        print("  index sits %+.1f units from the crossover, not two orders from it."
              % (now["upl"] - crossover))
        print("  Scope, stated rather than implied: this searches THIS machine now. It cannot")
        print("  speak for a file that existed elsewhere or has since been deleted.")

    json.dump({"script": os.path.basename(__file__), "published": PUBLISHED,
               "now": now, "crossover": crossover,
               "margin_now": now["upl"] - crossover,
               "unit_cap_binds_at_line": UNIT_CAP / now["upl"],
               "history": hist, "snapshots": len(upls),
               "upl_min": min(upls), "upl_max": max(upls),
               "within_10_of_crossover": len(inside),
               "files_searched": len(cands), "matches": [c["path"] for c in matches],
               "verdict": verdict,
               "controls": {"search_finds_the_current_file": True,
                            "history_varies": max(upls) - min(upls),
                            "crossover_recomputed": crossover}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print()
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
