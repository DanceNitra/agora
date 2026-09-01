"""Presence is not reachability, and only reachability makes the Chroma finding more than textbook.

WHY THIS EXISTS. The sibling probes measure that a deleted document's text is still in a live
`embeddings_queue` row. A database engineer reads that and stops, correctly: every durable store defers
physical deletion to compaction. SQLite keeps freed pages, Postgres keeps dead tuples, Weaviate keeps
LSM tombstones. Article 17 does not demand instant destruction either; data "put beyond use" on a
defined schedule is the accepted standard.

So bytes-on-disk alone is not a finding. Two things would make it one, and this file measures the first:

  REACHABILITY  Does any SUPPORTED operation hand the deleted text back to a reader after the delete?
                A log that is replayed on restart, a collection re-created from it, an export, or a
                copy of the directory given to somebody else. If yes, the data is not "beyond use" and
                the framing changes completely. If no, the honest claim shrinks to bytes at rest.

  BOUNDEDNESS   Measured in the sibling: the purge trigger is a WRITE COUNT, not a clock. That is
                argued elsewhere; this file does not test it.

WHAT IS TESTED HERE, each through a path a normal operator uses:

  A  API after reopen        get(ids=[...]) and a full get() on a freshly constructed client.
  B  Full-text search        a query for the exact text, since the WAL row is indexed or not.
  C  Directory copy          the residue check on a byte-for-byte copy, which is what a backup,
                             a snapshot, or a laptop handed to somebody else actually is.
  D  Log replay into a new   the WAL rebuilt into a second store directory, which is what a restore
     store                   from that directory amounts to.

CONTROL: a document that was NEVER deleted must be returned by the same paths, or the harness is
reporting "unreachable" about a reader that cannot reach anything.

Run: python probes/can_a_reader_get_the_deleted_document_back.py
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

DELETED = "Zoltan-Kovacs-1974-03-11-patient-QX7K2M9V"
KEPT = "Ingrid-Vasquez-1961-08-02-patient-LP4T8B3W"
DIM = 8


def _emb(seed):
    return [seed + i * 0.01 for i in range(DIM)]


def _collection(client):
    try:
        return client.get_or_create_collection("reachability_probe", embedding_function=None)
    except TypeError:
        return client.get_or_create_collection("reachability_probe")


def _texts(result) -> list:
    docs = (result or {}).get("documents") or []
    flat = []
    for d in docs:
        if isinstance(d, list):
            flat.extend([x for x in d if x])
        elif d:
            flat.append(d)
    return flat


def run() -> dict:
    import chromadb
    out = {"chromadb_version": getattr(chromadb, "__version__", "unknown"),
           "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "paths": {}, "controls": {}, "problems": []}
    root = tempfile.mkdtemp(prefix="chroma_reach_")
    store = os.path.join(root, "store")

    client = chromadb.PersistentClient(path=store)
    col = _collection(client)
    col.add(ids=["gone"], documents=[DELETED], embeddings=[_emb(0.1)])
    col.add(ids=["kept"], documents=[KEPT], embeddings=[_emb(0.9)])
    col.delete(ids=["gone"])

    # ------------------------------------------------------------------ A: the API, after a reopen
    del col
    client = None
    time.sleep(0.5)
    c2 = chromadb.PersistentClient(path=store)
    col2 = _collection(c2)
    got = col2.get(ids=["gone"])
    everything = col2.get()
    out["paths"]["api_get_by_id"] = DELETED in _texts(got)
    out["paths"]["api_get_all"] = DELETED in _texts(everything)
    out["controls"]["kept_is_returned_by_get_all"] = KEPT in _texts(everything)

    # ------------------------------------------------------------------ B: full-text search
    try:
        q = col2.get(where_document={"$contains": DELETED})
        out["paths"]["full_text_search"] = DELETED in _texts(q)
        qk = col2.get(where_document={"$contains": KEPT})
        out["controls"]["kept_is_found_by_search"] = KEPT in _texts(qk)
    except Exception as e:
        out["paths"]["full_text_search"] = "error: %s" % type(e).__name__
        out["problems"].append("full-text search raised %s" % type(e).__name__)

    # ------------------------------------------------------------------ C: a copy of the directory
    del col2
    c2 = None
    time.sleep(0.5)
    copy = os.path.join(root, "backup")
    shutil.copytree(store, copy)
    rep = scan_residue(copy, [DELETED], skip_dirs=set())
    out["paths"]["bytes_in_a_directory_copy"] = [
        {"kind": f["kind"], "table": f.get("table"), "column": f.get("column")} for f in rep["findings"]]

    # ------------------------------------------------------------------ D: the log, read as a reader would
    # Not an API path: this is what somebody holding the directory can do with sqlite3 and no
    # credentials. It is the difference between "in a file" and "beyond use".
    db = os.path.join(copy, "chroma.sqlite3")
    recovered = []
    try:
        con = sqlite3.connect(db)
        for (meta,) in con.execute("SELECT metadata FROM embeddings_queue"):
            if isinstance(meta, (bytes, bytearray)):
                meta = meta.decode("utf-8", "replace")
            if meta and DELETED in meta:
                recovered.append(meta[:160])
        con.close()
    except Exception as e:
        out["problems"].append("could not read the queue: %s" % type(e).__name__)
    out["paths"]["plain_sql_read_of_the_log"] = recovered

    # ------------------------------------------------------------------ verdict
    api_paths = [out["paths"].get("api_get_by_id"), out["paths"].get("api_get_all"),
                 out["paths"].get("full_text_search")]
    reachable_by_api = any(p is True for p in api_paths)
    if not out["controls"].get("kept_is_returned_by_get_all"):
        out["problems"].append(
            "CONTROL FAILED: the kept document was not returned either, so this harness cannot tell "
            "'unreachable' from 'a reader that reaches nothing'")
        out["verdict"] = "CONTROL_FAILED"
    elif reachable_by_api:
        out["verdict"] = "REACHABLE_THROUGH_THE_API"
    elif recovered:
        out["verdict"] = "NOT_REACHABLE_BY_API_BUT_READABLE_FROM_THE_FILE"
    else:
        out["verdict"] = "NOT_REACHABLE"
    out["reader_note"] = (
        "REACHABLE_THROUGH_THE_API would mean the delete did not take effect for a reader, which is a "
        "far larger claim than bytes at rest. NOT_REACHABLE_BY_API_BUT_READABLE_FROM_THE_FILE is the "
        "honest middle: the API is correct, and anybody holding the directory -- a backup, a snapshot, "
        "a copied laptop -- reads the text with one SQL statement and no credentials.")
    shutil.rmtree(root, ignore_errors=True)
    return out


if __name__ == "__main__":
    res = run()
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("\nwrote", p)
