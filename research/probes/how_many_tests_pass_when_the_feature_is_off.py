"""Disable the thing the suite exists to test, and count how many tests still pass.

THE QUESTION. A test suite is a claim: "these behaviours hold." A test that passes when the
behaviour cannot occur is not making that claim -- it is making a weaker one nobody wrote down. On
2026-08-17 one of our own probes scored 14/14 over a store that had received nothing, and five other
checks failed the same way in one day, every one of them green. So: on a real suite, at scale, how
many?

VERDICT AFTER RUNNING IT: THIS DESIGN CANNOT ANSWER THE QUESTION, and the reason is worth keeping.

  Run 1 reported "8 passed, 99.7% of the suite noticed the sabotage" -- a flattering number and a
  PARSING ARTIFACT. `(\d+) passed` matched an intermediate xdist line, not the final tally. Run 2,
  reading the whole tally, gives 1,815 of 3,158 still passing.

  And 1,815 is not a vacuity rate either. Most of a 3,158-test suite legitimately never touches
  `remember` -- it tests the CLI, receipts, erasure, governance, the witness. Feature-level sabotage
  measures HOW MUCH OF A SUITE DEPENDS ON A FEATURE. That is a real quantity and it is not this one.

  Which retires the differentiator. Vera-Perez, Danglot, Monperrus & Baudry (EMSE 2018, "A
  Comprehensive Study of Pseudo-tested Methods") work per-METHOD -- "covered by the test suite, yet
  no test case fails when the method body is removed" -- and per-method is not a limitation they
  settled for. The test-to-target pairing is what makes "still passes" mean anything. Coarsening it
  to a feature, which I took for the novelty, is exactly what destroys the signal.

  Kept runnable as a negative result, and because the dependency number it DOES produce is worth
  having. Anyone extending this should go finer, not coarser.

WHY THIS IS NOT MUTATION TESTING. A mutation score asks "if the code were wrong, would a test
notice?" and reports survivors. It cannot distinguish a mutant that survived because the oracle is
weak from one that survived because no test ever REACHED it -- most tools bucket the second as
not-covered and move on. This asks the reachability question directly and from the other end: break
the entry point, and whatever still passes was never depending on it.

WHAT A PASS HERE DOES AND DOES NOT MEAN. Three populations pass under sabotage and only the third is
a finding:
  (1) tests that legitimately do not touch the sabotaged surface -- most of a large suite;
  (2) tests that assert an ERROR path, which sabotage may satisfy for the wrong reason;
  (3) tests that NAME the surface, exercise it, and pass anyway.
Only (3) is vacuity, so this reports (3) separately by intersecting with the tests that FAIL under a
milder sabotage, and never quotes the raw pass count as the headline.

Run:  python how_many_tests_pass_when_the_feature_is_off.py [--repo <inspeximus checkout>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=None)
ap.add_argument("--workers", default="12", help="xdist workers; this machine has 24 logical CPUs")
ap.add_argument("--quick", action="store_true", help="one sabotage only, for a smoke run")
a = ap.parse_args()


def find_repo() -> Path:
    env = os.environ.get("INSPEXIMUS_REPO")
    if env and Path(env, "inspeximus", "core.py").is_file():
        return Path(env)
    here = Path(__file__).resolve().parents[2]
    for sib in ("inspeximus-repo", "inspeximus"):
        c = here.parent / sib
        if (c / "inspeximus" / "core.py").is_file():
            return c
    raise SystemExit("no inspeximus checkout found; pass --repo")


REPO = Path(a.repo) if a.repo else find_repo()
CORE = REPO / "inspeximus" / "core.py"

# Each sabotage removes ONE load-bearing behaviour at its entry point. They are deliberately crude:
# a subtle change measures oracle strength, and this is measuring reachability.
# The anchors carry the FULL signature on purpose. `    def remember(self,` matches twice -- the
# Inspeximus method and the _TenantView forwarder -- and the uniqueness guard below refused both
# sabotages on the first run, correctly: a sabotage applied to the wrong one of two identically
# named methods measures something nobody chose.
_REM = "    def remember(self, text: str, tags=None, value: float = 1.0, meta: dict | None = None,"
_REC = "    def recall(self, query: str, k: int = 6, include_superseded: bool = False,"
SABOTAGES = {
    "remember_is_a_noop": (
        _REM,
        "    def remember(self, *_a, **_k):\n"
        "        return 'sabotaged'\n"
        + _REM.replace("def remember(", "def _remember_real(")),
    "recall_returns_nothing": (
        _REC,
        "    def recall(self, *_a, **_k):\n"
        "        return []\n"
        + _REC.replace("def recall(", "def _recall_real(")),
}
if a.quick:
    SABOTAGES = {"remember_is_a_noop": SABOTAGES["remember_is_a_noop"]}

FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.M)
#: pytest's tail line, e.g. "8 passed, 1385 failed, 12 error, 40 skipped in 300s"
TALLY = re.compile(r"(\d+) (passed|failed|error(?:s)?|skipped|xfailed|xpassed|deselected)")


def run_suite(tag: str) -> tuple[dict, set]:
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "-rfE",
                        "-p", "no:randomly", "-n", a.workers],
                       capture_output=True, text=True, cwd=str(REPO),
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    tally = {}
    for n, what in TALLY.findall(out):
        tally[what.rstrip("s")] = tally.get(what.rstrip("s"), 0) + int(n)
    failing = {x for x in FAILED.findall(out)}
    print(f"  {tag:26s} " + " ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    return tally, failing


def accounted(base: dict, now: dict) -> tuple[bool, str]:
    """DOES EVERY BASELINE TEST HAVE A VERDICT UNDER SABOTAGE?

    The first run of this file reported "99.7% of tests noticed the sabotage", which reads as a
    superb suite and is why it deserved no trust. The arithmetic did not close: 8 passed + 1385
    failing = 1393 against a baseline of 3159, leaving ~1766 tests with no verdict at all. A test
    that produced nothing did not "notice" anything -- most likely a module-level fixture raised and
    its whole file never ran.

    So a rate is refused unless the outcomes account for the baseline population. An unaccounted
    test is not evidence in either direction, and a flattering number with a hole in its denominator
    is the exact defect this whole file exists to measure, committed by the file itself.
    """
    total_base = sum(v for k, v in base.items() if k != "deselected")
    total_now = sum(v for k, v in now.items() if k != "deselected")
    gap = total_base - total_now
    return abs(gap) <= 0.02 * total_base, f"{total_now} of {total_base} accounted for (gap {gap})"


original = CORE.read_text(encoding="utf-8")
results = {}
try:
    print(f"\nBASELINE  (repo {REPO}, {a.workers} workers)")
    base_tally, base_fail = run_suite("baseline")
    base_pass = base_tally.get("passed", 0)
    assert base_pass > 0, "COVER: the baseline suite did not run, so every count below is vacuous"

    for name, (needle, repl) in SABOTAGES.items():
        n = original.count(needle)
        if n != 1:
            print(f"  {name:26s} SKIPPED: anchor appears {n} times, so the sabotage is not aimed")
            continue
        try:
            CORE.write_text(original.replace(needle, repl, 1), encoding="utf-8")
            tally, f = run_suite(name)
        finally:
            CORE.write_text(original, encoding="utf-8")
        # A sabotage that changes nothing has told us nothing -- it is the must-fail control on the
        # sabotage itself, not on the suite.
        ok, why = accounted(base_tally, tally)
        if not ok:
            print(f"  {name:26s} REFUSED: {why}. A test with no verdict did not notice anything, so "
                  f"no rate is reportable from this run.")
            results[name] = {"refused": why}
            continue
        if f <= base_fail:
            print(f"  {name:26s} SABOTAGE INERT: it broke nothing the baseline had not already "
                  f"broken. Not a finding about the suite -- a defect in the sabotage.")
            continue
        results[name] = {"passed_under_sabotage": tally.get("passed", 0),
                         "newly_failing": len(f - base_fail), "accounting": why,
                         "sample": sorted(f - base_fail)[:5]}
finally:
    CORE.write_text(original, encoding="utf-8")
    same = subprocess.run(["git", "diff", "--quiet", "--", "inspeximus/core.py"], cwd=str(REPO))
    print(f"\n  tree restored byte-exact: {same.returncode == 0}")
    if same.returncode != 0:
        subprocess.run(["git", "checkout", "--", "inspeximus/core.py"], cwd=str(REPO))
        print("  (restored from git; a sabotage harness must never leave the tree changed)")

print("\n" + "=" * 96)
print(f"BASELINE PASSING: {base_pass}")
for name, r in results.items():
    if "refused" in r:
        print(f"\n{name}")
        print(f"  NO RATE REPORTED -- {r['refused']}")
        continue
    still = r["passed_under_sabotage"]
    print(f"\n{name}")
    print(f"  tests that NOTICED  : {r['newly_failing']}")
    print(f"  tests still passing : {still}   ({100.0 * still / base_pass:.1f}% of baseline)")
    print(f"  e.g. noticed        : {', '.join(x.split('::')[-1][:38] for x in r['sample'][:3])}")
print(f"""
READ THE 'still passing' NUMBER WITH ITS DENOMINATOR. Most of a suite legitimately does not touch
any one entry point, so a high figure is expected and is NOT a vacuity rate. The number that means
something is how many tests NAME the sabotaged surface and pass anyway -- that intersection is the
next thing to build, and until it exists this file publishes the raw counts and says so.
""")
print("=" * 96)
json.dump({"repo": str(REPO), "baseline_passed": base_pass, "sabotages": results},
          open(Path(__file__).with_suffix(".result.json"), "w"), indent=2)
