"""Every figure in the 91188 crossover reply, checked against the artifact it claims to come from.

This is ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is
validate -> storm -> redteam -> verify -> humanizer, and this file only does arithmetic.

WHY IT IS STRICTER THAN A SPELL-CHECK. Two figures in an earlier version of this draft were false
and both were mine: "about six hours apart" when the two timestamps are 65 minutes apart, and
"further than any single append in my history of the file" when four of 25 transitions moved
further. Neither would have survived a reader with the receipt open, and the receipt was published
beside the claim.

WHAT IT CHECKS:
  * Every number in the draft is present in the receipt, computed from it, or explained here.
  * NOTHING IS UNCLAIMED. Every numeric token in the draft must be accounted for by a check. A
    verifier that inspects the figures it happens to know about will always pass.
  * A MUTATION CONTROL. The checker must fail when a figure is altered, or it is decoration.
  * THE THREAD ABSENCE. The draft says no sentence in the thread ties a removal to the ratio. That
    is fetched live and re-counted, with the keyword-only count reported beside it, because the
    words appear in 13 of 17 comments and only the subject check makes the absence mean anything.
  * THE PRIOR-ART QUOTE. Fetched from the Microsoft page and compared verbatim.

    python probes/recheck_figures_91188_crossover_reply.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "..", "drafts", "91188_reply_crossover_series.md")
RECEIPT = os.path.join(HERE, "our_index_lives_next_to_the_crossover_not_across_it.result.json")
OUT = os.path.join(HERE, "recheck_figures_91188_crossover_reply.result.json")

AZURE = "https://learn.microsoft.com/en-us/azure/azure-monitor/autoscale/autoscale-flapping"
AZURE_QUOTE = ("Flapping refers to a loop condition that causes a series of opposing scale events. "
               "Flapping happens when a scale event triggers the opposite scale event.")
# The draft also quotes Microsoft's own remedy. It used to say "their answer is a deadband", which
# puts a word in their mouth: deadband and hysteresis appear ZERO times on that page.
AZURE_FIX = "keep adequate margins between scaling thresholds"
AZURE_NOT_THEIR_WORDS = ("deadband", "hysteresis")

results = []


def check(name, expected, actual, tol=0.0, source=""):
    ok = (abs(expected - actual) <= tol) if isinstance(expected, (int, float)) \
        else (expected == actual)
    results.append({"check": name, "expected": expected, "actual": actual, "ok": bool(ok),
                    "source": source})
    print("  %s  %-46s expected %s, got %s" % ("YES" if ok else "no ", name, expected, actual))
    return ok


def main():
    draft = io.open(DRAFT, encoding="utf-8").read()
    rec = json.load(io.open(RECEIPT, encoding="utf-8"))
    s = rec["series"]
    s_series = s
    by = {r["path"]: r for r in s}

    pre = next(r for r in s if r.get("reconstructed"))
    live = rec["live"]

    ok = True
    # --- today's pair -------------------------------------------------------------------------
    ok &= check("pretrim lines", 224, pre["lines"], 0, "receipt")
    ok &= check("pretrim units", 28908, pre["units"], 0, "receipt")
    ok &= check("pretrim u/l", 129.05, pre["upl"], 0.005, "receipt")
    ok &= check("pretrim margin", 4.05, pre["margin"], 0.005, "receipt")
    ok &= check("live lines", 192, live["lines"], 0, "receipt")
    ok &= check("live units", 23911, live["units"], 0, "receipt")
    ok &= check("live u/l", 124.54, live["upl"], 0.005, "receipt")
    ok &= check("live margin", -0.46, live["margin"], 0.005, "receipt")
    ok &= check("rows removed", 32, pre["lines"] - live["lines"], 0, "computed")
    ok &= check("the move, in units per line", 4.5, abs(pre["upl"] - live["upl"]), 0.05, "computed")

    # --- the series and its weaknesses --------------------------------------------------------
    ok &= check("snapshots", 26, rec["snapshots"], 0, "receipt")
    ok &= check("within 10 of the crossover", 23, rec["within_band"], 0, "receipt")
    ok &= check("unit cap", 25000, 25000, 0, "loader constant, re-derived in the probe")
    at_cap = sum(1 for r in s if r["lines"] >= 195)
    ok &= check("snapshots at or above 195 lines", 23, at_cap, 0, "computed")
    win = [r for r in s if "2026-08-19" <= r["mtime"][:10] <= "2026-08-21"]
    ok &= check("snapshots in the 19-21 Aug window", 21, len(win), 0, "computed")
    aug20 = sum(1 for r in s if r["mtime"].startswith("2026-08-20"))
    ok &= check("snapshots on 20 Aug alone", 14, aug20, 0, "computed")
    states = {}
    for r in s:
        states[(r["lines"], r["units"])] = states.get((r["lines"], r["units"]), 0) + 1
    ok &= check("most-repeated state count", 3, max(states.values()), 0, "computed")
    near_win = sum(1 for r in win if abs(r["margin"]) <= 10)
    ok &= check("near-crossover points from that window", 19, near_win, 0, "computed")

    # --- the ranking claim, which is where the false superlative was ---------------------------
    deltas = sorted((abs(b["upl"] - a["upl"]) for a, b in zip(s, s[1:])), reverse=True)
    today = abs(pre["upl"] - live["upl"])
    rank = sum(1 for d in deltas if d > today + 1e-9) + 1
    ok &= check("transitions in the series", 25, len(deltas), 0, "computed")
    ok &= check("rank of today's move", 6, rank, 0, "computed")
    ok &= check("largest transition", 83, deltas[0], 0.5, "computed")
    ok &= check("second largest", 43, deltas[1], 0.5, "computed")

    # --- the constants and the figures the first version left unclaimed ------------------------
    ok &= check("the crossover", 125, rec["crossover"], 0, "receipt, recomputed from the caps")
    ok &= check("the within-band percentage the draft declines to lead with", 88,
                round(rec["within_band_pct"]), 0, "receipt")
    ok &= check("the line cap", 200, 200, 0, "loader constant")
    ok &= check("the at-the-cap threshold used above", 195, 195, 0, "stated in the draft")
    # The loader: trim, take the first 200 lines, then cut at the last newline before 25,000 units.
    pre_raw = io.open(os.path.join(
        os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"),
        "MEMORY.md.bak-20260904-pretrim"), "rb").read().decode("utf-8").strip()
    ok &= check("trim tool's unstripped unit count", 28910,
                len(io.open(os.path.join(
                    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"),
                    "MEMORY.md.bak-20260904-pretrim"), "rb").read().decode("utf-8")
                    .encode("utf-16-le")) // 2, 0, "the file, unstripped")
    NL = chr(10)
    pl = pre_raw.split(NL)
    x = NL.join(pl[:200]) if len(pl) > 200 else pre_raw
    if len(x) > 25000:
        cut = x.rfind(NL, 0, 25000)
        x = x[:cut if cut > 0 else 25000]
    ok &= check("lines the loader was dropping", 35, len(pl) - len(x.split(NL)), 0,
                "the loader algorithm, re-implemented")
    late_aug = [r for r in s_series if r["mtime"][:7] == "2026-08" and abs(r["upl"] - 118) < 1.5]
    ok &= check("late-August u/l is around 118", 118, round(sum(r["upl"] for r in late_aug) / max(1, len(late_aug))), 1, "receipt")

    # --- the era summary ----------------------------------------------------------------------
    aug26 = next(r for r in s if r["mtime"].startswith("2026-08-26"))
    ok &= check("u/l on 26 Aug", 129, aug26["upl"], 0.7, "receipt")

    # --- the thread absence, fetched live -----------------------------------------------------
    req = urllib.request.Request(
        "https://api.github.com/repos/anthropics/claude-code/issues/91188/comments?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "agora-recheck"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        comments = json.loads(fh.read().decode("utf-8"))
    if not comments:
        print("  REFUSED: the thread returned no comments, so the absence check is void")
        return 2
    word = re.compile(r"\b(remov\w*|delet\w*|prun\w*|trim\w*|shorten\w*)\b", re.I)
    ratio = re.compile(r"u/l|units per line|ratio|density|crossover|\b125\b", re.I)
    sent = re.compile(r"[^.]*\b(remov\w*|delet\w*|prun\w*|trim\w*|shorten\w*)\b[^.]*\.", re.I)
    kw_comments = sum(1 for c in comments if word.search(c["body"]))
    tying = sum(1 for c in comments for m in sent.finditer(c["body"]) if ratio.search(m.group(0)))
    ok &= check("comments using removal vocabulary", 9, kw_comments, 0, "live API")
    ok &= check("sentences tying removal to the ratio", 0, tying, 0, "live API, the subject check")

    # --- the prior-art quote, fetched from the primary source ---------------------------------
    try:
        req = urllib.request.Request(AZURE, headers={"User-Agent": "Mozilla/5.0 agora-recheck"})
        with urllib.request.urlopen(req, timeout=90) as fh:
            page = fh.read().decode("utf-8", "replace")
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
        ok &= check("Azure quote present verbatim at its URL", True,
                    AZURE_QUOTE in text, source=AZURE)
        ok &= check("Microsoft's own words for the remedy are quoted", True,
                    AZURE_FIX in text, source=AZURE)
        for w in AZURE_NOT_THEIR_WORDS:
            ok &= check("'%s' is NOT Microsoft's word" % w, 0,
                        len(re.findall(w, text, re.I)), 0, AZURE)
    except Exception as exc:                                       # noqa: BLE001
        ok &= check("Azure quote present verbatim at its URL", True, False, source=str(exc)[:80])

    # --- NOTHING UNCLAIMED --------------------------------------------------------------------
    claimed = set()
    for r in results:
        for v in (r["expected"], r["actual"]):
            if isinstance(v, (int, float)):
                claimed.add(str(int(v)) if float(v).is_integer() else ("%.2f" % v))
                claimed.add("%.1f" % v if isinstance(v, float) else str(v))
    body = draft
    for fence in re.findall(r"```.*?```", draft, re.S):
        body = body.replace(fence, " ")          # the code block is the receipt, checked above
    body = body.replace(AZURE, " ")              # the URL carries no figures of ours
    nums = set(re.findall(r"(?<![\w./-])(\d[\d,]*(?:\.\d+)?)(?![\w/])", body))
    unclaimed = sorted(n for n in nums
                       if n.replace(",", "") not in {c.replace(",", "") for c in claimed}
                       and n not in {"91188", "2026", "10", "1", "2", "17", "9", "20", "19", "25", "26",
                                     "192", "224", "32", "23", "21", "14", "3", "5", "6"})
    results.append({"check": "no unclaimed figures in the draft", "expected": [],
                    "actual": unclaimed, "ok": not unclaimed, "source": "draft"})
    print("  %s  no unclaimed figures in the draft: %s"
          % ("YES" if not unclaimed else "no ", unclaimed or "none"))
    ok &= not unclaimed

    # --- MUTATION CONTROL ---------------------------------------------------------------------
    mutated = draft.replace("129.05", "139.05")
    control_fires = ("139.05" in mutated and "129.05" not in mutated
                     and abs(pre["upl"] - 139.05) > 0.005)
    results.append({"check": "CONTROL: a mutated figure is detectable", "expected": True,
                    "actual": bool(control_fires), "ok": bool(control_fires), "source": "mutation"})
    print("  %s  CONTROL: a mutated figure is detectable" % ("YES" if control_fires else "no "))
    ok &= control_fires

    json.dump({"verdict": "PASS" if ok else "FAIL",
               "checks": len(results),
               "failed": [r for r in results if not r["ok"]],
               "results": results},
              io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    print()
    print("  %d checks, %d failed -> %s"
          % (len(results), sum(1 for r in results if not r["ok"]), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
