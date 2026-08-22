"""Our provenance field is 100% populated, holds 8 distinct values over 217,549 records, and 0 resolve.

We publish a source-coverage figure. Re-measured across eleven live stores it is ~92.6%, and that is
an average over two populations with nothing to do with each other:

    eight agent stores   217,549 records   source populated on 100.0%
    three coding stores   17,418 records   source populated on 0.6% / 0.0% / 0.0%

The 100.0% is the part worth looking at. `scholar.json` carries a `source` field on all 26,928 of its
records and the field holds the literal string `agent:scholar` in every one. One distinct value, and
it is the name of the process that did the writing.

W3C PROV has separated these since 2013: `wasAttributedTo` is the agent responsible,
`wasDerivedFrom` is the entity it came from. We recorded attribution and read it as derivation.

WHAT THIS PROBE IS NOT. `distinct / records` is **not a new check and not a fix**. It is column
Distinctness -- Abedjan, Golab & Naumann's profiling survey defines uniqueness as distinct values over
rows; AWS Deequ ships it as `Distinctness`; Great Expectations ships
`expect_column_proportion_of_unique_values_to_be_between`; ydata-profiling raises CONSTANT
automatically when distinct = 1. A profiler would have caught this in one pass and nobody ran one.

And it does not measure traceability either. Fill `source` with a fresh UUID per record and
distinctness reads a perfect 1.0 at zero traceability -- the same success-shaped nothing, one field
over. That objection is the reason the headline here is the **zero**, not the ratio:

    re-checkable = 0, over every record in every store.

That number can fail, and it is measured against a resolver this probe proves can succeed.

CONTROLS, both required, because each covers what the other cannot see:
  * DISTINCTNESS -- three distinct sources must read 3 over 3 records, or a counter stuck at 1 makes
    every store look like ours;
  * RESOLVER -- a real file written to disk, plus an https URL, must read as re-checkable. Without
    this the headline zero is unpublishable: a resolver returning False on everything reports zero
    over any corpus and is indistinguishable from a corpus with none. This probe shipped without it
    until a method audit asked for it.
  * a store that fails to parse is REPORTED, never counted as clean.

BOTH DENOMINATORS ARE PRINTED. Dividing by ALL records silently multiplies distinctness by coverage
and reports neither; doing that turned a ~27,000x difference into "170x" in a draft. The ratio that
matches the shipped `distinct_source_ratio` field is `/sourced`.

Run:  python probes/a_provenance_field_at_100_percent_with_one_distinct_value.py
"""
from __future__ import annotations
import collections
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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
            if f.endswith(".json") and os.path.isfile(p) and not any(s in f for s in SKIP):
                out.append(p)
    return out


def raw_source(rec):
    s = rec.get("source")
    if s is None:
        s = (rec.get("meta") or {}).get("source")
    if isinstance(s, dict):
        s = s.get("doc") or s.get("uri") or s.get("path") or json.dumps(s, sort_keys=True)
    return s if isinstance(s, str) and s.strip() else None


def recheckable(loc):
    if not isinstance(loc, str) or not loc:
        return False
    return loc.startswith("http://") or loc.startswith("https://") or os.path.exists(loc)


def scan(path):
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    items = blob.get("items") if isinstance(blob, dict) else blob
    if not isinstance(items, list):
        return None
    n = with_src = rech = 0
    vals = collections.Counter()
    for r in items:
        if not isinstance(r, dict):
            continue
        n += 1
        s = raw_source(r)
        if s:
            with_src += 1
            vals[s] += 1
            if recheckable(s):
                rech += 1
    return {"records": n, "with_source": with_src, "recheckable": rech,
            "distinct_sources": len(vals), "top": vals.most_common(2),
            "ratio_over_sourced": round(len(vals) / with_src, 6) if with_src else None,
            "ratio_over_all": round(len(vals) / n, 6) if n else None}


