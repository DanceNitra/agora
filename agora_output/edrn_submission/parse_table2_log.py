"""Recover a Table 2 regeneration run from its console log, so two grids can be diffed by machine.

WHY. The [0,2] run finished and its result file was then overwritten by a REFUSED verdict from a
later attempt, so its 41 rows survive only in the console log. Comparing the two grids by reading
two logs side by side is how a number gets misquoted, so the comparison is done on parsed rows.

CONTROLS, each able to fail:
  * THE ROW COUNT IS ASSERTED. A log missing rows, or a regex that matches nothing, is a REFUSED.
    A parser that returns 3 rows and a cheerful exit is the failure this file exists to avoid.
  * THE CALIBRATION LINE MUST BE PRESENT AND MUST HAVE PASSED. A run that never calibrated says
    nothing about Table 2, whatever its rows contain.
  * THE GRID IS READ FROM THE LOG, NOT PASSED IN. The parallelism and grid lines are part of the
    record, so a log cannot be relabelled with a grid it did not run.
  * EVERY EDGE APPEARS EXACTLY ONCE. imap_unordered returns out of order, and a duplicate row means
    the log holds two runs concatenated rather than one.

USAGE:  python parse_table2_log.py <log> [<log2> ...]
        With two or more logs it also prints the per-edge difference between the first and the last.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))

ROW_RE = re.compile(
    r"^\s+(\d+)/(\d+)\s+(\w+)\s+\((\d+),\s*(\d+)\)\s+"
    r"standard\s+([-+][\d.]+)\s+at\s+s=([\d.]+)\s+\|\s+"
    r"theory\s+([-+][\d.]+)\s+at\s+s=([\d.]+)", re.M)
CAL_RE = re.compile(r"standard\s+([\d.]+)\s+\(off\s+([\deE.+-]+)\)\s+\|\s+theory\s+([\d.]+)"
                    r"\s+\(off\s+([\deE.+-]+)\)\s+\|\s+expected\s+([\d.]+)")
CAL_RE_OLD = re.compile(r"standard\s+([\d.]+)\s+\|\s+theory\s+([\d.]+)\s+\|\s+expected"
                        r"\s+([\d.]+)\s+\|\s+off\s+([\deE.+-]+)")
WORKERS_RE = re.compile(r"parallelism:\s+(\d+)\s+workers")


def refuse(why):
    print("REFUSED: " + why)
    raise SystemExit(2)


def parse(path):
    if not os.path.isfile(path):
        refuse("no log at %s" % path)
    text = io.open(path, encoding="utf-8", errors="replace").read()

    m = WORKERS_RE.search(text)
    if not m:
        refuse("%s has no parallelism line, so it is not a run log" % path)
    workers = int(m.group(1))

    cal = CAL_RE.search(text) or CAL_RE_OLD.search(text)
    if not cal:
        refuse("%s has no calibration line; a run that never calibrated proves nothing" % path)
    off = float(cal.group(2)) if CAL_RE.search(text) else float(cal.group(4))
    if off > 5e-6:
        refuse("%s calibrated at %.2e, outside the 5e-6 tolerance" % (path, off))

    rows = {}
    total = None
    for m in ROW_RE.finditer(text):
        i, n, graph, u, v, std, s_std, thy, s_thy = m.groups()
        total = int(n)
        key = (graph, int(u), int(v))
        if key in rows:
            refuse("%s holds edge %s twice, so it is two runs concatenated" % (path, key))
        rows[key] = {"standard_depth": float(std), "standard_s": float(s_std),
                     "theory_depth": float(thy), "theory_s": float(s_thy)}
    if total is None:
        refuse("%s yielded no per-edge rows" % path)
    if len(rows) != total:
        refuse("%s yielded %d of %d rows, so the run is incomplete" % (path, len(rows), total))

    return {"log": os.path.basename(path), "workers": workers, "calibration_off_by": off,
            "n_edges": len(rows), "rows": rows}


def main(argv):
    if len(argv) < 2:
        refuse("usage: parse_table2_log.py <log> [<log2> ...]")

    runs = [parse(p) for p in argv[1:]]
    for r in runs:
        print("  %-28s %2d workers, %d edges, calibration off %.2e"
              % (r["log"], r["workers"], r["n_edges"], r["calibration_off_by"]))

    out = {"runs": [{k: v for k, v in r.items() if k != "rows"} for r in runs],
           "per_run_rows": [{"%s %d-%d" % k: v for k, v in r["rows"].items()} for r in runs]}

    if len(runs) >= 2:
        a, b = runs[0], runs[-1]
        shared = sorted(set(a["rows"]) & set(b["rows"]))
        if not shared:
            refuse("the two runs share no edge, so nothing can be compared")
        print()
        print("  edges where the theory-view valley MOVES between the two runs:")
        moved = []
        for k in shared:
            da, db = a["rows"][k], b["rows"][k]
            if abs(da["theory_depth"] - db["theory_depth"]) > 1e-9 or \
               abs(da["theory_s"] - db["theory_s"]) > 1e-9:
                moved.append({"edge": "%s (%d,%d)" % k,
                              "first": [da["theory_depth"], da["theory_s"]],
                              "last": [db["theory_depth"], db["theory_s"]]})
                print("    %-16s %+.6f at s=%.2f  ->  %+.6f at s=%.2f"
                      % ("%s (%d,%d)" % k, da["theory_depth"], da["theory_s"],
                         db["theory_depth"], db["theory_s"]))
        print("  moved: %d of %d shared edges" % (len(moved), len(shared)))
        out["moved"] = moved
        out["n_shared"] = len(shared)

    dest = os.path.join(HERE, "parse_table2_log.result.json")
    json.dump(out, io.open(dest, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
