"""Given a real need, can the right memory be picked out of the index? Three arms and a floor.

WHY THIS AND NOT THE COVERAGE METRIC. Stage one asked how much of a memory's own vocabulary survives
into its index line and got 2.1%, against a ceiling of 7.0% for the writer's own description. A
target that the best possible one-line summary reaches 7% of measures the target, not the line -- so
that framing cannot tell "the index line is bad" from "one line cannot hold a document". What decides
retrieval is not whether the line CONTAINS the question's words but whether it can be SELECTED over
the other 314 candidates. That is this.

THE ARMS, all ranking the same 315 candidates for the same query:
  A  lexical over the INDEX LINE      -- the surface the mechanism actually exposes
  B  lexical over the FULL BODY       -- an upper bound on what lexical matching could do here
  C  the model, given the whole index -- the mechanism itself: 2k tokens of MEMORY.md, pick 3
  floor  random ranking               -- recall@k is k/315 by construction

QUERIES COME FROM THE BODY, NEVER FROM THE LINE, so arm A gets no free lexical gift; and because
that hands arm B the advantage instead, query/line overlap is measured and the results are stratified
by it. The interesting cell is the one where the query shares NO word with the index line: arm A must
fail there by construction, and whether arm C also fails is the actual question.

CONTROLS:
  * POSITIVE -- a verbatim sentence from the body as the query must put arm B at rank 1. If it does
    not, the retriever is broken and no arm below is readable.
  * FLOOR -- random ranking, stated, so "better than nothing" is checkable rather than assumed.
  * WIRING -- arms A and B must receive DIFFERENT text for the same candidate. Asserted per query,
    because three of four arms once received byte-identical context and the run measured nothing.

Run: python probes/can_the_right_memory_be_selected_from_one_index_line.py [--n 60] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import math
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
OUT = pathlib.Path(__file__).with_suffix(".result.json")
sys.path.insert(0, str(ROOT / "server"))
# The client reads its credentials from server/.env relative to the CWD, so a probe launched from
# the repo root gets "Missing credentials" and every call returns None -- which the first run then
# scored as an empty result set rather than as a dead instrument. Load it explicitly instead.
import os                                                              # noqa: E402

for _line in (ROOT / "server" / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _line and not _line.lstrip().startswith("#"):
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
from agora.execution.llm_client import call_llm                        # noqa: E402

STOP = set("""a an the and or but if then than that this those these is are was were be been being
am do does did doing have has had having i you he she it we they them his her its our their my your
of in on at to for with from by as into over under about after before between during without within
not no nor so such can could would should may might must will shall there here when where which who
whom what why how all any both each few more most other some only own same too very just also we us
one two do not""".split())
TOK = re.compile(r"[a-z][a-z0-9_-]{2,}")


def toks(s: str) -> list[str]:
    return [t for t in TOK.findall(s.lower()) if t not in STOP]


class BM25:
    """Plain BM25 over a fixed candidate set. Deterministic, so the two lexical arms differ only in
    the text they were given -- which is the point of having two of them."""

    def __init__(self, docs: dict, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.ids = list(docs)
        self.tf = {i: Counter(toks(docs[i])) for i in self.ids}
        self.len = {i: sum(self.tf[i].values()) or 1 for i in self.ids}
        self.avg = sum(self.len.values()) / len(self.ids)
        df: Counter = Counter()
        for i in self.ids:
            df.update(self.tf[i].keys())
        n = len(self.ids)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def rank(self, query: str) -> list[str]:
        q = toks(query)
        scored = []
        for i in self.ids:
            tf, dl = self.tf[i], self.len[i]
            s = 0.0
            for t in q:
                f = tf.get(t)
                if not f:
                    continue
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            scored.append((s, i))
        # ties break by id so a zero-score run is a stable arbitrary order, not a lucky one
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [i for _, i in scored]


def load():
    index_text = (MEM / "MEMORY.md").read_text(encoding="utf-8")
    arch = MEM / "MEMORY_ARCHIVE.md"
    if arch.exists():
        index_text += "\n" + arch.read_text(encoding="utf-8")
    line_for: dict = {}
    for raw in index_text.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", raw):
            line_for.setdefault(fn, raw.strip())
    bodies = {}
    for p in sorted(MEM.glob("*.md")):
        if p.name in ("MEMORY.md", "MEMORY_ARCHIVE.md") or p.name not in line_for:
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        bodies[p.name] = re.sub(r"^---.*?^---", "", raw, flags=re.S | re.M).strip()
    return index_text, {k: v for k, v in line_for.items() if k in bodies}, bodies


QGEN = ("You write the question a person would ASK, months later, that a note answers. "
        "One question, under 25 words, plain language. Use the words someone would actually type "
        "who half-remembers the situation -- NOT the note's title, NOT file names, NOT rare "
        "identifiers, NOT version numbers. Output the question only.")

PICK = ("You are choosing which memory files to open. Below is the always-loaded index. "
        "Given the question, name up to THREE files from the index most likely to answer it. "
        "Output only their file names, one per line, best first. Nothing else.")


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260819)
    ap.add_argument("--tier", default="cheap")
    a = ap.parse_args(argv[1:])
    rng = random.Random(a.seed)

    index_text, line_for, bodies = load()
    cand = sorted(bodies)
    print("%d indexed memories, index is %d bytes" % (len(cand), len(index_text)), flush=True)

    bm_line = BM25({c: line_for[c] for c in cand})
    bm_body = BM25({c: bodies[c] for c in cand})

    # WIRING CHECK: the two arms must not be reading the same thing
    same = sum(1 for c in cand if line_for[c].strip() == bodies[c].strip())
    assert same == 0, "%d candidates have identical line and body -- the arms are not separated" % same

    sample = rng.sample(cand, min(a.n, len(cand)))

    # ---------------- POSITIVE CONTROL: a verbatim sentence must be findable in the body arm
    ctrl_hits = 0
    ctrl_n = 0
    for c in sample[:20]:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", bodies[c]) if len(s.split()) >= 12]
        if not sents:
            continue
        ctrl_n += 1
        ctrl_hits += bm_body.rank(rng.choice(sents))[0] == c
    print("POSITIVE CONTROL: verbatim sentence retrieved at rank 1 by the body arm on %d/%d"
          % (ctrl_hits, ctrl_n), flush=True)
    if ctrl_n and ctrl_hits / ctrl_n < 0.9:
        print("   the retriever cannot find text it was given verbatim -- stopping")
        return 2

    # ---------------- queries, generated from the BODY only
    def gen(c):
        body = " ".join(bodies[c].split()[:900])
        q = call_llm(QGEN, body, a.tier, 0.3, 16000) or ""
        return c, q.strip().strip('"').split("\n")[0][:300]

    t0 = time.time()
    queries = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (c, q) in enumerate(ex.map(gen, sample), 1):
            queries[c] = q
            if i % 10 == 0:
                print("  queries %d/%d  %.0fs" % (i, len(sample), time.time() - t0), flush=True)
    queries = {c: q for c, q in queries.items() if len(q.split()) >= 3}
    print("generated %d usable queries of %d attempted" % (len(queries), len(sample)), flush=True)
    if len(queries) < 0.5 * len(sample):
        # A harness that scores an empty result set reports a perfect null. Refuse instead.
        print("FEWER THAN HALF THE QUERIES CAME BACK -- the generator is failing, not the mechanism. "
              "Nothing below would be a measurement; stopping.")
        return 3

    # ---------------- arm C: the mechanism, one call per query
    def pick(c):
        out = call_llm(PICK, "INDEX:\n%s\n\nQUESTION: %s" % (index_text, queries[c]), a.tier, 0.0, 16000) or ""
        names = re.findall(r"[a-z0-9][a-z0-9._-]*\.md", out.lower())
        seen, ordered = set(), []
        for nm in names:
            if nm in bodies and nm not in seen:
                seen.add(nm)
                ordered.append(nm)
        return c, ordered[:3], out.strip()[:200]

    picks = {}
    raw_out = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (c, ordered, raw) in enumerate(ex.map(pick, list(queries)), 1):
            picks[c], raw_out[c] = ordered, raw
            if i % 10 == 0:
                print("  selections %d/%d  %.0fs" % (i, len(queries), time.time() - t0), flush=True)

    # ---------------- score
    rows = []
    for c, q in queries.items():
        ra, rb = bm_line.rank(q), bm_body.rank(q)
        overlap = len(set(toks(q)) & set(toks(line_for[c])))
        rows.append(dict(
            file=c, query=q, overlap_with_line=overlap,
            rank_line=ra.index(c) + 1, rank_body=rb.index(c) + 1,
            pick=picks.get(c, []), pick_rank=(picks.get(c, []).index(c) + 1) if c in picks.get(c, []) else None,
            raw=raw_out.get(c, "")))

    def mrr(key):
        return sum(1 / r[key] for r in rows if r[key]) / len(rows)

    def wilson(hits, n, z=1.96):
        """A point estimate on sixty-odd queries is not a result. Wilson rather than normal, because
        these counts sit near 0 and 1 where the normal approximation leaves the unit interval."""
        if not n:
            return (float("nan"), float("nan"))
        p = hits / n
        d = 1 + z * z / n
        c = p + z * z / (2 * n)
        s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return ((c - s) / d, (c + s) / d)

    def cell(key, k):
        h = sum(1 for r in rows if r[key] and r[key] <= k)
        lo, hi = wilson(h, len(rows))
        return "%.3f [%.2f,%.2f]" % (h / len(rows), lo, hi)

    print("\n%-32s %-19s %-19s %-19s %s"
          % ("arm", "recall@1 [95%]", "recall@3 [95%]", "recall@10 [95%]", "MRR"))
    print("%-32s %-19s %-19s %-19s %.3f" % ("A  lexical, index line", cell("rank_line", 1),
                                            cell("rank_line", 3), cell("rank_line", 10), mrr("rank_line")))
    print("%-32s %-19s %-19s %-19s %.3f" % ("B  lexical, full body", cell("rank_body", 1),
                                            cell("rank_body", 3), cell("rank_body", 10), mrr("rank_body")))
    print("%-32s %-19s %-19s %-19s %.3f" % ("C  the model, given the index", cell("pick_rank", 1),
                                            cell("pick_rank", 3), "-", mrr("pick_rank")))
    print("%-32s %-19.3f %-19.3f %-19.3f" % ("   random floor", 1 / len(cand), 3 / len(cand), 10 / len(cand)))
    none_named = sum(1 for r in rows if not r["pick"])
    print("\ninstrument health: the model named no file from the index on %d of %d queries (%.0f%%)"
          % (none_named, len(rows), 100 * none_named / len(rows)))

    print("\nSTRATIFIED BY QUERY/LINE WORD OVERLAP (arm A must fail at zero by construction)")
    print("%-18s %-7s %-11s %-11s %s" % ("overlap", "n", "A recall@3", "B recall@3", "C recall@3"))
    for label, lo, hi in (("0 words", 0, 0), ("1 word", 1, 1), ("2+ words", 2, 99)):
        sub = [r for r in rows if lo <= r["overlap_with_line"] <= hi]
        if not sub:
            continue
        f = lambda key: sum(1 for r in sub if r[key] and r[key] <= 3) / len(sub)   # noqa: E731
        print("%-18s %-7d %-11.3f %-11.3f %.3f" % (label, len(sub), f("rank_line"), f("rank_body"), f("pick_rank")))

    OUT.write_text(json.dumps(dict(
        n_candidates=len(cand), index_bytes=len(index_text), tier=a.tier,
        control_verbatim="%d/%d" % (ctrl_hits, ctrl_n), rows=rows), indent=1), encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
