#!/usr/bin/env python3
"""How many writes after a delete until Chroma's write-ahead log stops holding the deleted text?

Chroma appends a DELETE row to `embeddings_queue` in chroma.sqlite3 and keeps the earlier ADD row, with
the document text, until the HNSW segment persists and the log is purged. The segment persists every
`hnsw:sync_threshold` operations (default 1000). This probe measures the count directly: store a marker
document and a control document, delete the marker, then add filler documents one batch at a time and
read the raw file after each batch until the marker's bytes are gone. It prints the first batch count at
which the bytes left the file, once as the file lies on disk and once after a SQLite VACUUM.

Self-contained: chromadb and the standard library. Embeddings are random and fixed by seed; the residue
under test is the document text, not the vector. Deterministic on chromadb 1.1.1.

    python research/probes/chroma_wal_retention_threshold.py           # thresholds 50 and default
    python research/probes/chroma_wal_retention_threshold.py 50 200    # your own thresholds

Measured 2026-09-17, chromadb 1.1.1, batch size 1: threshold 50 clears after 59 filler adds, the default
after 1020 (after VACUUM in both cases; the raw file clears at the same count). These are the numbers the
Agora post "Your delete() returned OK. Are the bytes still on disk?" cites.
"""
import glob
import os
import random
import sqlite3
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
import chromadb  # noqa: E402

MARK = b"CHROMA-WAL-RETENTION-MARKER-7Q2X"
KEEP = b"CHROMA-WAL-RETENTION-KEEP-7Q2X"
R = random.Random(3)


def rv():
    return [R.random() for _ in range(8)]


def holds(d, needle):
    for f in glob.glob(os.path.join(d, "**", "*"), recursive=True):
        if os.path.isfile(f):
            with open(f, "rb") as fh:
                if needle in fh.read():
                    return True
    return False


def vacuum(d):
    for f in glob.glob(os.path.join(d, "**", "*.sqlite3"), recursive=True):
        c = sqlite3.connect(f); c.execute("VACUUM"); c.commit(); c.close()


def measure(threshold, batch=1, limit=3000):
    d = tempfile.mkdtemp()
    cl = chromadb.PersistentClient(path=d)
    kw = {"metadata": {"hnsw:sync_threshold": threshold}} if threshold else {}
    c = cl.get_or_create_collection("retention", **kw)
    c.add(ids=["m", "k"], embeddings=[rv(), rv()], documents=[MARK.decode(), KEEP.decode()])
    c.delete(ids=["m"])
    if not holds(d, MARK):
        return {"threshold": threshold or "default", "error": "marker not on disk right after the delete; the reader is blind"}
    n, raw_clear, vac_clear = 0, None, None
    while n < limit:
        c.add(ids=[f"f{n + i}" for i in range(batch)], embeddings=[rv() for _ in range(batch)],
              documents=[f"filler {n + i}" for i in range(batch)])
        n += batch
        if raw_clear is None and not holds(d, MARK):
            raw_clear = n
        if raw_clear is not None:
            vacuum(d)
            if not holds(d, MARK):
                vac_clear = n
                break
    control = holds(d, KEEP)
    return {"threshold": threshold or "default", "batch": batch, "raw_file_clears_after": raw_clear,
            "after_vacuum_clears_after": vac_clear, "control_still_present": control}


def main(argv):
    thresholds = [int(a) for a in argv] or [50, None]
    print(f"chromadb {chromadb.__version__}")
    for t in thresholds:
        r = measure(t)
        print(r)
        if r.get("control_still_present") is False:
            print("  CONTROL FAILED: the undeleted document vanished; the measurement is void")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