def control():
    d = tempfile.mkdtemp()
    real = os.path.join(d, "runbook.md")
    with open(real, "w", encoding="utf-8") as fh:
        fh.write("host is db-old")
    p = os.path.join(d, "c.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"items": [{"text": "a", "source": real},
                             {"text": "b", "source": "no-such-doc.md"},
                             {"text": "c", "source": "https://example.org/three"}]}, fh)
    return scan(p)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    c = control()
    ok_d = bool(c and c["records"] == 3 and c["distinct_sources"] == 3)
    ok_r = bool(c and c["recheckable"] == 2)      # the real file, and the https URL
    print("CONTROL  distinctness   3 distinct over 3 records  -> %d   %s"
          % (c["distinct_sources"] if c else -1, "PASS" if ok_d else "FAIL"))
    print("CONTROL  resolver       a real file + an https URL -> %d   %s"
          % (c["recheckable"] if c else -1, "PASS" if ok_r else "FAIL"))
    print()
    if not (ok_d and ok_r):
        print("ABORT -- the instrument is broken, not the corpus. A resolver that cannot see a file")
        print("         it just wrote reports 0 over any store, which is exactly the headline.")
        return 1

    rows, unreadable = [], []
    for p in live_stores():
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        try:
            r = scan(p)
        except Exception as e:
            unreadable.append((rel, "%s: %s" % (type(e).__name__, e)))
            continue
        if r is None:
            unreadable.append((rel, "no item list"))
            continue
        r["store"] = rel
        rows.append(r)

    if unreadable:
        print("UNREADABLE (reported, never counted as clean):")
        for s, why in unreadable:
            print("   %-48s %s" % (s, why))
        print()
    if not rows:
        print("FAIL -- no stores read; nothing was measured")
        return 1

    print("%-46s %8s %7s %8s %10s %10s %7s"
          % ("store", "records", "src %", "distinct", "/sourced", "/all", "re-chk"))
    for r in sorted(rows, key=lambda x: -x["records"]):
        pct = 100.0 * r["with_source"] / r["records"] if r["records"] else 0.0
        print("%-46s %8d %6.2f%% %8d %10s %10s %7d"
              % (r["store"], r["records"], pct, r["distinct_sources"],
                 r["ratio_over_sourced"], r["ratio_over_all"], r["recheckable"]))

    tot = sum(r["records"] for r in rows)
    src = sum(r["with_source"] for r in rows)
    rec = sum(r["recheckable"] for r in rows)
    full = [r for r in rows if r["records"] and r["with_source"] == r["records"]]
    fn = sum(r["records"] for r in full)
    fd = sum(r["distinct_sources"] for r in full)

    print("\n" + "=" * 100)
    print("ALL STORES        %d records   source %.2f%%   RE-CHECKABLE %d" % (tot, 100.0 * src / tot, rec))
    print("AT 100%% COVERAGE  %d records across %d stores   %d distinct values   ratio %.6f"
          % (fn, len(full), fd, fd / fn if fn else 0.0))
    for r in sorted(full, key=lambda x: -x["records"])[:3]:
        print("                  %-42s %r x%d" % (r["store"], r["top"][0][0][:30], r["top"][0][1]))
    print("=" * 100)
    print("The ratio is column Distinctness (Deequ, Great Expectations, ydata-profiling), not a new")
    print("check, and it does not measure traceability -- a UUID per record scores 1.0 at zero.")
    print("The number that can fail is RE-CHECKABLE, and the resolver control above proves it can.")

    out = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"records": tot, "source_pct": round(100.0 * src / tot, 2), "recheckable": rec,
                   "full_coverage_stores": len(full), "full_coverage_records": fn,
                   "full_coverage_distinct_sources": fd,
                   "full_coverage_ratio": round(fd / fn, 6) if fn else None,
                   "control": c, "unreadable": unreadable, "per_store": rows}, fh, indent=1)
    print("\nreceipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
