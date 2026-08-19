"""Every number in the reply to @safal207, re-derived against the shipped library and the draft.

The message tells him his examples do not reproduce as stated, so each figure behind that has to be
recomputed rather than quoted from the run that produced it. Exits non-zero on any mismatch.

Run: python probes/safal_cliff_reply_numbers.py
"""
from __future__ import annotations

import os
import pathlib
import random
import re
import string
import sys
import tempfile

REPO = pathlib.Path(r"C:\Users\Danculus\inspeximus-repo")
sys.path.insert(0, str(REPO))
import inspeximus                                                      # noqa: E402
from inspeximus import Inspeximus                                      # noqa: E402
from inspeximus.core import _prefix_collision_threshold                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAFT = ROOT / "agora_output" / "drafts" / "claude_code_34556_reply_safal_cliff.md"
TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("\u2212", "-"))
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("missing: " + " | ".join(missing) if missing else "")


def store(keys):
    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), embed=False)
    for i, k in enumerate(keys):
        ix.remember("r%d" % i, key=k)
    ix.flush()
    return ix


def lost_at(keys, L):
    g: dict = {}
    for k in keys:
        g.setdefault(k[:L], []).append(k)
    return sum(len({*v}) - 1 for v in g.values() if len({*v}) > 1)


ck("the library is 2.17.0", inspeximus.__version__ == "2.17.0", inspeximus.__version__)
ck("draft names it", *says("2.17.0"))
# The claim that it is installable is checked against the index, not against a green workflow: the
# first install after each of the last two releases returned "No matching distribution found" while
# the publish job was already reporting success.
# THE SIMPLE INDEX, not the JSON API: pip reads the former, and the two do not update together.
# Measured minutes apart today -- `pip install inspeximus==2.17.0` succeeded while the JSON API still
# named 2.16.0 as latest and did not list the release at all. The claim is that a user can install
# it, so the check is the file list a user's installer resolves against.
import urllib.request as _url
with _url.urlopen("https://pypi.org/simple/inspeximus/", timeout=30) as _r:
    _index = _r.read().decode("utf-8", "replace")
ck("2.17.0 is on the index pip reads", "inspeximus-2.17.0-py3-none-any.whl" in _index,
   "the JSON API can lag this by minutes in either direction")
ck("draft says how that was verified", *says("installing it from the index into a clean environment"))

# ---------------------------------------------------------------- his two populations, as run
rng = random.Random(20260819)
mono = sorted({"src/co/%s/index.ts" % "".join(rng.choice(string.ascii_letters) for _ in range(8))
               for _ in range(4000)})
ts = "01JBKQ8V"
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ulid = sorted({ts + "".join(rng.choice(B32) for _ in range(18)) for _ in range(4000)})
ck("both populations are 4,000 keys", len(mono) == 4000 and len(ulid) == 4000,
   "%d / %d" % (len(mono), len(ulid)))
ck("draft says so", *says("4,000 paths sharing a directory prefix, 4,000\nULIDs sharing a timestamp"))

cm = store(mono).identifier_contract()["measured"]
cu = store(ulid).identifier_contract()["measured"]
cells = {("monorepo paths", "prefix_8"): cm["prefix_8"],
         ("ULID burst", "prefix_8"): cu["prefix_8"],
         ("ULID burst", "prefix_12"): cu["prefix_12"]}
for (pop, fold), m in cells.items():
    ck("%s %s is COST_MEASURED" % (pop, fold), m["verdict"] == "COST_MEASURED", m["verdict"])
    ck("%s %s above its own threshold" % (pop, fold), m["threshold_population"] < 4000,
       "thresh %d" % m["threshold_population"])
ck("the three-row table", *says("3,948", "3,999", "145"))
ck("the counts are what we measured",
   cm["prefix_8"]["keys_that_would_be_lost"] == 3948
   and cu["prefix_8"]["keys_that_would_be_lost"] == 3999
   and cu["prefix_12"]["keys_that_would_be_lost"] == 6,
   "%d %d %d" % (cm["prefix_8"]["keys_that_would_be_lost"],
                 cu["prefix_8"]["keys_that_would_be_lost"],
                 cu["prefix_12"]["keys_that_would_be_lost"]))
