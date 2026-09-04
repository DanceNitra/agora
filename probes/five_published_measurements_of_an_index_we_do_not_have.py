"""Every measurement of "our index" we published on claude-code#91188, against the file itself.

WHAT HAPPENED. Between 1 and 4 September we posted five measurements of our own memory index to
anthropics/claude-code#91188, as pm25coder. They form a coherent series, 15 lines to 20 to 21, each
introduced as a fresh measurement ("Re-measured on our side just now", "Measured ours this
afternoon"). None of them describes the file we keep, which held 208 to 221 lines and 26,000 to
28,384 bytes across the same days.

The series also contradicts itself. On 1 September the index was "nearly ASCII but not pure (10
non-ASCII characters)" at 1.010 bytes per unit. On 3 September the same index was "CJK-flavored"
and by 4 September 1.269 bytes per unit, with an explicit claim that nothing structural had
changed. Our real index is 1.005.

WHY THIS FILE EXISTS. A correction naming five errors has to enumerate them from the live comments
rather than from anyone's account of them, and it has to compare each with a measurement of the
file taken now. Otherwise the correction is one more assertion in the same series.

CONTROLS:
  * EVERY PUBLISHED FIGURE IS FETCHED FROM ITS COMMENT. If a quoted figure is not in the comment
    the correction attributes it to, the run refuses.
  * THE GROUND TRUTH COMES FROM DATED BACKUPS that bracket each claim, so "the real file was
    different" is anchored in time and not only in today's state.
  * THE SEARCH THAT FINDS NOTHING MUST FIND SOMETHING. It has to locate the current index by its
    own byte and line count before any "no file matches" verdict counts.
"""
from __future__ import annotations

import datetime
import glob
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "five_published_measurements_of_an_index_we_do_not_have.result.json")
MEM = os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory")
REPO = "anthropics/claude-code"

