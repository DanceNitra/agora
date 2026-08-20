"""COVERAGE METER for a collaborator's artifact: what fraction of it have we actually checked?

WHY THIS EXISTS. Owner, 2026-08-20, after nineteen days on luoxuejian000/edrn-dmrg-verification#2:

    "sme v tom vlakne 1 mesiac a ty nieco vydas von potom to ludia podla teba prepracuju a
     zakazdym prides s niecim novym a s opravami a zase ludia musia opravovat podla teba...
     treba spravit mechanizmus tak aby vsetko co chodi von bolo 200% lebo takto sa nikde
     neposuvame"

He is right, and the thread proves it: 70 comments, 103,038 characters from us in 19 days, and today
alone we were on our third correction of the same manuscript -- two of them corrections of our OWN
earlier corrections. Each one costs an independent researcher in Hefei a rework cycle.

THE ROOT CAUSE IS NOT CARELESSNESS, IT IS PARTIAL AUDITING. We check the part we happened to look
at, send what we found, then look again later and find more. Every "one more thing" is a round trip
we imposed. The fix is not another checklist about rigor -- it is refusing to send until the WHOLE
artifact has been looked at, so there is one round instead of five.

WHAT THIS MEASURES. Every high-precision numeric literal asserted in the artifact's prose and tables
(figure coordinate blocks excluded -- those are plotted data, not claims), and whether each one has
ever appeared in an artifact of ours. That is a lower bound on real verification, not a substitute
for it: a number appearing in our files means we have at least TOUCHED it. A number appearing
nowhere means we have never looked, and we should not be sending an opinion on the document while
that is true.

  coverage = touched / asserted

USE. Run before drafting any correction to a collaborator. If coverage is not 100%, the honest move
is to finish the audit first and send once, not to send what you have and discover the rest later.

    python tools/audit_coverage.py <artifact> [--ledger <json>]

CONTROLS
  C1 the extractor must find the numbers we KNOW are in the document (the ones already argued about)
  C2 a number that appears nowhere in our tree must be reported as untouched, so the meter can fail
  C3 the denominator is printed, always
"""

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_DIRS = ["probes", "agora_output", "tools", "research"]

# Numbers we have demonstrably argued about in this collaboration -- C1's known-present set.
KNOWN_ARGUED = ["0.124449", "0.008856", "0.061969", "24.967537", "0.190238"]


def strip_figures(text):
    """Drop tikz coordinate blocks: plotted data is not an asserted claim."""
    out, depth, i = [], 0, 0
    tokens = text.split("\\begin{tikzpicture}")
    out.append(tokens[0])
    for chunk in tokens[1:]:
        end = chunk.find("\\end{tikzpicture}")
        if end == -1:
            out.append("[FIGURE]")
        else:
            out.append("[FIGURE]" + chunk[end + len("\\end{tikzpicture}"):])
    return "".join(out)


def asserted_numbers(text, min_decimals=4):
    pat = re.compile(r"(?<![\w.])(\d+\.\d{" + str(min_decimals) + r",})(?![\w])")
    return sorted(set(pat.findall(text)))


# Files that make the meter vacuous. Measured 2026-08-20: the first version of this tool reported
# 60/60 = 100% coverage while its own C2 control FAILED. The "hits" were 77MB/74MB/25MB
# embedding-cache JSONs full of floats, where any six-digit decimal sequence occurs by chance --
# plus this file itself, which contains the control literal it searches for. A meter that finds
# every number everywhere measures nothing. Verification lives in probes and their receipts.
EXCLUDE = ("/lab/data/", "emb_cache", "embcache", "embeddings", "audit_coverage")
MAX_FILE_BYTES = 2_000_000          # a float dump is not evidence


def classify(path):
    p = path.replace('\\', "/")
    if "/drafts/" in p or p.startswith("agora_output/edrn_"):
        return "quoted"             # restating their number is not verifying it
    if p.startswith("probes/") or p.startswith("tools/") or "hotrg_edrn" in p:
        return "computed"
    return "other"