ck("thresholds 2, 1 and 145", *says("4,000 keys against 2, 1 and\n145"))
ck("thresholds are right",
   (cm["prefix_8"]["threshold_population"], cu["prefix_8"]["threshold_population"],
    cu["prefix_12"]["threshold_population"]) == (2, 1, 145),
   "%d %d %d" % (cm["prefix_8"]["threshold_population"], cu["prefix_8"]["threshold_population"],
                 cu["prefix_12"]["threshold_population"]))

# ---------------------------------------------------------------- his scale, 50,000 paths
rng2 = random.Random(7)
big = sorted({"src/co/%s/index.ts" % "".join(rng2.choice(string.ascii_letters) for _ in range(8))
              for _ in range(50000)})
l12, l13 = lost_at(big, 12), lost_at(big, 13)
thr13 = _prefix_collision_threshold(big, 13)
# THE PROPERTY, NOT THE SAMPLE. The merge count at fold 12 depends on which suffixes the draw
# produced -- 6 on one run and 7 on the next -- so the draft quotes where the cliff SITS, which is
# stable, and this asserts that rather than a number that changes with the seed.
ck("at 50,000 the cliff sits between 12 and 13", l12 > 0 and l13 == 0, "%d / %d" % (l12, l13))
ck("and the threshold at 13 is near 19,900", 19000 < thr13 < 21000, str(thr13))
ck("draft quotes the property", *says("50,000 monorepo-shaped paths", "merges a handful of keys",
                                      "near 19,900"))
ck("draft does not quote a sampled merge count",
   "merges 6 keys" not in TEXT and "merges 7 keys" not in TEXT)

# ---------------------------------------------------------------- the cliff fixture and its flip
fixture = [("grp%08d" % g) + c + "-tail" for g in range(20) for c in string.ascii_lowercase]
c1 = store(fixture).identifier_contract()
c2 = store(fixture + ["grp00000000a-other"]).identifier_contract()
ck("the fixture is 520 keys", len(fixture) == 520, str(len(fixture)))
ck("it sits at the cliff", c1["at_cliff_edge"] == ["prefix_12"], str(c1["at_cliff_edge"]))
ck("one key flips it", c2["measured"]["prefix_12"]["verdict"] == "COST_MEASURED"
   and c2["at_cliff_edge"] == [], str(c2["at_cliff_edge"]))
ck("draft states the flip", *says("520-key fixture", "adding a single\nkey flips"))

# ---------------------------------------------------------------- the false-positive check
live = {"agora coding memory": r"C:\Users\Danculus\agora\.inspeximus\coding_memory.json",
        "server coding memory": r"C:\Users\Danculus\agora\server\.inspeximus\coding_memory.json",
        "dungeon coding memory": r"C:\Users\Danculus\agora\agora-game-server\.inspeximus\coding_memory.json",
        "agora decisions": r"C:\Users\Danculus\agora\.inspeximus\decisions.json"}
fired, sizes = [], []
for name, path in live.items():
    if not pathlib.Path(path).exists():
        continue
    c = Inspeximus(path=path).identifier_contract()
    sizes.append(c["keys"])
    if c["at_cliff_edge"]:
        fired.append(name)
ck("four live stores were reachable", len(sizes) == 4, str(sizes))
ck("it fires on none of them", not fired, str(fired))
# A BOUND, because the store grows while the message is written: the draft first said 14,112 and by
# the time it was ready that store held 14,141. The same correction, for the fourth time today.
ck("draft quotes a bound rather than a stale count", *says("over 14,000 keys", "917, 374 and 6"))
ck("the bound holds and the small ones are exact",
   max(sizes) > 14000 and sorted(sizes) == sorted([max(sizes), 917, 374, 6]),
   "sizes now %s" % sorted(sizes, reverse=True))
ck("no stale exact count survives in the draft", "14,112" not in TEXT)

bad = [c for c in checks if not c[1]]
w = max(len(c[0]) for c in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
print("\n%d/%d checks pass" % (len(checks) - len(bad), len(checks)))
if bad:
    print("\nmeasured: lost %d/%d/%d, thresh %d/%d/%d, 50k %d/%d thr %d, live %s"
          % (cm["prefix_8"]["keys_that_would_be_lost"], cu["prefix_8"]["keys_that_would_be_lost"],
             cu["prefix_12"]["keys_that_would_be_lost"], cm["prefix_8"]["threshold_population"],
             cu["prefix_8"]["threshold_population"], cu["prefix_12"]["threshold_population"],
             l12, l13, thr13, sizes))
sys.exit(1 if bad else 0)
