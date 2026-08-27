"""RECHECK THE FIGURES in CML#311 reply to @Stratogain.

Every figure in the draft is bound here to a receipt produced this cycle, not to prose:

  * the store figures come from `the_published_zero_is_still_a_measured_zero.result.json`, re-run
    today, and the draft's numbers are RECOMPUTED from its raw counts rather than string-matched;
  * the "four None, two 0.0" before-state is measured by importing the PUBLISHED 2.19.0 from PyPI
    in a clean venv -- the shipped artifact a reader could check, not our working tree;
  * the after-state is measured from the working tree;
  * `ok is False` on an empty store is measured on 2.19.0, because that is the property the old test
    was protecting and the claim in the draft is that it survived the change.

MUTATION CONTROLS, because a gate that only reads its own draft cannot fail: each figure is also
checked against a corrupted variant of the draft, and the gate must go red on every one. A check
that passes on both the true and the false text is measuring nothing.

Run:  python probes/gate_cml311_reply.py

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_cml311_vacuous_zero.md")
VENV = ("C:/Users/Danculus/AppData/Local/Temp/claude/C--Users-Danculus-agora/"
        "e6f8e2c8-b4c1-4269-a886-f10b2cd62521/scratchpad/v2191/Scripts/python.exe")
REPO = "C:/Users/Danculus/inspeximus-repo"
FIELDS = ("locator_coverage", "refetch_verification_coverage",
          "declared_observation_binding_coverage", "observation_binding_coverage",
          "source_enumeration_coverage", "environment_binding_coverage")
DASH = "\u2014"
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))
    return bool(ok)


PROBE_SRC = """
import json, tempfile, os, sys
EXTRA = sys.argv[1] if len(sys.argv) > 1 else ""
if EXTRA:
    sys.path.insert(0, EXTRA)
import inspeximus
from inspeximus import Inspeximus
FIELDS = {fields!r}
td = tempfile.mkdtemp()
m = Inspeximus(path=os.path.join(td, "e.json"))
r = m.check_sources()
cov = r["coverage"]
m2 = Inspeximus(path=os.path.join(td, "z.json"))
m2.remember("a record with no source at all")
cov2 = m2.check_sources()["coverage"]
print(json.dumps({{"v": inspeximus.__version__,
                   "empty": {{k: cov.get(k) for k in FIELDS}},
                   "ok": r["ok"],
                   "measured": {{k: cov2.get(k) for k in FIELDS}}}}))
