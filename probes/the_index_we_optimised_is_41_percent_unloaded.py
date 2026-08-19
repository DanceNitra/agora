"""The index we improved today is truncated before the agent reads it, and the gain has to be re-scored.

WHY THIS EXISTS. Today's deployment rewrote 192 title-only entries into written lines and measured
recall@3 rising 0.325 -> 0.567, +0.242 [+0.167, +0.317]. Every one of those numbers ranked all
candidates in the FILE, plus the archive. Claude Code's documentation says only "the first 200 lines
of MEMORY.md, or the first 25KB, whichever comes first" are loaded at the start of a conversation,
and "content beyond that threshold is not loaded"; topic files, including MEMORY_ARCHIVE.md, are not
loaded at startup at all. The file went from 19,990 bytes to 42,666 in that deployment. So the
measurement scored an index the runtime never assembles -- rule 12 of our own CLAUDE.md, committed by
the person who wrote it.

WHAT IS MEASURED. A ladder, one change per rung, so the gap between what was reported and what a
session actually gets is decomposed rather than asserted:

    L0  the deployment harness exactly as it ran        (positive control: must give 0.325 / 0.567)
    L1  minus MEMORY_ARCHIVE.md, which never loads
    L2  minus everything past 200 lines / 25KB          (what a session actually holds)

THE DENOMINATOR IS FIXED AT L0 AND NEVER SHRINKS. A query whose target is not in the loaded index at
some rung is a miss at that rung, not a row removed. Rescoring on survivors is how a truncated index
reports a recall it does not have.

CONTROLS:
  * POSITIVE CONTROL at L0 against the committed deployment figures. If L0 does not reproduce them,
    the ladder is measuring something else and no rung may be quoted.
  * THE CUT MUST BITE, and it is reported for BOTH files -- the pre-deployment index is 19,990 bytes
    and would look safe on size alone, but it carries 248 lines, so the 200-line cap takes it too.
    That is the un-crowding's own cost, and it was not measured this afternoon either.
  * BOTH READINGS OF "25KB" (25,000 and 25,600 bytes) are run, so the verdict cannot rest on a unit
    ambiguity in someone else's documentation.
  * TWO REGISTERS (question-form and search-box), because a single one flatters whichever index
    shares its voice.

Run: python probes/the_index_we_optimised_is_41_percent_unloaded.py
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
HERE = pathlib.Path(__file__).parent
OUT = HERE / "the_index_we_optimised_is_41_percent_unloaded.result.json"
QA = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"
QB = HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json"

LIVE = MEM / "MEMORY.md"
BEFORE = MEM / "MEMORY.md.bak-20260819-prewrittenlines"
MORNING = MEM / "MEMORY.md.bak-20260819-precrowdfix"
ARCHIVE = MEM / "MEMORY_ARCHIVE.md"

LINE_CAP = 200
BYTE_CAPS = (25000, 25600)

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


def lines_of(text):
    """file -> the whole index line carrying it, exactly as the deployment harness read it."""
    d = {}
    for raw in text.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", raw):
            d.setdefault(fn, raw.strip())
    return d


def loaded_prefix(path, byte_limit, line_limit=LINE_CAP):
    """What a session assembles: whole lines, cut at whichever limit comes first. Bytes ON DISK,
    so CRLF counts -- the runtime reads the file, not a newline-normalised copy of it."""
    kept, total = [], 0
    for line in path.read_bytes().split(b"\n"):
        if len(kept) >= line_limit or total + len(line) + 1 > byte_limit:
            break
        kept.append(line)
        total += len(line) + 1
    return b"\n".join(kept).decode("utf-8", "replace")


def main() -> int:
    if not BEFORE.exists():
        print("the pre-deployment backup is gone, so this cannot be re-verified: %s" % BEFORE)
        return 2

    live_txt, bef_txt = LIVE.read_text(encoding="utf-8"), BEFORE.read_text(encoding="utf-8")
    morn_txt = MORNING.read_text(encoding="utf-8") if MORNING.exists() else bef_txt
    arch_txt = ARCHIVE.read_text(encoding="utf-8") if ARCHIVE.exists() else ""

    # ---- the query set is fixed HERE, at L0, and is the denominator at every rung below
    qa_all = json.loads(QA.read_text(encoding="utf-8"))["rows"]
    l0_before = lines_of(bef_txt + "\n" + arch_txt)
    l0_after = lines_of(live_txt + "\n" + arch_txt)
    qa = [(r["file"], r["query"]) for r in qa_all if r["file"] in l0_before and r["file"] in l0_after]
    qb = [(k, v) for k, v in json.loads(QB.read_text(encoding="utf-8")).items()
          if k in l0_before and k in l0_after and len(v.split()) >= 2]
    print("denominator fixed at L0: %d question-form and %d search-box queries; it does not shrink "
          "on any rung below\n" % (len(qa), len(qb)))

    def ranks(index_map, queries):
        """A target absent from the loaded index is unreachable: rank = one past the pool."""
        bm = BM25(index_map) if index_map else None
        miss = len(index_map) + 1
        out = []
        for f, q in queries:
            out.append(bm.rank(q).index(f) + 1 if (bm and f in index_map) else miss)
        return out

    def rec(rk, k):
        return sum(1 for x in rk if x <= k) / len(rk)

    rungs = [("L0  as the deployment measured it", lambda t, p: lines_of(t + "\n" + arch_txt)),
             ("L1  minus the archive (never loads)", lambda t, p: lines_of(t))]
    for cap in BYTE_CAPS:
        rungs.append(("L2  minus past 200 lines / %s B" % f"{cap:,}",
                      lambda t, p, c=cap: lines_of(loaded_prefix(p, c))))

    print("%-38s %8s %9s %11s %11s %7s" % ("rung", "entries", "reachable", "questions@3",
                                           "searchbox@3", "median"))
    rows, keep = {}, {}
    for name, build in rungs:
        for lab, txt, path in (("morning  (crowded)", morn_txt, MORNING),
                               ("before   (uncrowded)", bef_txt, BEFORE),
                               ("after    (written)", live_txt, LIVE)):
            idx = build(txt, path)
            ra, rb = ranks(idx, qa), ranks(idx, qb)
            reach = sum(1 for f, _ in qa if f in idx)
            rows["%s | %s" % (name, lab)] = dict(
                entries=len(idx), reachable_qa=reach, questions=rec(ra, 3), searchbox=rec(rb, 3),
                median=sorted(ra)[len(ra) // 2], recall1=rec(ra, 1))
            keep[(name, lab)] = (ra, rb)
            print("%-38s %8d %9d %11.3f %11.3f %7d"
                  % (name + "  " + lab, len(idx), reach, rec(ra, 3), rec(rb, 3),
                     sorted(ra)[len(ra) // 2]))
        print()

    # ---------------------------------------------------------------- CONTROLS
    l0b = rows["L0  as the deployment measured it | before   (uncrowded)"]
    l0a = rows["L0  as the deployment measured it | after    (written)"]
    ok0 = abs(l0b["questions"] - 0.325) < 0.02 and abs(l0a["questions"] - 0.567) < 0.02
    print("POSITIVE CONTROL  L0 reproduces the committed deployment figures (0.325 -> 0.567): "
          "%s -> %.3f -> %.3f" % ("PASS" if ok0 else "FAIL", l0b["questions"], l0a["questions"]))
    if not ok0:
        print("   the ladder is not measuring the same thing the deployment did -- no rung may be quoted")
        OUT.write_text(json.dumps(dict(rows=rows, control_l0=False), indent=1), encoding="utf-8")
        return 3

    l2 = "L2  minus past 200 lines / 25,000 B"
    print("CONTROL the cut bites, on BOTH files      : before %d of %d entries load, after %d of %d"
          % (rows["%s | before   (uncrowded)" % l2]["entries"], l0b["entries"] - 58,
             rows["%s | after    (written)" % l2]["entries"], l0a["entries"] - 58))
    print("CONTROL unreachable targets stay in the denominator: after the cut only %d of %d question "
          "targets are present at all" % (rows["%s | after    (written)" % l2]["reachable_qa"], len(qa)))

    # ---------------------------------------------------------------- the answer
    print("\nWHAT TODAY'S TWO DEPLOYMENTS ACTUALLY BOUGHT A SESSION")
    print("   %-38s %-26s %s" % ("", "step 1: un-crowding", "step 2: written lines"))
    for name, _ in rungs:
        m = rows["%s | morning  (crowded)" % name]
        b = rows["%s | before   (uncrowded)" % name]
        a = rows["%s | after    (written)" % name]
        print("   %-38s q %+.3f  sb %+.3f        q %+.3f  sb %+.3f"
              % (name, b["questions"] - m["questions"], b["searchbox"] - m["searchbox"],
                 a["questions"] - b["questions"], a["searchbox"] - b["searchbox"]))
    mn = rows["%s | morning  (crowded)" % l2]
    af = rows["%s | after    (written)" % l2]
    print("\n   NET FOR THE WHOLE DAY, at what a session actually loads:")
    print("      questions@3  %.3f -> %.3f  (%+.3f)"
          % (mn["questions"], af["questions"], af["questions"] - mn["questions"]))
    print("      searchbox@3  %.3f -> %.3f  (%+.3f)"
          % (mn["searchbox"], af["searchbox"], af["searchbox"] - mn["searchbox"]))
    print("      entries a session can reach: %d -> %d" % (mn["entries"], af["entries"]))

    rb_, ra_ = keep[(l2, "before   (uncrowded)")][0], keep[(l2, "after    (written)")][0]
    rng = random.Random(11)
    hb = [1 if x <= 3 else 0 for x in rb_]
    ha = [1 if x <= 3 else 0 for x in ra_]
    d = []
    for _ in range(20000):
        ii = [rng.randrange(len(qa)) for _ in qa]
        d.append(sum(ha[i] for i in ii) / len(ii) - sum(hb[i] for i in ii) / len(ii))
    d.sort()
    lo, hi = d[int(0.025 * len(d))], d[int(0.975 * len(d))]
    delta = rec(ra_, 3) - rec(rb_, 3)
    print("\npaired bootstrap on recall@3 AT WHAT LOADS: %+.3f  95%% [%+.3f, %+.3f]" % (delta, lo, hi))
    survives = lo > 0
    print("the deployment's gain survives the window it is read through: %s"
          % ("YES, reduced" if survives else "NO -- the interval contains zero"))

    OUT.write_text(json.dumps(dict(rows=rows, control_l0=True, loaded_delta=delta,
                                   loaded_ci=[lo, hi], survives=bool(survives),
                                   n_qa=len(qa), n_qb=len(qb)), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
