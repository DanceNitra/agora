"""Our provenance field is 100% populated, holds 8 distinct values over 217,549 records, and 0 resolve.

We publish a source-coverage figure. Re-measured across eleven live stores it is ~92.6%, and that is
an average over two populations with nothing to do with each other:

    eight agent stores   217,549 records   source populated on 100.0%
    three coding stores   17,418 records   source populated on 0.6% / 0.0% / 0.0%

The 100.0% is the part worth looking at. `scholar.json` carries a `source` field on all 26,928 of its
records, holding one distinct value: the name of the process that did the writing.

CORRECTED 2026-08-22, and the truth is worse than the error. This file said the field "holds the
literal string `agent:scholar`". It does not. It holds a STRUCTURED OBJECT, `{"doc": "agent:scholar"}`
-- and in the coding store `{"doc": "git:9e4973400d34"}`, with `None` on the other 17,020 records. So
the shape is not a lazy string that a reviewer would squint at; it is a source object with a named
key, which is exactly what a provenance field is supposed to look like. It passes a schema check, it
passes a type check, it would pass a reviewer, and it still resolves to nothing. A wrong statement
about our own field type, inside the file arguing that fields lie, is the fourth instance of this
class today.

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

THE TIERS, AND THERE ARE FOUR OF THEM. u/Terrible_Front_583 on r/RAG proposed splitting "source
coverage" into field presence, semantic provenance and fetchability, which is a better decomposition
than the two integers this probe shipped with -- it separates the two failures we had merged. Checked
against our own stores it splits once more, because FIELD PRESENCE is itself two numbers:

    tier 1a  the key exists                .inspeximus/coding_memory.json  100.00%   (17,122)
    tier 1b  the key carries a value                                         0.62%   (106)
    tier 2   distinct values                                                 105
    tier 3   fetchable                                                         0

A schema check answers 1a. A coverage check answers 1b. Neither is provenance, and the gap between
them here is 99.4 percentage points inside a single store.

His fuller gate -- a resolvable source object plus snapshot/version, owner, and an access check -- we
cannot score at all: `version`, `snapshot`, `owner`, `access`, `retrieved_at`, `url` and `sha256` are
absent from every record in both schemas. That tier is not zero for us, it is UNMEASURABLE, and a
probe that printed 0 for it would be the same success-shaped nothing this file is about.

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

Run on OUR stores:      python probes/a_provenance_field_at_100_percent_with_one_distinct_value.py
Run on YOURS:           python a_provenance_field_at_100_percent_with_one_distinct_value.py STORE.json
                        python a_provenance_field_at_100_percent_with_one_distinct_value.py DIR/ ...

It reads any JSON that is a list of records, or an object with an `items` list, and looks for
`source` (or `meta.source`) on each -- a bare string, or an object with `doc` / `uri` / `path`.
The two controls run first and must both PASS, or your own zero means nothing. If it finds no
stores it exits 1 and says so rather than reporting a zero over an empty scan.
"""
from __future__ import annotations
import collections
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request

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


def live_stores(argv=None):
    """Stores to scan: whatever is on the command line, else this repo's own.

    ADDED 2026-08-22, and it should have been here before the post went out. The published version
    scanned four hard-coded directories of THIS repository, so the invitation in the write-up --
    point it at your store and tell me the two integers -- could not actually be accepted by anyone.
    It failed loud rather than reporting a fake zero, which is the control doing its job, but a
    stranger's only possible outcome was `FAIL -- no stores read`. An artifact offered publicly as
    runnable has to run somewhere other than where it was written.

    Usage:  python a_provenance_field...py [PATH ...]
            PATH may be a .json store or a directory of them; repeat for several.
    """
    args = [a for a in (argv if argv is not None else sys.argv[1:]) if not a.startswith("-")]
    if args:
        out = []
        for a in args:
            if os.path.isdir(a):
                out += [os.path.join(a, f) for f in sorted(os.listdir(a))
                        if f.endswith(".json") and os.path.isfile(os.path.join(a, f))]
            elif os.path.isfile(a):
                out.append(a)
            else:
                print("no such path: %s" % a, file=sys.stderr)
        return out
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


