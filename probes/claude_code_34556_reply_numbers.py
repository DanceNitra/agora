"""Every number in the reply to @Stratogain, re-derived against the shipped library and the draft.

Small gate for a small message, but the rule does not scale with length: three earlier messages in
these threads each carried a figure that had not been re-derived. Everything here is recomputed from
inspeximus 2.15.0 as installed in the working tree, then matched to the exact string in the draft.

Run: python probes/claude_code_34556_reply_numbers.py
"""
from __future__ import annotations

import ast
import math
import os
import pathlib
import re
import sys
import tempfile
import uuid

REPO = pathlib.Path(r"C:\Users\Danculus\inspeximus-repo")
DRAFT = (pathlib.Path(__file__).resolve().parent.parent
         / "agora_output" / "drafts" / "claude_code_34556_reply_stratogain.md")
sys.path.insert(0, str(REPO))

from inspeximus.core import Inspeximus, _prefix_collision_threshold, __version__  # noqa: E402

TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("\u2212", "-"))
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("missing: " + " | ".join(missing) if missing else "")


# ---------------------------------------------------------------- the version we claim
ck("the library really is 2.15.0", __version__ == "2.15.0", __version__)
ck("draft names it", *says("2.15.0"))

# ---------------------------------------------------------------- the four verdicts exist
d = tempfile.mkdtemp()
small = Inspeximus(path=os.path.join(d, "small.json"))
for i in range(13):
    small.remember("r%d" % i, key=uuid.uuid4().hex[:8], object=str(i))
small.flush()
m = small.identifier_contract()["measured"]["prefix_8"]
ck("13 keys give NOT_YET_MEASURABLE", m["verdict"] == "NOT_YET_MEASURABLE", m["verdict"])
ck("and the boolean is still true", m["invertible_on_this_store"] is True)
ck("draft states both", *says("13 UUID-derived keys", "`keys_that_would_be_lost: 0`",
                              "`invertible_on_this_store: true`"))
ck("the four verdict names", *says("COST_MEASURED", "NOT_YET_MEASURABLE", "ZERO_AT_SCALE",
                                   "ZERO_NO_THRESHOLD_MODEL"))
ck("the model-free companion", *says("collides_at_length", "headroom_chars", "positions_saturated"))

# ---------------------------------------------------------------- the positive control we quote
# THE ESTIMATOR IS STOCHASTIC, so one draw cannot establish a tolerance and a gate built on one
# draw would flap. Measured over 20 draws while writing this: worst-per-draw 0.60%..1.04%, median
# 0.74%. The draft quotes 1.5%; this re-measures over several draws and holds it to that.
want = [math.ceil(math.sqrt(2 * (16 ** L) * math.log(1 / 0.99))) for L in (4, 6, 8)]
per_draw = []
for _ in range(6):
    ks = [uuid.uuid4().hex for _ in range(4000)]
    got = [_prefix_collision_threshold(ks, L) for L in (4, 6, 8)]
    per_draw.append(max(abs(g - w) / w for g, w in zip(got, want)))
worst = max(per_draw)
ck("measured thresholds track the analytic ones across draws", worst < 0.015,
   "worst of %d draws %.3f%%" % (len(per_draw), 100 * worst))
ck("the analytic triple is quoted", *says("37 / 581 /", "9,292"))
# The measured triple is STOCHASTIC -- 4,000 fresh UUIDs give a different third figure every run --
# so the draft must quote the tolerance and not the sample. This check is what caught the draft
# quoting 9,233, a number that had already stopped being reproducible when it was written.
ck("draft quotes no sampled threshold",
   not any(str(g) in TEXT or "{:,}".format(g) in TEXT for g in got if g not in want),
   "last draw %s" % got)
ck("agreement is inside the bound the draft claims", worst < 0.015,
   "draft says 1.5%%, worst of %d draws %.3f%%" % (len(per_draw), 100 * worst))
ck("draft quotes the bound and the spread it came from",
   *says("20 independent draws", "0.60% to 1.04%", "median 0.74%", "within 1.5%"))

# path-like keys must collapse the threshold, which is the case a hex bound gets wrong
ck("path-like keys collapse to 1",
   _prefix_collision_threshold(["src/agora/mod_%03d.py" % i for i in range(60)], 8) == 1)
ck("draft says so", *says("collapses to 1"))

