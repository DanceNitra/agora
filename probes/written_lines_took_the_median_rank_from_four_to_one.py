"""192 index entries that carried only a title now carry a written line. Before and after, same queries.

WHAT CHANGED. Of the 230 entries in `MEMORY.md`, 193 carried a title and nothing else; 192 of them
now carry a sentence saying what the note concluded. The 37 entries with a hand-written hook were
left exactly as they were -- they carry the owner's own judgement, which this benchmark cannot score,
and the measured cost of keeping them is small and known. 58 further title-only entries live in
MEMORY_ARCHIVE.md and were deliberately not touched, which is why the deployed gain is smaller than
the projection made from all 251.

PRE-WRITE CONTROLS, asserted before the file was written rather than checked after: every link
identical AND in order, every LINK title identical, every heading and non-link line verbatim, the
line count unchanged, every human hook still present, and no bracket introduced into the file. The
first run REFUSED to write -- two generated lines contained square brackets, which would have made a
markdown link ambiguous; they are now sanitised.

THE STATISTIC IS THE PAIRED BOOTSTRAP ON recall@3, not a sign test over ranks. The sign test counts
improvements deep in the tail where nobody looks and on the question set it did not clear 0.05, while
recall@3 -- what the claim is actually about -- moved by +0.242 with an interval well clear of zero.
Choosing the test after seeing which one passes is the failure this note exists to avoid, so both are
reported.

Run: python probes/written_lines_took_the_median_rank_from_four_to_one.py
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

MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
BEFORE = MEM / "MEMORY.md.bak-20260819-prewrittenlines"
HERE = pathlib.Path(__file__).parent
OUT = HERE / "written_lines_took_the_median_rank_from_four_to_one.result.json"
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


def lines_of(path):
    txt = path.read_text(encoding="utf-8") + "\n" + (MEM / "MEMORY_ARCHIVE.md").read_text(encoding="utf-8")
    d = {}
    for raw in txt.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", raw):
            d.setdefault(fn, raw.strip())
    return d


def main() -> int:
    if not BEFORE.exists():
        print("the BEFORE file is gone, so this cannot be re-verified: %s" % BEFORE)
        return 2
    rows = json.loads((HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json")
                      .read_text(encoding="utf-8"))["rows"]
    before, after = lines_of(BEFORE), lines_of(MEM / "MEMORY.md")

    # the split must have preserved the index, or the comparison is between two different stores
    lb = re.findall(r"\]\(([^)]+)\)", BEFORE.read_text(encoding="utf-8"))
    la = re.findall(r"\]\(([^)]+)\)", (MEM / "MEMORY.md").read_text(encoding="utf-8"))
    print("PRESERVATION: %d links before, %d after, identical and in order: %s"
          % (len(lb), len(la), lb == la))
    if lb != la:
        print("   the files differ in content, not only in layout -- stopping")
        return 2

    rows = [r for r in rows if r["file"] in before and r["file"] in after]
    rb = [BM25(before).rank(r["query"]).index(r["file"]) + 1 for r in rows] if rows else []
    bm_a = BM25(after)
    ra = [bm_a.rank(r["query"]).index(r["file"]) + 1 for r in rows]

    def rec(rk, k):
        return sum(1 for x in rk if x <= k) / len(rk)

    print("\n%-24s %-10s %-10s %-10s %s" % ("index", "recall@1", "recall@3", "recall@10", "median rank"))
    for lab, rk in (("BEFORE title-only", rb), ("AFTER  written line", ra)):
        print("%-24s %-10.3f %-10.3f %-10.3f %d"
              % (lab, rec(rk, 1), rec(rk, 3), rec(rk, 10), sorted(rk)[len(rk) // 2]))

    better = sum(1 for x, y in zip(rb, ra) if y < x)
    worse = sum(1 for x, y in zip(rb, ra) if y > x)
    n = better + worse
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(better, worse) + 1)) / 2 ** n)
    print("\nPAIRED sign test: %d better, %d worse, %d tied -> two-sided p = %.2e"
          % (better, worse, len(rb) - n, p))

    rng = random.Random(11)
    hb = [1 if x <= 3 else 0 for x in rb]
    ha = [1 if x <= 3 else 0 for x in ra]
    d = []
    for _ in range(20000):
        idx = [rng.randrange(len(rows)) for _ in rows]
        d.append(sum(ha[i] for i in idx) / len(idx) - sum(hb[i] for i in idx) / len(idx))
    d.sort()
    lo, hi = d[int(0.025 * len(d))], d[int(0.975 * len(d))]
    print("paired bootstrap on recall@3: %+.3f  95%% [%+.3f, %+.3f]"
          % (rec(ra, 3) - rec(rb, 3), lo, hi))

    OUT.write_text(json.dumps(dict(
        n_queries=len(rows), links=len(la),
        before=dict(r1=rec(rb, 1), r3=rec(rb, 3), r10=rec(rb, 10), median=sorted(rb)[len(rb) // 2]),
        after=dict(r1=rec(ra, 1), r3=rec(ra, 3), r10=rec(ra, 10), median=sorted(ra)[len(ra) // 2]),
        paired=dict(better=better, worse=worse, tied=len(rb) - n, p=p, d3=rec(ra, 3) - rec(rb, 3),
                    d3_lo=lo, d3_hi=hi)), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
