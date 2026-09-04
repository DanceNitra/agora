"""Phase 0. Check the CLAIMS before the prose exists, deterministically, in seconds.

WHY THIS EXISTS, with the measurement that paid for it. On 2026-09-04 one reply to a physics
co-author went through nine versions and thirteen refusals at the outbound gate. Seven of those
thirteen were the same finding: the claim had already been made, by him or by us, in the thread or
in the files he sent. Each one was found by a five-agent red team or a verification pass, at
roughly 1.3M tokens across the day. Every one of them is a string search.

The order was wrong, not the gate. The expensive passes read finished prose and judged whether it
overreached its evidence. They never asked the cheaper question first: does this need to be written
at all. This file asks that one, before a draft exists, so the skeptic and the red team are spent
on what survives.

WHAT IT CHECKS, per claim:
  1. REPEAT. Every number in the claim, and its distinctive words, searched across the thread's
     comments and the collaborator's archive. A number we or they have already published is the
     strongest signal there is, because a repeat almost always carries its figure with it.
  2. SELF-ATTRIBUTION. A claim that says "I told you" or "I answered" must match a comment we
     actually posted. On 2026-09-04 a draft described an exchange that never happened.
  3. UNIT. A claim carrying a rank, a percentile or a comparison must name its unit, because the
     same pair ranked 97th on one axis and 75th on the axis the recipient publishes.
  4. PROVENANCE. Every number must be findable in a receipt under probes/ or in their files. A
     number that exists only in the claim has nothing behind it yet.

WHAT IT IS NOT. It is not the gate. The gate is validate, storm when the claim rests on literature,
stress-claim, verify-claims and the humanizer skill. This runs BEFORE all of them and only decides
what is worth handing to them.

USAGE
    python tools/pregate.py claims.md --thread owner/repo#2 --archive <dir> [--json out.json]

`claims.md` is one claim per line, blank lines and `#` comments ignored. Write the claims first,
run this, delete what it flags, and only then write the letter.

IT FAILS CLOSED. A thread it cannot fetch, an archive it cannot read, or a claims file it cannot
parse is a refusal, because a repeat check that sees nothing reports NEW for everything.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBES = os.path.join(ROOT, "probes")

# A number long enough to be a fingerprint. "1", "20" and "2026" appear everywhere; 0.049977 does
# not. Four significant digits is where a coincidence stops being plausible.
NUM = re.compile(r"(?<![\w.])(\d+\.\d{3,}|\d{4,})(?![\w.])")

# A YEAR IS NOT A FINGERPRINT. The first live run flagged two claims as already said because
# "2026" appears in the other party's comments, which it does in every comment anyone dates.
# Four-digit integers in the calendar range carry no identity, so they are dropped.
# ONLY A PLAUSIBLE DATE IS A DATE. The first version dropped every 20xx, which threw away
# 2081 and 2070 -- a byte count and a unit count from the very comments a correction was
# quoting, leaving two of its claims with nothing to check. The window is now the years a
# GitHub thread can actually carry.
YEARISH = re.compile(r"^(199\d|20[0-3]\d)$")

# A claim that names one of OUR comments and reports what it said is a RETRACTION, not a repeat.
# The check inverts for those: the figures must be IN that comment, and a claim that quotes us
# accurately is exactly what a correction is made of. Found on the first correction this tool was
# used for, where it flagged six of eighteen claims for restating the numbers being withdrawn.
QUOTES_OUR_COMMENT = re.compile(r"\bcomment\s+(\d{6,})\b", re.I)

SELF_CLAIM = re.compile(r"\b(i (?:told|answered|said|sent|wrote|replied|showed)|"
                        r"as i (?:said|wrote|showed)|my (?:earlier|previous) (?:comment|reply))\b",
                        re.I)
RANK_WORD = re.compile(r"\b(percentile|\d+(?:st|nd|rd|th)\b|rank(?:ed|s|ing)?|median|"
                       r"above|below|typical|outlier|more than|less than|higher|lower)\b", re.I)
# THE UNIT IS THE AXIS THE RANK IS COMPUTED ON, and it has to be named explicitly. Two false
# passes were measured while building this. "percentile" contains "percent", so a substring test
# cleared the very sentence the check exists for. And a loose `of the <word>` clause cleared "the
# 97th percentile OF THE 190-pair population", where "of the population" says which set was ranked
# and nothing at all about what it was ranked on. Only these phrasings name an axis.
UNIT_WORD = re.compile(r"(units? per line|bytes? per unit|u/l|b/u|per line|per unit|"
                       r"ranked (?:on|by)|as a fraction of|in absolute terms|"
                       r"absolute (?:deviation|value|terms)|raw (?:deviation|value|score)|"
                       r"normalis(?:ed|ing) by|normaliz(?:ed|ing) by|per unit|"
                       r"divided by|relative to (?:its|each|the) own)", re.I)

STOP = set("""the a an and or but of to in on at by for with from as is are was were be been it its
this that these those we you i he she they our your their my me us them not no yes if then than so
such which who whom what when where how why all any both each few more most other some only own same
too very can will just now also into over under again further once here there when both any""".split())


def refuse(why, out=None):
    print("REFUSED: " + why)
    if out:
        json.dump({"verdict": "REFUSED", "why": why},
                  io.open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def load_claims(path, out):
    if not os.path.isfile(path):
        refuse("no claims file at %s" % path, out)
    claims = [l.strip() for l in io.open(path, encoding="utf-8")
              if l.strip() and not l.lstrip().startswith("#")]
    if not claims:
        refuse("the claims file has no claims, so every check below would pass on nothing", out)
    return claims


def fetch_thread(spec, out):
    """[(id, author, created, body)] for every comment, including the issue body itself."""
    m = re.match(r"^([\w.-]+/[\w.-]+)#(\d+)$", spec)
    if not m:
        refuse("--thread must look like owner/repo#123, got %r" % spec, out)
    repo, num = m.group(1), m.group(2)
    rows = []
    for url, kind in (("repos/%s/issues/%s" % (repo, num), "issue"),
                      ("repos/%s/issues/%s/comments" % (repo, num), "comments")):
        cmd = ["gh", "api", url] + (["--paginate"] if kind == "comments" else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            refuse("could not read %s (%s). A repeat check that cannot see the thread reports NEW "
                   "for everything." % (url, (r.stderr or "").strip()[:120]), out)
        data = json.loads(r.stdout)
        for c in (data if isinstance(data, list) else [data]):
            rows.append((str(c.get("id")), (c.get("user") or {}).get("login", "?"),
                         (c.get("created_at") or "")[:16], c.get("body") or ""))
    if not rows:
        refuse("the thread returned no comments at all", out)
    return rows


def read_archive(root, out):
    """[(relpath, text)] for every readable text file under the collaborator's archive."""
    if not root:
        return []
    if not os.path.isdir(root):
        refuse("--archive %s is not a directory" % root, out)
    files = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            if os.path.getsize(p) > 8_000_000:
                continue
            try:
                files.append((os.path.relpath(p, root),
                              io.open(p, encoding="utf-8", errors="replace").read()))
            except Exception:
                continue
    if not files:
        refuse("the archive at %s holds no readable file, so half the repeat check is blind" % root,
               out)
    return files


