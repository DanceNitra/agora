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
import datetime
import json
import os
import re
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


GIT_REF = re.compile(r"^(?:git:)?[0-9a-f]{7,40}$")


def raw_source(rec):
    """The `source` field as a string. What it SELECTS is deliberately unchanged: the published
    metric is about this field, and moving the goalposts would make the correction unreadable.

    One thing did change. `doc` used to outrank every other key unconditionally, so a record holding
    both a bare {"doc": "agent:x"} and a real {"uri": "https://..."} reported the unresolvable one.
    No record in our stores has both, so this fixes nothing here; it would matter in somebody else's
    store, and this probe is offered to other people.
    """
    s = rec.get("source")
    if s is None:
        s = (rec.get("meta") or {}).get("source")
    if isinstance(s, dict):
        cand = [s.get(k) for k in ("doc", "uri", "url", "path", "href")]
        cand = [c.strip() for c in cand if isinstance(c, str) and c.strip()]
        for c in cand:
            if addressable(c):
                return c
        s = cand[0] if cand else json.dumps(s, sort_keys=True)
    return s.strip() if isinstance(s, str) and s.strip() else None


def record_locators(rec):
    """EVERY string in the record that could name a place, not only the one under `source`.

    THIS EXISTS BECAUSE THE PUBLISHED HEADLINE WAS FALSE, and an adversarial re-run caught it. We
    wrote that nothing in these stores resolves. In the coding store all 173 sourced records carry
    `meta.files` -- 428 repo-relative paths, 408 of which exist on disk -- beside a `meta.sha` whose
    values are real commits. The provenance was there. It sat one key away from the field named
    `source`, and an audit scoped to that field reported zero over it.

    That is the finding rather than a footnote. A field-level provenance audit measures the NAMING,
    and a record can carry a good reference somewhere the auditor never looks, which is the same
    mistake the post is about, made by the probe that found it.
    """
    out = []
    s = rec.get("source")
    if isinstance(s, str):
        out.append(s)
    elif isinstance(s, dict):
        out += [v for v in s.values() if isinstance(v, str)]
    m = rec.get("meta")
    if isinstance(m, dict):
        for k in ("files", "file", "path", "paths", "uri", "url", "href", "doc"):
            v = m.get(k)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                out += [x for x in v if isinstance(x, str)]
    return [x.strip() for x in out if isinstance(x, str) and x.strip()]


def addressable(loc, bases=()):
    """SYNTAX only: does this name a place, whether or not anything is there?

    Narrowed after @perseus-computing reported on r/RAG that the published version returned True for
    `https://example.invalid/...` without making a request, so the metric was syntax-level
    addressability while the write-up called it re-checkable. He was right. It also passed the bare
    string `https://`, a scheme with no host, though that is the degenerate member of the class he
    named rather than a second one.

    A relative path resolves against explicit bases, never against the current directory. It used to
    use plain `os.path.exists`, which made the answer depend on where you happened to run it: the
    same store scored differently from the repo root than from anywhere else.
    """
    if not isinstance(loc, str) or not loc.strip():
        return False
    loc = loc.strip()
    if os.path.isabs(loc):
        return os.path.exists(loc)
    for b in bases:
        if b and os.path.exists(os.path.join(b, loc)):
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


