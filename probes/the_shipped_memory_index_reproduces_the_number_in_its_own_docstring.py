"""The docstring of `memory_index()` quotes recall@3 0.833. This runs the SHIPPED code and checks it.

WHY IT IS SEPARATE FROM THE EXPERIMENT. The variant experiment ranked strings assembled by a probe.
The library assembles them differently -- it prefixes a key, joins with an em dash, caps at
`max_words`, and stores the line on the record. A number measured on the probe's strings and quoted
in the library's docstring would be a claim about code that does not run. So the index here is built
by calling `set_index_line()` and `memory_index()` on a real store, and the lines that get ranked are
the ones the library returns.

THE ARMS, all ranking the same 316 candidates on the same held-out questions:
  fallback  what memory_index() gives with no summariser -- the row its own limits call weak
  written   the same call after the model-written lines are stored through set_index_line()
  current   the hand-written index deployed in the live memory directory, for reference

Run: python probes/the_shipped_memory_index_reproduces_the_number_in_its_own_docstring.py
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
import sys
import tempfile
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

REPO = pathlib.Path(r"C:\Users\Danculus\inspeximus-repo")
sys.path.insert(0, str(REPO))
from inspeximus import Inspeximus                                      # noqa: E402

MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
HERE = pathlib.Path(__file__).parent
OUT = HERE / "the_shipped_memory_index_reproduces_the_number_in_its_own_docstring.result.json"
LINES = HERE / "what_does_an_index_line_have_to_say_to_be_found.lines.json"
QA = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"
QB = HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json"

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


def main() -> int:
    idx = (MEM / "MEMORY.md").read_text(encoding="utf-8")
    arch = MEM / "MEMORY_ARCHIVE.md"
    if arch.exists():
        idx += "\n" + arch.read_text(encoding="utf-8")
    line_for = {}
    for raw in idx.splitlines():
        if "](" not in raw:
            continue
        for chunk in re.split(r"\s+·\s+", raw.strip().lstrip("- ")):
            m = re.search(r"\[([^\]]*)\]\(([^)]+\.md)\)", chunk)
            if m:
                line_for.setdefault(m.group(2), chunk.strip())
    bodies = {}
    for p in sorted(MEM.glob("*.md")):
        if p.name in ("MEMORY.md", "MEMORY_ARCHIVE.md") or p.name not in line_for:
            continue
        bodies[p.name] = re.sub(r"^---.*?^---", "", p.read_text(encoding="utf-8", errors="replace"),
                                flags=re.S | re.M).strip()

    # --- a real store, one record per note, keyed by the file name
    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "notes.json"), embed=False)
    for name, body in bodies.items():
        ix.remember(body[:4000], key=name)
    ix.flush()
    print("loaded %d notes into a store" % len(bodies))

    fallback = ix.memory_index()
    assert fallback["records"] == len(bodies), "the library did not index every record"
    assert fallback["fallback"] == len(bodies) and fallback["generated"] == 0
    print("fallback index: %d records, ~%d tokens, %d need a line"
          % (fallback["records"], fallback["tokens_estimate"], len(fallback["needs_line"])))

    cached = json.loads(LINES.read_text(encoding="utf-8"))["written"]
    stored = sum(1 for name in bodies if cached.get(name)
                 and ix.set_index_line(name, cached[name])["stored"])
    written = ix.memory_index()
    print("after set_index_line on %d records: reused %d, fallback %d, ~%d tokens"
          % (stored, written["reused"], written["fallback"], written["tokens_estimate"]))

    def docs_from(res):
        out = {}
        for ln in res["lines"]:
            m = re.match(r"- (\S+?) — (.*)$", ln) or re.match(r"- (\S+)$", ln)
            if m:
                out[m.group(1)] = ln
        return out

    arms = {"fallback (no summariser)": docs_from(fallback),
            "written (via set_index_line)": docs_from(written),
            "the live hand-written index": {k: v for k, v in line_for.items() if k in bodies}}
    for name, d in arms.items():
        assert len(d) == len(bodies), "%s lost %d records in assembly" % (name, len(bodies) - len(d))

    qa = [(r["file"], r["query"]) for r in json.loads(QA.read_text(encoding="utf-8"))["rows"]
          if r["file"] in bodies]
    qb_raw = json.loads(QB.read_text(encoding="utf-8"))
    qb = [(k, v) for k, v in qb_raw.items() if k in bodies and len(v.split()) >= 2]

    print("\n%-30s %-16s %-16s %s" % ("arm", "questions@3", "search-box@3", "index tokens"))
    report = {}
    for name, d in arms.items():
        bm = BM25(d)
        r3a = sum(1 for f, q in qa if bm.rank(q).index(f) + 1 <= 3) / len(qa)
        r3b = sum(1 for f, q in qb if bm.rank(q).index(f) + 1 <= 3) / len(qb)
        tk = int(sum(len(v.split()) for v in d.values()) * 1.35)
        report[name] = dict(questions=r3a, searchbox=r3b, tokens=tk)
        print("%-30s %-16.3f %-16.3f %d" % (name, r3a, r3b, tk))

    w = report["written (via set_index_line)"]
    print("\nthe docstring claims 0.683 / 0.833 for a written line. Shipped code gives %.3f / %.3f."
          % (w["questions"], w["searchbox"]))
    ok = abs(w["searchbox"] - 0.833) < 0.05 and abs(w["questions"] - 0.683) < 0.05
    print("within 0.05 of the quoted pair: %s" % ("yes" if ok else "NO -- the docstring is wrong"))

    OUT.write_text(json.dumps(dict(n_notes=len(bodies), n_qa=len(qa), n_qb=len(qb),
                                   report=report, matches_docstring=bool(ok)), indent=1),
                   encoding="utf-8")
    print("wrote %s" % OUT.name)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
