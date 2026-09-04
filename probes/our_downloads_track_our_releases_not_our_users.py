"""Who is downloading inspeximus 245 times a day, and why does the number move when WE act?

WHY. inspeximus has 26,141 lines, 2,591 tests, 121 probes and 118 releases on PyPI. It has 6 GitHub
stars, 0 forks, 0 watchers and 0 packages depending on it. Before deciding whether the next week of
work goes into the product or into distribution, the question worth answering is whether the ~245
daily downloads are people. This measures that instead of assuming it in either direction.

THE TEST. A human user base does not notice that you cut a release. Automation notices every one:
mirrors, dependency scanners, security bots and CI caches pull each new version within hours. So the
ratio of downloads on a release day to downloads on a quiet day separates the two populations, and
it needs no access to anything private.

WHAT IT FOUND, last 30 days:

    inspeximus       3.38x   15 releases in the window, 375 on vs 111 off, daily median   245
    mem0ai           1.56x    4 releases,           157,548 vs 100,857,  daily median 104,364
    zep-cloud        0.70x    3 releases,             7,631 vs  10,837,  daily median  10,626
    langchain-core   1.17x    5 releases,         6,194,363 vs 5,284,388, daily median 5.3M

Every package with real adoption sits between 0.70 and 1.56. Ours is 3.38, more than double the
highest of them. The quietest day in the window is 17 downloads, the day after we stopped shipping.

A SECOND FIGURE POINTS THE SAME WAY. GitHub traffic over 14 days: 42 page views from 28 unique
visitors, and 3,393 clones from 239 unique cloners. Eighty times more clones than views. A person
who clones a repository has almost always looked at its page first; a scraper never does.

AND A THIRD. Of the 42 views, 32 landed on the front page. One person each opened AI_ACT.md, API.md,
COMPLIANCE.md and the integrity benchmark. The documentation we keep deepening is read by about one
person per page per fortnight.

WHAT THIS DOES NOT SAY. It does not say the downloads are worthless, that the package is bad, or
that nobody uses it. Some of those 111 quiet-day downloads are surely real. It says the headline
number is dominated by our own release cadence, so it cannot be read as adoption, and that shipping
the 119th release will move it again without meaning anything.

IT ALSO CORRECTS ONE OF OUR OWN RECORDS. The memory note `our-pypi-downloads-are-not-people` reports
"weekend median 336 beats weekday 279" as the bot signature. Re-measured today: weekday 247.5 against
weekend 233.5, so the weekday side is now higher, which is the HUMAN-shaped direction. The old tell
no longer reproduces. The conclusion survives on the release-spike evidence instead, which is why
that evidence is here and the weekday split is reported beside it rather than quietly dropped.

CONTROLS:
  * THE METRIC MUST DISCRIMINATE. It is run against packages with known real adoption. If they
    scored like us, the ratio would be measuring release cadence rather than audience, and the run
    refuses.
  * A WINDOW WITH NO RELEASE IN IT PROVES NOTHING, so a package whose window contains no release is
    reported as unmeasurable rather than scored (chromadb lands here).
  * MIRRORS ARE EXCLUDED at the API, because including them measures infrastructure by definition.
  * THE SPIKE IS A MEDIAN, not a mean, so one 1,005-download day cannot carry it.

    python probes/our_downloads_track_our_releases_not_our_users.py
"""
from __future__ import annotations

import io
import json
import os
import statistics
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "our_downloads_track_our_releases_not_our_users.result.json")

US = "inspeximus"
# Packages with adoption we do not dispute. They are the control: if they score like us, this metric
# measures how often a project releases, not whether anyone is waiting for it.
CONTROLS = ["mem0ai", "zep-cloud", "chromadb", "langchain-core"]
ADOPTED_MAX = 2.0     # declared before the data was read


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "agora-funnel-probe"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1)
    raise SystemExit(2)


def measure(pkg):
    """Release-day median over quiet-day median, last 30 days, mirrors excluded."""
    try:
        data = fetch("https://pypistats.org/api/packages/%s/overall?mirrors=false" % pkg)["data"]
    except Exception as exc:                                        # noqa: BLE001
        return {"package": pkg, "measurable": False, "why": "no download stats: %s" % str(exc)[:60]}
    rows = sorted((x["date"], x["downloads"]) for x in data
                  if x["category"] == "without_mirrors")[-30:]
    if not rows:
        return {"package": pkg, "measurable": False, "why": "empty 30-day window"}
    by_date = dict(rows)
    try:
        releases = fetch("https://pypi.org/pypi/%s/json" % pkg)["releases"]
    except Exception as exc:                                        # noqa: BLE001
        return {"package": pkg, "measurable": False, "why": "no release metadata"}
    rel_days = {f["upload_time"][:10] for _v, fs in releases.items() for f in fs}
    window = {d for d, _ in rows}
    on = [by_date[d] for d in sorted(rel_days & window)]
    off = [v for d, v in rows if d not in rel_days]
    if not on or not off:
        return {"package": pkg, "measurable": False,
                "why": "the window holds %d release days and %d quiet days; a ratio needs both"
                       % (len(on), len(off))}
    med_on, med_off = statistics.median(on), statistics.median(off)
    return {
        "package": pkg, "measurable": True,
        "releases_in_window": len(on),
        "median_on_release_day": med_on,
        "median_on_quiet_day": med_off,
        "spike": round(med_on / max(med_off, 1), 2),
        "daily_median": statistics.median([v for _d, v in rows]),
        "quietest_day": min(v for _d, v in rows),
    }


def main():
    us = measure(US)
    if not us.get("measurable"):
        refuse("cannot measure %s: %s" % (US, us.get("why")))

    controls = [measure(p) for p in CONTROLS]
    usable = [c for c in controls if c.get("measurable")]
    if len(usable) < 2:
        refuse("only %d control package(s) could be measured, so there is nothing to compare against "
               "and the ratio alone means nothing" % len(usable))

    worst_control = max(c["spike"] for c in usable)
    if worst_control > ADOPTED_MAX:
        refuse("a control package scored %.2fx, above the %.1fx line declared before the data was "
               "read. This metric is then tracking release cadence rather than audience, and our "
               "own score cannot be read as evidence of anything" % (worst_control, ADOPTED_MAX))

    verdict = ("DOWNLOADS_TRACK_OUR_RELEASES" if us["spike"] > worst_control
               else "OUR_SPIKE_IS_WITHIN_THE_ADOPTED_RANGE")

    res = {"verdict": verdict, "us": us, "controls": controls,
           "adopted_max_declared_before_reading": ADOPTED_MAX,
           "highest_control_spike": worst_control}
    json.dump(res, io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

    print("  release-day spike, last 30 days, mirrors excluded")
    print()
    print("  %-16s %8s %10s %12s %12s" % ("package", "spike", "releases", "daily median", "quietest"))
    for c in [us] + controls:
        if c.get("measurable"):
            print("  %-16s %7.2fx %10d %12s %12d"
                  % (c["package"], c["spike"], c["releases_in_window"],
                     "{:,}".format(int(c["daily_median"])), c["quietest_day"]))
        else:
            print("  %-16s %8s %s" % (c["package"], "-", c["why"]))
    print()
    print("  highest spike among packages with adoption: %.2fx" % worst_control)
    print("  ours: %.2fx" % us["spike"])
    print("  verdict: %s" % verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
