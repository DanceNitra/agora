"""Every figure in the index-window piece, re-derived and matched against the text. Exits non-zero on any miss.

WHY THIS EXISTS. Every number in that piece was originally measured against the LIVE `MEMORY.md`,
which changed four times in one day and no longer holds any of the states the piece describes. That
is the "lab receipts rotate out" failure: a draft outliving its evidence. So the four states are
pinned as fixtures and the numbers are re-derived from them here, rather than quoted from a run
nobody can repeat.

WHAT IS RE-DERIVED vs WHAT IS READ. Two classes, and the report says which is which for every line:
  * RE-DERIVED here, from pinned fixtures, no model calls: everything about an index STATE --
    the un-crowding, the deployment, the load-window ladder, the rebuilt index.
  * READ from a committed result file: the five line-writing VARIANTS and the length arm, which
    needed a model to generate lines. Their generated lines live in the probe caches beside them, so
    they are reproducible, but not in this file and not for free.

CONTROLS:
  * THE FIXTURES ARE ASSERTED, not assumed: byte size and line count of each, because a fixture that
    silently became a different file would re-derive different numbers and still pass every
    comparison against itself.
  * A POSITIVE CONTROL binds the reconstruction to the record it replaces: the written-lines fixture
    must reproduce the committed deployment measurement (0.325 -> 0.567) or nothing here is valid.
  * EVERY NUMBER MUST ALSO APPEAR IN THE TEXT. A gate that recomputes a value and never checks the
    draft says the maths is fine while the prose says something else.

Run: python probes/every_number_in_the_index_post.py
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import re
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).parent
FIX = HERE / "fixtures"
DRAFT = ROOT / "agora_output" / "drafts" / "post_the_index_line_is_the_only_surface_SKELETON.md"
OUT = HERE / "every_number_in_the_index_post.result.json"

TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("−", "-"))
checks: list[tuple[str, bool, str, str]] = []


def ck(name, ok, detail="", kind="re-derived"):
    checks.append((name, bool(ok), detail, kind))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("MISSING FROM DRAFT: " + " | ".join(missing) if missing else "")


STOP = set("""a an the and or but if then than that this those these is are was were be been being am do does
did have has had i you he she it we they them his her its our their my your of in on at to for with from by as
into over under about after before between during without within not no nor so such can could would should may
might must will shall there here when where which who whom what why how all any both each few more most other
some only own same too very just also us one two""".split())
TOK = re.compile(r"[a-z][a-z0-9_-]{2,}")


def toks(s):
    return [t for t in TOK.findall(s.lower()) if t not in STOP]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.ids = list(docs)
        self.tf = {i: Counter(toks(docs[i])) for i in self.ids}
        self.len = {i: sum(self.tf[i].values()) or 1 for i in self.ids}
        self.avg = sum(self.len.values()) / len(self.ids)
        df = Counter()
        for i in self.ids:
            df.update(self.tf[i].keys())
        n = len(self.ids)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def rank(self, q):
        qt = toks(q)
        sc = []
        for i in self.ids:
            tf, dl = self.tf[i], self.len[i]
            v = 0.0
            for t in qt:
                f = tf.get(t)
                if f:
                    v += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            sc.append((v, i))
        sc.sort(key=lambda x: (-x[0], x[1]))
        return [i for _, i in sc]


# ---------------------------------------------------------------- the fixtures, asserted
STATES = {"01-crowded": 20020, "02-uncrowded": 19990, "03-written-lines": 42664,
          "04-window-fitted": 23979}
raw = {}
for name, size in STATES.items():
    p = FIX / ("MEMORY.md." + name)
    if not p.exists():
        print("fixture missing: %s -- run the pinning step first" % p)
        sys.exit(2)
    raw[name] = p.read_text(encoding="utf-8")
    ck("fixture %s is the pinned file" % name, len(p.read_bytes()) == size,
       "%d B, expected %d" % (len(p.read_bytes()), size), "fixture")
ARCH = (FIX / "MEMORY_ARCHIVE.md").read_text(encoding="utf-8")


def lines_of(txt, with_archive=True):
    """file -> its index line. THE FOOTER'S POINTER TO THE ARCHIVE IS A LINK, NOT AN ENTRY, and
    counting it inflated reach by one on files whose footer still loads and not on files where it
    was truncated away -- an off-by-one that moves with the very truncation it is measuring."""
    src = txt + ("\n" + ARCH if with_archive else "")
    d = {}
    for line in src.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", line):
            if fn != "MEMORY_ARCHIVE.md":
                d.setdefault(fn, line.strip())
    return d


# TWO DIFFERENT CONSTANTS, and conflating them silently re-scores history. RUNTIME_CAP is what the
# product loads and is the only figure the ladder may use -- changing it to our own, more
# conservative deploy target moved "96 entries outside the window" to 101 and +0.092 to +0.075, which
# would have described a truncation that never happened. DEPLOY_TARGET is where WE choose to sit,
# below both readings of the stated "24.4KB", and it belongs only to the rebuilt file.
RUNTIME_CAP, DEPLOY_TARGET = 25000, 24000


def loaded(txt, byte_cap=RUNTIME_CAP, line_cap=200):
    kept, total = [], 0
    for line in txt.split("\n"):
        b = len(line.encode("utf-8")) + 2
        if len(kept) >= line_cap or total + b > byte_cap:
            break
        kept.append(line)
        total += b
    return "\n".join(kept)


QA = json.loads((HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json")
                .read_text(encoding="utf-8"))["rows"]
QB = json.loads((HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json")
                .read_text(encoding="utf-8"))


def ranks(idx, queries):
    bm = BM25(idx) if idx else None
    miss = len(idx) + 1
    return [bm.rank(q).index(f) + 1 if (bm and f in idx) else miss for f, q in queries]


def rec(rk, k):
    return sum(1 for x in rk if x <= k) / len(rk)


# ---------------------------------------------------------------- §3  the un-crowding
b_idx, a_idx = lines_of(raw["01-crowded"]), lines_of(raw["02-uncrowded"])
qa = [(r["file"], r["query"]) for r in QA if r["file"] in b_idx and r["file"] in a_idx]
rb, ra = ranks(b_idx, qa), ranks(a_idx, qa)
ck("un-crowding recall@3 0.208 -> 0.325",
   abs(rec(rb, 3) - 0.208) < .005 and abs(rec(ra, 3) - 0.325) < .005,
   "%.3f -> %.3f" % (rec(rb, 3), rec(ra, 3)))
ck("draft says it", *says("0.208", "0.325"))
better = sum(1 for x, y in zip(rb, ra) if y < x)
worse = sum(1 for x, y in zip(rb, ra) if y > x)
# THE DRIFT IS DECLARED, NOT HIDDEN. The state immediately after the un-crowding was never
# snapshotted; the nearest pinned copy carries a few hours of later additions, so it re-derives
# 64/11 where the run on the day gave 62/11. The draft must quote BOTH, and this checks both.
_committed = json.loads((HERE / "uncrowding_the_index_moved_62_queries_up_and_11_down.result.json")
                        .read_text(encoding="utf-8"))["paired"]
ck("the committed run gave 62 better / 11 worse",
   (_committed["better"], _committed["worse"]) == (62, 11),
   "%d / %d" % (_committed["better"], _committed["worse"]), "read")
ck("the pinned copy re-derives 64 / 11 -- the drift", (better, worse) == (64, 11),
   "%d / %d" % (better, worse), "control")
ck("draft quotes BOTH pairs", *says("62 better / 11 worse", "64 and 11"))
n = better + worse
p_fix = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(better, worse) + 1)) / 2 ** n)
ck("committed p = 9.1e-10", abs(_committed["p"] - 9.1e-10) / 9.1e-10 < .05,
   "%.3g" % _committed["p"], "read")
ck("re-derived p = 3.1e-10", abs(p_fix - 3.1e-10) / 3.1e-10 < .1, "%.3g" % p_fix, "control")
ck("draft quotes both p values", *says("9.1e-10", "3.1e-10"))
ck("BOTH clear 1e-9, so the conclusion does not turn on the drift",
   _committed["p"] < 1e-9 and p_fix < 1e-9, "%.3g / %.3g" % (_committed["p"], p_fix), "control")
ck("median rank got WORSE, 18 -> 21",
   sorted(rb)[len(rb) // 2] == 18 and sorted(ra)[len(ra) // 2] == 21,
   "%d -> %d" % (sorted(rb)[len(rb) // 2], sorted(ra)[len(ra) // 2]))
ck("the un-crowding's byte figures", *says("19,899", "19,714"))
ck("and the line count it cost", *says("121 lines to 248"))
ck("the line counts are real",
   len(raw["01-crowded"].splitlines()) == 121 and len(raw["02-uncrowded"].splitlines()) == 248,
   "%d -> %d" % (len(raw["01-crowded"].splitlines()), len(raw["02-uncrowded"].splitlines())))

# ---------------------------------------------------------------- §6  the deployment
w_idx = lines_of(raw["03-written-lines"])
qa6 = [(r["file"], r["query"]) for r in QA if r["file"] in a_idx and r["file"] in w_idx]
r_b, r_w = ranks(a_idx, qa6), ranks(w_idx, qa6)
ck("POSITIVE CONTROL: the reconstruction reproduces the deployment record 0.325 -> 0.567",
   abs(rec(r_b, 3) - 0.325) < .005 and abs(rec(r_w, 3) - 0.567) < .005,
   "%.3f -> %.3f" % (rec(r_b, 3), rec(r_w, 3)), "control")
ck("draft says it", *says("0.325", "0.567"))
rng = random.Random(11)
hb = [1 if x <= 3 else 0 for x in r_b]
ha = [1 if x <= 3 else 0 for x in r_w]
d = []
for _ in range(20000):
    ii = [rng.randrange(len(qa6)) for _ in qa6]
    d.append(sum(ha[i] for i in ii) / len(ii) - sum(hb[i] for i in ii) / len(ii))
d.sort()
lo, hi = d[int(.025 * len(d))], d[int(.975 * len(d))]
ck("+0.242 [+0.167, +0.317]",
   abs(rec(r_w, 3) - rec(r_b, 3) - 0.242) < .005 and abs(lo - 0.167) < .01 and abs(hi - 0.317) < .01,
   "%+.3f [%+.3f, %+.3f]" % (rec(r_w, 3) - rec(r_b, 3), lo, hi))
ck("draft says it", *says("+0.242 [+0.167, +0.317]"))
ck("median rank 21 -> 2",
   sorted(r_b)[len(r_b) // 2] == 21 and sorted(r_w)[len(r_w) // 2] == 2,
   "%d -> %d" % (sorted(r_b)[len(r_b) // 2], sorted(r_w)[len(r_w) // 2]))
ck("draft says 21 and 2, NOT the 4 -> 1 it used to claim",
   *says("| median rank | 21 | 2 |"))
ck("the 4 -> 1 claim is gone", "median rank | 4 | 1" not in TEXT)

# ---------------------------------------------------------------- §6a  the window ladder
qb = [(k, v) for k, v in QB.items() if k in a_idx and k in w_idx and len(v.split()) >= 2]
rows = {}
for lab, txt in (("crowded", raw["01-crowded"]), ("uncrowded", raw["02-uncrowded"]),
                 ("written", raw["03-written-lines"]), ("fitted", raw["04-window-fitted"])):
    idx = lines_of(loaded(txt), with_archive=False)
    rows[lab] = (rec(ranks(idx, qa6), 3), rec(ranks(idx, qb), 3), len(idx))
ck("at what LOADS, the un-crowding gave q +0.042 / sb +0.092",
   abs(rows["uncrowded"][0] - rows["crowded"][0] - 0.042) < .005
   and abs(rows["uncrowded"][1] - rows["crowded"][1] - 0.092) < .005,
   "q %+.3f sb %+.3f" % (rows["uncrowded"][0] - rows["crowded"][0],
                         rows["uncrowded"][1] - rows["crowded"][1]))
ck("draft says it", *says("q +0.042 · sb +0.092"))
ck("at what LOADS, the written lines gave q +0.092 / sb +0.000",
   abs(rows["written"][0] - rows["uncrowded"][0] - 0.092) < .005
   and abs(rows["written"][1] - rows["uncrowded"][1]) < .005,
   "q %+.3f sb %+.3f" % (rows["written"][0] - rows["uncrowded"][0],
                         rows["written"][1] - rows["uncrowded"][1]))
ck("draft says it", *says("q +0.092 · sb +0.000"))
ck("net for the day at what loads, 0.208 -> 0.342 and 0.292 -> 0.383",
   abs(rows["crowded"][0] - 0.208) < .005 and abs(rows["written"][0] - 0.342) < .005
   and abs(rows["crowded"][1] - 0.292) < .005 and abs(rows["written"][1] - 0.383) < .005,
   "q %.3f->%.3f sb %.3f->%.3f" % (rows["crowded"][0], rows["written"][0],
                                   rows["crowded"][1], rows["written"][1]))
ck("draft says it", *says("0.208 → 0.342", "0.292 → 0.383"))
ck("95 of 229 entries were outside the window",
   len(lines_of(raw["03-written-lines"], False)) - rows["written"][2] == 95,
   "%d outside" % (len(lines_of(raw["03-written-lines"], False)) - rows["written"][2]))
ck("draft says it", *says("95 of its 229 entries — 41% — were outside the window"))
ck("the written-lines file was 42,666 bytes / 248 lines -- as DEPLOYED",
   *says("42,666 bytes, 248 lines"))
ck("the pinned reconstruction is within 2 bytes of that",
   abs(len(raw["03-written-lines"].replace("\n", "\r\n").encode("utf-8")) - 42666) <= 2,
   "%d B" % len(raw["03-written-lines"].replace("\n", "\r\n").encode("utf-8")), "control")
ck("the rebuild: 23,979 bytes, 200 lines, 230 of 230 inside",
   len(raw["04-window-fitted"].replace("\n", "\r\n").encode("utf-8")) == 23979
   and len(raw["04-window-fitted"].splitlines()) == 200
   and rows["fitted"][2] == len(lines_of(raw["04-window-fitted"], False)) == 230,
   "%d B, %d lines, %d reachable" % (
       len(raw["04-window-fitted"].replace("\n", "\r\n").encode("utf-8")),
       len(raw["04-window-fitted"].splitlines()), rows["fitted"][2]))
ck("draft says it", *says("23,979 bytes, 200 lines, 230 of 230 entries inside the window"))
ck("the rebuild beats the deployed file on both registers",
   rows["fitted"][0] >= rows["written"][0] and rows["fitted"][1] >= rows["written"][1],
   "q %.3f vs %.3f, sb %.3f vs %.3f" % (rows["fitted"][0], rows["written"][0],
                                        rows["fitted"][1], rows["written"][1]))
ck("draft's rebuild figures, and it calls the tie a tie",
   *says("0.342 → **0.358**, a margin too small to lean on", "0.383 → **0.442**"))
ck("they are what the fixtures give ON THE SAME DENOMINATOR AS THE ROWS ABOVE",
   abs(rows["fitted"][0] - 0.358) < .005 and abs(rows["fitted"][1] - 0.442) < .005,
   "q %.3f sb %.3f" % (rows["fitted"][0], rows["fitted"][1]))
# Check the superseded PHRASES, not the bare digits: "0.350" is also the score of an unrelated
# variant in the section-4 table, and a substring test on a number cannot tell those apart.
ck("no superseded rebuild figure survives in the draft",
   "0.342 → **0.367**" not in TEXT and "0.383 → **0.458**" not in TEXT
   and "0.342 → **0.350**" not in TEXT)
ck("the 68-byte scaffolding figure", *says("median **68 bytes per entry** on"))
# THE STORE WAS ALREADY AT THE EDGE two days before any of this, which is what separates a finding
# from a self-inflicted wound. Re-derived from the 08-17 backup rather than asserted.
_aug17 = FIX / "MEMORY.md.05-2026-08-17"
if _aug17.exists():
    _r = _aug17.read_bytes()
    _t = _aug17.read_text(encoding="utf-8")
    _links = re.findall(r"\]\(([^)]+\.md)\)", _t)
    _costs = sorted(len(ch.encode("utf-8")) + 3 for line in _t.splitlines()
                    if line.strip().startswith("- ") and "](" in line
                    for ch in re.split(r"\s+·\s+", line.strip()[2:]) if "](" in ch)
    _med = _costs[len(_costs) // 2]
    _head = 25000 - len(_r)
    ck("on 2026-08-17 the index was 24,015 B, 96.1%% of the cap, 254 entries, all loading",
       len(_r) == 24015 and len(_links) == 254 and abs(100 * len(_r) / 25000 - 96.1) < 0.1,
       "%d B, %d entries" % (len(_r), len(_links)))
    ck("an entry cost a median 71 B there, so 10-13 more would have truncated it",
       _med == 71 and 10 <= _head // _med <= 13, "median %d B, room for %d" % (_med, _head // _med))
    ck("draft says it", *says("24,015 bytes — 96.1% of the cap — with 254 entries",
                              "ten to thirteen memories away"))
    ck("the draft separates the arithmetic claim from the instrument-dependent one",
       *says("arithmetic on bytes and lines", "still has to accept the 95"))
else:
    ck("the 2026-08-17 fixture is pinned", False, "missing -- pin it before quoting the figure",
       "fixture")
sc = 0
for f, line in lines_of(raw["03-written-lines"], False).items():
    m = re.search(r"\[([^\]]*)\]\(([^)]+\.md)\)", line)
    if m:
        sc += len(m.group(1)) + len(m.group(2)) + 6
ck("scaffolding really is ~68-71 B/entry",
   66 <= sc / len(lines_of(raw["03-written-lines"], False)) <= 74,
   "%.1f B" % (sc / len(lines_of(raw["03-written-lines"], False))))

# ---------------------------------------------------------------- READ from committed artifacts
V = json.loads((HERE / "what_does_an_index_line_have_to_say_to_be_found.result.json")
               .read_text(encoding="utf-8"))["report"]
R = json.loads((HERE / "the_winning_index_line_was_written_by_the_query_writer.result.json")
               .read_text(encoding="utf-8"))
L = json.loads((HERE / "a_line_written_to_length_beats_the_same_line_cut_to_it.result.json")
               .read_text(encoding="utf-8"))["report"]
for label, key, q, s in (("hand-written title + hook", "current", 0.333, 0.508),
                         ("the title alone", "title", 0.300, 0.450),
                         ("title + highest-idf terms", "terms", 0.350, 0.533),
                         ("a written line", "written", 0.683, 0.833),
                         ("ceiling: the full notes", "CEILING full note", 0.858, 0.967)):
    got_q = V[key]["r3"]
    got_s = R["B  search-box (control)"][key]["r3"] if key in R["B  search-box (control)"] else None
    ok = abs(got_q - q) < .005 and (got_s is None or abs(got_s - s) < .005)
    ck("variant %-26s %.3f / %.3f" % (label, q, s), ok,
       "%.3f / %s" % (got_q, "%.3f" % got_s if got_s is not None else "n/a"), "read")
ck("the register control: 57% of the question-form margin vanished",
   abs((1 - R["B  search-box (control)"]["question"]["d"] / R["A  question-form (original)"]["question"]["d"]) - 0.57) < .02,
   "%.0f%%" % (100 * (1 - R["B  search-box (control)"]["question"]["d"] / R["A  question-form (original)"]["question"]["d"])),
   "read")
ck("draft says 57%", *says("57% of the question-form margin vanished"))
ck("terms is a null on both registers (+0.017, +0.025), intervals contain zero",
   R["A  question-form (original)"]["terms"]["lo"] < 0 < R["A  question-form (original)"]["terms"]["hi"]
   and R["B  search-box (control)"]["terms"]["lo"] < 0 < R["B  search-box (control)"]["terms"]["hi"],
   "", "read")
ck("draft says it", *says("+0.017, +0.025"))
ck("cut-to-7 0.758 vs written-to-7 0.667 -- SEARCH-BOX register",
   abs(L["hybrid, CUT to 7"]["searchbox"] - 0.758) < .005
   and abs(L["hybrid, WRITTEN to 7"]["searchbox"] - 0.667) < .005,
   "%.3f / %.3f" % (L["hybrid, CUT to 7"]["searchbox"], L["hybrid, WRITTEN to 7"]["searchbox"]), "read")
ck("THE DRAFT MUST NAME THE REGISTER for those two numbers -- it is not the question set",
   *says("search-box"))
ck("and the question-register values are stated too, or the pair is cherry-picked",
   *says("0.575", "0.508"))
ck("the question-register pair is what the artifact holds",
   abs(L["hybrid, CUT to 7"]["questions"] - 0.575) < .005
   and abs(L["hybrid, WRITTEN to 7"]["questions"] - 0.508) < .005,
   "%.3f / %.3f" % (L["hybrid, CUT to 7"]["questions"], L["hybrid, WRITTEN to 7"]["questions"]),
   "read")

# ---------------------------------------------------------------- CITATIONS, verified 2026-08-20
# Each figure below was read out of the PRIMARY source (the ACL anthology PDF, the arXiv PDF, the
# GitHub issue, the vendor post), not from a secondary summary. They are asserted here so a later
# edit cannot quietly reintroduce the versions that did not survive checking:
#   * Wasson is pp. 27-36, not 37-44, and its two headline pairs are DIFFERENT evaluation scopes --
#     the draft had blended them, which would have made the precision compensation look universal.
#   * Dense X's venue (EMNLP 2024 Main) is not on the arXiv abstract page and had to come from the
#     paper itself.
CITES = [
    ("Wasson pages", "pp. 27–36"),
    ("Wasson all-reference recall", ".704 → .232"),
    ("Wasson all-reference precision compensation", "+.082"),
    ("Wasson main-reference precision", ".230 → .516"),
    ("Wasson scopes are kept apart", "depends on what the searcher wants"),
    ("Brandow relative recall", "100% → 58%"),
    ("Lin BM25 MAP", "abstract .163, whole article **.146**, paragraph span **.240**"),
    ("Dense X venue", "EMNLP 2024 Main Conference"),
    ("Dense X figures", "+10.1 on unsupervised dense retrievers and +2.7 on supervised ones"),
    ("Medrano", "Hit@10 0.51 → 0.48"),
    ("the warning, verbatim", "index entries are too long"),
    ("issue 25006 status", "closed as not planned"),
    ("mem0 is five days earlier", "14 Aug 2026 — **five days before us**"),
    ("fsgeek measured cutoff", "~25,500 bytes"),
]
for name, bit in CITES:
    ck("citation: %s" % name, *says(bit), kind="cite")
ck("no unverified page range survives", "pp. 37–44" not in TEXT, "", "cite")

# ---------------------------------------------------------------- report
bad = [c for c in checks if not c[1]]
w = max(len(c[0]) for c in checks)
for name, ok, detail, kind in checks:
    print("%-4s [%-9s] %-*s %s" % ("OK" if ok else "FAIL", kind, w, name, detail))
print("\n%d/%d checks pass  (%d re-derived from fixtures, %d read from committed results)"
      % (len(checks) - len(bad), len(checks),
         sum(1 for c in checks if c[3] == "re-derived"), sum(1 for c in checks if c[3] == "read")))
OUT.write_text(json.dumps(dict(passed=len(checks) - len(bad), total=len(checks),
                               failures=[c[0] for c in bad]), indent=1), encoding="utf-8")
sys.exit(1 if bad else 0)