def touched(number):
    """-> (computed, quoted). COMPUTED is the only thing that counts as checked."""
    dirs = [d for d in SEARCH_DIRS if os.path.isdir(os.path.join(ROOT, d))]
    r = subprocess.run(
        ["grep", "-rl", "--include=*.py", "--include=*.json", "--include=*.md", number] + dirs,
        capture_output=True, text=True, cwd=ROOT, encoding="utf-8", errors="replace")
    files = []
    for f in (r.stdout or "").strip().split("\n"):
        if not f:
            continue
        q = f.replace('\\', "/")
        if any(x in q for x in EXCLUDE):
            continue
        try:
            if os.path.getsize(os.path.join(ROOT, f)) > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(q)
    return ([f for f in files if classify(f) == "computed"],
            [f for f in files if classify(f) == "quoted"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--min-decimals", type=int, default=4)
    ap.add_argument("--ledger", default=None,
                    help="optional JSON of {number: verdict} recording what was CHECKED, not merely touched")
    a = ap.parse_args()

    raw = open(a.artifact, encoding="utf-8", errors="replace").read()
    body = strip_figures(raw)
    nums = asserted_numbers(body, a.min_decimals)

    print(f"artifact : {a.artifact}")
    print(f"           {len(raw):,} chars, {len(body):,} after removing figure coordinate blocks")
    print(f"asserted : {len(nums)} numeric literals with >= {a.min_decimals} decimals\n")

    hit, quoted_only, miss = [], [], []
    for n in nums:
        comp, quot = touched(n)
        if comp:
            hit.append((n, comp))
        elif quot:
            quoted_only.append((n, quot))
        else:
            miss.append((n, []))

    # ---------------- controls ----------------
    fails = []
    found_known = [k for k in KNOWN_ARGUED if k in nums or any(k == n for n, _ in hit + miss)]
    c1 = len([k for k in KNOWN_ARGUED if touched(k)[0]]) >= 3
    print(f"C1 EXTRACTOR  numbers we have demonstrably argued about are visible to the meter: "
          f"{'OK' if c1 else 'FAIL'}")
    if not c1:
        fails.append("C1")
    c2 = not any(touched("9.87654321012345"))
    print(f"C2 CAN FAIL   an invented literal is reported untouched: {'OK' if c2 else 'FAIL'}")
    if not c2:
        fails.append("C2")
    print(f"C3 DENOM      {len(nums)} asserted, {len(hit)} computed | {len(quoted_only)} only quoted | {len(miss)} never\n")

    pct = 100.0 * len(hit) / len(nums) if nums else 0.0
    print("=" * 78)
    print(f"COVERAGE  {len(hit)}/{len(nums)} = {pct:.0f}%")
    print()
    if miss or quoted_only:
        print(f"NEVER TOUCHED BY US ({len(miss)}) -- we have no basis for an opinion on these:")
        vals = [n for n, _ in miss]
        for i in range(0, len(vals), 7):
            print("   " + ", ".join(vals[i:i + 7]))
        print()
        print("  Sending a correction while this list is non-empty is what produces the next round.")
        print("  Finish the audit, then send ONCE.")
    else:
        print("Every asserted number has been COMPUTED by us. A single consolidated send"
              " is defensible.")
    print("=" * 78)

    if a.ledger:
        led = json.load(open(a.ledger, encoding="utf-8")) if os.path.exists(a.ledger) else {}
        checked = [n for n in nums if led.get(n, {}).get("verdict") in ("verified", "refuted")]
        print(f"\nLEDGER    {len(checked)}/{len(nums)} carry an explicit verdict "
              f"({100*len(checked)/max(1,len(nums)):.0f}%) -- touched is a floor, verdict is the bar")

    out = os.path.join(ROOT, "probes", "audit_coverage.result.json")
    json.dump({"artifact": a.artifact, "asserted": len(nums), "touched": len(hit),
               "never": [n for n, _ in miss], "coverage_pct": round(pct, 1),
               "controls_failed": fails}, open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nreceipt -> {out}")
    return 1 if (fails or miss or quoted_only) else 0


if __name__ == "__main__":
    sys.exit(main())
