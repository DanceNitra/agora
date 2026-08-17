"""Re-derive every number in an outward draft from its artifact, and FAIL if one does not match.

The standing rule is that a number in a document is not verified data. This closes the loop for
`agora_output/drafts/claude_code_34556_the_instrument_had_the_defect.md`: each figure below is
recomputed from the thing it describes, in this process, now -- not read back from the draft, and
not remembered from when it was written.

Two of the draft's figures deliberately have NO check here, and their absence is the finding:

  * "seven writes, one NFC/NFD check, four reads, a near-miss, an aggregate" (= 14) describes a probe
    version that was never committed. There is no artifact, so there is no check, so the draft must
    not present it as evidence -- which is why the draft says exactly that.
  * the two v2.13.0 GitHub links resolve only after the tag is pushed. LINKS_MUST_RESOLVE below turns
    that from an intention into a gate.

Run: python probes/verify_every_number_in_the_34556_draft.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("INSPEXIMUS_REPO", "C:/Users/Danculus/inspeximus-repo")
DRAFT = Path(__file__).resolve().parent.parent / "agora_output" / "drafts" / \
    "claude_code_34556_the_instrument_had_the_defect.md"
LINKS_MUST_RESOLVE = os.environ.get("CHECK_LINKS", "0") == "1"
F: list = []


def check(tag: str, ok: bool, detail: str) -> None:
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {detail}")


text = DRAFT.read_text(encoding="utf-8")


def claims(pattern: str) -> bool:
    """Is this exact figure actually IN the draft? A verifier that checks a number the draft does
    not make is measuring its own expectations -- so every check below asserts presence first."""
    return re.search(pattern, text) is not None


# ── 1. the CLI print surface ──────────────────────────────────────────────────────────────────
cli = Path(REPO, "inspeximus", "cli.py").read_text(encoding="utf-8")
n_print = len(re.findall(r"\bprint\(", cli))
# A DRAFT GETS EDITED BETWEEN RUNS, and a check on a figure the current draft does not state would
# report a defect in a claim nobody is making. So it is skipped WITH ITS REASON printed, which is a
# different thing from passing -- the same distinction this whole file exists to keep.
if claims(r"\b153\b"):
    check("153 print() calls in cli.py", n_print == 153, f"counted {n_print}; draft says 153")
    hits = [ln for ln in cli.splitlines() if "ASCII-only output" in ln]
    check("one caller out of 153 had already fixed this locally", len(hits) == 1,
          f"{len(hits)} site(s) carry the ASCII-only comment")
else:
    print(f"  [n/a ] the draft no longer cites the print() count (it is {n_print} in cli.py today)")

# ── 2. identifier_contract on the two named stores ────────────────────────────────────────────
sys.path.insert(0, REPO)
from inspeximus import Inspeximus                                    # noqa: E402

# THESE STORES ARE LIVE AND GROW WHILE YOU WORK. Between writing the draft and verifying it they
# moved 11,501 -> 11,630 keys, which is not drift to be tolerated: a published figure has to match
# the run behind it. So the rule is the one in the failure message -- update the DRAFT to whatever
# this measures, immediately before sending, and never the other way round.
EXPECT = {
    "C:/Users/Danculus/agora/.inspeximus/coding_memory.json":
        {"keys": 11600, "tol": 100, "pct": 12, "pct_tol": 1.0, "groups": 610, "grp_tol": 25,
         "label": "coding store"},
    "C:/Users/Danculus/.inspeximus/mcp_memory.json":
        {"keys": 436, "tol": 15, "pct": 95, "pct_tol": 2.0, "groups": 1, "grp_tol": 0,
         "label": "decision store"},
}
for path, e in EXPECT.items():
    if not os.path.exists(path):
        check(f"{e['label']} present", False, f"MISSING: {path} -- cannot verify its row")
        continue
    c = Inspeximus(path=path, embed=False).identifier_contract()
    assert c["keys"] > 0, f"COVER: {path} produced no keys, so every comparison below is vacuous"
    # EVERY figure here drifts, and finding that out is why the draft publishes PROPORTIONS.
    #
    # First attempt pinned exact integers. They failed within the hour -- these are live stores and
    # every hook write adds a row: 11,501 -> 11,630 -> 11,642 keys, and with them 1,373 -> 1,392 ->
    # 1,394 keys lost to prefix_8. Second attempt granted tolerance to the key TOTAL only, on the
    # stated grounds that the fold figures "did not move across any of those runs". That comment was
    # false one run later. So the tolerance is not a concession to noise, it is the correct shape for
    # a measurement of a moving population, and the DRAFT was rewritten to publish "about 12%" rather
    # than a number with an expiry date nobody printed on it.
    #
    # What is checked, therefore, is the proportion the draft actually states. A drifting integer
    # would have quietly falsified a published claim; a proportion holds while the shape holds, and
    # this fails loudly the moment the shape changes -- which is the event worth hearing about.
    lost8 = c["measured"]["prefix_8"]["keys_that_would_be_lost"]
    pct = 100.0 * lost8 / c["keys"]
    check(f"{e['label']}: prefix_8 collapses ~{e['pct']}% of keys",
          abs(pct - e["pct"]) <= e["pct_tol"],
          f"{lost8}/{c['keys']} = {pct:.1f}%; draft says ~{e['pct']}% (+-{e['pct_tol']})")
    groups = c["measured"]["prefix_8"]["groups_that_would_merge"]
    check(f"{e['label']}: ~{e['groups']} colliding groups",
          abs(groups - e["groups"]) <= e["grp_tol"],
          f"{groups} groups; draft says ~{e['groups']} (+-{e['grp_tol']})")
    drift = abs(c["keys"] - e["keys"])
    check(f"{e['label']}: key total within its published rounding", drift <= e["tol"],
          f"{c['keys']} live vs ~{e['keys']} published (drift {drift}, tolerance {e['tol']})")
    check(f"{e['label']}: casefold reported invertible",
          c["measured"]["casefold"]["invertible_on_this_store"] is True,
          "0 keys lost to casefold, as the draft's table says")

# ── 3. the sabotage harness and its 17-of-19 ──────────────────────────────────────────────────
r = subprocess.run([sys.executable, "-X", "utf8",
                    str(Path(__file__).with_name("a_probe_that_passes_on_an_empty_store.py"))],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=str(Path(__file__).resolve().parent.parent))
out = (r.stdout or "") + (r.stderr or "")
check("the vacuous-pass harness passes", "RECEIPT: 0 failure(s)" in out,
      "0 failures" if "RECEIPT: 0 failure(s)" in out else out.strip().splitlines()[-1][:100])

m = re.search(r"-> (\d+) of (\d+) checks FAIL", out)
check("cover removed -> 17 of 19 fail", bool(m) and m.group(0) == "-> 17 of 19 checks FAIL",
      (m.group(0) if m else "no tally found") + f"; draft says 17 of 19"
      + ("" if claims(r"17 of 19") else "  <- but the draft does not state it!"))

# ── 4. the mutant the new fixtures must kill ──────────────────────────────────────────────────
core_p = Path(REPO, "inspeximus", "core.py")
orig = core_p.read_text(encoding="utf-8")
LIVE = "            lost = sum(len({*v}) - 1 for v in merging.values())"
MUT = "            lost = sum(1 for v in merging.values())"
TESTS = "tests/test_the_identifier_contract_is_declared_not_inferred.py"


def run_tests() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q", "-n", "0"],
                          capture_output=True, text=True, cwd=REPO)


def _tree_is_quiescent() -> tuple[bool, str]:
    """Refuse to mutate a tree somebody else is reading.

    MEASURED THE HARD WAY: this leg ran while `tools/release_check.py` was running on the same
    checkout. The two fought over one file, this script reported THE MUTANT SURVIVES, and the
    release gate reported "the working tree CHANGED while this ran ... do not read the result above
    as a verdict" and exited 3. Both were correct about a tree neither of them owned, and the
    conclusion I nearly drew -- that the new fixtures do not kill the mutant -- was false; a manual
    re-run killed it on both tests.

    So: a temporary source mutation needs exclusive use of the tree, and the cheap check for that is
    whether git already sees it as dirty. Skipping is the safe answer, because a skip is a claim
    ("unverified") while a raced result is a claim that is wrong.
    """
    r = subprocess.run(["git", "status", "--porcelain", "--", "inspeximus/"],
                       capture_output=True, text=True, cwd=REPO)
    dirty = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return (not dirty), ("clean" if not dirty else f"dirty: {', '.join(d[3:] for d in dirty[:3])}")


quiet, why = _tree_is_quiescent()
if not quiet:
    check("SKIPPED: the mutation leg needs an exclusive tree", False,
          f"{why} -- another process may be reading or writing inspeximus/. This is UNVERIFIED, "
          "not passing: re-run when the tree is quiescent.")
elif LIVE not in orig:
    check("the mutation target still exists", False,
          "the `lost = sum(...)` line moved; this check is aimed at nothing and proves nothing")
else:
    try:
        core_p.write_text(orig.replace(LIVE, MUT, 1), encoding="utf-8")
        mutated = run_tests()
    finally:
        core_p.write_text(orig, encoding="utf-8")          # ALWAYS restore, even on exception
    restored = run_tests()
    check("the groups/lost mutant is KILLED", mutated.returncode != 0,
          "the suite fails when keys-lost is conflated with group-count"
          if mutated.returncode != 0 else
          "THE MUTANT SURVIVES -- the fixtures still cannot tell the two fields apart")
    check("control: green again once reverted", restored.returncode == 0,
          "a mutant-killer that leaves the tree red has proved nothing"
          if restored.returncode else "tree restored and passing")

# ── 5. the links the draft offers ─────────────────────────────────────────────────────────────
urls = re.findall(r"https://github\.com/\S+?\.py", text)
check("the draft offers the artifacts it describes", len(urls) >= 3,
      f"{len(urls)} artifact link(s) in the draft")
if LINKS_MUST_RESOLVE:
    for u in urls:
        try:
            with urllib.request.urlopen(u, timeout=20) as resp:
                ok, code = resp.status == 200, resp.status
        except urllib.error.HTTPError as ex:
            ok, code = False, ex.code
        except Exception as ex:                                  # noqa: BLE001
            ok, code = False, type(ex).__name__
        check(f"resolves: {u.rsplit('/', 1)[-1]}", ok, f"HTTP {code}")
else:
    print("  [skip] link resolution -- set CHECK_LINKS=1 once the tag and branch are pushed.")
    print("         A SKIP IS A CLAIM: this one says the links are UNVERIFIED, not that they work.")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"DRAFT NUMBERS: {len(bad)} unverified of {len(F)}" + (f"  -> {bad}" if bad else ""))
print("Not checked, and the draft says so itself: the '14 of 14' from a probe version that was "
      "never committed. There is no artifact to re-derive it from, so it is a description of what "
      "happened rather than evidence, and it must not be cited as the latter.")
raise SystemExit(1 if bad else 0)