def receipts_text():
    out = []
    for n in sorted(os.listdir(PROBES)) if os.path.isdir(PROBES) else []:
        if n.endswith(".result.json"):
            try:
                out.append((n, io.open(os.path.join(PROBES, n), encoding="utf-8",
                                       errors="replace").read()))
            except Exception:
                pass
    return out


def words(s):
    return {w for w in re.findall(r"[a-z][a-z0-9_-]{4,}", s.lower()) if w not in STOP}


def ubiquitous_numbers(thread, ceiling=0.5):
    """Figures that appear in half the thread or more identify nothing.

    On claude-code#91188 those are 200, 25000 and 125: the caps under discussion and their ratio.
    Every participant quotes them in every comment, so matching on one says only that the claim is
    about the thread's subject.
    """
    import collections
    df = collections.Counter()
    for _i, _a, _t, body in thread:
        df.update(set(NUM.findall(body)))
    cap = max(2, int(ceiling * len(thread)))
    return {n for n, k in df.items() if k >= cap}


def rare_words(thread, ceiling=0.15):
    """Words that appear in few enough comments to fingerprint a claim.

    THE FIRST VERSION OF THE TEXT CHECK WAS WALLPAPER, and its own negative control said so. It
    counted any six shared words as a repeat, in a thread where every comment is about valleys,
    points, spreads and measurements. Three genuinely new claims came back as "already said by us"
    on the strength of "exactly, measured, point, spread, symmetry, valley". A word that appears in
    a hundred of a hundred and thirty comments identifies nothing.
    """
    import collections
    df = collections.Counter()
    for _i, _a, _t, body in thread:
        df.update(words(body))
    cap = max(2, int(ceiling * len(thread)))
    return {w for w, n in df.items() if n <= cap}, cap


