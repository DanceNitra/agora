"""Every published count must equal the ledger. Fails the build when one drifts.

WHY THIS EXISTS. On 2026-07-28 an SEO audit of our own site found four different answers to one countable
question. public/crucible/crucible.json -- the generated artifact, and the only thing here that is derived
from the ledger -- said 22 REPRODUCED / 12 FAILED / 20 NOT_COMPUTABLE over 54 entries. Meanwhile:

    index.html            "53 claims tested, 21 reproduced"   (in meta description AND og:description,
                                                               i.e. in what Google and every share card show)
    public/track-record   "21 reproduced ... (53 verdicts)"
    crucible JSON-LD      "4 not-computable"                  (the curated EXAMPLE count, reused as if it
                                                               were the category count)
    index.html            "52 essays"                          (58 posts exist)

Nothing was fabricated: the ledger moved and the hand-typed pages did not follow. That is exactly the
failure mode this repo already knows -- a number is only trustworthy if it is DERIVED, and a check that
lives in a human's attention is not a check. On a site whose proposition is "verdicts with receipts", a
reader who opens two pages and finds the receipts disagree has learned the wrong thing about us.

This asserts the published surfaces against the ledger. Run it before publishing; wire it into CI.
Exit 0 = every surface agrees. Exit 1 = a number drifted, with the diff.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "public" / "crucible" / "crucible.json"


def ledger_counts() -> dict:
    """The single source of truth: recount the ENTRIES, do not trust the `counts` field beside them.

    A summary field sitting next to the rows it summarises is the same hand-typed-number risk one level
    down, so this recomputes and cross-checks the two.
    """
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    # RETRACTED added 2026-08-06 with the state itself (see render_crucible.render). It is counted
    # here for the same reason it exists there: a withdrawn verdict must not be silently absorbed
    # into FAILED, and it must not vanish from TOTAL either -- both would restate the ledger.
    counted = {v: sum(1 for e in entries if e.get("verdict") == v)
               for v in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE", "RETRACTED")}
    declared = data.get("counts") or {}
    if declared and declared != counted:
        raise SystemExit(f"crucible.json disagrees with ITSELF: counts={declared} but the entries "
                         f"tally to {counted}. Re-render before anything else.")
    counted["TOTAL"] = len(entries)
    return counted


def posts_published() -> int:
    """Posts that are actually live, taken from the posts index the site itself renders."""
    idx = (ROOT / "public" / "posts" / "index.html").read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r'"@type":\s*"BlogPosting"', idx))


FORECAST = ROOT / "public" / "track-record.json"


def forecast_truth() -> dict:
    """The derived forecast numbers. Committed, because the ledger they come from is not.

    server/.predictions.json is runtime state and .gitignore excludes it, so CI cannot read it. That
    is exactly why the forecasting line on the track-record page went unverified for five weeks while
    the Crucible line beside it was checked on every run: one had a committed source and the other did
    not. tools/derive_track_record.py writes this artifact; here the pages are held to it, and when
    the live ledger IS present the artifact is held to the ledger as well.
    """
    if not FORECAST.exists():
        raise SystemExit("public/track-record.json is missing -- run tools/derive_track_record.py. "
                         "Without it the forecast numbers on the site are unverifiable.")
    return json.loads(FORECAST.read_text(encoding="utf-8"))


def forecast_artifact_matches_ledger(truth: dict) -> list:
    """When the ledger is reachable, the artifact must still agree with it. Absent in CI, and the run
    SAYS which mode it took rather than reporting a silent pass."""
    ledger = ROOT / "server" / ".predictions.json"
    if not ledger.exists():
        return []
    data = json.loads(ledger.read_text(encoding="utf-8"))
    recs = data if isinstance(data, list) else (data.get("predictions") or data.get("records") or [])
    res = [r for r in recs if r.get("actual") not in (None, "", "pending")]
    live_resolved = len(res)
    live_correct = sum(1 for r in res if r.get("direction") == r.get("actual"))
    out = []
    if live_resolved != truth["resolved"]:
        out.append("public/track-record.json: says %d resolved, the live ledger has %d -- re-run "
                   "tools/derive_track_record.py" % (truth["resolved"], live_resolved))
    if live_correct != truth["correct"]:
        out.append("public/track-record.json: says %d correct, the live ledger has %d -- re-run "
                   "tools/derive_track_record.py" % (truth["correct"], live_correct))
    return out


#: Forecast claims on the published pages, checked against the derived artifact above.
FORECAST_CHECKS = [
    ("public/track-record.html", r"<b>(\d+) forecasts on record</b>", "total"),
    ("public/track-record.md", r"\*\*(\d+) forecasts on record", "total"),
]

#: A page may not claim there is no score while the ledger holds one. This is the exact sentence the
#: live site carried for five weeks, and no numeric check can reach it.
#: WIDER THAN THE OBVIOUS WORDING, because the live page said "no RESOLVED Brier score to
#: report yet" and a pattern written for "no Brier score" slid straight past it -- a guard
#: narrower than the property it guards, which is the defect this whole file exists to catch.
NO_SCORE_CLAIM = r"no\s+(?:\w+\s+){0,3}Brier score"


#: (file, regex, group -> expected key). Every published integer that restates the ledger.
CHECKS = [
    ("index.html", r"(\d+)\s+claims tested", "TOTAL"),
    ("index.html", r"(\d+)\s+reproduced", "REPRODUCED"),
    ("index.html", r"(\d+)\s+failed", "FAILED"),
    # the hyphen here is U+2011 NON-BREAKING HYPHEN, which the page wrote as the entity `&#8209;` until
    # the language split re-serialised the document and emitted the literal character. Match both, or
    # this check silently stops covering the surface -- which is what it caught itself doing.
    ("index.html", r"(\d+)\s+not(?:&#8209;|‑|-)computable", "NOT_COMPUTABLE"),
    ("index.html", r"All\s+(\d+)\s+claims", "TOTAL"),
    ("index.html", r"<b>(\d+)</b>\s+claims tested", "TOTAL"),
    # Slovak moved to its own document in the 2026-07-28 language split; the numbers must agree there too,
    # and a Slovak page quietly keeping a stale count is exactly as wrong as an English one.
    ("sk/index.html", r"<b>(\d+)</b>\s+tvrdení testovaných", "TOTAL"),
    ("sk/index.html", r"Všetkých\s+(\d+)\s+tvrdení", "TOTAL"),
    # ADDED 2026-08-06. The Slovak masthead carries its OWN failed count (`<b>N</b> zlyhaných`) and no
    # check read it, so it sat at 12 against a ledger of 14 while every English surface was verified.
    # A bilingual site needs the check on BOTH languages or the unchecked one is where the drift lives.
    ("sk/index.html", r"<b>(\d+)</b>\s+zlyhaných", "FAILED"),
    ("public/track-record.html", r"(\d+)\s+reproduced", "REPRODUCED"),
    # THE .md IS SERVED TOO, AND IT WAS NOT IN THIS LIST. Measured 2026-08-10: the html said
    # 21/13/23 over 58 verdicts while public/track-record.md said 20/10/20 over 50, was live at
    # 200, and this gate printed "31 published numbers all agree with the ledger". A checker
    # whose target list omits a live artifact reports SAFE about a file it never opened.
    ("public/track-record.md", r"(\d+)\s+reproduced", "REPRODUCED"),
    ("public/track-record.md", r"(\d+)\s+failed", "FAILED"),
    ("public/track-record.md", r"(\d+)\s+not computable", "NOT_COMPUTABLE"),
    ("public/track-record.html", r"(\d+)\s+failed", "FAILED"),
    ("public/track-record.html", r"(\d+)\s+not[- ]computable", "NOT_COMPUTABLE"),
    ("public/track-record.html", r"\((\d+)\s+verdicts\)", "TOTAL"),
    ("public/crucible/index.html", r"(\d+)\s+reproduced", "REPRODUCED"),
    ("public/crucible/index.html", r"(\d+)\s+failed", "FAILED"),
    ("public/crucible/index.html", r"(\d+)\s+not-computable", "NOT_COMPUTABLE"),
]


def main() -> int:
    truth = ledger_counts()
    truth_posts = posts_published()
    print(f"ledger: {truth['REPRODUCED']}R / {truth['FAILED']}F / {truth['NOT_COMPUTABLE']}NC "
          f"= {truth['TOTAL']} verdicts   ·   {truth_posts} posts published\n")

    bad, checked = [], 0
    for rel, pattern, key in CHECKS:
        path = ROOT / rel
        if not path.exists():
            bad.append(f"{rel}: MISSING -- cannot verify {key}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(pattern, text)
        if not hits:
            # A silently-unmatched pattern is how this check would rot into a check that cannot fail.
            bad.append(f"{rel}: pattern /{pattern}/ matched NOTHING -- the wording changed, so this "
                       f"surface is no longer being verified at all")
            continue
        for h in hits:
            checked += 1
            if int(h) != truth[key]:
                bad.append(f"{rel}: says {h} for {key}, ledger says {truth[key]}   (/{pattern}/)")

    # the essay count, same class of defect, different source of truth
    for rel, pattern in (("index.html", r"<b>(\d+)</b>\s+essays"),
                         ("sk/index.html", r"<b>(\d+)</b>\s+esejí")):
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        hits = re.findall(pattern, text)
        if not hits:
            bad.append(f"{rel}: pattern /{pattern}/ matched NOTHING -- essay count no longer verified")
        for h in hits:
            checked += 1
            if int(h) != truth_posts:
                bad.append(f"{rel}: says {h} essays, {truth_posts} posts are published")

    # ── the forecasting numbers, which are what this page exists for ──────────────────────────
    fc = forecast_truth()
    bad.extend(forecast_artifact_matches_ledger(fc))
    ledger_here = (ROOT / "server" / ".predictions.json").exists()
    print("forecasts: %d resolved / %d correct (%.1f%%) - Brier %s   [%s]"
          % (fc["resolved"], fc["correct"], 100 * fc["hit_rate"], fc["brier"],
             "artifact cross-checked against the live ledger" if ledger_here
             else "pages vs artifact only - no ledger here, as in CI"))
    for rel, pattern, key in FORECAST_CHECKS:
        path = ROOT / rel
        if not path.exists():
            bad.append("%s: MISSING -- cannot verify %s" % (rel, key))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(pattern, text)
        if not hits:
            bad.append("%s: pattern /%s/ matched NOTHING -- the forecast wording changed, so this "
                       "surface is no longer being verified at all" % (rel, pattern))
            continue
        for h in hits:
            checked += 1
            if int(h) != fc[key]:
                bad.append("%s: says %s for %s, the ledger artifact says %s"
                           % (rel, h, key, fc[key]))
    for rel in ("public/track-record.html", "public/track-record.md"):
        path = ROOT / rel
        if path.exists() and fc.get("brier") is not None:
            checked += 1
            if re.search(NO_SCORE_CLAIM, path.read_text(encoding="utf-8", errors="replace"), re.I):
                bad.append("%s: still says there is no Brier score to report, while the ledger has "
                           "%s over %d resolved forecasts" % (rel, fc["brier"], fc["resolved"]))


    if bad:
        print(f"FAIL -- {len(bad)} published number(s) disagree with the source ({checked} checked):\n")
        for b in bad:
            print(f"  {b}")
        print("\nFix the PAGE, not this check. If a number here is genuinely meant to differ from the "
              "ledger, it needs a label that says what it counts -- not a quiet mismatch.")
        return 1
    print(f"OK -- {checked} published numbers all agree with the ledger.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
