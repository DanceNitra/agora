"""Point the residue scanner at inspeximus itself, because we sell erasure certificates.

WHY THIS EXISTS. On 2026-08-30 we spent a day measuring whether ChromaDB keeps a deleted document's
text on disk. It does, until its write-ahead log is purged, and that turned out to be documented
behaviour already filed by somebody else. The lesson worth keeping is the one a red-team raised
against us rather than against Chroma: we ship `forget`, `forget_subject` and a signed erasure
certificate, and we had never run the byte scanner against our OWN store. A vendor that publishes an
erasure product and has not scanned itself is making a claim it did not check, whoever else is worse.

WHAT IT TESTS, on a real store built by the shipped library:

  A  forget(key=...)          the ordinary delete
  B  forget_subject(...)      the right-to-erasure path we advertise, including lineage
  C  a copy of the directory  what a backup, a snapshot, or a handed-over laptop actually is

For each, the question is the same one we asked Chroma: after the API says it is gone, is the text
still in the bytes, and is it in a LIVE row or in space the engine has not reclaimed?

CONTROLS, because a scan that cannot see the store reports clean and looks like good news:

  * POSITIVE, before any erasure: the value MUST be found. If it is not, the scanner is blind here and
    every later "clean" is an artefact of the harness rather than a property of the store.
  * NEGATIVE: a value never written must not be found.
  * KEPT: a record we did NOT erase must still be found afterwards, or the run proves only that the
    store was emptied.

An honest bad result here is worth more than a good one, so the verdict names what was found rather
than summarising it away.

Run: python probes/does_our_own_store_keep_what_it_says_it_erased.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus, scan_residue                     # noqa: E402

ERASED = "Zoltan-Kovacs-1974-03-11-patient-QX7K2M9V"
SUBJECT_SECRET = "Ingrid-Vasquez-1961-08-02-patient-LP4T8B3W"
KEPT = "Bartholomew-Nkemdirim-1988-12-05-patient-RW9F2H6C"
NEVER = "Persephone-Achterberg-1955-04-19-patient-TK3M7Q1X"


def _scan(root, value):
    r = scan_residue(root, [value], skip_dirs=set())
    return [{"kind": f["kind"], "path": f["path"], "table": f.get("table"),
             "column": f.get("column")} for f in r["findings"]]


def run() -> dict:
    out = {"measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "steps": {}, "controls": {}, "problems": []}
    root = tempfile.mkdtemp(prefix="inspeximus_selfscan_")
    store_dir = os.path.join(root, "store")
    os.makedirs(store_dir)
    path = os.path.join(store_dir, "memory.json")

    m = Inspeximus(path=path, receipts=True)
    ids = {}
    ids["a"] = m.remember("the patient record is %s" % ERASED, key="patient-a", object=ERASED)
    ids["a2"] = m.remember("a second note about %s" % ERASED, key="patient-a-note")
    m.remember("subject record %s" % SUBJECT_SECRET, key="patient-b",
               source={"doc": "dsar://patient-b"})
    m.remember("this one stays: %s" % KEPT, key="patient-c")
    m.flush()

    out["controls"]["positive_before_erasure"] = _scan(store_dir, ERASED)
    if not out["controls"]["positive_before_erasure"]:
        out["problems"].append(
            "POSITIVE CONTROL FAILED: the value is not visible before erasure, so this scan cannot see "
            "our store and any later 'clean' is the harness, not the product")
        out["verdict"] = "CONTROL_FAILED"
        shutil.rmtree(root, ignore_errors=True)
        return out

    # ------------------------------------------------------------------ A: the ordinary delete
    forgot = m.forget(ids=[ids["a"], ids["a2"]])
    m.flush()
    out["steps"]["forget_by_key"] = {"reported": forgot, "residue": _scan(store_dir, ERASED)}

    # ------------------------------------------------------------------ B: the advertised erasure path
    try:
        res = m.forget_subject("dsar://patient-b")
        m.flush()
        out["steps"]["forget_subject"] = {"reported": res if isinstance(res, (int, dict)) else str(res),
                                          "residue": _scan(store_dir, SUBJECT_SECRET)}
    except Exception as e:
        out["problems"].append("forget_subject raised %s: %s" % (type(e).__name__, e))
        out["steps"]["forget_subject"] = {"error": type(e).__name__}

    # ------------------------------------------------------------------ controls after the fact
    out["controls"]["kept_is_still_there"] = bool(_scan(store_dir, KEPT))
    out["controls"]["never_written_is_absent"] = not _scan(store_dir, NEVER)
    if not out["controls"]["kept_is_still_there"]:
        out["problems"].append(
            "CONTROL FAILED: a record we did not erase is also gone, so this run shows an emptied store "
            "rather than a working erasure")
    if not out["controls"]["never_written_is_absent"]:
        out["problems"].append("CONTROL FAILED: a value never written was found, so the scanner matches "
                               "anything")

    # ------------------------------------------------------------------ C: a copy of the directory
    copy = os.path.join(root, "backup")
    shutil.copytree(store_dir, copy)
    out["steps"]["directory_copy"] = {"erased_by_key": _scan(copy, ERASED),
                                      "erased_subject": _scan(copy, SUBJECT_SECRET)}

    residue = (out["steps"]["forget_by_key"]["residue"]
               + (out["steps"].get("forget_subject", {}).get("residue") or []))
    live = [f for f in residue if f["kind"] == "LIVE"]
    if out["problems"]:
        out["verdict"] = "CONTROL_FAILED"
    elif live:
        out["verdict"] = "OUR_OWN_STORE_RETAINS_IN_LIVE_ROWS"
    elif residue:
        out["verdict"] = "UNRECLAIMED_ONLY"
    else:
        out["verdict"] = "GONE_FROM_DISK"
    out["reader_note"] = (
        "GONE_FROM_DISK is the only result that supports selling an erasure certificate without a "
        "caveat. UNRECLAIMED_ONLY means the record is logically gone and its bytes linger in space the "
        "file format has not reused, which is the same class we reported about somebody else and must "
        "be disclosed in the same words. Anything LIVE is retention and is ours to fix before we "
        "describe erasure anywhere.")
    shutil.rmtree(root, ignore_errors=True)
    return out


if __name__ == "__main__":
    res = run()
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("\nwrote", p)
