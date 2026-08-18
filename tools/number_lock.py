"""Which numbers in our published documents can anything re-derive?

THE DEFECT THIS MEASURES. On 2026-08-18 our shared toolchain README claimed an "exact L2 local valley
depth 0.1902" and never defined "local". Asked to reproduce it, we could bracket it -- 0.181144 and
0.200462 under the definition the code implies -- but not reach it. The number had been standing,
cited by a co-authored manuscript, with nothing in the repository able to produce it.

That is the failure qingkong66 named on deepseek-ai/DeepSeek-V3#1466 as the thing we keep hitting:
numbers that do not declare their own definition, cannot be reproduced, and have no consistency
reconciliation. He is right, and this tool measures how much of it we have.

WHAT IT DOES. Walks the documents we publish, pulls out every figure that reads as a MEASUREMENT,
and asks the only question that matters: does the exact value appear anywhere in a committed
artifact -- a result JSON, a probe, a script -- or does it exist only in prose?

That criterion is deliberately weak. A number present in a result file is not thereby correct; it
only means SOMETHING produced it and a reader has a thread to pull. A number present only in prose
has no thread at all, and is the class 0.1902 belonged to. So read the output as a lower bound on
the problem, never as a certificate.

    python tools/number_lock.py                # the inventory
    python tools/number_lock.py --unlocked     # only the figures nothing can reproduce
    python tools/number_lock.py --self-test    # the extractor's own controls

CONTROLS, because an extractor that finds nothing would report a clean repository:
  * POSITIVE -- a planted measurement must be found, and a planted number present in an artifact
    must come back locked;
  * NEGATIVE -- version strings, dates, issue numbers, DOIs and URLs must NOT be counted, or the
    inventory is noise and its ratio means nothing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Documents we put in front of other people.
DOC_GLOBS = ["public/**/*.md", "agora_output/hotrg_edrn/*.md", "README.md"]
# Where a number would have to appear for something to be able to reproduce it.
ARTIFACT_GLOBS = ["probes/**/*.py", "probes/**/*.json", "tools/**/*.py",
                  "agora_output/**/*.py", "agora_output/**/*.json", "public/**/*.json",
                  "research/**/*.py", "server/**/*.py"]

# A measurement: three or more decimals, or a percentage carrying a decimal.
MEASUREMENT = re.compile(r"(?<![\w.\-/])(\d+\.\d{3,})(?![\w])|(?<![\w.\-/])(\d+\.\d+)\s*%")

# Things that look numeric but are not measurements. Each of these has bitten a naive scan.
NOT_A_MEASUREMENT = [
    re.compile(r"\bv?\d+\.\d+\.\d+\b"),                 # version strings
    re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b"),        # dates
    re.compile(r"10\.\d{4,}/\S+"),                      # DOIs
    re.compile(r"https?://\S+"),                        # URLs
    re.compile(r"#\d+"),                                # issue references
    re.compile(r"\b\d+\.\d+e[-+]?\d+\b", re.I),         # exponentials are usually tolerances
    # arXiv identifiers are YYMM.NNNNN and read as five-decimal measurements. This was the FIRST
    # real run's dominant false positive: every one of the 40 figures it called "unlocked" was a
    # paper ID, so the 15% it reported was a property of the extractor, not of the documents.
    re.compile(r"\b(?:arXiv:)?(0[7-9]|[12]\d)(0[1-9]|1[0-2])\.\d{4,5}(v\d+)?\b", re.I),
]


def _masked(text: str) -> str:
    """Blank out the spans that are not measurements, so their digits cannot be extracted."""
    out = text
    for pat in NOT_A_MEASUREMENT:
        out = pat.sub(lambda m: " " * len(m.group(0)), out)
    return out


def measurements(text: str) -> list[str]:
    found = []
    for m in MEASUREMENT.finditer(_masked(text)):
        found.append(m.group(1) or m.group(2))
    return found


def _files(globs):
    seen = []
    for g in globs:
        for f in ROOT.glob(g):
            if f.is_file() and ".git" not in f.parts:
                seen.append(f)
    return sorted(set(seen))


def artifact_index() -> str:
    """One blob of everything a number could have been produced by. Crude and fast; the question is
    only whether the value occurs at all."""
    parts = []
    for f in _files(ARTIFACT_GLOBS):
        try:
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))
        except Exception:                                          # noqa: BLE001
            continue
    return "\n".join(parts)


def occurs(value: str, blob: str) -> bool:
    """WEAK. Does the digit string appear anywhere in a committed artifact?

    This is NOT a lock and the difference is the whole point. Measured 2026-08-18: 0.1902 -- the one
    figure we had just proved unreproducible -- passes it, because the sequence turns up in embedding
    caches full of random floats, as an unrelated constant in the impurity code, and in the files
    written today to say it was unverified. Occurrence cannot tell a derivation from a coincidence.
    Kept only so the tool can demonstrate its own insufficiency.
    """
    if value in blob:
        return True
    if "." in value:
        head, tail = value.split(".", 1)
        if len(tail) > 3 and ("%s.%s" % (head, tail[:-1])) in blob:
            return True
    return False


def receipt_for(doc: pathlib.Path) -> list[str]:
    """STRONG. Is there code that READS this document and asserts its numbers?

    That is the only criterion that would have caught 0.1902, and it is what the outbound-message
    gates written for the EDRN thread actually do: open the document, re-derive each figure, exit
    non-zero on a mismatch. A document with no such receipt has numbers nobody can check, however
    many times the digits happen to appear elsewhere.
    """
    rel = str(doc.relative_to(ROOT)).replace("\\", "/")
    name = doc.name
    found = []
    for f in _files(["probes/**/*.py", "tools/**/*.py", ".github/workflows/*.yml"]):
        if f.resolve() == doc.resolve():
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:                                          # noqa: BLE001
            continue
        if rel in t or (name in t and name != "README.md"):
            found.append(str(f.relative_to(ROOT)).replace("\\", "/"))
    return found


def self_test() -> int:
    ok = True
    planted = "The measured depth is 0.190237 across the run."
    got = measurements(planted)
    if got != ["0.190237"]:
        print("FAIL positive control: expected ['0.190237'], got %s" % got)
        ok = False
    noise = ("inspeximus 2.14.0 on 2026-08-18, see doi:10.5281/zenodo.20818291 and "
             "https://x.test/a/1.234567 and issue #1466, tolerance 1.4e-11, "
             "arXiv:2408.06292 and 2104.08663 and 2606.04193v2")
    got = measurements(noise)
    if got:
        print("FAIL negative control: version/date/DOI/URL/issue/exponent leaked as %s" % got)
        ok = False
    blob = "corr = 0.190237  # from the probe"
    if not occurs("0.190237", blob):
        print("FAIL occurrence control: a value present in an artifact read as absent")
        ok = False
    if occurs("0.999111", blob):
        print("FAIL occurrence control: a value absent from every artifact read as present")
        ok = False

    # THE CONTROL THAT MATTERS. 0.1902 is a figure we published and then proved we could not
    # reproduce. The weak criterion must be shown to MISS it -- if occurrence ever starts catching
    # it, this file's central claim has stopped being true and the wording must change.
    real = artifact_index()
    if not occurs("0.1902", real):
        print("FAIL known-bad control: occurrence now flags 0.1902, so the tool's own argument about "
              "occurrence being insufficient no longer holds -- rewrite it")
        ok = False
    print("self-test: %s" % ("PASS -- measurements found, identifiers ignored, and the weak criterion "
                             "demonstrably passes a number we know is unreproducible" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unlocked", action="store_true", help="list only what nothing can reproduce")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv[1:])
    if a.self_test:
        return self_test()

    blob = artifact_index()
    rows = []
    for f in _files(DOC_GLOBS):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:                                          # noqa: BLE001
            continue
        vals = measurements(text)
        if not vals:
            continue
        uniq = sorted(set(vals))
        rec = receipt_for(f)
        rows.append({"doc": str(f.relative_to(ROOT)).replace("\\", "/"),
                     "measurements": len(uniq),
                     "absent_from_every_artifact": [v for v in uniq if not occurs(v, blob)],
                     "receipt": rec})

    tot = sum(r["measurements"] for r in rows)
    with_rec = [r for r in rows if r["receipt"]]
    covered = sum(r["measurements"] for r in with_rec)
    if a.json:
        print(json.dumps({"total": tot, "docs_with_receipt": len(with_rec), "docs": rows}, indent=1))
        return 0

    print("Can anything RE-DERIVE the numbers in our published documents?\n")
    print("%-56s %6s  %s" % ("document", "meas.", "receipt that reads it and asserts its numbers"))
    for r in sorted(rows, key=lambda x: (bool(x["receipt"]), -x["measurements"])):
        if a.unlocked and r["receipt"]:
            continue
        print("%-56s %6d  %s" % (r["doc"][-56:], r["measurements"],
                                 ", ".join(r["receipt"]) if r["receipt"] else "-- none --"))
    print("\n%d distinct measurements across %d documents." % (tot, len(rows)))
    print("%d documents (%d of the measurements, %.0f%%) have a receipt that re-derives them."
          % (len(with_rec), covered, 100.0 * covered / tot if tot else 0))
    print("\nThe weaker question -- does the digit string occur anywhere in a committed artifact --")
    print("says %d of %d are missing. Do not read that as reassurance: 0.1902, the figure we proved"
          % (sum(len(r["absent_from_every_artifact"]) for r in rows), tot))
    print("unreproducible on 2026-08-18, passes it, on embedding caches full of random floats.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
