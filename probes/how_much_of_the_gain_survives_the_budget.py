"""A written index line doubles retrieval and costs twice the tokens. How much survives a budget?

WHAT IS OPEN. Through the shipped `memory_index()`, written lines reach recall@3 0.692 on
question-form queries and 0.842 on search-box ones, against 0.333 / 0.508 for the hand-written index
deployed today -- but they cost 6,484 tokens against 3,063, on a file loaded every session. That is a
trade, and a trade is a thing people decline. The question this settles is whether it stays a trade
when the written lines are cut to the budget the current index already spends.

FALSIFIER, WRITTEN FIRST: if at 3,063 tokens the search-box recall@3 falls below 0.6 -- roughly
halfway back to the hand-written baseline -- the gain does not survive the budget, the feature is a
permanent trade, and this file is the record of that rather than an argument for it.

CONTROLS:
  * THE BUDGET MUST BIND. At every budget the returned index is checked against it, and any overshoot
    must be reported in `over_budget` rather than silently exceeded.
  * NOTHING IS DROPPED. All 316 records must appear at every budget, including ones far too small.
  * POSITIVE CONTROL. At an unlimited budget the numbers must reproduce the un-budgeted measurement
    (0.692 / 0.842). If they do not, the budgeting path is measuring something else.

Run: python probes/how_much_of_the_gain_survives_the_budget.py
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
OUT = HERE / "how_much_of_the_gain_survives_the_budget.result.json"
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

    ix = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "notes.json"), embed=False)
    for name, body in bodies.items():
        ix.remember(body[:4000], key=name)
    ix.flush()
    cached = json.loads(LINES.read_text(encoding="utf-8"))["written"]
    stored = sum(1 for n in bodies if cached.get(n) and ix.set_index_line(n, cached[n])["stored"])
    print("%d notes, %d written lines stored" % (len(bodies), stored), flush=True)

    qa = [(r["file"], r["query"]) for r in json.loads(QA.read_text(encoding="utf-8"))["rows"]
          if r["file"] in bodies]
    qb = [(k, v) for k, v in json.loads(QB.read_text(encoding="utf-8")).items()
          if k in bodies and len(v.split()) >= 2]

    def docs_from(res):
        out = {}
        for ln in res["lines"]:
            m = re.match(r"- (\S+?) — (.*)$", ln) or re.match(r"- (\S+)$", ln)
            if m:
                out[m.group(1)] = ln
        return out

    def score(res):
        d = docs_from(res)
        assert len(d) == len(bodies), "%d of %d records lost in assembly" % (len(d), len(bodies))
        bm = BM25(d)
        a = sum(1 for f, q in qa if bm.rank(q).index(f) + 1 <= 3) / len(qa)
        b = sum(1 for f, q in qb if bm.rank(q).index(f) + 1 <= 3) / len(qb)
        return a, b

    print("\n%-14s %-8s %-9s %-11s %-11s %s"
          % ("budget", "tokens", "over", "questions@3", "searchbox@3", "words/line"))
    rows = {}
    budgets = [1500, 1918, 2500, 3063, 4000, 5000, 6484, None]
    for bud in budgets:
        res = ix.memory_index(budget_tokens=bud)
        assert res["records"] == len(bodies), "a record was dropped at budget %s" % bud
        if bud:
            assert res["tokens_estimate"] <= bud or res["over_budget"] > 0, \
                "budget %s exceeded without saying so" % bud
        a, b = score(res)
        wl = res["words"] / res["records"]
        rows[str(bud)] = dict(tokens=res["tokens_estimate"], over=res["over_budget"],
                              questions=a, searchbox=b, words_per_line=wl)
        print("%-14s %-8d %-9d %-11.3f %-11.3f %.1f"
              % (bud or "unlimited", res["tokens_estimate"], res["over_budget"], a, b, wl))

    # ---- the baselines it has to be read against
    hand = BM25({k: v for k, v in line_for.items() if k in bodies})
    ha = sum(1 for f, q in qa if hand.rank(q).index(f) + 1 <= 3) / len(qa)
    hb = sum(1 for f, q in qb if hand.rank(q).index(f) + 1 <= 3) / len(qb)
    ceil_ = BM25(bodies)
    ca = sum(1 for f, q in qa if ceil_.rank(q).index(f) + 1 <= 3) / len(qa)
    cb = sum(1 for f, q in qb if ceil_.rank(q).index(f) + 1 <= 3) / len(qb)
    hand_tokens = int(sum(len(v.split()) for k, v in line_for.items() if k in bodies) * 1.35)
    print("\n%-14s %-8d %-9s %-11.3f %-11.3f" % ("hand-written", hand_tokens, "-", ha, hb))
    print("%-14s %-8s %-9s %-11.3f %-11.3f" % ("CEILING notes", "207k", "-", ca, cb))

    # ---- POSITIVE CONTROL and the falsifier
    unl = rows["None"]
    ok_ctrl = abs(unl["questions"] - 0.692) < 0.03 and abs(unl["searchbox"] - 0.842) < 0.03
    print("\nPOSITIVE CONTROL: unlimited reproduces the un-budgeted measurement "
          "(0.692 / 0.842): %s -> %.3f / %.3f" % (ok_ctrl, unl["questions"], unl["searchbox"]))

    at = rows["3063"]
    kept = (at["searchbox"] - hb) / (unl["searchbox"] - hb) if unl["searchbox"] > hb else float("nan")
    print("\nAT THE CURRENT INDEX'S OWN BUDGET (3,063 tokens):")
    print("   search-box recall@3 %.3f against %.3f hand-written and %.3f unbudgeted"
          % (at["searchbox"], hb, unl["searchbox"]))
    print("   that keeps %.0f%% of the gain, for no extra tokens" % (100 * kept))
    print("\nFALSIFIER (below 0.6 at this budget means the gain does not survive): %s"
          % ("SURVIVES" if at["searchbox"] >= 0.6 else "DOES NOT SURVIVE -- it is a permanent trade"))

    OUT.write_text(json.dumps(dict(rows=rows, hand=dict(tokens=hand_tokens, questions=ha, searchbox=hb),
                                   ceiling=dict(questions=ca, searchbox=cb),
                                   control_ok=bool(ok_ctrl), kept_fraction=kept), indent=1),
                   encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