def addressable(loc):
    """SYNTAX only: does this name a place, whether or not anything is there?

    Renamed from `recheckable` and narrowed, after @perseus-computing reported on r/RAG that the
    original returned True for `https://example.invalid/...` without making a request, so the
    published metric was syntax-level addressability while the write-up called it re-checkable.
    That is correct and it was worse than reported: the original also passed the bare string
    `https://`, a scheme with no host at all.

    The zero is unaffected, because `agent:scholar` and `git:162de50e1702` fail this too, but any
    store holding real URLs would have been scored optimistically, and this is a probe other people
    were invited to run. A metric that cannot tell a live URL from a dead one must not be named
    after fetching.
    """
    if not isinstance(loc, str) or not loc.strip():
        return False
    if os.path.exists(loc):
        return True
    # NOT a bare `except Exception`. The first version of this function wrapped the parse in one,
    # and while the module was missing `import urllib.parse` the AttributeError was swallowed and
    # every locator on earth came back False. That is not a safe default here: this probe's headline
    # IS a zero, so a bug that returns zero for everyone is indistinguishable from the finding and
    # would have confirmed it for every reader. Only a genuine parse failure is tolerated.
    try:
        u = urllib.parse.urlparse(loc)
    except ValueError:
        return False
    return u.scheme in ("http", "https") and bool(u.netloc)


def fetches(loc, timeout=5.0):
    """ONE REQUEST. Returns True only on a 2xx, and it is opt-in for the obvious reasons.

    @perseus-computing's separation, adopted: locator-present, syntax-valid and fetch-succeeded are
    three different states and collapsing them is what produced the original defect. The two they
    also named, snapshot-verified and claim-supported, are not implemented here because this probe
    does not hold snapshots or claims, and naming a state it cannot measure would repeat the
    mistake in a new place.
    """
    if not addressable(loc):
        return False
    if os.path.exists(loc):
        return True
    req = urllib.request.Request(loc, method="GET", headers={"User-Agent": "provenance-probe"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= getattr(r, "status", r.getcode()) < 300
    except Exception:                                            # noqa: BLE001
        return False


def recheckable(loc):
    """Kept so anyone who scripted against the old name still gets an answer, and gets the honest
    one: it now means addressable, which is what it always measured."""
    return addressable(loc)


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


def fetch_control():
    """A LOCAL server, so the fetch state is checkable without the network or anyone's uptime.

    @perseus-computing asked for exactly this on r/RAG: "a local HTTP fixture plus a known 404 would
    make the resolver control deterministic and publishable." It is the right shape. A control that
    reaches out to a real site tests that site, and on a machine with no network it fails for a
    reason that has nothing to do with the code.

    Two-sided on purpose. A fetcher that returns True for everything passes a 200-only check, and a
    fetcher that returns False for everything, which is precisely the bug this function was added
    after, passes a 404-only check. Both are required.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/there":
                b = b"ok"
                self.send_response(200)
                self.send_header("content-length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            else:
                self.send_response(404)
                self.send_header("content-length", "0")
                self.end_headers()

    try:
        srv = HTTPServer(("127.0.0.1", 0), H)
    except OSError as e:                                         # noqa: BLE001
        return False, "could not bind a local server (%s)" % e
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        good = fetches("http://127.0.0.1:%d/there" % port)
        bad = fetches("http://127.0.0.1:%d/missing" % port)
    finally:
        srv.shutdown()
    if good and not bad:
        return True, ""
    if good and bad:
        return False, "the 404 was counted as a fetch, so this fetcher says yes to anything"
    if not good and not bad:
        return False, "even the 200 did not fetch, so this fetcher says no to everything"
    return False, "inverted: the 404 fetched and the 200 did not"


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
    print("CONTROL  addressable    a real file + an https URL -> %d   %s"
          % (c["recheckable"] if c else -1, "PASS" if ok_r else "FAIL"))
    ok_f, f_why = fetch_control()
    print("CONTROL  fetch          local 200 fetches, local 404 does not   %s   %s"
          % ("PASS" if ok_f else "FAIL", f_why))
    print()
    if not (ok_d and ok_r and ok_f):
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
