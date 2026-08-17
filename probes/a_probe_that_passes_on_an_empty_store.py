"""Sabotage our own identifier probe and require it to FAIL. A live receipt of a vacuous pass.

This exists because the instrument had the defect it was built to detect, and the only honest way
to keep that finding is to keep it runnable.

WHAT HAPPENED. `identifier_roundtrip_from_the_outermost_surface.py` v2 asserted seven CLI writes,
one NFC/NFD distinctness check, four reads, a near-miss control and an aggregate -- fourteen checks.
Every one carried an escape on its own precondition:

    writes      `same or rc != 0`              a refusal counted as a pass
    NFC/NFD     `distinct == 2 or len(both) < 2`   fewer than two rows counted as a pass
    reads       `found or not stored.get(name)`    an absent record counted as a pass
    near-miss   `hit == []`                     an empty store satisfies it
    aggregate   iterated only the keys that arrived

Refuse every write and all fourteen pass over a store that received nothing. 7 + 1 + 4 + 1 + 1 = 14.

READ THAT NUMBER WITH ITS LIMIT: v2 was never committed, so it is a description of a lost artifact
and you cannot check it. It is kept because it is what happened, not offered as evidence. What has a
receipt is everything below, which runs against the file sitting next to this one.

The names for this are not ours, and the nearest one is not exotic: Meszaros calls it CONDITIONAL
TEST LOGIC ("xUnit Test Patterns", Addison-Wesley 2007; xunitpatterns.com) -- branching in test code
that lets a test complete without its assertions ever executing. That is the proximate source and it
is twenty years old. The test-smell lineage it belongs to starts with van Deursen et al.,
"Refactoring Test Code" (XP2001).

The same structural defect was named independently in a stricter domain, which is worth knowing but
does not ground the software claim. IEEE 1800 defines VACUOUS SUCCESS for an assertion that holds
because its antecedent never occurred (it ships `$assertvacuousoff` and
`vpiAssertVacuousSuccessCovered` to detect and suppress it); pairing each assertion with a `cover` on
its antecedent is verification-methodology PRACTICE rather than standard text. Beer, Ben-David,
Eisner & Rodeh formalised vacuity detection in FMSD 18(2):141-163, 2001. Kupferman ("Sanity Checks in
Formal Verification", CONCUR 2006, LNCS 4137:37-51) shows coverage and vacuity are the same question
asked of the system and of the specification.

REACHABILITY is the first of the four RIPR conditions -- Ammann & Offutt, "Introduction to Software
Testing" 2nd ed. (Cambridge, 2017), extending the RIP model with Revealability. RIPR is THEIR
coinage, not Voas's: Voas's own model is PIE = Propagation, Infection, Execution ("PIE: A Dynamic
Failure-Based Technique", IEEE TSE 18(8):717-727, 1992). Conflating the two is an easy error and this
file made it before a review caught it.

WHICH MATTERS HERE, because a cover buys exactly ONE of the four. It proves the antecedent was
REACHED. It says nothing about whether the reached state became wrong (Infection), whether the wrong
state survived to the checkpoint (Propagation), or whether the assertion is sensitive enough to tell
wrong from right (Revealability). A fixture whose antecedent is covered and whose oracle cannot
distinguish a correct fold from a corrupting one is vacuous one level further in.

WHAT THIS FILE ASSERTS: that the CURRENT probe fails under the same sabotage. It is a control on a
control. If it ever reports that the sabotaged probe passed, the cover has been removed or routed
around, and the identifier result is worth nothing again.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(__file__).with_name("identifier_roundtrip_from_the_outermost_surface.py")
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
F: list = []


def check(tag, ok, text):
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {text}")


def run_variant(label: str, mutate) -> tuple[int, str]:
    src = TARGET.read_text(encoding="utf-8")
    sab = mutate(src)
    assert sab != src, f"{label}: the sabotage did not change the source, so it tests nothing"
    p = Path(tempfile.mkdtemp()) / "variant.py"
    p.write_text(sab, encoding="utf-8")
    r = subprocess.run([sys.executable, "-X", "utf8", str(p)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(TARGET.parent.parent), env=ENV)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── 1. the original defect: every CLI write refused, nothing reaches the store ───────────────
rc, out = run_variant(
    "refuse every write",
    lambda s: s.replace(
        "        r = subprocess.run(",
        "        r = subprocess.CompletedProcess(args=[], returncode=2, stdout=b'', stderr=b'')\n"
        "        _unused = (lambda *a, **k: None)(" , 1))
vacuous = "0 failure" in out
check("a sabotaged probe does NOT report a clean pass", not vacuous,
      "the run fails or aborts when nothing reaches the store"
      if not vacuous else "IT PASSED -- the cover has been removed and the result means nothing")
check("and it says WHY, not just that it failed", "COVER" in out or "ABORT" in out.upper(),
      "the output names the uncovered antecedent" if ("COVER" in out or "ABORT" in out.upper())
      else "it failed for some other reason, which is luck rather than a guard")

# ── 1b. IS THE COVER THE ONLY THING HOLDING THIS UP? ─────────────────────────────────────────
# I built this section to reconstruct the "14 of 14" -- strip the cover, refuse every write, and
# watch the sweep come back, so the headline number would be measured rather than remembered (a
# red-team pass called it unfalsifiable, and it was: v2 was never committed, so no reader can open
# the artifact the number describes). It did not come back. That is the more useful answer and it
# is the one reported, so this block now asks the question it can actually settle.
def _strip_the_cover(s: str) -> str:
    return s.replace('if len(stored) != len(CASES):', 'if False:', 1)


rc2, out2 = run_variant(
    "no cover + every write refused",
    lambda s: _strip_the_cover(s).replace(
        "        r = subprocess.run(",
        "        r = subprocess.CompletedProcess(args=[], returncode=2, stdout=b'', stderr=b'')\n"
        "        _unused = (lambda *a, **k: None)(", 1))
import re as _re
m = _re.search(r"(\d+) failure\(s\) of (\d+)", out2)
fails, total = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
# MEASURED, and it came out the OTHER WAY, which is why it is reported instead of the number I
# expected. Removing the cover does NOT restore the clean sweep: v3's assertions fail 17 of 19 on
# their own. So the cover is a second, independent guard rather than the only thing holding this
# probe up -- and the "14 of 14" from v2 CANNOT be reconstructed from anything a reader can open,
# because v2 was never committed. That number stays a description of a lost artifact; this is the
# claim that has a receipt behind it.
strict = fails > 0
check("the assertions are strict on their OWN, not merely masked by the cover", strict,
      f"cover removed, every write refused -> {fails} of {total} checks FAIL"
      if strict else f"cover removed and the probe still swept ({fails}/{total}) -- the assertions "
                     "are carrying escapes again and the cover is the only thing left")

# ── 2. the control that keeps THIS file honest ───────────────────────────────────────────────
r = subprocess.run([sys.executable, "-X", "utf8", str(TARGET)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=str(TARGET.parent.parent), env=ENV)
clean = (r.stdout or "")
# This used to say the probe reports one honest failure -- the CLI needing a UTF-8 environment -- so
# "0 failures" was NOT the healthy state. inspeximus 2.13.0 fixed that CLI crash, and the probe now
# reports 0 of 19. Left as a note because the comment outlived the condition it described by exactly
# one release, which is the ordinary way a guard's rationale goes quietly wrong.
#
# Either way the assertion below pins the COVER LINE rather than the tally: a pass count is a moving
# target that changes whenever the probe or the product changes, while "the checks below the cover
# executed" is the property this control actually needs.
ran = "COVER: every case reached the store" in clean
check("control: the unsabotaged probe still reaches its assertions", ran,
      "the cover passes and the checks below it execute"
      if ran else "the real probe no longer gets past its own cover, so check 1 proves nothing")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"VACUOUS-PASS RECEIPT: {len(bad)} failure(s) of {len(F)}" + (f"  -> {bad}" if bad else ""))
print("Keep this runnable. The finding is not that the probe was wrong once; it is that an "
      "instrument can report a clean sweep over a store that received nothing -- and that "
      "the count from the version which did so is NOT reader-verifiable, because that file "
      "was never committed. What is verifiable is above: sabotage it and it fails, name the "
      "reason, and fail on the assertions alone with the cover taken away.")
