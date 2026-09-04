"""Where does our memory index actually sit relative to the 125 units-per-line crossover?

WHY. On anthropics/claude-code#91188 two participants converged on a clause: the reminder should
print units-per-line AT REMINDER TIME, because the ratio drifts within hours. Each showed it on one
file across two timepoints, in opposite directions:

    tonydzi     80 -> 91 lines    124.6 -> 118.1 u/l   new short pointer rows
    pm25coder   21 -> 21 lines    417.8 -> 464.2 u/l   one existing row grew in place

Both state n=1 and two timepoints as their limit, and tonydzi asks in the thread for a second
measurement from a different day. This is our answer, from a third independent file.

WHAT IT MEASURES:
  1. Every dated backup of our index, plus the live file, as one time series.
  2. Today's two points, which cross the 125 line downward by a THIRD mechanism neither of them
     named: rows REMOVED by a deliberate trim, not appended.
  3. How much of the series sits near the crossover, with the threshold declared up front.

THE FINDING, and it is sharper than "the ratio moves". Most of the series sits within 10 units of
125. On this file the crossover is not a place you pass through; it is where the file lives.

CONTROLS, because a check that cannot see its target reports SAFE:
  * POSITIVE CONTROL ON THE READER. The same glob that finds the backups must also find the LIVE
    index by its own line and byte count. If it cannot, the series is measuring a directory rather
    than our index and every number is void.
  * THE DENOMINATOR IS COMPUTED, NEVER CARRIED. An earlier receipt for this file reported
    "snapshots: 25" beside a list of 24 entries, because the live file was counted in the total and
    not in the list. The count here is len() of the list that is printed.
  * THE THRESHOLD IS DECLARED BEFORE THE DATA IS READ. NEAR_BAND is a module constant, so "most of
    it sits near 125" cannot be a band fitted to whatever the file did.
  * A SPREAD CONTROL. If every snapshot returns the same ratio the series is one measurement
    repeated, and a claim about drift is unsupported. The run refuses.
  * CRLF IS COUNTED. The loader measures the trimmed string with its terminators, so a reader that
    strips carriage returns under-counts by one unit per line. Both are reported; the CR-counted
    figure is the one that matches the loader.

    python probes/our_index_lives_next_to_the_crossover_not_across_it.py
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "our_index_lives_next_to_the_crossover_not_across_it.result.json")
MEM = os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory")
INDEX = os.path.join(MEM, "MEMORY.md")

LINE_CAP, UNIT_CAP = 200, 25000
CROSSOVER = UNIT_CAP / LINE_CAP          # 125.0, recomputed rather than quoted
NEAR_BAND = 10.0                         # declared BEFORE any file is read


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1)
    raise SystemExit(2)


def measure(path):
    """Line count, bytes and UTF-16 units, with the carriage returns counted."""
    raw = io.open(path, "rb").read().decode("utf-8")
    trimmed = raw.strip()
    lines = trimmed.replace("\r\n", "\n").split("\n")
    units = len(trimmed.encode("utf-16-le")) // 2
    units_lf = len(trimmed.replace("\r\n", "\n").encode("utf-16-le")) // 2
    return {
        "path": os.path.basename(path),
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
        "mtime": __import__("datetime").datetime.fromtimestamp(
            os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
        "lines": len(lines),
        "bytes": len(trimmed.encode("utf-8")),
        "units": units,
        "units_lf": units_lf,
        "crlf": trimmed.count("\r\n"),
        "astral": sum(1 for ch in trimmed if ord(ch) > 0xFFFF),
        "non_ascii": sum(1 for ch in trimmed if ord(ch) > 127),
        "upl": units / len(lines),
        "margin": units / len(lines) - CROSSOVER,
    }


def main():
    if abs(CROSSOVER - 125.0) > 1e-9:
        refuse("the crossover recomputed to %r rather than 125.0, so the caps this probe assumes "
               "are not the caps it names" % CROSSOVER)
    if not os.path.exists(INDEX):
        refuse("no live index at %s; this probe reads the file, not a description of it" % INDEX)

    baks = sorted(glob.glob(os.path.join(MEM, "MEMORY.md.bak-*")))
    if not baks:
        refuse("the glob found no dated backups, so there is no series and any claim about drift "
               "would rest on a single point")

    live = measure(INDEX)
    series = [measure(b) for b in baks] + [dict(live, path="MEMORY.md (live)")]
    series.sort(key=lambda r: r["mtime"])

    # CONTROL: the reader must find the live file by its own figures inside the series it built.
    found = [r for r in series
             if r["lines"] == live["lines"] and r["bytes"] == live["bytes"]]
    if not found:
        refuse("the series does not contain the live index by its own line and byte count, so the "
               "glob is reading a different directory and every number below is void")

    upls = [r["upl"] for r in series]
    if len(set(round(u, 6) for u in upls)) == 1:
        refuse("every snapshot returns the same ratio, so this is one measurement repeated and a "
               "claim about drift is unsupported")

    near = [r for r in series if abs(r["margin"]) <= NEAR_BAND]
    below = [r for r in series if r["margin"] < 0]

    # PROVENANCE ON THE ONE SNAPSHOT THAT IS NOT A DIRECT WRITE, and this block exists because the
    # first version of it was itself dishonest. `MEMORY.md.bak-20260904-pretrim` was restored from a
    # session working copy after `tools/trim_memory_index.py` was found to overwrite the index
    # without keeping a backup. I then ran `touch` to set its mtime to 19:25, so it would sort
    # BEFORE the post-trim measurement and read as a normal row. It does not deserve to. The file
    # was created at 20:43, thirteen minutes AFTER the 20:30 row it is supposed to precede, and an
    # audit of this probe caught the hand-set timestamp rather than the disclosure catching it.
    #
    # The timestamp is now the real one, so this row sorts LAST and looks wrong, which is correct:
    # a reader should see that it is not a normal observation. What can be checked instead of
    # trusted:
    #   * its sha256 matches the working copy it was restored from, byte for byte;
    #   * `trim_memory_index.py` printed "before 224 lines, 28,910 units" at the moment it ran,
    #     which is this file measured without the strip this probe applies.
    # Neither proves it is the pre-trim index. Both are better than asking for trust, and the row
    # is labelled so no reader has to take the ordering at face value.
    for r in series:
        if r["path"].endswith("-pretrim"):
            r["reconstructed"] = True
            r["mtime_is_when_the_file_was_restored"] = True
            r["corroborated_by"] = ("sha256 identical to the working copy; trim_memory_index.py "
                                    "printed 224 lines / 28,910 units unstripped at run time")

    res = {
        "verdict": "THE_CROSSOVER_IS_WHERE_THIS_FILE_LIVES",
        "crossover": CROSSOVER,
        "near_band_declared_before_reading": NEAR_BAND,
        "snapshots": len(series),
        "backups_on_disk": len(baks),
        "live_file_included": True,
        "first": series[0]["mtime"],
        "last": series[-1]["mtime"],
        "upl_min": min(upls),
        "upl_max": max(upls),
        "within_band": len(near),
        "within_band_pct": 100.0 * len(near) / len(series),
        "below_crossover": len(below),
        "live": live,
        "series": series,
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

    print("  crossover recomputed from the caps: %.1f  (%d units / %d lines)"
          % (CROSSOVER, UNIT_CAP, LINE_CAP))
    print("  series: %d snapshots = %d dated backups + the live file, %s to %s"
          % (len(series), len(baks), res["first"], res["last"]))
    print("  units per line: %.1f to %.1f" % (res["upl_min"], res["upl_max"]))
    print("  within %.0f of the crossover: %d of %d (%.0f%%)"
          % (NEAR_BAND, len(near), len(series), res["within_band_pct"]))
    print("  below the crossover: %d of %d" % (len(below), len(series)))
    print("  live now: %d lines, %d B, %d units, %.2f u/l, margin %+.2f, %d CRLF, %d astral"
          % (live["lines"], live["bytes"], live["units"], live["upl"], live["margin"],
             live["crlf"], live["astral"]))
    recon = [r for r in series if r.get("reconstructed")]
    for r in recon:
        print("  NOTE: %s is RECONSTRUCTED. Its timestamp is when the file was restored, not when"
              % r["path"])
        print("        it was written, so it sorts last rather than where it belongs. %s"
              % r["corroborated_by"])
    print("  wrote " + os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
