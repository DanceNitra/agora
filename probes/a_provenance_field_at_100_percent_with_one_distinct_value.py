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
    # Request() itself raises on a URL urlparse accepted, so it is INSIDE the try. Found by the
    # mutation harness beside this file: one malformed locator in someone else's store would
    # otherwise abort the whole scan, and this probe is one we invite other people to run.
    try:
        req = urllib.request.Request(loc, method="GET", headers={"User-Agent": "provenance-probe"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= getattr(r, "status", r.getcode()) < 300
    except Exception:                                            # noqa: BLE001
        return False


def recheckable(loc):
    """Kept so anyone who scripted against the old name still gets an answer, and gets the honest
    one: it now means addressable, which is what it always measured."""
    return addressable(loc)


class Fetcher:
    """One GET per DISTINCT addressable locator, capped, and the cap is reported rather than silent.

    Splitting the metric was only half of @perseus-computing's point, and the first attempt at that
    fix got the half that is easy to see. It added `fetches()` and a control for it, and then left
    the store scan calling `addressable()`. So the fetcher existed, passed its own test, and never
    saw a single record of the real corpus. A check that never reaches its target reports whatever
    the absence of a target looks like, which here is the headline itself.

    The cap exists because a store holding 200,000 real URLs would otherwise become a crawl. It is
    counted and printed, because a bound nobody is told about reads as full coverage.
    """

    def __init__(self, cap=200, timeout=5.0):
        self.cap = cap
        self.timeout = timeout
        self.seen = {}
        self.attempts = 0
        self.skipped_by_cap = 0

    def __call__(self, loc):
        if not addressable(loc):
            return False
        if loc in self.seen:
            return self.seen[loc]
        if self.attempts >= self.cap:
            self.skipped_by_cap += 1
            return False
        self.attempts += 1
        ok = fetches(loc, self.timeout)
        self.seen[loc] = ok
        return ok


def scan(path, fetcher):
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    items = blob.get("items") if isinstance(blob, dict) else blob
    if not isinstance(items, list):
        return None
    n = with_src = addr = got = 0
    vals = collections.Counter()
    for r in items:
        if not isinstance(r, dict):
            continue
        n += 1
        s = raw_source(r)
        if s:
            with_src += 1
            vals[s] += 1
            if addressable(s):
                addr += 1
                if fetcher(s):
                    got += 1
    return {"records": n, "with_source": with_src,
            "addressable": addr, "fetched": got, "recheckable": addr,
            "distinct_sources": len(vals), "top": vals.most_common(2),
            "ratio_over_sourced": round(len(vals) / with_src, 6) if with_src else None,
            "ratio_over_all": round(len(vals) / n, 6) if n else None}


def control():
    """ONE fixture, run through the SAME scan the corpus goes through, against a local server.

    @perseus-computing asked for a local HTTP fixture and a known 404 so the resolver control is
    deterministic and publishable. That is the right shape: a control that reaches a real site tests
    that site, and on a machine with no network it fails for a reason unrelated to the code.

    Every state is two-sided, and each row can fail on its own:

        a real file on disk       addressable, fetched
        a missing relative doc    neither
        served /there             addressable, fetched
        served /missing           addressable, NOT fetched  <- kills a yes-to-everything fetcher
        the bare string https://  NOT addressable           <- the exact reported defect

    The last row is a regression guard. The published version returned True for it: a scheme with no
    host, which cannot be re-checked by anyone.
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
        return None, "could not bind a local server (%s)" % e
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    d = tempfile.mkdtemp()
    real = os.path.join(d, "runbook.md")
    with open(real, "w", encoding="utf-8") as fh:
        fh.write("host is db-old")
    p = os.path.join(d, "c.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"items": [{"text": "a", "source": real},
                             {"text": "b", "source": "no-such-doc.md"},
                             {"text": "c", "source": "http://127.0.0.1:%d/there" % port},
                             {"text": "d", "source": "http://127.0.0.1:%d/missing" % port},
                             {"text": "e", "source": "https://"}]}, fh)
    try:
        return scan(p, Fetcher()), ""
    finally:
        srv.shutdown()


CONTROL_EXPECT = {"records": 5, "with_source": 5, "distinct_sources": 5,
                  "addressable": 3, "fetched": 2}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    c, why = control()
    if c is None:
        print("ABORT -- could not build the control fixture: %s" % why)
        return 1
    ok_all = True
    for k in ("records", "with_source", "distinct_sources", "addressable", "fetched"):
        good = c[k] == CONTROL_EXPECT[k]
        ok_all = ok_all and good
        print("CONTROL  %-16s want %d  got %d   %s"
              % (k, CONTROL_EXPECT[k], c[k], "PASS" if good else "FAIL"))
    print()
    if not ok_all:
        print("ABORT -- the instrument is broken, not the corpus. A resolver that cannot see a file")
        print("         it just wrote reports 0 over any store, which is exactly the headline.")
        return 1

    fetcher = Fetcher()
    rows, unreadable = [], []
    for p in live_stores():
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        try:
            r = scan(p, fetcher)
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

    print("%-46s %8s %7s %8s %10s %10s %6s %8s"
          % ("store", "records", "src %", "distinct", "/sourced", "/all", "addr", "fetched"))
    for r in sorted(rows, key=lambda x: -x["records"]):
        pct = 100.0 * r["with_source"] / r["records"] if r["records"] else 0.0
        print("%-46s %8d %6.2f%% %8d %10s %10s %6d %8d"
              % (r["store"], r["records"], pct, r["distinct_sources"],
                 r["ratio_over_sourced"], r["ratio_over_all"], r["addressable"], r["fetched"]))

    tot = sum(r["records"] for r in rows)
    src = sum(r["with_source"] for r in rows)
    adr = sum(r["addressable"] for r in rows)
    got = sum(r["fetched"] for r in rows)
    full = [r for r in rows if r["records"] and r["with_source"] == r["records"]]
    fn = sum(r["records"] for r in full)
    fd = sum(r["distinct_sources"] for r in full)

    print("\n" + "=" * 100)
    print("ALL STORES        %d records   source %.2f%%   ADDRESSABLE %d   FETCHED %d"
          % (tot, 100.0 * src / tot, adr, got))
    print("                  %d GET(s) issued; a request is only made for an addressable locator%s"
          % (fetcher.attempts,
             "" if not fetcher.skipped_by_cap
             else ", and %d were NOT tried (cap %d)" % (fetcher.skipped_by_cap, fetcher.cap)))
    print("AT 100%% COVERAGE  %d records across %d stores   %d distinct values   ratio %.6f"
          % (fn, len(full), fd, fd / fn if fn else 0.0))
    for r in sorted(full, key=lambda x: -x["records"])[:3]:
        print("                  %-42s %r x%d" % (r["store"], r["top"][0][0][:30], r["top"][0][1]))
    print("=" * 100)
    print("The ratio is column Distinctness (Deequ, Great Expectations, ydata-profiling), not a new")
    print("check, and it does not measure traceability -- a UUID per record scores 1.0 at zero.")
    print("ADDRESSABLE is syntax: does the value name a place. FETCHED is one GET returning 2xx.")
    print("They are separate columns because collapsing them is the defect @perseus-computing found")
    print("on r/RAG: the published version called a prefix check re-checkable. Both can fail, and")
    print("the control above makes each of them fail on its own before any store is read.")

    out = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"records": tot, "source_pct": round(100.0 * src / tot, 2),
                   "addressable": adr, "fetched": got,
                   "fetch_attempts": fetcher.attempts,
                   "fetch_skipped_by_cap": fetcher.skipped_by_cap,
                   "recheckable": adr,
                   "recheckable_note": ("deprecated alias, kept so older scripts still read: it "
                                        "equals addressable, which is what it always measured"),
                   "full_coverage_stores": len(full), "full_coverage_records": fn,
                   "full_coverage_distinct_sources": fd,
                   "full_coverage_ratio": round(fd / fn, 6) if fn else None,
                   "control": c, "unreadable": unreadable, "per_store": rows}, fh, indent=1)
    print("\nreceipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
