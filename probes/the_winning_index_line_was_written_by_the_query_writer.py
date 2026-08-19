"""The best index-line variant is a question, and so is every evaluation query. This is the control.

WHAT IT IS CHECKING. On question-form queries the `question` variant reached recall@3 0.775 against
the deployed index's 0.333 and a full-note ceiling of 0.858. But both the queries and that variant
were written by the same model from the same bodies, one asked for "the question a person would ask"
and the other for "the question this note answers". A question matching a question is not evidence
that the line is a better index -- it may be evidence that the two prompts converge.

THE CONTROL. A second query set over the same notes, written in a deliberately different register:
what someone TYPES INTO A SEARCH BOX -- a few words, no question mark, no sentence. If `question`
keeps its margin there, the effect is about content. If it collapses toward the others, the margin
was style-matching and the result is void.

AND A CORRECTED CRITERION. The first run's falsifier asked whether a variant beat the deployed index
on a paired sign test over RANKS, and `title` passed it while having a WORSE recall@3 -- the sign
test counts improvements deep in the tail, where nobody looks. The decision statistic here is
recall@3 with a paired bootstrap, which is what the question is actually about.

Run: python probes/the_winning_index_line_was_written_by_the_query_writer.py [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
HERE = pathlib.Path(__file__).parent
OUT = HERE / "the_winning_index_line_was_written_by_the_query_writer.result.json"
QCACHE = HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json"
LINES = HERE / "what_does_an_index_line_have_to_say_to_be_found.lines.json"
QUERIES_A = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"

sys.path.insert(0, str(ROOT / "server"))
for _l in (ROOT / "server" / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _l and not _l.lstrip().startswith("#"):
        _k, _v = _l.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
from agora.execution.llm_client import call_llm                        # noqa: E402

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


SEARCHBOX = ("Someone half-remembers this note and wants to find it again. Write what they would TYPE "
             "INTO A SEARCH BOX: three to eight words, no question mark, no full sentence, no file "
             "names. Just the words. Output them only.")


def load():
    idx = (MEM / "MEMORY.md").read_text(encoding="utf-8")
    arch = MEM / "MEMORY_ARCHIVE.md"
    if arch.exists():
        idx += "\n" + arch.read_text(encoding="utf-8")
    line_for, title_for = {}, {}
    for raw in idx.splitlines():
        if "](" not in raw:
            continue
        for chunk in re.split(r"\s+·\s+", raw.strip().lstrip("- ")):
            m = re.search(r"\[([^\]]*)\]\(([^)]+\.md)\)", chunk)
            if m:
                line_for.setdefault(m.group(2), chunk.strip())
                title_for.setdefault(m.group(2), m.group(1))
    bodies = {}
    for p in sorted(MEM.glob("*.md")):
        if p.name in ("MEMORY.md", "MEMORY_ARCHIVE.md") or p.name not in line_for:
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        bodies[p.name] = re.sub(r"^---.*?^---", "", raw, flags=re.S | re.M).strip()
    return {k: v for k, v in line_for.items() if k in bodies}, title_for, bodies


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tier", default="cheap")
    a = ap.parse_args(argv[1:])

    line_for, title_for, bodies = load()
    cand = sorted(bodies)
    cache = json.loads(LINES.read_text(encoding="utf-8"))
    rows_a = [r for r in json.loads(QUERIES_A.read_text(encoding="utf-8"))["rows"] if r["file"] in bodies]
    targets = [r["file"] for r in rows_a]

    # ---- the same variants as the first run
    df = Counter()
    for c in cand:
        df.update(set(toks(bodies[c])))
    idf = {t: math.log(len(cand) / v) for t, v in df.items()}
    QUERYABLE = re.compile(r"^[a-z]{4,}$")

    def terms_line(c, k=8):
        seen = Counter(t for t in toks(bodies[c]) if QUERYABLE.match(t) and df.get(t, 0) >= 3)
        best = [t for t, _ in sorted(seen.items(), key=lambda kv: (-idf.get(kv[0], 0.0), -kv[1]))[:k]]
        return "%s — %s" % (title_for[c], " ".join(best))

    variants = {
        "current": {c: line_for[c] for c in cand},
        "title": {c: title_for[c] for c in cand},
        "terms": {c: terms_line(c) for c in cand},
        "question": {c: "%s — %s" % (title_for[c], cache["question"].get(c, "")) for c in cand},
        "written": {c: (cache["written"].get(c) or title_for[c]) for c in cand},
        "CEILING full note": {c: bodies[c] for c in cand},
    }

    # ---- query set B: a different register entirely
    qb = json.loads(QCACHE.read_text(encoding="utf-8")) if QCACHE.exists() else {}
    todo = [t for t in targets if t not in qb or not qb[t]]
    if todo:
        print("generating %d search-box queries" % len(todo), flush=True)
        t0 = time.time()

        def gen(c):
            body = " ".join(bodies[c].split()[:700])
            out = call_llm(SEARCHBOX, body, a.tier, 0.3, 16000) or ""
            return c, out.strip().strip('"').split("\n")[0][:120]

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for i, (c, q) in enumerate(ex.map(gen, todo), 1):
                qb[c] = q
                if i % 30 == 0:
                    print("   %d/%d  %.0fs" % (i, len(todo), time.time() - t0), flush=True)
        QCACHE.write_text(json.dumps(qb, indent=1), encoding="utf-8")
    usable = [t for t in targets if len(qb.get(t, "").split()) >= 2]
    if len(usable) < 0.8 * len(targets):
        print("only %d of %d search-box queries came back -- the generator failed, not the variants"
              % (len(usable), len(targets)))
        return 3

    sets = {
        "A  question-form (original)": [(r["file"], r["query"]) for r in rows_a],
        "B  search-box (control)": [(t, qb[t]) for t in usable],
    }
    print("\nquery set A mean length %.1f words, set B %.1f words"
          % (sum(len(q.split()) for _, q in sets["A  question-form (original)"]) / len(rows_a),
             sum(len(q.split()) for _, q in sets["B  search-box (control)"]) / len(usable)), flush=True)

    def rec3(docs, pairs):
        bm = BM25(docs)
        return [1 if bm.rank(q).index(f) + 1 <= 3 else 0 for f, q in pairs]

    rng = random.Random(23)
    report = {}
    for sname, pairs in sets.items():
        hits = {v: rec3(docs, pairs) for v, docs in variants.items()}
        base = hits["current"]
        print("\n%s  (n=%d)" % (sname, len(pairs)))
        print("  %-20s %-9s %s" % ("variant", "recall@3", "paired difference vs current [95%]"))
        for v in ("current", "title", "terms", "question", "written", "CEILING full note"):
            h = hits[v]
            d = sum(h) / len(h) - sum(base) / len(base)
            if v == "current":
                print("  %-20s %-9.3f %s" % (v, sum(h) / len(h), "-"))
                continue
            boot = []
            for _ in range(20000):
                idx2 = [rng.randrange(len(h)) for _ in h]
                boot.append(sum(h[i] for i in idx2) / len(idx2) - sum(base[i] for i in idx2) / len(idx2))
            boot.sort()
            lo, hi = boot[500], boot[19499]
            report.setdefault(sname, {})[v] = dict(r3=sum(h) / len(h), d=d, lo=lo, hi=hi)
            print("  %-20s %-9.3f %+.3f [%+.3f, %+.3f]%s"
                  % (v, sum(h) / len(h), d, lo, hi, "" if lo > 0 else "   (contains zero)"))

    ra = report["A  question-form (original)"]
    rb = report["B  search-box (control)"]
    print("\nDOES THE WINNER SURVIVE THE REGISTER CHANGE?")
    for v in ("terms", "question", "written"):
        print("  %-10s A %+.3f [%+.3f,%+.3f]   B %+.3f [%+.3f,%+.3f]   %s"
              % (v, ra[v]["d"], ra[v]["lo"], ra[v]["hi"], rb[v]["d"], rb[v]["lo"], rb[v]["hi"],
                 "HOLDS" if rb[v]["lo"] > 0 else "does NOT hold"))

    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
