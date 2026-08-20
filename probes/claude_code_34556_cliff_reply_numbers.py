"""Every number in the gated reply to @Stratogain and @safal207 on #34556, re-derived. Non-zero on any miss.

The reply tells two people that their findings reproduce on our code and that one of my own probe
runs produced a false alarm about one of them. Every figure behind that is recomputed here against
the SHIPPED library rather than quoted from the run that produced it.

CONTROLS:
  * THE FALSE ALARM IS REPRODUCED, not just described: the random fixture that collided at 6
    characters must still collide at 6, and the deterministic one at 7, or the story in the reply
    about my own error is itself unverified.
  * THE FIX IS ASSERTED THROUGH THE PUBLIC API, so "shipped" means a caller sees it.
  * NO OVERCLAIM: the reply must not say "first", "nobody", or "proves".

Run: python probes/claude_code_34556_cliff_reply_numbers.py
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import re
import string
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

REPO = pathlib.Path(r"C:\Users\Danculus\inspeximus-repo")
sys.path.insert(0, str(REPO))
import inspeximus                                                      # noqa: E402
from inspeximus import Inspeximus                                      # noqa: E402
from inspeximus.core import _prefix_collision_threshold                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAFT = ROOT / "agora_output" / "drafts" / "claude_code_34556_reply_cliff_and_witness.md"
TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("\u2212", "-"))
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("MISSING: " + " | ".join(missing) if missing else "")


def store(keys, **kw):
    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), embed=False, **kw)
    for i, k in enumerate(keys):
        ix.remember("r%d" % i, key=k)
    ix.flush()
    return ix


def lost_at(keys, L):
    g: dict = {}
    for k in keys:
        g.setdefault(k[:L], []).append(k)
    return sum(len({*v}) - 1 for v in g.values() if len({*v}) > 1)


def saturated_at(keys, L):
    return sum(1 for i in range(L)
               if len({(k[i] if i < len(k) else "") for k in keys}) >= len({*keys}))


def verdict_at(keys, L):
    if lost_at(keys, L):
        return "COST_MEASURED"
    thr = _prefix_collision_threshold(keys, L)
    if thr is None:
        return "ZERO_NO_THRESHOLD_MODEL"
    if len(keys) < thr or saturated_at(keys, L):
        return "NOT_YET_MEASURABLE"
    return "ZERO_AT_SCALE"


# ---------------------------------------------------------------- the populations, rebuilt
rng = random.Random(20260820)
DEEP = "c:/users/x/agora/scratchpad/probe/assets-monitor/finder-v05/nested/deeper/deepest/leafdir/"
DEEP = DEEP + "x" * max(0, 148 - len(DEEP))
paths = [DEEP + n for n in ("lib/tg.mjs", "run-v05.mjs", "scan-s1.mjs", "mutation-probe.mjs")]
while len(paths) < 516:
    d = "/".join("".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(3, 9)))
                 for _ in range(rng.randint(2, 5)))
    paths.append("c:/%s/%s.py" % (d, "".join(rng.choice(string.ascii_lowercase) for _ in range(6))))
paths = sorted(set(paths))[:516]
sessions = sorted({"".join(rng.choice("0123456789abcdef") for _ in range(8)) for _ in range(3)})
unstructured = sorted({"".join(rng.choice(string.digits + string.ascii_lowercase) for _ in range(20))
                       for _ in range(400)})

ck("the path population is 516 keys", len(paths) == 516, str(len(paths)))
ck("reply says so", *says("516-key path-shaped population"))

top = min(max(len(k) for k in paths), 200)
zero_lengths = [L for L in range(1, top + 1) if verdict_at(paths, L) == "ZERO_AT_SCALE"]
ck("ZERO_AT_SCALE at no length 1 to 166", not zero_lengths and top == 166,
   "scanned 1-%d, hits %s" % (top, zero_lengths[:3]))
ck("reply says so", *says("no length from 1 to 166"))
ck("unreachable on the 3-key hash store too",
   not [L for L in range(1, 9) if verdict_at(sessions, L) == "ZERO_AT_SCALE"],
   "%d keys" % len(sessions))
ck("reply says so", *says("On a 3-key hash-shaped store\nit is unreachable too"))

cliff_paths = max((L for L in range(1, max(len(k) for k in paths) + 1) if lost_at(paths, L)), default=0)
ck("the path cliff is at 148", cliff_paths == 148, str(cliff_paths))
ck("reply says so", *says("Your cliff is at 148"))
cliff_uns = max((L for L in range(1, 21) if lost_at(unstructured, L)), default=0) + 1
# THE PROPERTY, NOT THE SAMPLE. The exact fold moves with the draw -- one run gave 3, this one 4 --
# and quoting it would be the "sample as a result" error for the fifth time today. What is stable,
# and what the argument needs, is that an unstructured store HAS a cliff, a few characters in.
ck("the unstructured control has a cliff, a handful of characters in", 2 <= cliff_uns <= 8,
   "fold %d" % cliff_uns)
ck("reply quotes the property, not the sampled integer",
   *says("at a length that moves with the draw"))
ck("no sampled fold number survives in the reply", "cliff sits at fold 3" not in TEXT)

# ---------------------------------------------------------------- MY OWN FALSE ALARM, reproduced
rng2 = random.Random(20260820)
_ = [rng2.choice("0123456789abcdef") for _ in range(0)]
drawn = sorted({"ab" + "".join(rng2.choice("0123456789abcdef") for _ in range(6)) for _ in range(400)})
built = sorted(set(["ab" + "%04d" % i + "xy" for i in range(398)] + ["ab0000zz", "ab0000zw"]))
d_col = max((L for L in range(1, 9) if lost_at(drawn, L)), default=0)
b_col = max((L for L in range(1, 9) if lost_at(built, L)), default=0)
ck("a DRAWN ab+6hex fixture collides at 6, so headroom at fold 8 is 2", d_col == 6, str(d_col))
ck("a BUILT one collides at 7, headroom 1, and the gate can fire", b_col == 7, str(b_col))
ck("reply owns the false alarm", *says("collide at 6 characters, not 7"))
ck("and says the control fires once built",
   bool(store(built).identifier_contract()["at_cliff_edge"]),
   str(store(built).identifier_contract()["at_cliff_edge"]))
ck("reply says so", *says("your control fires"))

# ---------------------------------------------------------------- what shipped, through the public API
c = store(paths).identifier_contract()
ck("cliff block reports collides_at_length 148", c["cliff"]["collides_at_length"] == 148,
   str(c["cliff"]["collides_at_length"]))
ck("and names the silence on his shape",
   c["cliff"]["why_at_cliff_edge_is_silent"] == "threshold_unreachable_at_that_fold",
   str(c["cliff"]["why_at_cliff_edge_is_silent"]))
ck("reply says so", *says("threshold_unreachable_at_that_fold"))
c149 = store(paths).identifier_contract(prefix_folds=[149])
ck("prefix_folds measures the caller's own fold", "prefix_149" in c149["measured"],
   ", ".join(sorted(k for k in c149["measured"] if k.startswith("prefix_"))))
ck("reply says so", *says("`prefix_folds=[...]`"))
tiny = store(sessions).identifier_contract()
ck("a store with no cliff says so rather than returning a falsy sentinel",
   isinstance(tiny["cliff"], dict)
   and tiny["cliff"]["why_at_cliff_edge_is_silent"] == "no_fold_merges_these_keys",
   str(tiny["cliff"]["why_at_cliff_edge_is_silent"]))
ck("reply lists the four reasons", *says("`positions_saturated`", "`no_fold_merges_these_keys`"))

# ---------------------------------------------------------------- safal's five, before and after
A, B, C, D = "aaa11111", "bbb22222", "ccc33333", "ddd44444"
abc, abd = store([A, B, C]).identifier_contract(), store([A, B, D]).identifier_contract()
ck("class 1 is now separated", abc["population_commitment"] != abd["population_commitment"],
   "%s vs %s" % (abc["population_commitment"][:12], abd["population_commitment"][:12]))
ck("and the counts really are equal, or it proves nothing", abc["keys"] == abd["keys"] == 3,
   "%d/%d" % (abc["keys"], abd["keys"]))
ck("reply quotes the byte-identical result", *says("byte-identical report"))
t1 = store([A, B, C], tenant="t1").identifier_contract()
t2 = store([A, B, C], tenant="t2").identifier_contract()
ck("class 5 is now separated", t1["population_commitment"] != t2["population_commitment"])
ck("reply says four of five landed", *says("Four landed"))
ck("reply names what is still NOT covered",
   *says("says nothing about which version wrote each record"))
lim = " ".join(store([A, B]).identifier_contract()["limits"])
ck("and the limits say it in the product too",
   "cannot tell you what it lost" in lim and "does NOT bind the writer policy" in lim)

# ---------------------------------------------------------------- no-overclaim guard
# NOVELTY PHRASINGS, not the bare word: the draft legitimately says "my first run" and "your
# first", and a substring guard on "first" flagged those. A guard that fires on correct prose gets
# switched off, which is worse than not having it.
for bad_s in ("the first to", "first implementation", "first measurement", "nobody has",
              "no one has", "proves that", "we prove", "novel"):
    ck("no overclaim: %r absent" % bad_s, bad_s.lower() not in TEXT.lower())
ck("it ends on questions, not on a result", *says("does\nanything in your fixtures distinguish"))

bad = [c_ for c_ in checks if not c_[1]]
w = max(len(c_[0]) for c_ in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
print("\n%d/%d checks pass  (inspeximus %s)" % (len(checks) - len(bad), len(checks),
                                                inspeximus.__version__))
sys.exit(1 if bad else 0)
