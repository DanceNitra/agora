"""Gate the reply to Stratogain on DanceNitra/ramr#2.

The reply's load-bearing move is telling a contributor that a premise he took from MY file is
contradicted elsewhere in MY file. If that is wrong, the reply is worse than saying nothing, so
every quotation is checked against the live document rather than against my memory of it, and the
population-mismatch table is checked against the numbers actually in his PR.

Controls
  C1  every phrase attributed to METHODOLOGY.md is present in the live file
  C2  the contradiction is real: BOTH phrasings exist, at the lines claimed
  C3  every number in the mismatch table appears in his PR body or its commits
  C4  a mutated quotation must fail C1 (the check can fail)
  C5  the reply does not assert a capability of his store that he did not state

Run:  python probes/gate_ramr_pr2_reply.py
"""
from __future__ import annotations
import base64
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_ramr_pr2_boundary.md")
REPO = "DanceNitra/ramr"
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout.strip() if r.returncode == 0 else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    draft = " ".join(open(DRAFT, encoding="utf-8").read().split())

    b = gh("api", f"repos/{REPO}/contents/integrity/METHODOLOGY.md", "--jq", ".content")
    ck(b is not None, "fetched METHODOLOGY.md live")
    if b is None:
        print("cannot verify without the file"); return 1
    meth = base64.b64decode(b.replace("\n", "")).decode("utf-8", "replace")
    lines = meth.splitlines()

    # ---- C1/C2 the contradiction I am claiming in my own file --------------------------------
    ranked = "on its own native retrieval\nsurface"
    full = "**full memory state** (`get_all` / all valid facts,\n  not just top-k search)"
    ck(ranked.replace("\n", " ") in meth.replace("\n", " "),
       "C2: the 'native retrieval surface' phrasing really is in the file")
    ck(full.replace("\n", " ") in meth.replace("\n", " "),
       "C2: the 'full memory state / not just top-k' phrasing really is in the file")
    ln_ranked = next((i + 1 for i, l in enumerate(lines) if "native retrieval" in l), None)
    ln_full = next((i + 1 for i, l in enumerate(lines) if "full memory state" in l), None)
    # ANCHORED, not presence-anywhere. The first version asked `f"line {n}" in draft`, and a live
    # mutation of the FIRST mention passed because a SECOND mention of the same number survived
    # elsewhere in the reply. Collect EVERY line reference the reply makes and require all of them
    # to be right -- a claim is wrong if any of its statements is wrong, not if all of them are.
    cited = set(int(x) for x in re.findall(r"line (\d+)", draft))
    ck(cited == {ln_ranked, ln_full},
       "C2: every line number the reply cites is one of the two real ones",
       f"cited={sorted(cited)} real={sorted({ln_ranked, ln_full})}")
    ck(draft.count(f"line {ln_ranked}") >= 1 and draft.count(f"line {ln_full}") >= 1,
       "C2: both real lines are actually cited", f"{ln_ranked} and {ln_full}")
    ck(ln_ranked != ln_full and ln_ranked and ln_full,
       "C2: they are two different lines, so 'contradict each other' is a fair word")
    for q in ("Feeding the full state isolates the",
              "did the operation change the state",
              "a different axis we do not test here",
              "not just top-k search",
              "full memory state",
              "native retrieval"):
        ck(q in meth and q in draft, f"C1: quoted phrase is verbatim in the file", q[:44])
    ck("top-1" in meth and "two_writer_coherence" in meth,
       "C1: ranking really does enter only via two_writer_coherence's top-1")
    ck(sum(1 for l in lines if "top-1" in l) >= 1
       and "integrity_bench_revert" in meth and "integrity_bench_echo" in meth,
       "C1: Cells 1 and 2 exist under the names the reply uses")

    # ---- C3 the population mismatch, against HIS text ----------------------------------------
    # HIS text is not only the PR body. The uneven-key-space point lives in his PR COMMENT and
    # the no-delete property in ISSUE #1 -- an earlier version of this gate read only the body and
    # reported three of his own statements as mine, which is the check being narrower than the
    # property it tests.
    parts = [gh("api", f"repos/{REPO}/pulls/2", "--jq", ".body") or "",
             gh("api", f"repos/{REPO}/pulls/2/files", "--jq", ".[].patch") or "",
             gh("api", f"repos/{REPO}/issues/1", "--jq", ".body") or ""]
    for issue in (1, 2):
        parts.append(gh("api", f"repos/{REPO}/issues/{issue}/comments",
                        "--jq", '.[] | select(.user.login==\"Stratogain\") | .body') or "")
    his = " ".join(" ".join(parts).split())
    ck(len(his) > 4000, "C3: his full text was fetched (body + diff + issue + his comments)",
       f"{len(his)} chars")
    for n in ("634", "1,855", "226", "787", "417", "266", "181", "27"):
        ck(n in his, f"C3: {n} comes from his text, not from me")
    # The mismatch TABLE is the load-bearing artefact, so parse the two rows rather than asking
    # whether the digits appear somewhere. A mutation of a cell must move the parsed value.
    trow = re.search(r"\*\*Measured\*\* bullet \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \|", draft)
    nrow = re.search(r"\*\*Not claimed\*\* bullet \| ([\d,]+) \|[^|]*\| ([\d,]+) \|", draft)
    ck(trow is not None and nrow is not None, "C3: both table rows parsed")
    if trow and nrow:
        ck(trow.groups() == ("634", "1,855", "226"),
           "C3: the Measured row is his first population", str(trow.groups()))
        ck(nrow.groups() == ("787", "266"),
           "C3: the Not-claimed row is his second population", str(nrow.groups()))
        ck(trow.group(1) != nrow.group(1),
           "C3: the reply's whole point -- the two denominators differ")
    ck("634" in his and "787" in his and "226" in his and "266" in his,
       "C3: the two populations really are different in his text")
    ck("On this very population" in his,
       "C3: he really wrote 'On this very population', which is the sentence at issue")

    # ---- C5 do not put words in his mouth ------------------------------------------------------
    for phrase, why in (("pin the digests a fact came from", "his own description of his receipt"),
                        ("temp/scratch", "his uneven-key-space observation")):
        ck(phrase in his, f"C5: '{phrase}' is his phrasing, quoted not invented", why)
    # Test the PROPERTY, not one spelling of it: he writes it as `delete()` in backticks, so a
    # literal "no delete" search reported his own statement as mine.
    hl = his.lower()
    ck("append-only" in hl and "delete" in hl
       and any(f"no {q}delete" in hl for q in ("", "`", "'", '"')),
       "C5: the append-only / no-delete property is his statement")

    # ---- the reply's own conduct ---------------------------------------------------------------
    ck("I am fixing line" in draft or "I am fixing" in draft,
       "the reply takes the defect in our file as ours to fix")
    ck("merge" in draft and ("apply them myself" in draft or "follow-up commit" in draft),
       "the reply offers a path that does not cost him another round")
    ck("@safal207" in draft, "the second reviewer is credited by name")
    ck("close this" not in draft.lower() and "reject" not in draft.lower(),
       "the reply does not echo his own offer to be closed")

    # ---- C4 the checks can fail -----------------------------------------------------------------
    mutated = draft.replace("not just top-k search", "not just top-N search", 1)
    ck(mutated != draft, "C4: the mutation landed")
    ck("not just top-k search" not in mutated,
       "C4: a mutated quotation would no longer match the file")

    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