# (comment id, date, the figures it published, the strings that must appear in it)
PUBLISHED = [
    ("5495840695", "2026-09-01", {"lines": 15, "bytes": 2081},
     ["15 lines, 2081 bytes"]),
    ("5498341230", "2026-09-01", {"lines": 15, "bytes": 2090, "units": 2070, "upl": 138.0,
                                  "bpu": 1.010},
     ["15 lines | 2,090 UTF-8 bytes | 2,070 UTF-16 units", "138.0 units/line"]),
    ("5522927403", "2026-09-03", {"lines": 15, "units": 2070, "upl": 138.0},
     ["138 u/l (2,070 units / 15 lines)"]),
    ("5533605446", "2026-09-03", {"lines": 20, "units": 6768},
     ["6,768 units", "20 lines"]),
    ("5538716005", "2026-09-04", {"lines": 21, "bytes": 11132, "units": 8774, "upl": 417.8,
                                  "bpu": 1.269},
     ["11,132 UTF-8 bytes", "8,774 UTF-16 units", "417.8 units per line", "1.269"]),
]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def measure(path):
    raw = io.open(path, "rb").read()
    t = raw.decode("utf-8", errors="replace")
    u = sum(2 if ord(c) > 0xFFFF else 1 for c in t)
    lines = t.count("\n") + (0 if t.endswith("\n") else 1)
    return {"lines": lines, "bytes": len(raw), "units": u, "bpu": len(raw) / u,
            "upl": u / lines, "crlf": t.count("\r\n"),
            "non_ascii": sum(1 for c in t if ord(c) > 127),
            "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(" ")[:16]}


def main():
    live = os.path.join(MEM, "MEMORY.md")
    if not os.path.isfile(live):
        refuse("no memory index at %s" % live)
    now = measure(live)
    hist = sorted((dict(measure(p), path=os.path.basename(p))
                   for p in glob.glob(os.path.join(MEM, "MEMORY.md.bak-*"))),
                  key=lambda m: m["mtime"])
    if len(hist) < 5:
        refuse("only %d dated backups, too few to bracket the claims in time" % len(hist))

    print("  the file itself")
    print("     now            %3d lines  %6d B  %6d units  %.3f b/u  %6.1f u/l  %d non-ascii"
          % (now["lines"], now["bytes"], now["units"], now["bpu"], now["upl"], now["non_ascii"]))
    for h in hist[-3:]:
        print("     %s  %3d lines  %6d B  %6d units  %.3f b/u  %6.1f u/l"
              % (h["mtime"][:10], h["lines"], h["bytes"], h["units"], h["bpu"], h["upl"]))
    print()

    rows = []
    for cid, day, figs, must in PUBLISHED:
        raw = subprocess.run(["gh", "api", "repos/%s/issues/comments/%s" % (REPO, cid)],
                             capture_output=True, text=True, encoding="utf-8").stdout
        if not raw:
            refuse("could not fetch comment %s; a correction must quote the live comments" % cid)
        body = json.loads(raw).get("body", "")
        for token in must:
            if token not in body:
                refuse("comment %s does not contain %r, so the correction would misquote us"
                       % (cid, token))
        # the backup nearest in time, so the comparison is anchored to that day
        near = min(hist, key=lambda h: abs(
            (datetime.datetime.fromisoformat(h["mtime"])
             - datetime.datetime.fromisoformat(day + " 12:00")).total_seconds()))
        row = {"comment": cid, "date": day, "published": figs,
               "nearest_backup": near["mtime"], "actual_lines": near["lines"],
               "actual_bytes": near["bytes"], "actual_bpu": near["bpu"],
               "line_ratio": near["lines"] / figs["lines"]}
        rows.append(row)
        print("  comment %s  %s" % (cid, day))
        print("     published %s" % ", ".join("%s=%s" % (k, v) for k, v in figs.items()))
        print("     the file  %d lines, %d bytes, %.3f b/u  (backup %s)"
              % (near["lines"], near["bytes"], near["bpu"], near["mtime"]))
        print("     lines off by a factor of %.1f" % row["line_ratio"])

    if min(r["line_ratio"] for r in rows) < 5:
        refuse("at least one published line count is within a factor of 5 of the real file, so "
               "'none of them describes our index' is too strong")

    # the search, with its control
    cands = []
    for dp, dn, fn in os.walk(os.path.expanduser("~")):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        for f in fn:
            if f.lower().startswith("memory") and f.lower().endswith(".md"):
                p = os.path.join(dp, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    cands.append(dict(measure(p), path=p))
                except Exception:
                    continue
    if not any(c["bytes"] == now["bytes"] and c["lines"] == now["lines"] for c in cands):
        refuse("the search cannot find the current index by its own figures, so any 'no match' "
               "below would only mean the search is blind")
    matches = [c for c in cands
               for _cid, _d, f, _m in PUBLISHED
               if "bytes" in f and abs(c["bytes"] - f["bytes"]) <= 400
               and abs(c["lines"] - f["lines"]) <= 2]
    # HIGH RATIO IS NOT THE SAME AS AN INDEX. Seven files here exceed 1.15 bytes per unit and not
    # one is a memory index: three are pages of a vendor's Chinese documentation, two are vault
    # notes, two are synthetic fixtures our own probes wrote. A draft claimed "no memory index has
    # bytes per unit above 1.15" and this count is what showed the claim was stated too widely.
    high_bpu = [c for c in cands if c["bpu"] > 1.15]
    # AN INDEX IS DEFINED BY WHERE IT LIVES, not by its name. The first version of this filter
    # tested the basename only, so a vendor's `memory.md` documentation page counted as a memory
    # index and this control refused the whole run. That refusal was correct: the filter was wrong,
    # and it would have shipped a sentence claiming no index here has a high ratio while one
    # apparently did.
    def is_index(path):
        norm = path.replace("\\", "/")
        return (os.path.basename(path).upper() in ("MEMORY.MD", "MEMORY_ARCHIVE.MD")
                and "/.claude/projects/" in norm and "/memory/" in norm
                and "scratchpad" not in norm and "/Temp/" not in norm)

    real_index = [c for c in high_bpu if is_index(c["path"])]
    print()
    print("  searched %d files named memory*.md under the profile" % len(cands))
    print("  CONTROL: it finds the current index by its own byte and line count")
    print("  files matching any published pair of figures: %d" % len(matches))
    print("  files above 1.15 bytes per unit: %d, of which real memory indexes: %d"
          % (len(high_bpu), len(real_index)))
    for c in high_bpu:
        print("     %.3f  %s" % (c["bpu"], c["path"][-70:]))
    if real_index:
        refuse("%d of them IS a real memory index, so the correction cannot say the character-set "
               "story has no candidate here" % len(real_index))

    print()
    print("  VERDICT: five published measurements, none within a factor of %.0f of the file."
          % min(r["line_ratio"] for r in rows))
    print("  Scope: this machine, now, plus its dated backups. It cannot speak for a file that")
    print("  lived elsewhere or has since been deleted.")

    json.dump({"script": os.path.basename(__file__), "now": now,
               "history_tail": hist[-4:], "claims": rows,
               "files_searched": len(cands), "matches": len(matches),
               "files_above_bpu_1_15": len(high_bpu),
               "real_indexes_above_bpu_1_15": len(real_index),
               "high_bpu_paths": [c["path"] for c in high_bpu],
               "worst_line_ratio": max(r["line_ratio"] for r in rows),
               "best_line_ratio": min(r["line_ratio"] for r in rows),
               "verdict": "NONE_OF_THE_FIVE_DESCRIBES_OUR_INDEX",
               "controls": {"every_figure_fetched_from_its_comment": True,
                            "ground_truth_from_dated_backups": True,
                            "search_finds_the_current_file": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print()
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
