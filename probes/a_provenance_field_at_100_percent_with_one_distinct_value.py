"""Our provenance field is at 100% coverage and holds one distinct value across 217,000 records.

We publish a source-coverage figure. Re-measured today across eleven live stores it is 92.75%, and
that number is an average over two populations that have nothing to do with each other:

    eight agent stores   217,444 records   source coverage 100.0%
    three coding stores   17,113 records   source coverage 0.6% / 0.0% / 0.0%

The 100.0% is the part worth looking at. In `scholar.json`, 26,928 records carry a `source` field and
the field holds the literal string `agent:scholar` in every one of them. One distinct value. It is
the name of the process that did the writing, not the origin of what was written.

So the coverage number measures that a field is POPULATED. Nothing in it measures whether anything is
traceable, and the two are reported with the same word.

THE ONE-LINE CHECK, which is the point of publishing this: **distinct source values divided by
records.** At 1/26,928 a coverage figure is a schema check wearing the clothes of a guarantee. This
probe computes it for every store it can find and prints the distribution, so a reader can run the
same thing on their own store and get a number to compare.

CONTROLS, because a scan that reads nothing reports a clean 100%:
  * a store that fails to parse is REPORTED, never counted as clean;
  * a synthetic control store with three genuinely distinct sources must read 3 distinct / 3 records,
    so a distinct-count of 1 elsewhere means the corpus, not the counter;
  * re-checkability is measured beside coverage, because a locator that resolves is the property
    coverage is assumed to imply.

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
            "distinct_sources": len(vals), "top": vals.most_common(2)}


def control():
    """Three genuinely distinct sources must read 3 distinct over 3 records."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "c.json")
    json.dump({"items": [{"text": "a", "source": "doc-one.md"},
                         {"text": "b", "source": "doc-two.md"},
                         {"text": "c", "source": "https://example.org/three"}]},
              open(p, "w", encoding="utf-8"))
    return scan(p)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    c = control()
    ok = c and c["records"] == 3 and c["distinct_sources"] == 3
    print("CONTROL  3 distinct sources over 3 records -> %d distinct  %s\n"
          % (c["distinct_sources"] if c else -1, "PASS" if ok else "FAIL"))
    if not ok:
        print("the counter is broken, not the corpus")
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
            print("   %-52s %s" % (s, why))
        print()

    if not rows:
        print("FAIL -- no stores read; nothing was measured")
        return 1

    print("%-52s %8s %7s %9s %11s" % ("store", "records", "src %", "distinct", "re-checkable"))
    for r in sorted(rows, key=lambda x: -x["records"]):
        pct = 100.0 * r["with_source"] / r["records"] if r["records"] else 0.0
        print("%-52s %8d %6.1f%% %9d %11d"
              % (r["store"], r["records"], pct, r["distinct_sources"], r["recheckable"]))

    tot = sum(r["records"] for r in rows)
    src = sum(r["with_source"] for r in rows)
    rec = sum(r["recheckable"] for r in rows)
    full = [r for r in rows if r["records"] and r["with_source"] == r["records"]]
    fn = sum(r["records"] for r in full)
    fd = sum(r["distinct_sources"] for r in full)

    print("\n" + "=" * 92)
    print("ALL STORES        %d records   source %.2f%%   re-checkable %d" % (tot, 100.0 * src / tot, rec))
    print("AT 100%% COVERAGE  %d records across %d stores   %d distinct source values in total"
          % (fn, len(full), fd))
    if fn:
        print("                  distinct-per-record = %d / %d = %.6f" % (fd, fn, fd / fn))
    for r in full[:3]:
        print("                  %-40s top value %r x%d"
              % (r["store"], r["top"][0][0][:32], r["top"][0][1]))
    print("=" * 92)

    out = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.result.json")
    json.dump({"records": tot, "source_pct": round(100.0 * src / tot, 2), "recheckable": rec,
               "full_coverage_stores": len(full), "full_coverage_records": fn,
               "full_coverage_distinct_sources": fd,
               "control": c, "unreadable": unreadable, "per_store": rows},
              open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
