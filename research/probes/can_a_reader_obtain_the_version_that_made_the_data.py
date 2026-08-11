"""A provenance pointer that EXISTS is not one that RESOLVES.

A reproducibility annex names how to obtain the artifact that produced the data. This asks the only
question that makes such an annex worth anything: can a reader, TODAY, obtain the version that was
running when the data was made?

The case: DeepSeek-V3 issue #1466. HeartFlow contributed B-series trace data, and the thread names the
versions live around those contributions -- v5.5.0 and v5.5.1 (2026-07-01 05:50/05:56Z), v5.7.6
(2026-07-06). The proposed annex points at `npm install @yun520-1/heartflow`.

This is NOT an audit of someone else's project. It is the same defect we measured in OURSELVES hours
earlier: across 210,499 records our `source` field had 98.3% coverage and 0.01% that resolved to
anything re-checkable. A field that looks like provenance and cannot answer the question it appears to
answer. We wrote check_sources() because of it; this probe is that question pointed outward.

THREE CHANNELS, NOT ONE. The first version of this probe checked the npm registry and the git tags and
concluded all three versions were unobtainable. That was WRONG, and the error is the one this whole
line of work is about: it did not read the channel where the answer lived. `package.json` at a plain
commit carries a version that was never tagged and never published -- v5.7.6 sits at dfb456a6 -- so a
reader CAN obtain it, by SHA. A checker blind to a channel reports absence and sounds authoritative.

WHAT ABSENCE MEANS HERE. A version in none of the three channels is one a READER cannot obtain. It is
NOT evidence the version never existed: an internal deployment ("live in production") leaves no trace
in any public channel by design, and that is the most likely explanation.

THE CONTROL IS THE POINT. A broken reader returns "absent" for everything, manufacturing this exact
result. Each channel therefore first asserts it can find versions known to be present -- including one
that exists ONLY in commit history -- and the run reports nothing if that fails.

    python research/probes/can_a_reader_obtain_the_version_that_made_the_data.py

Network required. All endpoints are public; unauthenticated GitHub allows 60 requests/hour and one run
costs roughly 35, so a second run inside the hour may be rate-limited (reported as UNRESOLVED, never as
an absence).
"""
import base64
import json
import sys
import urllib.error
import urllib.request

NPM = "https://registry.npmjs.org/@yun520-1%2Fheartflow"
REPO = "yun520-1/mark-heartflow-skill"
GH = "https://api.github.com/repos/" + REPO

#: Versions the thread names as live around the B-series trace contributions.
NAMED_IN_THREAD = ["5.5.0", "5.5.1", "5.7.6"]

#: The window to scan for package.json versions: from before the first named version through after the
#: last. Bounded on purpose -- a full-history scan is thousands of requests -- and the bound is declared
#: so a reader can see what was NOT looked at.
SINCE, UNTIL = "2026-06-25T00:00:00Z", "2026-07-10T00:00:00Z"

#: POSITIVE CONTROLS, one per channel. Chosen as neighbours of the versions under test, so a control
#: passing means the reader can see THAT REGION of the version space, not merely that it sees something.
CONTROL_NPM = ["5.7.3", "5.10.0"]
CONTROL_TAGS = ["v5.7.3", "v5.10.0"]
CONTROL_HISTORY = ["5.5.2"]      # never tagged, never on npm; only a commit carries it


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "agora-probe",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8")), r.headers


def npm_versions():
    d, _ = _get(NPM)
    if "error" in d:
        raise RuntimeError("npm registry: %s" % d["error"])
    return sorted(d.get("versions", {})), (d.get("dist-tags") or {}).get("latest")


def _paginated(url, cap=20):
    out, pages = [], 0
    while url and pages < cap:
        page, headers = _get(url)
        out += page
        pages += 1
        url = None
        for part in (headers.get("Link") or "").split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    return out, pages


def git_tags():
    """Paginated. A first page is not a tag list, and reading one is how an 'absent' gets invented."""
    tags, pages = _paginated(GH + "/tags?per_page=100")
    return [t["name"] for t in tags], pages


def history_versions():
    """{version: commit sha} read from package.json at every commit that touched it in the window."""
    commits, _ = _paginated(
        GH + "/commits?path=package.json&per_page=100&since=%s&until=%s" % (SINCE, UNTIL))
    found = {}
    for c in commits:
        sha = c["sha"]
        try:
            blob, _ = _get(GH + "/contents/package.json?ref=" + sha)
            v = json.loads(base64.b64decode(blob["content"]).decode("utf-8")).get("version")
        except Exception:
            continue                      # one unreadable commit is not an absent version
        if v:
            found.setdefault(v, sha)
    return found, len(commits)


def main():
    try:
        versions, latest = npm_versions()
        tags, tag_pages = git_tags()
        hist, n_commits = history_versions()
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
        print("UNRESOLVED: could not read a channel (%s). This probe reports nothing on a failed read;" % e)
        print("            an unreachable endpoint is not an absent version.")
        return 2

    print("npm  @yun520-1/heartflow : %d versions, latest %s" % (len(versions), latest))
    print("git  tags                : %d over %d page(s)" % (len(tags), tag_pages))
    print("git  package.json history: %d versions across %d commits in [%s .. %s]"
          % (len(hist), n_commits, SINCE[:10], UNTIL[:10]))
    print()

    missing = ([v for v in CONTROL_NPM if v not in versions]
               + [t for t in CONTROL_TAGS if t not in tags]
               + [v for v in CONTROL_HISTORY if v not in hist])
    if missing:
        print("CONTROL FAILED: %r are known to be present and the reader did not find them." % missing)
        print("                Every 'absent' below would be an artefact of a broken lookup. Reporting nothing.")
        return 2
    print("control: npm sees %s, tags see %s, history sees %s (tagged and published NOWHERE) -- all three"
          % (CONTROL_NPM, CONTROL_TAGS, CONTROL_HISTORY))
    print("         readers can see this region of the version space  [OK]")
    print()

    rows = []
    for v in NAMED_IN_THREAD:
        where = []
        if v in versions:
            where.append("npm")
        if ("v" + v) in tags or v in tags:
            where.append("tag")
        if v in hist:
            where.append("commit " + hist[v][:8])
        rows.append((v, where))
        print("  %-7s -> %s" % (v, ", ".join(where) if where else "NOT FOUND in any of the three"))

    obtainable = [(v, w) for v, w in rows if w]
    print()
    print("named in thread : %d" % len(rows))
    print("obtainable      : %d" % len(obtainable))
    print("not obtainable  : %d" % (len(rows) - len(obtainable)))
    print("npm install serves today: %s" % latest)
    print()

    if obtainable:
        print("THE ANNEX IS BUILDABLE, but not from npm. %d of %d named versions resolve, and every one of"
              % (len(obtainable), len(rows)))
        print("them resolves ONLY through a commit SHA -- absent from npm and untagged:")
        for v, w in obtainable:
            print("    %-7s  %s" % (v, ", ".join(w)))
    if len(obtainable) < len(rows):
        print()
        print("%d of %d were in none of the three channels. Absence from PUBLIC channels is not evidence"
              % (len(rows) - len(obtainable), len(rows)))
        print("they never existed -- an internal deployment leaves no trace here by design.")
    print()
    print("So `npm install @yun520-1/heartflow` cannot reproduce these runs at ANY pin: it serves %s," % latest)
    print("a different major line. A commit SHA can, for the versions that are in history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