"""


def probe(python_exe, extra_path=""):
    code = PROBE_SRC.format(fields=list(FIELDS))
    out = subprocess.run([python_exe, "-c", code, extra_path],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[-400:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def figures(text):
    """Pull the store figures back OUT of the draft, so the gate compares numbers, not substrings."""
    t = " ".join(text.split())
    g = {}
    m = re.search(r"\*\*([\d,]+) records across (\d+) live stores, ([\d.]+)% carrying a", t)
    if m:
        g["records"] = int(m.group(1).replace(",", ""))
        g["stores"] = int(m.group(2))
        g["source_pct"] = float(m.group(3))
    # PROPERTY, NOT SPELLING. The first version of this line pinned one exact phrasing, and a
    # humanizer pass that kept the claim intact ("zero re-fetchable. Not 0.01%. Zero.") turned the
    # check red -- a gate that fails on rewording is measuring prose, not truth. What the draft has
    # to do is state the zero AND deny the stale 0.01%, in whatever words.
    g["claims_zero"] = (re.search("[^a-z]zero[^a-z]", t, re.I) is not None
                        and re.search("[Nn]ot 0[.]01[ ]*%", t) is not None)
    g["published_date"] = "2026-08-10" in t
    g["published_pct"] = "0.01% on 2026-08-10" in t
    return g


def check_draft(text, receipt, before, after):
    """The whole gate as a pure function of the text, so a mutant can be run through it."""
    bad = []
    g = figures(text)
    for k in ("records", "stores", "source_pct"):
        if k not in g:
            bad.append("figure '%s' unreadable from the draft" % k)
    if "records" in g:
        if g["records"] != receipt["records"]:
            bad.append("records %s != receipt %s" % (g["records"], receipt["records"]))
        if g["stores"] != len(receipt["per_store"]):
            bad.append("stores %s != receipt %s" % (g["stores"], len(receipt["per_store"])))
        recomputed = round(100.0 * receipt["with_source"] / receipt["records"], 1)
        if abs(g["source_pct"] - recomputed) > 0.05:
            bad.append("source%% %s != recomputed %s" % (g["source_pct"], recomputed))
    if not g["claims_zero"]:
        bad.append("the draft no longer states the zero")
    if receipt["recheckable"] != 0:
        bad.append("receipt says %s re-checkable, draft says zero" % receipt["recheckable"])
    if not g["published_date"] or not g["published_pct"]:
        bad.append("the 2026-08-10 figure is not dated in the draft")
    if "**Four** already returned `None`" in text:
        n = sum(1 for k in FIELDS if before["empty"][k] is None)
        if n != 4:
            bad.append("before-state has %s None fields, draft says four" % n)
    else:
        bad.append("the four/two split is not stated")
    if "`ok` is still `False` on an empty store" not in text:
        bad.append("the surviving-property claim is missing")
    elif before["ok"] is not False:
        bad.append("2.19.0 does not report ok=False on an empty store")
    return bad


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    text = open(DRAFT, encoding="utf-8").read()
    receipt = json.load(open(os.path.join(
        HERE, "the_published_zero_is_still_a_measured_zero.result.json"), encoding="utf-8"))

    ck(receipt.get("control", {}).get("recheckable") == 2,
       "the re-measurement carried a control that CAN report non-zero",
       str(receipt.get("control")))
    ck(receipt["records"] > 200000 and not receipt["unreadable"],
       "the scan read every live store, none unreadable", "%s records" % f"{receipt['records']:,}")

    before = probe(VENV)
    after = probe(sys.executable, REPO)
    ck(before["v"] == "2.19.0", "before-state measured on PUBLISHED 2.19.0", before["v"])
    ck(sum(1 for k in FIELDS if before["empty"][k] is None) == 4
       and sum(1 for k in FIELDS if before["empty"][k] == 0.0) == 2,
       "2.19.0: four None, two 0.0, in the same dict")
    ck(all(after["empty"][k] is None for k in FIELDS),
       "after: all six None on an empty population")
    ck(after["measured"]["locator_coverage"] == 0.0
       and after["measured"]["environment_binding_coverage"] == 0.0,
       "after: a MEASURED zero is still 0.0 -- the control that makes the above mean something")
    ck(all(k in after["empty"] for k in FIELDS), "after: every key still present, none omitted")
    ck(before["ok"] is False, "2.19.0 reports ok=False on an empty store (the surviving property)")

    bad = check_draft(text, receipt, before, after)
    ck(not bad, "every figure in the draft matches its receipt", "; ".join(bad) or "clean")

    # ---- mutation controls: the gate must go RED on each corrupted draft ------------------------
    muts = {
        "record count": ("%s records" % f"{receipt['records']:,}", "999,999 records"),
        "store count": ("across 11 live stores", "across 4 live stores"),
        "source percent": ("92.7% carrying", "98.3% carrying"),
        "the zero": ("and zero re-fetchable. Not 0.01%. Zero.",
                     "and 0.01% re-fetchable."),
        "four/two split": ("**Four** already returned `None`",
                           "**Five** already returned `None`"),
        "surviving prop": ("`ok` is still `False` on an empty store",
                           "`ok` flipped to `True` on an empty store"),
    }
    for name, (find, repl) in muts.items():
        if find not in text:
            ck(False, "mutation '%s': anchor absent, the control cannot run" % name, find[:40])
            continue
        caught = bool(check_draft(text.replace(find, repl, 1), receipt, before, after))
        ck(caught, "mutation '%s' is caught" % name)

    # The tell list lives in tools/humanizer_tells.py, not here. Twelve gates had twelve
    # hand-typed copies and they had already drifted apart; @jason-sachs's reading on
    # claude-code#34556 also moved "honest" from a banned WORD to a banned CONSTRUCTION
    # ("the honest X"), which a per-gate word list cannot express.
    sys.path.insert(0, ROOT)
    from tools.humanizer_tells import find_tells, em_dash_rate, contraction_rate
    tells = find_tells(text)
    ck(not tells, "humanizer: no tells (shared list)",
       "; ".join("%s=%r" % (n, g) for n, g, _ in tells[:4]) or "clean")
    ck(em_dash_rate(text) < 0.8, "em-dash rate under our long-comment baseline of 1.4-1.8",
       "%.2f per 100w" % em_dash_rate(text))
    ck(contraction_rate(text) > 1.0, "contractions present -- zero is our strongest tell",
       "%.2f per 100w" % contraction_rate(text))
    ck(len(text) < 3000, "length is inside the range of our recent replies",
       "%s chars" % len(text))

    jq = '[.[] | "\\(.id) \\(.user.login)"] | last'
    last = subprocess.run(["gh", "api", "--paginate",
                           "repos/safal207/Causal-Memory-Layer/issues/311/comments",
                           "--jq", jq], capture_output=True, text=True)
    ck(last.returncode == 0 and bool(last.stdout.strip()),
       "read the room as a separate step (newest comment reported, not pinned)",
       last.stdout.strip())

    for ok, l, dt in rows:
        print("  %s  %s%s" % ("PASS" if ok else "FAIL", l, ("   [%s]" % dt) if dt else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print("\n%s/%s checks pass" % (p, len(rows)))
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
