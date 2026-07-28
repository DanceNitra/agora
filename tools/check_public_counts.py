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
    counted = {v: sum(1 for e in entries if e.get("verdict") == v)
               for v in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")}
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
    ("public/track-record.html", r"(\d+)\s+reproduced", "REPRODUCED"),
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
