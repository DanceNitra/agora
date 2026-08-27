"""Six honest processes, one store file. Does the store survive, and do the writes land?

THE INCIDENT THIS COMES FROM. Three of this project's own Claude Code hook stores corrupted in ten
days; the main one -- 6 MB, 10,059 records -- was silently dead for two days (the hooks fail open, so
nothing complained). `.claude/settings.json` wires four hooks to `python -m inspeximus.claude_code`,
and Claude Code fires them CONCURRENTLY for parallel tool calls, so "several processes writing one
store" is the normal operating mode of our own dogfood, not an exotic case.

THE MECHANISM. `_save` wrote to a temp named `<store>.tmp` -- one fixed name, shared by every writer
-- then `os.replace`d it. Two processes writing that temp at overlapping offsets produce a BLEND, and
the replace promotes it. The recovered files carry the signature: a valid document, then a second
document's tail, two closing brackets at the end. `_file_sig` cannot help; it is a TOCTOU check read
BEFORE the write, so it detects a competing writer only once that writer has already finished.

WHAT IS MEASURED. Each child opens the store, remembers one record, flushes, 40 times. A watcher
polls the file the whole time. Then:

  tears          -- how often a reader found the store unparseable (0 is the only acceptable number:
                    the loader correctly REFUSES a store it cannot parse, so one tear is a total
                    outage, not a degraded read)
  ok             -- writes that landed, out of 240
  final parses   -- the store is still a store at the end

WHAT WOULD MAKE THE RESULT BAD, stated before running: any tear at all, or a final store that does
not parse. Write LOSS (StoreChangedOnDisk) is a different and acceptable outcome -- the store is
documented single-writer and refusing is the designed behaviour -- but corruption is not.

THE CONTROL that makes the number mean something: the same harness with the OLD write path monkey-
patched back in (fixed temp name, no lock, no fsync). If the old path does not tear here, this probe
is not reproducing the incident and its green result on the new path proves nothing.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "inspeximus-repo"))

WRITERS, ROUNDS = 6, 40


def _legacy_save_patch():
    """Restore the pre-2.10.1 write: one fixed temp name, no lock, no fsync."""
    from inspeximus import core

    def _legacy(path, payload, encoding="utf-8"):
        import pathlib
        tmp = pathlib.Path(str(path) + ".tmp")
        if isinstance(payload, bytes):
            tmp.write_bytes(payload)
        else:
            tmp.write_text(payload, encoding=encoding)
        os.replace(tmp, path)

    core._durable_replace = _legacy

    class _NoLock:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *e):
            return False

    core._StoreLock = _NoLock


def child(path: str, wid: int, legacy: bool, q) -> None:
    if legacy:
        _legacy_save_patch()
    from inspeximus import Inspeximus
    from inspeximus.core import StoreChangedOnDisk

    tally = {"ok": 0, "changed_on_disk": 0, "unparseable": 0, "other": 0}
    for i in range(ROUNDS):
        try:
            ix = Inspeximus(path=path)
        except ValueError as e:
            # The refusing loader. Separate the two reasons it refuses: "cannot parse" is a torn
            # store and a hard outage; anything else is not corruption and must not be scored as it.
            tally["unparseable" if "cannot parse" in str(e) else "other"] += 1
            continue
        except Exception:
            tally["other"] += 1
            continue
        try:
            ix.remember(f"writer {wid} round {i} note", key=f"w{wid}::{i}", mtype="episodic")
            ix.flush()
            tally["ok"] += 1
        except StoreChangedOnDisk:
            tally["changed_on_disk"] += 1
        except Exception:
            tally["other"] += 1
    q.put((wid, tally))


def watcher(path: str, stop, q) -> None:
    """A TEAR is a JSONDecodeError. A PermissionError is not.

    The first version of this counted `except Exception` as a tear, so it scored 6 transient Windows
    "the file is busy while os.replace runs" failures as corruption and declared the fix NOT FIXED --
    a check that cannot tell a torn store from a busy one. The two failures need different verdicts:
    a tear is permanent and kills the store, a busy read succeeds on the next poll.
    """
    polls = torn = busy = 0
    while not stop.is_set():
        polls += 1
        try:
            json.load(open(path, encoding="utf-8"))
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            torn += 1
        except OSError:
            busy += 1
        time.sleep(0.01)
    q.put(("watcher", {"polls": polls, "torn": torn, "busy": busy}))


def run(legacy: bool, seed_store: str) -> dict:
    d = tempfile.mkdtemp()
    path = os.path.join(d, "store.json")
    shutil.copy2(seed_store, path)

    q, stop = mp.Queue(), mp.Event()
    w = mp.Process(target=watcher, args=(path, stop, q))
    w.start()
    kids = [mp.Process(target=child, args=(path, i, legacy, q)) for i in range(WRITERS)]
    t0 = time.time()
    for k in kids:
        k.start()
    for k in kids:
        k.join(timeout=300)
    stop.set()
    w.join(timeout=10)

    tot = {"ok": 0, "changed_on_disk": 0, "unparseable": 0, "other": 0}
    watch = {"polls": 0, "torn": 0, "busy": 0}
    while not q.empty():
        who, t = q.get()
        if who == "watcher":
            watch = t
        else:
            for k, v in t.items():
                tot[k] += v
    try:
        n = len(json.load(open(path, encoding="utf-8")))
        final = f"parses, {n} records"
    except Exception as e:
        final = f"DOES NOT PARSE -- {type(e).__name__}: {e}"
    leftover = [f for f in os.listdir(d) if ".tmp" in f]
    return {"elapsed": round(time.time() - t0, 1), **tot, "watch": watch,
            "final": final, "leftover_tmp": leftover}


def main() -> int:
    seed_dir = tempfile.mkdtemp()
    seed = os.path.join(seed_dir, "seed.json")
    from inspeximus import Inspeximus
    ix = Inspeximus(path=seed)
    for i in range(900):
        ix.remember(f"baseline record {i} with enough text to give the file real size", key=f"b::{i}")
    ix.flush()
    print(f"seed store: {os.path.getsize(seed):,} bytes, 900 records\n")

    out = {}
    for label, legacy in (("CONTROL (pre-2.10.1 write path)", True), ("FIXED (2.10.1)", False)):
        r = run(legacy, seed)
        out[label] = r
        print(f"{label}")
        print(f"  {WRITERS} writers x {ROUNDS} rounds in {r['elapsed']}s")
        print(f"  writes landed        : {r['ok']}/{WRITERS * ROUNDS}")
        print(f"  refused (single-writer): {r['changed_on_disk']}")
        print(f"  TEARS seen by a reader : {r['unparseable']}  "
              f"(watcher: {r['watch']['torn']} torn / {r['watch']['busy']} busy "
              f"of {r['watch']['polls']} polls)")
        print(f"  final store            : {r['final']}")
        print(f"  leftover .tmp          : {r['leftover_tmp'] or 'none'}\n")

    ctl, fix = out["CONTROL (pre-2.10.1 write path)"], out["FIXED (2.10.1)"]
    ctl_tears = ctl["unparseable"] + ctl["watch"]["torn"]
    fix_tears = fix["unparseable"] + fix["watch"]["torn"]
    if not ctl_tears:
        print("INCONCLUSIVE: the control did not tear, so this harness is not reproducing the "
              "incident and the FIXED result proves nothing.")
        verdict = "inconclusive"
    elif fix_tears:
        print(f"NOT FIXED: {fix_tears} tear(s) remain on the new write path.")
        verdict = "not_fixed"
    else:
        print(f"FIXED: {ctl_tears} tears -> 0, and the final store parses.")
        verdict = "fixed"
    json.dump({"verdict": verdict, **out}, open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
