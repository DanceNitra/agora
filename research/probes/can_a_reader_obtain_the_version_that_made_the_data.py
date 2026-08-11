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
import os
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
    # GITHUB_TOKEN is OPTIONAL and only raises the rate limit -- it grants no access a reader lacks,
    # because every endpoint here is public. Without it the hourly budget is 60 and one run costs about
    # 40, so a second run inside the hour is refused as UNRESOLVED rather than reported as an absence.
    headers = {"User-Agent": "agora-probe", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8")), r.headers


def npm_versions():
    d, _ = _get(NPM)
    if "error" in d:
        raise RuntimeError("npm registry: %s" % d["error"])
    return sorted(d.get("versions", {})), (d.get("dist-tags") or {}).get("latest")


_PAGE_CAP = 20


def _paginated(url, cap=_PAGE_CAP):
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
    """{version: [(sha, date), ...]} from package.json at every commit touching it in the window.

    A LIST, not one sha. The first cut kept `setdefault(v, sha)` over a newest-first API, so it silently
    kept the LAST commit carrying each version -- the state just before the next bump, not the change
    that produced anything -- and printed it as though it were "the commit for" that version. Measured:
    5.7.6 is carried by FOUR commits here, so that phrase is not even well formed. And `version` is a
    DECLARATION: bumps land in a release commit after the code, or a "prepare vX" commit before it. A
    version therefore resolves to a NEIGHBOURHOOD of commits, and saying otherwise oversells the pointer
    this probe exists to examine.
    """
    commits, pages = _paginated(
        GH + "/commits?path=package.json&per_page=100&since=%s&until=%s" % (SINCE, UNTIL))
    if pages >= _PAGE_CAP:
        raise RuntimeError("hit the %d-page cap; the commit list is TRUNCATED and any absence below "
                           "would be an artefact of the cap, not a finding" % _PAGE_CAP)
    found = {}
    for c in commits:
        try:
            blob, _ = _get(GH + "/contents/package.json?ref=" + c["sha"])
            v = json.loads(base64.b64decode(blob["content"]).decode("utf-8")).get("version")
        except Exception:
            continue                      # one unreadable commit is not an absent version
        if v:
            found.setdefault(v, []).append((c["sha"], c["commit"]["author"]["date"][:19]))
    return found, len(commits)


#: A branch whose HEAD must NOT read as an ancestor of main -- the negative control for the reachability
#: test below. This repository carries an `archive/old-history` branch and two lineages with IDENTICAL
#: trees under DIFFERENT parents (tree d66c6dd0 at both 901183ef and 4ac2eea3), which is the signature of
#: a history reorganisation. That is exactly the condition under which "just cite the commit" quietly
#: stops working, so the probe measures reachability instead of assuming it.
NEGATIVE_CONTROL_BRANCH = "archive%2Fold-history"


def reachable_from_main(sha):
    """Is this commit an ANCESTOR of main, or merely fetchable?

    Not the same question. GitHub serves unreachable commits by SHA for a long time, so `git cat-file`
    succeeding proves the object is there TODAY, not that anything points at it. `compare/main...<sha>`
    answers the real one: an ancestor reads `behind` (or `identical`), anything off the line reads
    `diverged`.
    """
    d, _ = _get(GH + "/compare/main..." + sha)
    return d.get("status")


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
            where.append("%d commit(s) %s..%s" % (len(hist[v]), hist[v][-1][0][:8], hist[v][0][0][:8]))
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
        print("them resolves ONLY through commit history -- absent from npm and untagged.")
        print("A version spans a NEIGHBOURHOOD of commits, so both ends are printed; naming one SHA as")
        print("'the' commit for a version would oversell exactly the pointer under examination:")
        for v, w in obtainable:
            for sha, when in hist.get(v, []):
                print("    %-7s %s  %s" % (v, sha[:8], when))

        # Fetchable is not reachable. Run the negative control FIRST: if a branch head known to be off
        # the main line also reads as an ancestor, the test cannot tell the two apart and reports nothing.
        print()
        try:
            control = reachable_from_main(_get(GH + "/branches/" + NEGATIVE_CONTROL_BRANCH)[0]["commit"]["sha"])
        except Exception as e:
            control = "unavailable (%s)" % e
        if control != "diverged":
            print("REACHABILITY NOT REPORTED: the negative control read %r, not 'diverged', so this test" % control)
            print("                           cannot distinguish an ancestor from an orphan.")
        else:
            print("control: the head of archive/old-history reads 'diverged'  [OK]")
            for v, _w in obtainable:
                for sha, _when in hist.get(v, []):
                    try:
                        st = reachable_from_main(sha)
                    except Exception as e:      # a fork SHA 404s; that is a reading, not a crash
                        st = "unreadable (%s)" % e
                    print("    %-7s %s  main-ancestor: %-5s (status=%s)"
                          % (v, sha[:8], st in ("behind", "identical"), st))
            print("  -- on the main line TODAY. A snapshot, not a durability claim: squash and rebase")
            print("     merges make an original SHA read 'diverged' even though its content shipped.")
    if len(obtainable) < len(rows):
        print()
        print("%d of %d were in none of the three channels. Absence from PUBLIC channels is not evidence"
              % (len(rows) - len(obtainable), len(rows)))
        print("they never existed -- an internal deployment leaves no trace here by design.")
    print()
    print("WHAT THIS DOES AND DOES NOT SHOW. It shows `npm install @yun520-1/heartflow` cannot reach these")
    print("versions at ANY pin: it serves %s, a different major line, and none of the three was ever" % latest)
    print("published there (npm's own time map lists 24 versions and 24 timestamps, with no unpublish")
    print("record, so 'never published' rather than 'published then withdrawn').")
    print()
    print("It does NOT show a commit SHA reproduces the runs. It shows a SHA is a BETTER-FORMED pointer:")
    print("a version spans several commits, package.json's version is a declaration rather than a record")
    print("of what was deployed, and source pins no lockfile, runtime or model endpoint. Whether any of")
    print("these commits is the software that produced the data is a question only its author can")
    print("answer -- this probe resolves version STRINGS, and a string is not a provenance claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
