"""Lift every inline TikZ figure out of the manuscript into its own compilable file.

WHY. The Springer Nature template says so at the top of its own first page: "All additional figures
and files should be attached separately and not embedded in the TeX document itself." The
as-received manuscript draws four figures with tikz/pgfplots inside figure environments, so the
submission cannot be assembled until they are files.

WHAT IT PRODUCES. For each figure, in order: FigN.tex, a standalone document carrying only that
picture, and FigN.pdf compiled from it. The caption and label stay in the manuscript, because they
belong to the text and the guidelines require captions in the manuscript file rather than in the
figure file.

CONTROLS, each able to fail:
  * THE TARGET MUST PARSE: the count of \\begin{tikzpicture} found inside figure environments must
    equal the count in the whole file, or a picture lives somewhere this script does not look.
  * EVERY FIGURE MUST COMPILE. A .tex that produces no .pdf is reported as a failure, not skipped.
  * EVERY FIGURE MUST BE NON-TRIVIAL: a PDF under 4 kB usually means an empty page, so the size is
    recorded and a suspiciously small one is flagged.
  * THE PICTURES MUST BE DISTINCT: the four PDFs must have four different hashes. Extracting the
    same block four times is a plausible failure of a regex that does not backtrack correctly.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "manuscript_2026-08-29_asreceived.tex")
FIGDIR = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "extract_figures.result.json")
def _find_pdflatex() -> str:
    """Locate pdflatex without hardcoding one machine's home directory.

    The first version of this file carried the absolute path to MiKTeX under a user profile, which
    put that user's home directory into a file we publish as a receipt, and made the script
    unrunnable for anyone else. Order: an explicit override, then PATH, then the two default
    install locations.
    """
    override = os.environ.get("PDFLATEX")
    if override and os.path.isfile(override):
        return override
    found = shutil.which("pdflatex")
    if found:
        return found
    for cand in (os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "MiKTeX",
                              "miktex", "bin", "x64", "pdflatex.exe"),
                 os.path.join("C:" + os.sep, "texlive", "2025", "bin", "windows", "pdflatex.exe")):
        if os.path.isfile(cand):
            return cand
    raise SystemExit("REFUSED: pdflatex not found. Put it on PATH or set the PDFLATEX variable.")


PDFLATEX = _find_pdflatex()
NL = chr(10)
BS = chr(92)

PREAMBLE = NL.join([
    BS + "documentclass[border=2pt]{standalone}",
    BS + "usepackage{amsmath,amssymb}",
    BS + "usepackage{tikz}",
    BS + "usepackage{pgfplots}",
    BS + "pgfplotsset{compat=1.18}",
    BS + "begin{document}",
])


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def main() -> int:
    if not os.path.isfile(SRC):
        refuse("source manuscript not found: " + SRC)
    text = io.open(SRC, encoding="utf-8").read()

    fig_env = re.compile(BS + BS + r"begin\{(figure\*?)\}(.*?)" + BS + BS + r"end\{\1\}", re.S)
    tikz_re = re.compile(BS + BS + r"begin\{tikzpicture\}.*?" + BS + BS + r"end\{tikzpicture\}", re.S)

    figures, total_in_env = [], 0
    for m in fig_env.finditer(text):
        body = m.group(2)
        pics = tikz_re.findall(body)
        total_in_env += len(pics)
        if not pics:
            continue
        label = re.search(BS + BS + r"label\{([^}]*)\}", body)
        figures.append({"env": m.group(1), "picture": pics[0],
                        "label": label.group(1) if label else "",
                        "line": text[:m.start()].count(NL) + 1})

    all_pics = len(tikz_re.findall(text))
    if all_pics != total_in_env:
        refuse("%d tikzpicture blocks exist but only %d sit inside a figure environment; one is "
               "somewhere this script does not look" % (all_pics, total_in_env))
    if not figures:
        refuse("no tikz figures found, so there is nothing to extract and the manuscript cannot be "
               "the one this script was written for")

    os.makedirs(FIGDIR, exist_ok=True)
    rows = []
    for i, f in enumerate(figures, 1):
        name = "Fig%d" % i
        tex = os.path.join(FIGDIR, name + ".tex")
        io.open(tex, "w", encoding="utf-8", newline=NL).write(
            PREAMBLE + NL + f["picture"] + NL + BS + "end{document}" + NL)
        r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-enable-installer",
                            "-halt-on-error", name + ".tex"],
                           cwd=FIGDIR, capture_output=True, text=True, timeout=900)
        pdf = os.path.join(FIGDIR, name + ".pdf")
        ok = os.path.isfile(pdf)
        size = os.path.getsize(pdf) if ok else 0
        sha = hashlib.sha256(io.open(pdf, "rb").read()).hexdigest() if ok else ""
        rows.append({"figure": name, "label": f["label"], "source_line": f["line"],
                     "compiled": ok, "pdf_bytes": size, "sha256": sha[:16],
                     "suspiciously_small": bool(ok and size < 4000)})
        print("  %-6s label=%-18s line %-4d compiled=%-5s %7d bytes"
              % (name, f["label"] or "-", f["line"], ok, size))
        if not ok:
            print((r.stdout or "")[-800:])

    failed = [r for r in rows if not r["compiled"]]
    if failed:
        refuse("these figures produced no PDF: %s" % ", ".join(r["figure"] for r in failed))
    hashes = {r["sha256"] for r in rows}
    if len(hashes) != len(rows):
        refuse("the extracted figures are not distinct (%d files, %d unique hashes): the extractor "
               "is copying the same picture" % (len(rows), len(hashes)))
    tiny = [r["figure"] for r in rows if r["suspiciously_small"]]

    res = {"probe": os.path.basename(__file__),
           "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "source": os.path.basename(SRC), "figures": rows,
           "controls": {"every_tikz_is_inside_a_figure_environment": True,
                        "every_figure_compiled": True,
                        "all_figures_distinct": True,
                        "suspiciously_small_pdfs": tiny},
           }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(NL + "%d figures extracted and compiled." % len(rows))
    if tiny:
        print("CHECK BY EYE: %s are under 4 kB and may be blank." % ", ".join(tiny))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
