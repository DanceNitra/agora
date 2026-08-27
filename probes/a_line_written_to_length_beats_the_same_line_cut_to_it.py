"""Truncating a written line to seven words gives a sentence cut in half. Writing one to seven does not.

WHY THIS EXISTS. The budget sweep cut written index lines to a word count and the numbers looked
good, so it nearly shipped. Printing the actual lines killed it: "Trend test on log(median",
"Language policy: code and", "Invertibility check on growing" -- retrieval-useful and unreadable,
in a file a person reads. A word cap is not a length instruction.

WHAT IS MEASURED. The same 251 index entries that today carry a title and nothing else, given lines
GENERATED at the target length rather than cut to it, scored against the same held-out questions and
compared to the truncated version of the same idea and to the index deployed today.

THE 65 ENTRIES WITH A HUMAN HOOK ARE LEFT ALONE, on purpose. They carry the owner's own judgement --
"6 of 8 threads got 0 replies" -- which is worth something this benchmark cannot score, and the
measured cost of keeping them is small and now known: the hybrid captures 86% of the full-replacement
gain for 443 extra tokens.

CONTROLS:
  * NO GENERATOR SEES A QUERY. The lines are written from note bodies; the queries are loaded after.
  * LENGTH IS CHECKED, not requested and assumed -- a model told "seven words" often gives twelve.
  * THE TRUNCATED ARM IS RUN BESIDE IT, so "written to length is better" is a comparison rather than
    an assertion, and can come out the other way.

Run: python probes/a_line_written_to_length_beats_the_same_line_cut_to_it.py [--words 7]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
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
OUT = HERE / "a_line_written_to_length_beats_the_same_line_cut_to_it.result.json"
CACHE = HERE / "a_line_written_to_length_beats_the_same_line_cut_to_it.lines.json"
TRUNC = HERE / "what_does_an_index_line_have_to_say_to_be_found.lines.json"
QA = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"
QB = HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json"

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


def load():
    idx = (MEM / "MEMORY.md").read_text(encoding="utf-8")
    arch = MEM / "MEMORY_ARCHIVE.md"
    if arch.exists():
        idx += "\n" + arch.read_text(encoding="utf-8")
    entry, title = {}, {}
    for raw in idx.splitlines():
        if "](" not in raw:
            continue
        for ch in re.split(r"\s+·\s+", raw.strip().lstrip("- ")):
            m = re.search(r"\[([^\]]*)\]\(([^)]+\.md)\)", ch)
            if m:
                entry.setdefault(m.group(2), ch.strip())
                title.setdefault(m.group(2), m.group(1))
    bodies = {}
    for p in sorted(MEM.glob("*.md")):
        if p.name in ("MEMORY.md", "MEMORY_ARCHIVE.md") or p.name not in entry:
            continue
        bodies[p.name] = re.sub(r"^---.*?^---", "", p.read_text(encoding="utf-8", errors="replace"),
                                flags=re.S | re.M).strip()
    return entry, title, bodies


def hook_len(entry, k):
    return len(re.sub(r"\[[^\]]*\]\([^)]+\)", "", entry[k]).strip(" —·.-"))


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", type=int, default=7)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tier", default="cheap")
    a = ap.parse_args(argv[1:])

    entry, title, bodies = load()
    cand = [k for k in entry if k in bodies]
    empty = [k for k in cand if hook_len(entry, k) <= 15]
    print("%d indexed, %d carry a human hook, %d carry only a title" % (
        len(cand), len(cand) - len(empty), len(empty)), flush=True)

    prompt = ("Write ONE line for an index of notes: what this note CONCLUDED, as a complete phrase a "
              "reader can scan. AT MOST %d WORDS and it must read as a finished phrase, not a "
              "sentence cut short. Name the specific thing. No file names, no version numbers, no "
              "preamble, no quotes. Output the line only." % a.words)

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = str(a.words)
    have = cache.get(key, {})
    todo = [k for k in empty if not have.get(k)]
    if todo:
        print("generating %d lines at %d words" % (len(todo), a.words), flush=True)
        t0 = time.time()

        def gen(k):
            body = " ".join(bodies[k].split()[:700])
            out = call_llm(prompt, body, a.tier, 0.2, 16000) or ""
            return k, out.strip().strip('"').split("\n")[0][:200]

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for i, (k, line) in enumerate(ex.map(gen, todo), 1):
                have[k] = line
                if i % 40 == 0:
                    print("   %d/%d  %.0fs" % (i, len(todo), time.time() - t0), flush=True)
        cache[key] = have
        CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    made = [k for k in empty if have.get(k)]
    if len(made) < 0.9 * len(empty):
        print("only %d of %d lines came back -- the generator failed, not the idea" % (len(made), len(empty)))
        return 3

    # ---- LENGTH CONTROL: asked for at most N words; check rather than trust
    lens = [len(have[k].split()) for k in made]
    over = sum(1 for x in lens if x > a.words)
    print("\nLENGTH CONTROL: asked for <= %d words. median %d, max %d, over the cap %d of %d (%.0f%%)"
          % (a.words, sorted(lens)[len(lens) // 2], max(lens), over, len(lens), 100 * over / len(lens)))

    trunc = json.loads(TRUNC.read_text(encoding="utf-8"))["written"]
    qa = [(r["file"], r["query"]) for r in json.loads(QA.read_text(encoding="utf-8"))["rows"]
          if r["file"] in entry]
    qb = [(k, v) for k, v in json.loads(QB.read_text(encoding="utf-8")).items()
          if k in entry and len(v.split()) >= 2]
    print("evaluating on %d + %d held-out questions, loaded after every line existed"
          % (len(qa), len(qb)), flush=True)

    def arm(fn):
        return {k: fn(k) for k in cand}

    arms = {
        "current (today)": arm(lambda k: entry[k]),
        "hybrid, CUT to %d" % a.words: arm(
            lambda k: entry[k] if hook_len(entry, k) > 15
            else "[%s] — %s" % (title[k], " ".join(trunc.get(k, "").split()[:a.words]))),
        "hybrid, WRITTEN to %d" % a.words: arm(
            lambda k: entry[k] if hook_len(entry, k) > 15
            else "[%s] — %s" % (title[k], have.get(k, ""))),
    }

    print("\n%-26s %-9s %-13s %s" % ("index", "tokens", "questions@3", "search-box@3"))
    report = {}
    for name, d in arms.items():
        bm = BM25(d)
        qa3 = sum(1 for f, q in qa if bm.rank(q).index(f) + 1 <= 3) / len(qa)
        qb3 = sum(1 for f, q in qb if bm.rank(q).index(f) + 1 <= 3) / len(qb)
        tk = int(sum(len(v.split()) for v in d.values()) * 1.35)
        report[name] = dict(tokens=tk, questions=qa3, searchbox=qb3)
        print("%-26s %-9d %-13.3f %.3f" % (name, tk, qa3, qb3))

    cut = report["hybrid, CUT to %d" % a.words]
    wri = report["hybrid, WRITTEN to %d" % a.words]
    print("\nwritten-to-length vs cut-to-length: %+.3f questions, %+.3f search-box, %+d tokens"
          % (wri["questions"] - cut["questions"], wri["searchbox"] - cut["searchbox"],
             wri["tokens"] - cut["tokens"]))
    print("\nA SAMPLE, so the half no benchmark scores can be judged by eye:")
    for k in made[:6]:
        print("   %-52s %s" % (title[k][:50], have[k]))

    OUT.write_text(json.dumps(dict(words=a.words, indexed=len(cand), with_hook=len(cand) - len(empty),
                                   generated=len(made), over_cap=over, report=report,
                                   sample={k: have[k] for k in made[:20]}), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
