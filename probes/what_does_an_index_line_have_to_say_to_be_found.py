"""Four ways to write an index line, measured against the same questions, ceiling and floor.

THE GAP THIS ATTACKS. Un-crowding the live index moved recall@3 from 0.208 to 0.325 at zero token
cost, and stopped there: the note itself supports 0.858. So a hand-written one-line summary carries
about a third of what its own note can be found by, and the rest of that gap is unexplained. It is
not a Claude Code problem -- it is the general shape of an always-loaded index over a growing store,
which is the thing this library is for.

THE VARIANTS, one line per memory, none of which ever sees a query:

  current    what the deployed index says today (the baseline to beat)
  title      the title alone, nothing else
  terms      title + the terms most distinctive to that note, chosen by idf over the store
  question   title + the question the note answers, written by a model from the BODY
  written    a free-form line written by a model from the BODY, budgeted

THE INVARIANT THAT KEEPS IT HONEST: no variant generator is shown a single evaluation query. Every
variant derives from the note body, exactly as the human-written line did, so no variant has a
privileged relationship with the questions. This is asserted, not promised -- the queries are loaded
after the variants are built.

WHAT IS REPORTED BESIDE RECALL: the token cost of the whole index in each variant. The index is
loaded every session, so a variant that buys recall with three times the tokens is a different trade
from one that is free, and reporting recall alone would hide that.

FALSIFIER, WRITTEN FIRST: if no variant beats `current` on a paired test, there is nothing here to
build and this file is the record that we looked.

Run: python probes/what_does_an_index_line_have_to_say_to_be_found.py [--workers 6]
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
OUT = HERE / "what_does_an_index_line_have_to_say_to_be_found.result.json"
CACHE = HERE / "what_does_an_index_line_have_to_say_to_be_found.lines.json"
QUERIES_FROM = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"

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


QUESTION = ("Write the single question this note answers, as someone would ask it months later who "
            "half-remembers the situation. Under 20 words, plain language, no file names, no version "
            "numbers. Output the question only.")
WRITTEN = ("Write ONE index line for this note: the line a reader scans to decide whether to open it. "
           "Under 22 words. Name the specific thing it is about and what it concluded. No file names, "
           "no preamble, no quotes. Output the line only.")


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
    ap.add_argument("--refresh", action="store_true", help="regenerate the model-written variants")
    a = ap.parse_args(argv[1:])

    line_for, title_for, bodies = load()
    cand = sorted(bodies)
    print("%d indexed memories" % len(cand), flush=True)

    # ---- deterministic variants
    df = Counter()
    for c in cand:
        df.update(set(toks(bodies[c])))
    n = len(cand)
    idf = {t: math.log(n / v) for t, v in df.items()}
    QUERYABLE = re.compile(r"^[a-z]{4,}$")

    def terms_line(c, k=8):
        seen = Counter(t for t in toks(bodies[c]) if QUERYABLE.match(t) and df.get(t, 0) >= 3)
        best = [t for t, _ in sorted(seen.items(), key=lambda kv: (-idf.get(kv[0], 0.0), -kv[1]))[:k]]
        return "%s — %s" % (title_for[c], " ".join(best))

    variants = {
        "current": {c: line_for[c] for c in cand},
        "title": {c: title_for[c] for c in cand},
        "terms": {c: terms_line(c) for c in cand},
    }

    # ---- model-written variants, cached; the generators never see a query
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() and not a.refresh else {}
    for name, prompt in (("question", QUESTION), ("written", WRITTEN)):
        have = cache.get(name, {})
        todo = [c for c in cand if c not in have or not have[c]]
        if todo:
            print("generating %s for %d notes" % (name, len(todo)), flush=True)
            t0 = time.time()

            def gen(c):
                body = " ".join(bodies[c].split()[:700])
                out = call_llm(prompt, body, a.tier, 0.2, 16000) or ""
                return c, out.strip().strip('"').split("\n")[0][:220]

            with ThreadPoolExecutor(max_workers=a.workers) as ex:
                for i, (c, line) in enumerate(ex.map(gen, todo), 1):
                    have[c] = line
                    if i % 50 == 0:
                        print("   %d/%d  %.0fs" % (i, len(todo), time.time() - t0), flush=True)
            cache[name] = have
            CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        missing = sum(1 for c in cand if not have.get(c))
        if missing > 0.1 * len(cand):
            print("   %d of %d %s lines are empty -- the generator is failing, not the variant"
                  % (missing, len(cand), name))
            return 3
        variants[name] = {c: ("%s — %s" % (title_for[c], have.get(c, "")) if name == "question"
                              else (have.get(c) or title_for[c])) for c in cand}

    variants["CEILING full note"] = {c: bodies[c] for c in cand}

    # ---- queries are loaded ONLY NOW, after every variant exists
    rows = json.loads(QUERIES_FROM.read_text(encoding="utf-8"))["rows"]
    rows = [r for r in rows if r["file"] in bodies]
    print("evaluating on %d held-out questions, none of which any generator saw" % len(rows), flush=True)

    def index_tokens(d):
        return int(sum(len(v.split()) for v in d.values()) * 1.35)

    ranks, report = {}, {}
    for name, docs in variants.items():
        bm = BM25(docs)
        ranks[name] = [bm.rank(r["query"]).index(r["file"]) + 1 for r in rows]

    base = ranks["current"]

    def rec(rk, k):
        return sum(1 for x in rk if x <= k) / len(rk)

    def sign_vs_base(rk):
        better = sum(1 for x, y in zip(base, rk) if y < x)
        worse = sum(1 for x, y in zip(base, rk) if y > x)
        m = better + worse
        p = min(1.0, 2 * sum(math.comb(m, i) for i in range(min(better, worse) + 1)) / 2 ** m) if m else 1.0
        return better, worse, p

    print("\n%-20s %-9s %-9s %-9s %-8s %-22s %s"
          % ("variant", "recall@1", "recall@3", "recall@10", "MRR", "paired vs current", "index tokens"))
    for name in ("current", "title", "terms", "question", "written", "CEILING full note"):
        rk = ranks[name]
        b, w, p = sign_vs_base(rk)
        vs = "-" if name == "current" else "%d up / %d down  p=%.1e" % (b, w, p)
        report[name] = dict(r1=rec(rk, 1), r3=rec(rk, 3), r10=rec(rk, 10),
                            mrr=sum(1 / x for x in rk) / len(rk), better=b, worse=w, p=p,
                            tokens=index_tokens(variants[name]))
        print("%-20s %-9.3f %-9.3f %-9.3f %-8.3f %-22s %d"
              % (name, rec(rk, 1), rec(rk, 3), rec(rk, 10),
                 report[name]["mrr"], vs, report[name]["tokens"]))

    winners = [k for k, v in report.items()
               if k not in ("current", "CEILING full note") and v["p"] < 0.05 and v["better"] > v["worse"]]
    print("\nFALSIFIER: variants beating the deployed index on a paired test -> %s"
          % (", ".join(winners) if winners else "NONE. Nothing to build; the record stands."))

    OUT.write_text(json.dumps(dict(n_queries=len(rows), n_candidates=len(cand),
                                   report=report, winners=winners), indent=1), encoding="utf-8")
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
