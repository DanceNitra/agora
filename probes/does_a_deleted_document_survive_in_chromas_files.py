"""Does a document Chroma reports as deleted survive in the bytes on disk?

THE QUESTION, and it is somebody else's open dispute rather than ours. chroma-core/chroma#3793,
"Document deletion leaves plain text and embeddings in db", was closed as fixed by PR #4884 in June
2025. In July 2025 a user replied on the closed issue that it still happens on chromadb/chroma:1.0.15.
Nobody answered. The thread cannot settle itself, because every participant is reading the API, and the
API is the thing under suspicion: `delete()` returning success is a statement about rows, not about
bytes.

Answering it needs a byte-level read of the store directory, which is what `inspeximus.scan_residue`
does and what the only comparable tool, rimironenko/rag-staleness-check, explicitly does not: it checks
retrievability by id and by top-k query, both through the client.

WHAT A HONEST ANSWER HAS TO SEPARATE, because the difference decides whether this is a vendor defect
at all:

  LIVE         a live SQLite row still holds the text. The system retained it. This is retention.
  UNRECLAIMED  the bytes are in the file but in no live row. SQLite does not zero a freed page, so the
               record is gone logically and lingers physically until VACUUM. This is a property of the
               storage engine, NOT a vendor's choice, and reporting it as retention is the overclaim
               that gets a report dismissed.
  PLAIN        a non-SQLite file (a WAL sidecar, a log, an index segment) still contains it.

The original issue names `embeddings_queue`, Chroma's write-ahead log, so the table a finding lands in
is part of the answer and not a detail.

THE CONTROLS, because a scan that cannot see the store reports "clean" and looks like good news:

  * POSITIVE CONTROL, run BEFORE the delete: the value must be FOUND. A scanner pointed at the wrong
    directory, or defeated by an encoding, returns exactly the same "clean" as a genuinely erased
    store. Without this the whole measurement is unfalsifiable, and the run aborts if it fails.
  * NEGATIVE CONTROL: a value that was never inserted must NOT be found, or the scanner matches
    anything and every finding is noise.
  * VACUUM ARM: after an explicit VACUUM, UNRECLAIMED bytes must go while LIVE rows stay. This is what
    separates "the engine has not compacted yet" from "the system kept your data", and it is the arm
    that decides whether any finding is Chroma's to fix.

Run: python probes/does_a_deleted_document_survive_in_chromas_files.py
Writes: does_a_deleted_document_survive_in_chromas_files.result.json beside this file.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")
from inspeximus import scan_residue                                  # noqa: E402

# A value that cannot occur naturally, so any hit is ours and any miss is a real absence.
SENTINEL = "Zoltan-Kovacs-1974-03-11-patient-QX7K2M9V"
NEVER_INSERTED = "Ingrid-Vasquez-1961-08-02-patient-LP4T8B3W"
DIM = 8


def _embedding(seed: float):
    return [seed + i * 0.01 for i in range(DIM)]


def _scan(root, value):
    """Byte-level scan, with every directory included: a store's residue lives exactly in the places a
    default skip list drops."""
    return scan_residue(root, [value], skip_dirs=set())


def _kinds(report):
    out = {}
    for f in report["findings"]:
        out.setdefault(f["kind"], []).append(
            {"path": f["path"], "table": f.get("table"), "column": f.get("column"), "rows": f.get("rows")})
    return out


def _sqlite_files(root):
    hits = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            try:
                with open(p, "rb") as fh:
                    if fh.read(16).startswith(b"SQLite format 3"):
                        hits.append(p)
            except OSError:
                pass
    return hits


def run() -> dict:
    import chromadb

    version = getattr(chromadb, "__version__", "unknown")
    root = tempfile.mkdtemp(prefix="chroma_residue_")
    store = os.path.join(root, "store")
    result = {"chromadb_version": version, "python": sys.version.split()[0],
              "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "sentinel_length": len(SENTINEL), "steps": {}, "controls": {}, "problems": []}

    client = chromadb.PersistentClient(path=store)
    try:
        col = client.get_or_create_collection("residue_probe", embedding_function=None)
    except TypeError:
        col = client.get_or_create_collection("residue_probe")

    col.add(ids=["doc-1"], documents=[SENTINEL], embeddings=[_embedding(0.10)])
    col.add(ids=["doc-2"], documents=["an unrelated document that stays"], embeddings=[_embedding(0.90)])

    # -------------------------------------------------------------- POSITIVE CONTROL, before any delete
    before = _scan(store, SENTINEL)
    result["controls"]["positive_before_delete"] = {
        "found": bool(before["findings"]), "kinds": _kinds(before),
        "checked_files": before["checked_files"]}
    if not before["findings"]:
        result["problems"].append(
            "POSITIVE CONTROL FAILED: the value was not found even before the delete, so this scan "
            "cannot see Chroma's store and every later 'clean' would be an artefact of the harness")
        result["verdict"] = "CONTROL_FAILED"
        shutil.rmtree(root, ignore_errors=True)
        return result

    # -------------------------------------------------------------- the delete under test
    col.delete(ids=["doc-1"])
    result["steps"]["api_reports_deleted"] = "doc-1" not in (col.get(ids=["doc-1"]).get("ids") or [])

    after_open = _scan(store, SENTINEL)
    result["steps"]["while_client_open"] = {"found": bool(after_open["findings"]),
                                            "kinds": _kinds(after_open)}

    # Close the client so nothing is merely unflushed. A finding that survives this is on disk in the
    # state another process, a backup, or a disk handed to somebody else would see.
    try:
        client = None
        del col
    except Exception:
        pass
    time.sleep(0.5)

    after = _scan(store, SENTINEL)
    result["steps"]["after_client_closed"] = {
        "found": bool(after["findings"]), "kinds": _kinds(after),
        "checked_files": after["checked_files"], "ok": after["ok"]}

    # -------------------------------------------------------------- NEGATIVE CONTROL
    neg = _scan(store, NEVER_INSERTED)
    result["controls"]["negative_never_inserted"] = {"found": bool(neg["findings"])}
    if neg["findings"]:
        result["problems"].append(
            "NEGATIVE CONTROL FAILED: a value never inserted was found, so the scanner matches "
            "anything and no finding here means what it says")

    # -------------------------------------------------------------- VACUUM ARM: engine, or retention?
    vacuumed = []
    for db in _sqlite_files(store):
        try:
            con = sqlite3.connect(db)
            con.execute("VACUUM")
            con.close()
            vacuumed.append(os.path.relpath(db, store))
        except Exception as e:
            result["problems"].append("could not VACUUM %s: %s" % (os.path.basename(db), type(e).__name__))
    after_vacuum = _scan(store, SENTINEL)
    result["controls"]["vacuum_arm"] = {
        "vacuumed": vacuumed, "found": bool(after_vacuum["findings"]),
        "kinds": _kinds(after_vacuum)}

    # -------------------------------------------------------------- verdict
    kinds_after = _kinds(after)
    live = kinds_after.get("LIVE") or []
    plain = kinds_after.get("PLAIN") or []
    unreclaimed = kinds_after.get("UNRECLAIMED") or []
    survives_vacuum = bool(after_vacuum["findings"])

    if live:
        verdict = "RETAINED_IN_LIVE_ROWS"
    elif plain and survives_vacuum:
        verdict = "RETAINED_OUTSIDE_SQLITE"
    elif (unreclaimed or plain) and not survives_vacuum:
        verdict = "UNRECLAIMED_ONLY"
    elif not after["findings"]:
        verdict = "GONE_FROM_DISK"
    else:
        verdict = "MIXED"
    result["verdict"] = verdict
    result["summary"] = {
        "live_rows": live, "plain_files": plain, "unreclaimed": unreclaimed,
        "survives_vacuum": survives_vacuum}
    shutil.rmtree(root, ignore_errors=True)
    return result


if __name__ == "__main__":
    res = run()
    out = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("\nwrote", out)
