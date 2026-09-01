"""Does Chroma's own documented maintenance remove the deleted document, and how much writing does it take?

The finding this tests the limits of: after `collection.delete()`, the original ADD record stays in
`embeddings_queue`, carrying the document verbatim in its `metadata` field as `chroma:document`. It
survives VACUUM, eleven later writes, and a client restart, on 1.0.15, 1.1.1 and 1.5.9, with
`automatically_purge` reading true in the store's own configuration.

A maintainer's first two questions are the reason this file exists, and neither is answered by the
finding itself:

  ARM A  DOES IT EVER CLEAR ON ITS OWN? Automatic purging removes queue entries below the sequence id
         every subscriber has consumed, so the row may go once enough activity has moved the log along.
         Eleven writes is a small number. This arm writes 2,000 and re-checks at intervals. Claiming
         "it never clears" from eleven writes would be a claim about the harness.

  ARM B  DOES THE DOCUMENTED REMEDY WORK? Chroma ships `chroma vacuum`, and the cookbook points at
         `chops cleanup-wal`. If the remedy removes the value, the honest report is a gap between the
         default and the remedy, with the command a reader runs today. If it does not, that is a much
         larger finding and needs saying plainly.

Reporting the retention without both arms would hand a maintainer a complaint instead of a fix, and it
would be a complaint they could dismiss in one reply.

Run: python probes/does_chromas_own_remedy_remove_the_deleted_document.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")
from inspeximus import scan_residue                                  # noqa: E402

SENTINEL = "Zoltan-Kovacs-1974-03-11-patient-QX7K2M9V"
DIM = 8
CHECKPOINTS = (100, 300, 500, 600, 700, 800, 900, 1000, 1500, 2000)


def _emb(seed):
    return [seed + (i * 0.001) for i in range(DIM)]


def _hit(store):
    r = scan_residue(store, [SENTINEL], skip_dirs=set())
    return [{"table": f.get("table"), "column": f.get("column")} for f in r["findings"]]


def _collection(client):
    try:
        return client.get_or_create_collection("residue_probe", embedding_function=None)
    except TypeError:
        return client.get_or_create_collection("residue_probe")


def run() -> dict:
    import chromadb
    out = {"chromadb_version": getattr(chromadb, "__version__", "unknown"),
           "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "arm_a_writes": {}, "arm_b_remedy": {}, "problems": []}

    root = tempfile.mkdtemp(prefix="chroma_remedy_")
    store = os.path.join(root, "store")
    client = chromadb.PersistentClient(path=store)
    col = _collection(client)
    col.add(ids=["doc-1"], documents=[SENTINEL], embeddings=[_emb(0.1)])
    if not _hit(store):
        out["problems"].append("POSITIVE CONTROL FAILED: not found before the delete, so this scan is blind")
        out["verdict"] = "CONTROL_FAILED"
        shutil.rmtree(root, ignore_errors=True)
        return out
    col.delete(ids=["doc-1"])
    out["arm_a_writes"]["0"] = _hit(store)

    # ---------------------------------------------------------------- ARM A: does volume clear it?
    written = 0
    for target in (() if os.environ.get("ARM_B_ONLY") else CHECKPOINTS):
        while written < target:
            batch = min(100, target - written)
            col.add(ids=["f-%d" % (written + i) for i in range(batch)],
                    documents=["filler %d" % (written + i) for i in range(batch)],
                    embeddings=[_emb(0.2 + ((written + i) % 500) * 0.001) for i in range(batch)])
            written += batch
        out["arm_a_writes"][str(target)] = _hit(store)
        print("  after %5d writes: %s" % (target, out["arm_a_writes"][str(target)] or "GONE"), flush=True)
        if not out["arm_a_writes"][str(target)]:
            break

    # ---------------------------------------------------------------- ARM B: the documented remedy
    # On a SEPARATE store with no filler, because the first version ran this after the volume arm had
    # already cleared the value: `before` was empty, so "after: GONE" was true of a store that had
    # nothing to remove and said nothing at all about the remedy.
    del col
    client = None
    time.sleep(0.5)
    root_b = tempfile.mkdtemp(prefix="chroma_remedy_b_")
    store = os.path.join(root_b, "store")
    client_b = chromadb.PersistentClient(path=store)
    col_b = _collection(client_b)
    col_b.add(ids=["doc-1"], documents=[SENTINEL], embeddings=[_emb(0.1)])
    col_b.delete(ids=["doc-1"])
    del col_b
    client_b = None
    time.sleep(0.5)
    before = _hit(store)
    if not before:
        out["problems"].append(
            "ARM B could not be set up: the value was already gone before the remedy ran, so this arm "
            "would report a success the remedy did not earn")
    # The `chroma` console script is not always on PATH, and the first version of this arm reported
    # "not tested" because of that alone. The command itself lives in chromadb_rust_bindings, which is
    # importable whenever chromadb is, so drive it there instead of hunting for an executable.
    driver = ("import sys, chromadb_rust_bindings as b; "
              "sys.argv = ['chroma', 'vacuum', '--path', r'%s', '--force']; b.cli(sys.argv)" % store)
    r = subprocess.run([sys.executable, "-c", driver], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)
    out["arm_b_remedy"] = {"ran": True, "exit": r.returncode,
                           "stdout": (r.stdout or "")[-500:], "stderr": (r.stderr or "")[-400:],
                           "before": before, "after": _hit(store)}

    after = out["arm_b_remedy"].get("after")
    if out["arm_a_writes"].get(str(CHECKPOINTS[-1])) == [] and not os.environ.get("ARM_B_ONLY"):
        out["verdict"] = "CLEARED_BY_VOLUME"
    elif out["arm_b_remedy"].get("ran") and after == []:
        out["verdict"] = "ONLY_THE_DOCUMENTED_REMEDY_CLEARS_IT"
    elif out["arm_b_remedy"].get("ran"):
        out["verdict"] = "SURVIVES_THE_DOCUMENTED_REMEDY"
    else:
        out["verdict"] = "REMEDY_NOT_TESTED"
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(root_b, ignore_errors=True)
    return out


if __name__ == "__main__":
    res = run()
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False)[:2500])
    print("\nwrote", p)
