"""Two ways the Chroma residue finding could be an artefact of how it was measured, tested directly.

The sibling probe, does_a_deleted_document_survive_in_chromas_files.py, measures that a document deleted
through the API stays in a live `embeddings_queue` row on 1.0.15, 1.1.1 and 1.5.9. Before that becomes a
claim, two alternative explanations have to be ruled out, and both would have made the finding mine
rather than Chroma's.

  ARM 1  WHAT survives. Chroma writes the delete itself into the write-ahead log, so a hit on
         `embeddings_queue` might be the delete's own record rather than the document that was deleted.
         A tool reporting "your deleted text is still there" when it found only the tombstone of the
         deletion would be the same over-claim we refuse in the other direction. This arm prints the
         surviving row: its operation, its sequence id, and where in the row the value sits.

  ARM 2  WHETHER A LATER WRITE CLEARS IT. `automatically_purge` defaults on for a fresh store, and
         `purge_log()` is called after a submit rather than on a timer. The sibling probe deletes and
         then immediately scans, so it may simply have measured the window before the next write. A
         deployment that keeps writing would then never see this, and the honest claim would shrink to
         "until the next write". This arm adds a document after the delete, and adds ten more, and
         re-scans after each.

  ARM 3  WHETHER REOPENING CLEARS IT. A fresh client may purge on startup.

A negative result in arms 2 or 3 does not kill the finding, it RESIZES it, and the size is the part a
reader needs. Reporting the retention without this test would be stating a property of my harness as a
property of Chroma.

Run: python probes/what_survives_a_chroma_delete_and_does_a_later_write_purge_it.py
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

SENTINEL = "Zoltan-Kovacs-1974-03-11-patient-QX7K2M9V"
DIM = 8


def _emb(seed):
    return [seed + i * 0.01 for i in range(DIM)]


def _scan(root):
    return scan_residue(root, [SENTINEL], skip_dirs=set())


def _found(root):
    r = _scan(root)
    return [{"kind": f["kind"], "table": f.get("table"), "column": f.get("column"), "rows": f.get("rows")}
            for f in r["findings"]]


def _queue_rows(store):
    """Read embeddings_queue directly, so the claim rests on the row rather than on a substring hit."""
    db = os.path.join(store, "chroma.sqlite3")
    if not os.path.exists(db):
        return {"error": "no chroma.sqlite3"}
    con = sqlite3.connect(db)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(embeddings_queue)")]
        rows = []
        for r in con.execute("SELECT * FROM embeddings_queue"):
            row = dict(zip(cols, r))
            carries = {}
            for k, v in row.items():
                if isinstance(v, (bytes, bytearray)):
                    v = v.decode("utf-8", "replace")
                if isinstance(v, str) and SENTINEL in v:
                    carries[k] = v[:200]
            rows.append({"seq_id": row.get("seq_id"), "operation": row.get("operation"),
                         "id": row.get("id"), "carries_sentinel_in": carries})
        return {"columns": cols, "rows": rows}
    finally:
        con.close()


def run() -> dict:
    import chromadb
    version = getattr(chromadb, "__version__", "unknown")
    root = tempfile.mkdtemp(prefix="chroma_arms_")
    store = os.path.join(root, "store")
    out = {"chromadb_version": version,
           "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arms": {}}

    client = chromadb.PersistentClient(path=store)
    try:
        col = client.get_or_create_collection("probe", embedding_function=None)
    except TypeError:
        col = client.get_or_create_collection("probe")

    try:
        cfg = client._server._sysdb._db.config if hasattr(client, "_server") else None
        out["automatically_purge"] = str(cfg.get_parameter("automatically_purge").value) if cfg else "unread"
    except Exception as e:
        out["automatically_purge"] = "unread (%s)" % type(e).__name__

    col.add(ids=["doc-1"], documents=[SENTINEL], embeddings=[_emb(0.10)])
    out["arms"]["before_delete"] = {"findings": _found(store)}

    col.delete(ids=["doc-1"])
    out["arms"]["after_delete"] = {"findings": _found(store)}

    # -------------------------------------------------------------------- ARM 1: what exactly survives
    out["arms"]["what_survives"] = _queue_rows(store)

    # -------------------------------------------------------------------- ARM 2: does a later write purge
    col.add(ids=["doc-2"], documents=["a later, unrelated write"], embeddings=[_emb(0.50)])
    out["arms"]["after_one_more_write"] = {"findings": _found(store)}

    for i in range(10):
        col.add(ids=["bulk-%d" % i], documents=["filler %d" % i], embeddings=[_emb(0.6 + i * 0.01)])
    out["arms"]["after_ten_more_writes"] = {"findings": _found(store)}

    # -------------------------------------------------------------------- ARM 3: does reopening purge
    del col
    client = None
    time.sleep(0.5)
    client2 = chromadb.PersistentClient(path=store)
    try:
        col2 = client2.get_or_create_collection("probe", embedding_function=None)
    except TypeError:
        col2 = client2.get_or_create_collection("probe")
    col2.add(ids=["after-reopen"], documents=["written by a new client"], embeddings=[_emb(0.99)])
    out["arms"]["after_reopen_and_write"] = {"findings": _found(store)}
    out["arms"]["queue_at_end"] = _queue_rows(store)

    still = bool(out["arms"]["after_reopen_and_write"]["findings"])
    carriers = [r for r in (out["arms"]["queue_at_end"].get("rows") or []) if r["carries_sentinel_in"]]
    out["verdict"] = ("SURVIVES_EVERYTHING" if still else "CLEARED_BY_LATER_ACTIVITY")
    out["surviving_rows"] = carriers
    out["reader_note"] = (
        "A row whose operation is the ADD and which still carries the document is retention of the "
        "deleted content. A row that is only the DELETE tombstone is not, and must not be reported as "
        "such." if carriers else "Nothing in the queue carries the value at the end of the run.")
    shutil.rmtree(root, ignore_errors=True)
    return out


if __name__ == "__main__":
    res = run()
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:4000])
    print("\nwrote", p)
