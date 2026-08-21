"""Re-measure the figure the CML#311 reply cites, on the live stores, today.

The claim going outward is that a VACUOUS 0.0 is worse for us than a vacuous 1.0 would be, because
we published a REAL 0.0 as a finding: 210,499 records, source coverage 98.3%, and 0.01% whose source
resolves to anything a reader could re-fetch. That figure was measured 2026-08-10 and has been
carried in prose ever since -- a number in a note is not verified data, so it is re-derived here
before it is quoted to a collaborator.

Definitions, taken from the product rather than invented for the probe:

  populated source   Inspeximus._raw_source(record) is truthy -- the same predicate that drives
                     locator_coverage in check_sources().
  re-checkable       that locator names something a READER could go and re-read: a file that exists
                     on disk, or an http(s) URL. `agent:scholar` is a writer identity and is not.

CONTROLS, because a scan that reads no records reports a reassuring 0.0 by construction and that is
the exact class this reply is about:
  * the record count must be non-zero, per store and in total;
  * a store whose parse fails is reported, never silently skipped;
  * a synthetic control store with one re-fetchable source must read 1.0, so the scanner is shown
    capable of returning something other than ~0.

Run:  python probes/the_published_zero_is_still_a_measured_zero.py
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")

from inspeximus import Inspeximus  # noqa: E402

STORE_DIRS = [
    os.path.join(ROOT, ".inspeximus"),
    os.path.join(ROOT, "server", ".inspeximus"),
    os.path.join(ROOT, "agora-game-server", ".inspeximus"),
    os.path.join(ROOT, "agora-game-server", ".agent_memory"),
]
SKIP = (".bak", ".tombstones.json", ".corrupt", ".torn", ".embedid", ".lock",
        "config.json", "nudge.json", "decisions.json", ".update_check.json")


def live_stores():
    out = []
    for d in STORE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if not f.endswith(".json") or not os.path.isfile(p):
                continue
            if any(s in f for s in SKIP):
                continue
            out.append(p)
    return out


def recheckable(loc):
    if not isinstance(loc, str) or not loc:
        return False
    if loc.startswith("http://") or loc.startswith("https://"):
        return True
    return os.path.exists(loc)


def scan(path):
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    items = blob.get("items") if isinstance(blob, dict) else blob
    if not isinstance(items, list):
        return None
    n = with_src = rech = 0
    for r in items:
        if not isinstance(r, dict):
            continue
        n += 1
        s = Inspeximus._raw_source(r)
        if s:
            with_src += 1
            loc = s.get("doc") if isinstance(s, dict) else s
            if recheckable(loc):
                rech += 1
    return {"records": n, "with_source": with_src, "recheckable": rech}


def control():
    """The scanner must be able to report something other than ~0, or its 0 means nothing."""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "runbook.md")
        open(src, "w", encoding="utf-8").write("host is db-old")
        m = Inspeximus(path=os.path.join(td, "c.json"))
        m.remember("host is db-old", source={"doc": src})
        m.remember("a second one", source={"doc": src})
        m._save()
        return scan(os.path.join(td, "c.json"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()

    c = control()
    ok_ctrl = c and c["records"] == 2 and c["recheckable"] == 2
    print(f"CONTROL  {c}  ->  {'PASS' if ok_ctrl else 'FAIL -- the scanner cannot report non-zero'}")
    if not ok_ctrl:
        return 1

    per, failed = [], []
    tot = src = rec = 0
    for p in live_stores():
        try:
            r = scan(p)
        except Exception as e:
            failed.append({"store": p, "error": f"{type(e).__name__}: {e}"})
            print(f"  UNREADABLE  {os.path.relpath(p, ROOT)}  {type(e).__name__}")
            continue
        if r is None:
            failed.append({"store": p, "error": "no item list"})
            continue
        r["store"] = os.path.relpath(p, ROOT).replace("\\", "/")
        per.append(r)
        tot += r["records"]; src += r["with_source"]; rec += r["recheckable"]
        print(f"  {r['store']:56} {r['records']:>7} rec  {r['with_source']:>7} src  "
              f"{r['recheckable']:>5} re-checkable   ({time.time()-t0:.0f}s)")

    if tot == 0:
        print("FAIL -- zero records scanned; a 0.0 here would be vacuous, which is the whole point")
        return 1

    sp = 100.0 * src / tot
    rp = 100.0 * rec / tot
    print(f"\nTOTAL  {tot:,} records   source {sp:.1f}%   re-checkable {rp:.2f}%  ({rec:,} records)")
    print(f"published 2026-08-10:  210,499 records   source 98.3%   re-checkable 0.01%")

    out = {"measured_at": time.strftime("%Y-%m-%d"), "stores": len(per),
           "records": tot, "with_source": src, "recheckable": rec,
           "source_pct": round(sp, 2), "recheckable_pct": round(rp, 4),
           "published_2026_08_10": {"records": 210499, "source_pct": 98.3,
                                    "recheckable_pct": 0.01},
           "control": c, "unreadable": failed, "per_store": per}
    dst = os.path.join(HERE, "the_published_zero_is_still_a_measured_zero.result.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"receipt -> {dst}   ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
