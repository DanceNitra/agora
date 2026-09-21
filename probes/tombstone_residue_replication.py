#!/usr/bin/env python3
"""Replicate Tombstone's residue bench (Poojan6216/tombstone @58d57ae, tombstone-erase 0.1.1).

The claim, from the author's README, section "Results":
  1. after a native delete() 92.0 to 100.0 percent of a subject's vectors stay recoverable from
     the index files (chroma 99.8, faiss 92.0, qdrant 100.0, pgvector 94.9; 200 subjects each);
  2. after `tombstone erase` 0.0 percent of the subjects' own records remain.

What this probe does:
  * compares the author's committed `bench/results/residue-latest.json` with our own run of his
    `bench/residue/run_residue.py --backends chroma,faiss,qdrant --subjects 200` (WSL Ubuntu 24.04,
    2026-09-20 to 21, his lockfile, his corpus, his embedder), cell by cell;
  * runs the mechanism check for the one backend that disagreed: a marker record written to a
    Qdrant local-mode store, deleted through the client, then looked for in the store's files, with
    a second, undeleted marker as the control. The answer depends on whether the platform's SQLite
    was built with SQLITE_SECURE_DELETE, which the probe reads from `pragma secure_delete`.

pgvector is not in our run: it needs a Postgres server and the author's bench skips it without one.

Run:  python probes/tombstone_residue_replication.py            (compare only)
      python probes/tombstone_residue_replication.py --marker   (also the Qdrant marker check; needs qdrant-client)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "tombstone"
TOL = 0.02  # a cell agrees when the two residue rates are within two percentage points


def cells(path: Path) -> dict[tuple[str, str], dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {(c["backend"], c["baseline"]): c for c in d["cells"]}


def compare() -> tuple[int, int, list[str]]:
    author = cells(DATA / "author-58d57ae.json")
    ours: dict[tuple[str, str], dict] = {}
    for f in ("ours-chroma.json", "ours-faiss.json", "ours-qdrant.json"):
        ours.update(cells(DATA / f))
    agree = disagree = 0
    lines = []
    for key in sorted(ours):
        a, o = author[key]["physical_residue_rate"], ours[key]["physical_residue_rate"]
        same = abs(a - o) <= TOL
        agree += same
        disagree += not same
        lines.append(f"{key[0]:7s} {key[1]}  ours {o:5.3f}  author {a:5.3f}  {'agree' if same else 'DIFFER'}")
    return agree, disagree, lines


def marker_check() -> dict:
    """Write two marker points to a Qdrant local store, delete one, read the files back."""
    import glob
    import os
    import struct
    import tempfile

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    d = tempfile.mkdtemp()
    c = QdrantClient(path=d)
    c.create_collection("kb", vectors_config=VectorParams(size=8, distance=Distance.COSINE))
    c.upsert("kb", [PointStruct(id=1, vector=[0.7654321] * 8, payload={"t": "MARKER_DELETED_XYZ"}),
                    PointStruct(id=2, vector=[0.1234567] * 8, payload={"t": "MARKER_KEPT_XYZ"})])

    # The vector itself is stored as a pickled numpy array, big-endian float64, so the marker is
    # looked for both as its payload string and as the raw bytes of its first coordinate.
    kill_vec = struct.pack(">d", 0.7654321)
    keep_vec = struct.pack(">d", 0.1234567)

    def found() -> tuple[bool, bool, bool, bool]:
        blob = b"".join(open(f, "rb").read() for f in glob.glob(d + "/**/*", recursive=True) if os.path.isfile(f))
        return (b"MARKER_DELETED_XYZ" in blob, b"MARKER_KEPT_XYZ" in blob, kill_vec in blob, keep_vec in blob)

    before = found()
    c.delete("kb", points_selector=[1])
    del c
    after = found()
    db = glob.glob(d + "/**/storage.sqlite", recursive=True)[0]
    secure = sqlite3.connect(db).execute("pragma secure_delete").fetchone()[0]
    return {"sqlite_version": sqlite3.sqlite_version, "secure_delete": secure,
            "deleted_marker_before": before[0], "deleted_marker_after": after[0],
            "control_marker_before": before[1], "control_marker_after": after[1],
            "deleted_vector_before": before[2], "deleted_vector_after": after[2],
            "control_vector_before": before[3], "control_vector_after": after[3]}


def main() -> int:
    agree, disagree, lines = compare()
    print("\n".join(lines))
    print(f"\n{agree} of {agree + disagree} cells agree within {TOL:.2f}")
    if "--marker" in sys.argv:
        r = marker_check()
        print("\nQdrant local-mode marker check:", json.dumps(r))
        if not (r["control_marker_before"] and r["control_marker_after"] and r["control_vector_before"] and r["control_vector_after"]):
            print("CONTROL FAILED: the undeleted marker is not readable, the scan cannot be trusted")
            return 2
        stays = r["deleted_marker_after"] or r["deleted_vector_after"]
        verdict = "bytes stay after delete" if stays else "bytes are gone after delete (payload and vector)"
        print(f"{verdict}; pragma secure_delete = {r['secure_delete']} (SQLite {r['sqlite_version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