def check(claims, thread, archive, receipts, ours):
    rare, cap = rare_words(thread)
    ubiq = ubiquitous_numbers(thread)
    if ubiq:
        print("  figures in half the thread or more, ignored as fingerprints: %s"
              % ", ".join(sorted(ubiq)))
    by_id = {cid: (who, when, body) for cid, who, when, body in thread}
    print("  text check uses %d word(s) appearing in <= %d of %d comments"
          % (len(rare), cap, len(thread)))
    print()
    results = []
    for c in claims:
        nums = sorted(n for n in set(NUM.findall(c))
                      if not YEARISH.match(n) and n not in ubiq)

        # RETRACTION MODE. If the claim names one of our comments, the question is not whether we
        # said this before. We did, on purpose, and the claim exists to withdraw it. What matters
        # is that the figures really are in the comment named.
        quoted = [q for q in QUOTES_OUR_COMMENT.findall(c) if q in by_id]
        if quoted:
            cid = quoted[0]
            who, when, body = by_id[cid]
            # The comment id itself is not one of its figures, and a retraction claim carries
            # the ground truth beside the published number on purpose. So the test is not "every
            # figure is in that comment" but "at least one is". Zero means we are attributing the
            # numbers to the wrong comment, which is the only failure that matters here.
            check_nums = [n for n in nums if n not in quoted]
            present = [n for n in check_nums if n.replace(",", "") in body.replace(",", "")]
            missing = [n for n in check_nums if n not in present]
            results.append({"claim": c,
                            "verdict": "QUOTES US" if present else "MISQUOTES US",
                            "numbers": nums, "hits": [], "leads": [],
                            "self_attribution": None, "unit": None,
                            "quotes_comment": cid, "quoted_author": who,
                            "figures_in_that_comment": present,
                            "figures_not_in_that_comment": missing,
                            "numbers_with_no_source": []})
            continue
        w = words(c)
        hits = []
        for cid, who, when, body in thread:
            found = [n for n in nums if n in body]
            if found:
                hits.append({"where": "comment %s" % cid, "who": who, "when": when,
                             "numbers": found})
        for rel, text in archive:
            found = [n for n in nums if n in text]
            if found:
                hits.append({"where": "their file %s" % rel, "who": "them", "when": "",
                             "numbers": found})

        # 2 SELF-ATTRIBUTION. A claim about our own history needs no number to be false: on
        # 2026-09-04 a draft said "I answered that a null does not have to be the same observation",
        # and we had never sent it. So when there is no number, fall back to word overlap.
        self_issue = None
        if SELF_CLAIM.search(c):
            ourbodies = [b for _i, a, _t, b in thread if a in ours]
            if nums:
                hit = any(any(n in b for n in nums) for b in ourbodies)
            else:
                key = w - words(" ".join(SELF_CLAIM.findall(c)))
                hit = any(len(key & words(b)) >= max(3, len(key) // 2) for b in ourbodies) if key                     else False
            if not hit:
                self_issue = ("claims we said something that no comment of ours matches. Quote the "
                              "comment id or drop the claim.")

        # 3 UNIT
        unit_issue = None
        if RANK_WORD.search(c) and not UNIT_WORD.search(c):
            unit_issue = "states a rank or comparison without naming the unit it is ranked in"

        # 4 PROVENANCE
        # PROVENANCE TOLERATES ROUNDING. A receipt holds 0.20805151 and the claim says 0.208052,
        # so an exact string test reports "no source" for a number that has one. Match on the
        # leading significant digits instead, which is what a human comparing the two would do.
        unbacked = []
        for n in nums:
            stem = n.rstrip("0")[:max(6, len(n) - 2)] if "." in n else n
            hay = [t for _f, t in receipts] + [b for _i, _a, _t, b in thread]                 + [t for _r, t in archive]
            if any(stem in h for h in hay):
                continue
            unbacked.append(n)

        # 1b TEXT-ONLY REPEATS. A claim can be a repeat with no number in it at all. On
        # 2026-09-04 "E(0) is a different graph from every other scan point" was his own sentence
        # from 3 September and this tool's first version cleared it, because it looked only at
        # figures. Distinctive-word overlap catches the ones the numbers miss.
        # A SHARED NUMBER IS EVIDENCE. SHARED WORDS ARE A LEAD. The negative control settled this
        # rather than an opinion: after restricting the match to rare words, two genuinely new
        # claims still matched on "leaves, removing, simple" and "absolute, deviation, population".
        # Those are three ordinary words in a thread of 131 comments about the same physics. So a
        # text-only match is reported for reading and never blocks, which keeps the tool from
        # becoming the thing it exists to prevent: a gate so noisy it gets switched off.
        leads = []
        if not hits and len(w & rare) >= 3:
            for cid, who, when, body in thread:
                shared = (w & rare) & words(body)
                if len(shared) >= max(3, int(0.6 * len(w & rare))):
                    leads.append({"where": "comment %s" % cid, "who": who, "when": when,
                                  "words": sorted(shared)[:6]})
                    if len(leads) >= 2:
                        break

        verdict = "NEW"
        if any(h["who"] in ours for h in hits):
            verdict = "ALREADY SAID BY US"
        elif hits:
            verdict = "ALREADY IN THEIR MATERIAL"
        if self_issue or unit_issue:
            verdict = "DEFECT"
        results.append({"claim": c, "verdict": verdict, "numbers": nums, "hits": hits[:4],
                        "leads": leads,
                        "self_attribution": self_issue, "unit": unit_issue,
                        "numbers_with_no_source": unbacked})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("claims")
    ap.add_argument("--thread", required=True, help="owner/repo#123")
    ap.add_argument("--archive", default="", help="directory of files they sent us")
    ap.add_argument("--ours", default="DanceNitra", help="comma-separated logins that are us")
    ap.add_argument("--before", default="",
                    help="ignore comments at or after this ISO timestamp. Use it to ask whether a "
                         "claim was new AT THE TIME you started, rather than after your own reply "
                         "landed in the thread.")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    out = a.json or None
    claims = load_claims(a.claims, out)
    thread = fetch_thread(a.thread, out)
    # OUR OWN LAST REPLY IS IN THE THREAD TOO. Without a cut-off, re-running this after a send
    # flags every claim in it as "already said by us", which is true and useless. The negative
    # control caught exactly that: three genuinely new claims came back OURS because the comment
    # carrying them was two minutes old.
    if a.before:
        n0 = len(thread)
        thread = [t for t in thread if t[2] < a.before]
        print("  --before %s: %d of %d comments in scope" % (a.before, len(thread), n0))
        if not thread:
            refuse("no comment predates %s, so the repeat check would see nothing" % a.before, out)
    archive = read_archive(a.archive, out)
    receipts = receipts_text()
    ours = {x.strip() for x in a.ours.split(",") if x.strip()}

    print("  %d claim(s) against %d comment(s), %d of their file(s), %d receipt(s)"
          % (len(claims), len(thread), len(archive), len(receipts)))
    print("  we are: %s" % ", ".join(sorted(ours)))
    print()

    res = check(claims, thread, archive, receipts, ours)
    bad = 0
    for i, r in enumerate(res, 1):
        tag = {"NEW": "NEW ", "ALREADY SAID BY US": "OURS", "ALREADY IN THEIR MATERIAL": "THEIRS",
               "DEFECT": "STOP", "QUOTES US": "QUOTE", "MISQUOTES US": "STOP"}[r["verdict"]]
        print("  [%s] %d. %s" % (tag, i, r["claim"][:96]))
        for h in r["hits"]:
            print("          %s (%s %s) carries %s"
                  % (h["where"], h["who"], h["when"], ", ".join(h["numbers"])))
        for l in r.get("leads", []):
            print("          READ %s (%s %s): shares %s"
                  % (l["where"], l["who"], l["when"], ", ".join(l["words"])))
        if r["self_attribution"]:
            print("          SELF: %s" % r["self_attribution"])
        if r["unit"]:
            print("          UNIT: %s" % r["unit"])
        if r["numbers_with_no_source"]:
            print("          no receipt and not in their material: %s"
                  % ", ".join(r["numbers_with_no_source"]))
        if r.get("quotes_comment"):
            print("          quotes comment %s (%s); every figure checked against it"
                  % (r["quotes_comment"], r["quoted_author"]))
            print("          in it: %s%s"
                  % (", ".join(r.get("figures_in_that_comment") or []) or "NOTHING",
                     ("   |  elsewhere (ground truth): " + ", ".join(r["figures_not_in_that_comment"]))
                     if r["figures_not_in_that_comment"] else ""))
        if r["verdict"] not in ("NEW", "QUOTES US"):
            bad += 1
        print()

    print("  %d of %d claims are worth writing. %d are not." % (len(res) - bad, len(res), bad))
    # THE RECEIPT BINDS THE NUMBERS, not just the verdict. `send_approved` refuses a draft
    # carrying a distinctive figure that no pregate run ever examined, so writing a letter with a
    # number that skipped this check is the case that closes.
    examined = sorted({n for r in res for n in r["numbers"]})
    if out:
        json.dump({"tool": "pregate", "thread": a.thread, "claims": len(res),
                   "worth_writing": len(res) - bad, "blocked": bad,
                   "numbers_examined": examined, "results": res},
                  io.open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("  written: %s" % out)
    if bad:
        print()
        print("  Delete the flagged claims, then write. Do not spend a red team on them.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