def retrieves(loc, bases=(), timeout=5.0):
    """Actually get the bytes: open the file, or issue one GET and require a 2xx.

    Named `retrieves` rather than `fetches` because for a local path it is an open() and not a
    request, and the old name made the printed line "FETCHED is one GET returning 2xx" untrue for
    every path. It reads a byte instead of calling os.path.exists, so a file that exists and cannot
    be read counts as a failure, which is what a reader chasing the citation would experience.
    """
    if not addressable(loc, bases):
        return False
    loc = loc.strip()
    cands = [loc] if os.path.isabs(loc) else [os.path.join(b, loc) for b in bases if b]
    for c in cands:
        if os.path.exists(c):
            try:
                with open(c, "rb") as fh:
                    fh.read(1)
                return True
            except OSError:
                return False
    # Request() itself raises on a URL urlparse accepted, so it is INSIDE the try. Found by the
    # mutation harness beside this file: one malformed locator in someone else's store would
    # otherwise abort the whole scan, and this is a probe we invite other people to run.
    try:
        req = urllib.request.Request(loc, method="GET", headers={"User-Agent": "provenance-probe"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= getattr(r, "status", r.getcode()) < 300
    except Exception:                                            # noqa: BLE001
        return False


def fetches(loc, timeout=5.0):
    """Deprecated alias kept so older scripts still answer. It cannot resolve a relative path."""
    return retrieves(loc, (), timeout)


def recheckable(loc):
    """Deprecated alias, kept honest: it means addressable, which is what it always measured."""
    return addressable(loc)


OK, FAILED, NOT_TRIED = "ok", "failed", "not_tried"


class Fetcher:
    """One retrieval per DISTINCT locator, capped, with every outcome accounted for separately.

    THE CAP USED TO LIE BY OMISSION. It returned False once it bound, so a locator nobody tried was
    counted beside one that was tried and failed, and the shortfall could not be reconstructed from
    the output. It now returns a third value and the printout carries it.
    """

    def __init__(self, cap=200, timeout=5.0):
        self.cap = cap
        self.timeout = timeout
        self.seen = {}
        self.attempts = 0
        self.local_reads = 0
        self.untried = set()

    @staticmethod
    def _is_local(loc, bases):
        if os.path.isabs(loc):
            return os.path.exists(loc)
        return any(b and os.path.exists(os.path.join(b, loc)) for b in bases)

    def __call__(self, loc, bases=()):
        key = (loc, tuple(bases))
        if key in self.seen:
            return self.seen[key]
        # THE CAP GUARDS THE NETWORK, NOT THE DISK. It was counting local opens too, and on the
        # first run that mattered it bound at 200 while 148 further locators went untried, which
        # turned a record-level count into an undercount reported as a result. Opening a file that
        # is already on this machine costs nothing and nobody else's server is involved.
        if not addressable(loc, bases):
            # Nothing is attempted for a string that does not name a place, so nothing is counted.
            # An earlier version counted these as network attempts and printed 169 of them on a run
            # that never opened a socket.
            self.seen[key] = FAILED
            return FAILED
        if self._is_local(loc, bases):
            self.local_reads += 1
        else:
            if self.attempts >= self.cap:
                self.untried.add(loc)
                return NOT_TRIED
            self.attempts += 1
        out = OK if retrieves(loc, bases, self.timeout) else FAILED
        self.seen[key] = out
        return out


def scan(path, fetcher, bases=None):
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    items = blob.get("items") if isinstance(blob, dict) else blob
    if not isinstance(items, list):
        return None
    if bases is None:
        bases = (ROOT, os.path.dirname(os.path.abspath(path)))
    n = with_src = addr = got = failed = untried = rec_addr = rec_got = gitref = 0
    vals = collections.Counter()
    for r in items:
        if not isinstance(r, dict):
            continue
        n += 1
        s = raw_source(r)
        if s:
            with_src += 1
            vals[s] += 1
            if GIT_REF.match(s):
                gitref += 1
            if addressable(s, bases):
                addr += 1
                v = fetcher(s, bases)
                got += v == OK
                failed += v == FAILED
                untried += v == NOT_TRIED
        # RECORD LEVEL, and it retrieves rather than merely parsing. The first version of this
        # column counted addressability only, which repeats -- one layer up, inside the fix for it
        # -- the exact defect that was reported to us: a count of strings that look like places.
        locs = [x for x in record_locators(r) if addressable(x, bases)]
        if locs:
            rec_addr += 1
            if any(fetcher(x, bases) == OK for x in locs):
                rec_got += 1
    return {"records": n, "with_source": with_src,
            "addressable": addr, "fetched": got,
            "fetch_failed": failed, "fetch_not_tried": untried,
            "record_addressable": rec_addr, "record_retrieved": rec_got,
            "git_ref_shaped": gitref,
            "recheckable": addr,
            "distinct_sources": len(vals), "top": vals.most_common(2),
            "ratio_over_sourced": round(len(vals) / with_src, 6) if with_src else None,
            "ratio_over_all": round(len(vals) / n, 6) if n else None}


def control():
    """ONE fixture, run through the SAME scan the corpus goes through, against a local server.

    @perseus-computing asked for a local HTTP fixture and a known 404 so the resolver control is
    deterministic and publishable. That is the right shape: a control that reaches a real site tests
    that site, and on a machine with no network it fails for a reason unrelated to the code.

    THE SOURCES HERE ARE DICTS, and that is not cosmetic. The earlier fixture used plain strings
    while every record in the real corpus carries `{"doc": ...}`. An adversarial pass mutated
    raw_source to ignore the dict branch, which takes our published coverage figure from 90.47% to
    0.00%, and this control stayed green the whole time. A fixture that cannot take the only shape
    the data has is decorative.

        1 a real absolute file        addressable, retrieved
        2 a missing relative doc      neither
        3 served /there               addressable, retrieved
        4 served /missing             addressable, NOT retrieved  <- kills a yes-to-everything fetcher
        5 the bare string https://    NOT addressable             <- the defect that was reported
        6 git: ref + meta.files       source unresolvable, RECORD resolvable  <- the false headline
        7 doc unresolvable + uri live addressable through uri     <- key-preference guard

    Row 6 is the one that matters. It is the shape of every sourced record in our coding store, and
    it is why the published claim that nothing resolves was wrong.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/there"):
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
    rel = "notes/inner.md"
    os.makedirs(os.path.join(d, "notes"))
    with open(os.path.join(d, rel), "w", encoding="utf-8") as fh:
        fh.write("reached by a repo-relative path, the way meta.files is")
    p = os.path.join(d, "c.json")
    u = "http://127.0.0.1:%d" % port
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"items": [
            {"text": "a", "source": {"doc": real}},
            {"text": "b", "source": {"doc": "no-such-doc.md"}},
            {"text": "c", "source": {"doc": u + "/there"}},
            {"text": "d", "source": {"doc": u + "/missing"}},
            {"text": "e", "source": {"doc": "https://"}},
            {"text": "f", "source": {"doc": "git:9e4973400d34"},
             "meta": {"files": [rel], "sha": "9e4973400d34"}},
            {"text": "g", "source": {"doc": "agent:scholar", "uri": u + "/there2"}},
        ]}, fh)
    try:
        return scan(p, Fetcher(), bases=(d,)), ""
    finally:
        srv.shutdown()


CONTROL_EXPECT = {"records": 7, "with_source": 7, "distinct_sources": 7,
                  "addressable": 4, "fetched": 3,
                  "record_addressable": 5, "record_retrieved": 4,
                  "git_ref_shaped": 1}


def git_pair_audit(items, repo=None, public_ref="origin/main"):
    """Resolve `meta.sha` + `meta.files` as a PAIR, inside the commit's own tree.

    This is the check the coding store's records actually invite, and neither of the columns above
    performs it. `addressable` asks whether a string names a place; `retrieves` opens whatever is
    on disk NOW. A record saying "this came from probes/x.py at commit 9e49734" is a claim about a
    path inside a specific tree, and the working copy is the wrong place to test it: a file can
    exist today, untracked, and be unfetchable by any reader.

    Two numbers, because they answer different questions:

        pairs_in_tree     `git cat-file -e <sha>:<path>` -- did that file exist at that commit
        shas_public       is the commit an ancestor of the public ref -- can a READER get it

    A reference that resolves only in a private clone is not re-checkable by the person reading the
    claim, and this probe exists to count what a reader can re-check.

    Returns None when git or the repository is missing, and the caller reports that as NOT ATTEMPTED
    rather than as zero. A missing tool must never look like a finding.
    """
    import subprocess

    repo = repo or ROOT
    def git(*a):
        try:
            return subprocess.run(("git",) + a, cwd=repo, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None

    probe = git("rev-parse", "--git-dir")
    if probe is None or probe.returncode != 0:
        return None

    pairs = ok_pairs = 0
    recs = full_recs = 0
    shas = set()
    for r in items:
        if not isinstance(r, dict):
            continue
        m = r.get("meta")
        if not isinstance(m, dict):
            continue
        sha = m.get("sha")
        files = m.get("files")
        if isinstance(files, str):
            files = [files]
        if not (isinstance(sha, str) and sha.strip() and isinstance(files, list) and files):
            continue
        sha = sha.strip()
        shas.add(sha)
        recs += 1
        hit = 0
        for f in files:
            if not isinstance(f, str) or not f.strip():
                continue
            pairs += 1
            res = git("cat-file", "-e", "%s:%s" % (sha, f.strip().replace("\\", "/")))
            if res is not None and res.returncode == 0:
                ok_pairs += 1
                hit += 1
        if hit and hit == len([f for f in files if isinstance(f, str) and f.strip()]):
            full_recs += 1

    real = pub = 0
    for s in shas:
        t = git("cat-file", "-t", s)
        if t is not None and t.returncode == 0 and t.stdout.strip() == "commit":
            real += 1
            a = git("merge-base", "--is-ancestor", s, public_ref)
            if a is not None and a.returncode == 0:
                pub += 1
    return {"records_with_pair": recs, "records_fully_resolved": full_recs,
            "pairs": pairs, "pairs_in_tree": ok_pairs,
            "distinct_shas": len(shas), "shas_are_commits": real,
            "shas_public": pub, "public_ref": public_ref}


def git_pair_control(repo=None):
    """Two-sided, against this repository: a pair that must resolve and one that must not.

    Without the negative half, a `git cat-file` that answered yes to everything would look like a
    perfect provenance record. Without the positive half, a broken git invocation would report zero
    resolvable pairs, which on this probe is indistinguishable from the finding.
    """
    import subprocess

    repo = repo or ROOT

    def git(*a):
        try:
            return subprocess.run(("git",) + a, cwd=repo, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None

    try:
        head = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repo,
                              capture_output=True, text=True, timeout=30)
        listing = subprocess.run(("git", "ls-tree", "--name-only", "HEAD"), cwd=repo,
                                 capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None, "git not runnable"
    if head.returncode != 0 or listing.returncode != 0:
        return None, "not a git repository"
    sha = head.stdout.strip()
    names = [n for n in listing.stdout.splitlines() if n.strip()]
    if not names:
        return None, "empty tree at HEAD"
    good = {"meta": {"sha": sha, "files": [names[0]]}}
    bad = {"meta": {"sha": sha, "files": ["no/such/file/at/this/commit.xyz"]}}
    g = git_pair_audit([good], repo)
    b = git_pair_audit([bad], repo)
    if g is None or b is None:
        return None, "audit unavailable"

    # THE ROW THAT SEPARATES THIS FROM A WORKING-COPY CHECK, and it was missing. An adversarial
    # pass replaced git_pair_audit with one that ignores the sha and calls os.path.exists, and the
    # two rows above still passed it: a file present in HEAD is also present on disk, and a file
    # absent everywhere is absent in both. So the control could not tell "inside that commit's
    # tree" from "on this machine right now" -- which is the distinction the whole audit exists to
    # make, and the one the reader who prompted this fix had reported in its first form.
    #
    # A path that exists on disk now and did NOT exist at the root commit separates them:
    # os.path.exists says yes, `git cat-file -e <root>:<path>` says no.
    root = git("rev-list", "--max-parents=0", "HEAD")
    later = None
    if root is not None and root.returncode == 0 and root.stdout.strip():
        r0 = root.stdout.split()[0]
        for cand in (os.path.relpath(os.path.abspath(__file__), repo).replace("\\", "/"),
                     "probes/prove_the_provenance_controls_can_fail.py"):
            at_head = git("cat-file", "-e", "HEAD:%s" % cand)
            at_root = git("cat-file", "-e", "%s:%s" % (r0, cand))
            if (at_head is not None and at_head.returncode == 0
                    and at_root is not None and at_root.returncode != 0
                    and os.path.exists(os.path.join(repo, cand))):
                later = {"meta": {"sha": r0, "files": [cand]}}
                break
    if later is None:
        return None, ("no path found that exists on disk but not at the root commit, so the "
                      "working-copy row could not be built; this control is NOT complete")
    w = git_pair_audit([later], repo)
    if w is None:
        return None, "audit unavailable"
    if w["pairs_in_tree"] != 0:
        return False, ("a path that did not exist at that commit resolved, so this is reading the "
                       "working copy rather than the commit's tree")

    if g["pairs_in_tree"] == 1 and b["pairs_in_tree"] == 0:
        return True, ""
    if g["pairs_in_tree"] == 1 and b["pairs_in_tree"] == 1:
        return False, "a path absent from the tree resolved, so this says yes to anything"
    if g["pairs_in_tree"] == 0 and b["pairs_in_tree"] == 0:
        return False, "a path present in the tree did NOT resolve, so this says no to everything"
    return False, "inverted"



def print_footer():
    print("ADDRESSABLE is syntax over the `source` field: does the value name a path or an http(s)")
    print("URL. FETCHED opens the file or issues one GET and requires a 2xx. RECORD-ADDRESSABLE asks")
    print("the same question of the WHOLE record.")
    print("The first two are separate because collapsing them is the defect @perseus-computing")
    print("reported on r/RAG: the published version called a prefix check re-checkable.")
    print("The third is here because the published headline was wrong. Every sourced record in the")
    print("coding store carries meta.files, and most of those repo-relative paths exist on disk, so")
    print("the provenance was real and sat one key away from the field named `source`. The count is")
    print("in the receipt rather than in this sentence, because it moves.")
    print("All three can fail, and the control makes each fail on its own before a store is read.")


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
    for k in ("records", "with_source", "distinct_sources", "addressable", "fetched",
              "record_addressable", "record_retrieved", "git_ref_shaped"):
        good = c[k] == CONTROL_EXPECT[k]
        ok_all = ok_all and good
        print("CONTROL  %-16s want %d  got %d   %s"
              % (k, CONTROL_EXPECT[k], c[k], "PASS" if good else "FAIL"))
    gok, gwhy = git_pair_control()
    if gok is None:
        print("CONTROL  git pair        NOT ATTEMPTED   %s" % gwhy)
    else:
        print("CONTROL  git pair        a path in HEAD resolves, one absent from it does not   %s%s"
              % ("PASS" if gok else "FAIL", "" if gok else "   " + gwhy))
        ok_all = ok_all and gok
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
        # Only where a git ref actually appears; the audit shells out per path and there is no
        # reason to spend that on stores whose sources are all `agent:<name>`.
        if r["git_ref_shaped"]:
            try:
                with open(p, encoding="utf-8") as fh:
                    blob = json.load(fh)
                r["git_pairs"] = git_pair_audit(blob.get("items") if isinstance(blob, dict) else blob)
            except Exception as e:                               # noqa: BLE001
                r["git_pairs"] = None
                unreadable.append((rel, "git pair audit: %s: %s" % (type(e).__name__, e)))
        rows.append(r)

    if unreadable:
        print("UNREADABLE (reported, never counted as clean):")
        for s, why in unreadable:
            print("   %-48s %s" % (s, why))
        print()
    if not rows:
        print("FAIL -- no stores read; nothing was measured")
        return 1

    print("%-46s %8s %7s %8s %9s %6s %8s %9s"
          % ("store", "records", "src %", "distinct", "/sourced", "addr", "fetched", "rec-addr"))
    for r in sorted(rows, key=lambda x: -x["records"]):
        pct = 100.0 * r["with_source"] / r["records"] if r["records"] else 0.0
        print("%-46s %8d %6.2f%% %8d %9s %6d %8d %9d"
              % (r["store"], r["records"], pct, r["distinct_sources"],
                 r["ratio_over_sourced"], r["addressable"], r["fetched"],
                 r["record_addressable"]))

    tot = sum(r["records"] for r in rows)
    src = sum(r["with_source"] for r in rows)
    adr = sum(r["addressable"] for r in rows)
    got = sum(r["fetched"] for r in rows)
    rad = sum(r["record_addressable"] for r in rows)
    rgot = sum(r["record_retrieved"] for r in rows)
    gp = [r["git_pairs"] for r in rows if r.get("git_pairs")]
    gref = sum(r["git_ref_shaped"] for r in rows)
    full = [r for r in rows if r["records"] and r["with_source"] == r["records"]]
    fn = sum(r["records"] for r in full)
    fd = sum(r["distinct_sources"] for r in full)

    print("\n" + "=" * 100)
    print("ALL STORES        %d records   source %.2f%%   ADDRESSABLE %d   FETCHED %d"
          % (tot, 100.0 * src / tot, adr, got))
    print("                  RECORD-ADDRESSABLE %d, RECORD-RETRIEVED %d -- a locator ANYWHERE in"
          % (rad, rgot))
    print("                  the record, not only in `source`. This is the column the published")
    print("                  post did not have, and it is the reason its headline was wrong.")
    print("                  %d network retrieval(s) attempted, %d local file(s) opened%s"
          % (fetcher.attempts, fetcher.local_reads,
             "" if not fetcher.untried
             else "; %d distinct remote locators NOT tried (cap %d)"
                  % (len(fetcher.untried), fetcher.cap)))
    if not fetcher.attempts and not fetcher.local_reads:
        print("                  FETCHED is 0 BY ENTAILMENT, not by observation: nothing was")
        print("                  addressable, so no retrieval was attempted. The retriever was")
        print("                  exercised only against the control fixture above.")
    if gref and not gp:
        print("                  %d source values are git-ref shaped and were NOT resolved (no git,"
              % gref)
        print("                  or not a repository). Reported, never counted as zero.")
    for r in [x for x in rows if x.get("git_pairs")]:
        g = r["git_pairs"]
        print("                  git pairs in %s:" % r["store"])
        print("                    %d/%d path+commit pairs exist in the tree of their OWN commit"
              % (g["pairs_in_tree"], g["pairs"]))
        print("                    %d/%d records have every path resolve"
              % (g["records_fully_resolved"], g["records_with_pair"]))
        print("                    %d/%d distinct shas are real commits, %d reachable from %s"
              % (g["shas_are_commits"], g["distinct_shas"], g["shas_public"], g["public_ref"]))
        print("                    a reference only a private clone can follow is not one a reader")
        print("                    can re-check, which is what this probe counts.")
    print("AT 100%% COVERAGE  %d records across %d stores   %d distinct values   ratio %.6f"
          % (fn, len(full), fd, fd / fn if fn else 0.0))
    for r in sorted(full, key=lambda x: -x["records"])[:3]:
        print("                  %-42s %r x%d" % (r["store"], r["top"][0][0][:30], r["top"][0][1]))
    print("=" * 100)
    print("The ratio is column Distinctness (Deequ, Great Expectations, ydata-profiling), not a new")
    print("check, and it does not measure traceability -- a UUID per record scores 1.0 at zero.")
    print_footer()

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("")
    print("measured_at %s -- these stores are LIVE and grow while you read this, so" % stamp)
    print("the record count moves between runs. Cite a number with its timestamp or not at all.")
    out = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"measured_at": stamp,
                   "records": tot, "source_pct": round(100.0 * src / tot, 2),
                   "addressable": adr, "fetched": got,
                   "record_addressable": rad, "record_retrieved": rgot,
                   "git_ref_shaped": gref,
                   "git_pairs": {r["store"]: r["git_pairs"] for r in rows if r.get("git_pairs")},
                   "fetch_attempts": fetcher.attempts,
                   "local_reads": fetcher.local_reads,
                   "fetch_not_tried_distinct": len(fetcher.untried),
                   "fetched_is_entailed": (fetcher.attempts + fetcher.local_reads) == 0,
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
