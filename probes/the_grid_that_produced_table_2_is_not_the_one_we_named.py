"""Which of the scans in Li Guanghao's archive produced Table 2, measured rather than argued.

WHY. On 2026-09-03 at 16:07 UTC we told him his Section 4.5 grid statement had to read 41 points
over s in [0,2]. His own item 5 said 61 points over s in [0,3], step 0.05. One of us is wrong and
the manuscript sentence gets rewritten either way, so this settles it from his files.

THE TEST. His archive holds several per-edge scans with different grids. Only one of them can be the
source of Table 2, and Table 2 carries four numbers specific enough to identify it. The probe reads
every script for its declared grid, then asks which data file carries all four numbers.

CONTROLS, each able to fail:
  * EVERY TARGET IS ASSERTED TO EXIST AND TO PARSE. A missing file or a regex that matches nothing
    is a REFUSED, never a quiet zero. That is how a check reports SAFE without seeing its subject.
  * THE CANDIDATES MUST BE DISTINGUISHABLE. If every folder declared the same grid, or if more than
    one data file carried Table 2's numbers, the question cannot be answered from these files and
    the probe says so instead of picking one.
  * A MUTATION. The four-number comparison is re-run against a deliberately wrong expectation and
    must FAIL. A comparison that passes on 0.1051 as readily as on 0.1050 measures nothing.
  * THE CORRECTION TARGET MUST EXIST. The Section 4.5 sentence is located in the manuscript and its
    stated point count is read out, so the planned edit has something to edit.
  * WHAT THIS FILE DOES NOT COVER IS REPORTED. Table 2 has a Ring row; the winning data file may
    hold tree and random only. That is left UNRESOLVED rather than folded into the verdict.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARCHIVE = os.path.join(ROOT, "agora_output", "edrn_submission", "guanghao_archive_2026-09-03")
MANUSCRIPT = os.path.join(ROOT, "agora_output", "edrn_submission", "manuscript.tex")
OUT = os.path.join(HERE, "the_grid_that_produced_table_2_is_not_the_one_we_named.result.json")

TABLE2_ROWS = ("Tree", "Random")


def ascii_safe(text):
    """The console here is cp1250, so a Chinese folder name raises rather than prints."""
    return text.encode("ascii", "backslashreplace").decode("ascii")


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def read(path):
    for enc in ("utf-8", "utf-8-sig", "gbk", "cp1252"):
        try:
            return io.open(path, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    refuse("cannot decode %s in any of four encodings" % path)


def find_files():
    """Return {folder: {'py': [...], 'txt': [...]}} for every scan folder in the archive."""
    if not os.path.isdir(ARCHIVE):
        refuse("the archive is not at %s, so nothing was read" % ARCHIVE)
    found = {}
    for root, _dirs, files in os.walk(ARCHIVE):
        py = [f for f in files if f.endswith(".py")]
        txt = [f for f in files if f.endswith(".txt")]
        if py and txt:
            found[os.path.basename(root)] = {
                "py": [os.path.join(root, f) for f in py],
                "txt": [os.path.join(root, f) for f in txt],
            }
    if len(found) < 2:
        refuse("found %d scan folders holding both a script and a data file; the comparison "
               "needs at least two" % len(found))
    return found


GRID_RE = re.compile(r"linspace\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9]+)\s*\)")


def declared_grids(paths):
    grids = set()
    for p in paths:
        for lo, hi, n in GRID_RE.findall(read(p)):
            grids.add((float(lo), float(hi), int(n)))
    return sorted(grids)


def table2_from_manuscript():
    tex = read(MANUSCRIPT)
    rows = {}
    for name in TABLE2_ROWS:
        m = re.search(r"^%s\s*&(.+?)\\\\" % name, tex, re.M)
        if not m:
            refuse("Table 2 has no row named %r in %s" % (name, MANUSCRIPT))
        cells = [c.strip() for c in m.group(1).split("&")]
        nums = re.findall(r"[0-9]+\.[0-9]+", " ".join(cells[1:4]))
        if len(nums) < 2:
            refuse("row %r yielded %d numbers, expected at least 2: %r" % (name, len(nums), cells))
        rows[name] = {"cells": cells, "numbers": nums}
    return rows


def main():
    folders = find_files()
    print("  archive folders holding a script and a data file: %d" % len(folders))

    report = {}
    for label, paths in folders.items():
        grids = declared_grids(paths["py"])
        blob = "\n".join(read(p) for p in paths["txt"])
        report[label] = {"grids": grids, "blob": blob}
        print("    %-44s grids=%s  data=%d chars" % (ascii_safe(label)[:44], grids, len(blob)))

    if all(not r["grids"] for r in report.values()):
        refuse("no linspace call was found in any script, so no grid was measured")

    tbl = table2_from_manuscript()
    wanted = [tbl["Tree"]["numbers"][0], tbl["Tree"]["numbers"][1],
              tbl["Random"]["numbers"][0], tbl["Random"]["numbers"][1]]
    print("  Table 2 asks for: tree %s / %s, random %s / %s" % tuple(wanted))

    def carries(blob, values):
        return [v for v in values if v in blob]

    verdict = {}
    for label, r in report.items():
        hit = carries(r["blob"], wanted)
        verdict[label] = {"grids": r["grids"], "carries": hit, "n": len(hit)}
        print("    %-44s carries %d of 4: %s" % (ascii_safe(label)[:44], len(hit), hit))

    winners = [k for k, v in verdict.items() if v["n"] == len(wanted)]
    if len(winners) != 1:
        refuse("%d folders carry all four of Table 2's numbers, so this archive cannot say which "
               "grid produced it" % len(winners))
    winner = winners[0]
    losers = [k for k in verdict if k != winner]

    grid_sets = {tuple(v["grids"]) for v in verdict.values()}
    if len(grid_sets) < 2:
        refuse("every folder declares the same grid, so the finding cannot discriminate")

    mutated = list(wanted)
    mutated[2] = wanted[2][:-1] + str((int(wanted[2][-1]) + 1) % 10)
    mut_hit = carries(report[winner]["blob"], mutated)
    if len(mut_hit) == len(mutated):
        refuse("the mutated expectation %r also matched in full, so the comparison does not "
               "discriminate" % mutated)
    print("  mutation control: %r matches %d of 4, so the comparison can fail"
          % (mutated, len(mut_hit)))

    tex = read(MANUSCRIPT)
    m = re.search(r"scanned over \$s\\in\[([^\]]+)\]\$ with ([0-9]+) points", tex)
    if not m:
        refuse("the Section 4.5 grid sentence was not found, so the correction has no target")
    stated = {"range": m.group(1), "points": int(m.group(2))}
    print("  manuscript Sec. 4.5 states: s in [%s] with %d points"
          % (stated["range"], stated["points"]))

    winner_grid = verdict[winner]["grids"]
    print()
    print("  SOURCE OF TABLE 2: %s" % ascii_safe(winner))
    print("  its declared grid: %s" % (winner_grid,))
    for k in losers:
        print("  other candidate:   %-44s %s" % (ascii_safe(k)[:44], verdict[k]["grids"]))

    ring_missing = "ring" not in report[winner]["blob"].lower()

    json.dump({
        "script": os.path.basename(__file__),
        "verdict": "MEASURED",
        "table2_numbers_sought": wanted,
        "per_folder": {k: {"grids": v["grids"], "carries": v["carries"]}
                       for k, v in verdict.items()},
        "source_of_table2": winner,
        "grid_that_produced_table2": winner_grid,
        "manuscript_section_4_5_states": stated,
        "unresolved": {
            "ring_row_not_in_this_file": bool(ring_missing),
            "note": "Table 2 has a Ring row; check whether the winning data file covers it.",
        },
        "controls": {
            "every_target_asserted_to_exist_and_parse": True,
            "candidates_declare_different_grids": True,
            "mutated_expectation_failed": len(mut_hit) < len(mutated),
            "correction_target_located_in_manuscript": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