# ---------------------------------------------------------------- the live coding store
live = Inspeximus(path=r"C:\Users\Danculus\agora\.inspeximus\coding_memory.json")
c = live.identifier_contract()
p8, p12 = c["measured"]["prefix_8"], c["measured"]["prefix_12"]
# LOWER BOUNDS ON A GROWING QUANTITY, checked as bounds: every figure the draft quotes must still be
# true now, and it must stay true as the store grows. An exact count could not pass this twice.
BOUNDS = {"keys": 13900, "lost8": 1780, "groups8": 850, "lost12": 775, "thr12": 53000}
ck("draft quotes the bounds", *says("above 13,900 keys", "at least 1,780 keys",
                                    "at least 850 groups", "at least 775",
                                    "threshold above 53,000"))
ck("and every bound still holds",
   c["keys"] > BOUNDS["keys"] and p8["keys_that_would_be_lost"] >= BOUNDS["lost8"]
   and p8["groups_that_would_merge"] >= BOUNDS["groups8"]
   and p12["keys_that_would_be_lost"] >= BOUNDS["lost12"]
   and p12["threshold_population"] > BOUNDS["thr12"],
   "keys=%d lost8=%d groups8=%d lost12=%d thr12=%d"
   % (c["keys"], p8["keys_that_would_be_lost"], p8["groups_that_would_merge"],
      p12["keys_that_would_be_lost"], p12["threshold_population"]))
ck("prefix_12 really does collide below its own modelled threshold",
   p12["keys_that_would_be_lost"] > 0 and p12["threshold_population"] > c["keys"],
   "lost=%d thr=%d keys=%d" % (p12["keys_that_would_be_lost"], p12["threshold_population"], c["keys"]))
ck("the earlier published population is named", *says("11,501"))

# ---------------------------------------------------------------- the mirror grep, with its controls
def _dump(n):
    return ast.dump(n, annotate_fields=False)


files = list((REPO / "inspeximus").rglob("*.py"))
loose = tight = 0
for p in files:
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Eq, ast.NotEq)):
            L, R = n.left, n.comparators[0]
            fn = lambda x: (x.func.id if isinstance(x.func, ast.Name) else x.func.attr) \
                if isinstance(x, ast.Call) else None                      # noqa: E731
            if fn(L) and fn(L) == fn(R):
                loose += 1
            if _dump(L) == _dump(R):
                tight += 1
ck("file count", *says("34 files"))
ck("files really number that", len(files) == 34, str(len(files)))
ck("loose and tight counts", *says("23 comparisons", "returns two"))
ck("the counts are what we measured", loose == 23 and tight == 2, "loose=%d tight=%d" % (loose, tight))

planted_loose = ast.parse("x = norm(a) == norm(b)")
planted_tight = ast.parse("x = norm(s) == norm(s)")
fired_l = any(isinstance(n, ast.Compare) and isinstance(n.left, ast.Call)
              for n in ast.walk(planted_loose))
fired_t = any(isinstance(n, ast.Compare) and _dump(n.left) == _dump(n.comparators[0])
              for n in ast.walk(planted_tight))
ck("both detectors fire on planted mirrors", fired_l and fired_t)
ck("draft claims the control", *says("Both detectors fire on planted mirrors"))

# ---------------------------------------------------------------- claims we must NOT make
# THE CLAIM FLIPPED once v2.15.0 was tagged and CI published it, so the check flips with it: the
# draft may now say PyPI, and this asserts the package really is installable at that version from
# the index rather than merely that a workflow went green. The first install attempt after the
# workflow reported success returned "No matching distribution found" -- the upload had not
# propagated -- which is precisely why the green tick is not the evidence.
import json as _json
import urllib.request as _url
with _url.urlopen("https://pypi.org/pypi/inspeximus/json", timeout=30) as r:
    _pypi = _json.load(r)
ck("2.15.0 is really on PyPI", "2.15.0" in _pypi["releases"] and _pypi["info"]["version"] == "2.15.0",
   "index says latest=%s" % _pypi["info"]["version"])
ck("draft claims PyPI and says how it was verified",
   *says("on PyPI", "installing it from PyPI into a clean environment"))

bad = [c for c in checks if not c[1]]
w = max(len(c[0]) for c in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
print("\n%d/%d checks pass" % (len(checks) - len(bad), len(checks)))
if bad:
    print("\nmeasured now: thresholds %s vs analytic %s; live keys %s lost8 %s groups8 %s "
          "lost12 %s thr12 %s; mirrors loose %d tight %d"
          % (got, want, c["keys"], p8["keys_that_would_be_lost"], p8["groups_that_would_merge"],
             p12["keys_that_would_be_lost"], p12["threshold_population"], loose, tight))
sys.exit(1 if bad else 0)
