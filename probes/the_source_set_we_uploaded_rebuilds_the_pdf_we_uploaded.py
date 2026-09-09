# -*- coding: utf-8 -*-
"""Does the LaTeX source we uploaded to EPJ B rebuild the PDF we uploaded beside it?

The journal requires both: "The submission should include the original source (including all
style files and figures) and a PDF version of the compiled output."
(https://link.springer.com/journal/10051/submission-guidelines, read 2026-09-10)

A source set that is merely present is not the same as a source set that is COMPLETE. This copies
the seven files we uploaded into an empty directory, compiles them there with nothing else in
reach, and requires the rendered text to match the uploaded manuscript.pdf exactly.

THE CONTROL IS THE POINT. Run the same measurement with one figure removed. If that still passes,
the check is reading something other than the source set, and its green means nothing. A guard that
cannot be made to fail has measured nothing.

Byte equality is NOT the criterion and must not be: a PDF carries its creation timestamp and a
document id, so two compiles of one source differ in bytes by construction. The criterion is the
rendered text.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), "agora_output", "edrn_submission")
BIN = os.path.expanduser(r"~\AppData\Local\Programs\MiKTeX\miktex\bin\x64")
PDFLATEX = os.path.join(BIN, "pdflatex.exe")
PDFTOTEXT = os.path.join(BIN, "pdftotext.exe")

# exactly what was uploaded as source, and nothing else
SOURCE_SET = ["manuscript.tex", "sn-jnl.cls", os.path.join("bst", "sn-mathphys-num.bst"),
              "Fig1.pdf", "Fig2.pdf", "Fig3.pdf", "Fig4.pdf"]
PASSES = 3


def _text_of(pdf):
    r = subprocess.run([PDFTOTEXT, pdf, "-"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def build(omit=None):
    """Compile the source set in an empty directory. Returns (ok, text, log)."""
    tmp = tempfile.mkdtemp(prefix="epjb_src_")
    try:
        for rel in SOURCE_SET:
            if omit and os.path.basename(rel) == omit:
                continue
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(PKG, rel), dst)
        log = ""
        for _ in range(PASSES):
            r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "manuscript.tex"],
                               cwd=tmp, capture_output=True, text=True)
            log = r.stdout
        out = os.path.join(tmp, "manuscript.pdf")
        if not os.path.exists(out):
            return False, "", log
        return True, _text_of(out), log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    shipped = _text_of(os.path.join(PKG, "manuscript.pdf"))
    if not shipped:
        sys.exit("cannot read the uploaded manuscript.pdf; the instrument is dead, not the claim")

    ok, rebuilt, log = build()
    undefined = log.count("undefined") if log else -1
    match = ok and rebuilt == shipped

    # CONTROL: the same measurement with Fig1.pdf withheld must NOT pass
    ok_c, rebuilt_c, _ = build(omit="Fig1.pdf")
    control_fires = not (ok_c and rebuilt_c == shipped)

    result = {
        "source_set": SOURCE_SET,
        "passes": PASSES,
        "shipped_text_chars": len(shipped),
        "rebuilt_text_chars": len(rebuilt),
        "undefined_mentions_in_log": undefined,
        "text_identical": match,
        "control_without_Fig1_fails_as_it_must": control_fires,
        "verdict": "PASS" if (match and undefined == 0 and control_fires) else "FAIL",
    }
    with open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
              "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)

    for k, v in result.items():
        print(f"{k}: {v}")
    if result["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
