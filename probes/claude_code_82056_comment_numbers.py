"""Every number in the gated comment for anthropics/claude-code#82056, re-derived. Non-zero on any mismatch.

The comment tells a maintainer-facing thread what a partial index load cost us, so each figure is
recomputed from the pinned fixtures rather than quoted from the run that produced it. The four index
states live in probes/fixtures/ and are gitignored: they are the private auto-memory index, so a
reader of the public repo cannot re-run this, and the comment says so rather than implying otherwise.

CONTROLS:
  * THE FIXTURES ARE ASSERTED by byte size, so a fixture that silently became a different file cannot
    pass by agreeing with itself.
  * THE CANCELLATION IS CHECKED IN BOTH HALVES -- the near-zero total AND the large fixed-pool gain --
    because quoting either alone is the defect this comment exists to correct.
  * THE WARNING COUNT is derived by grepping our own session transcripts, not remembered.
  * NO OVERCLAIM STRINGS: the comment must not contain "first", "nobody has", or "proves".

Run: python probes/claude_code_82056_comment_numbers.py
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
DRAFT = ROOT / "agora_output" / "drafts" / "claude_code_82056_load_receipt_cost.md"
SESSIONS = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora")
TEXT = re.sub(r"\s+", " ", DRAFT.read_text(encoding="utf-8").replace("\u2212", "-"))
checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def says(*bits):
    missing = [b for b in bits if re.sub(r"\s+", " ", b) not in TEXT]
    return (not missing), ("MISSING: " + " | ".join(missing) if missing else "")


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


STATES = {"02-uncrowded": 19990, "03-written-lines": 42664}
raw = {}
for name, size in STATES.items():
    p = FIX / ("MEMORY.md." + name)
    if not p.exists():
        print("fixture missing: %s" % p)
        sys.exit(2)
    raw[name] = p.read_text(encoding="utf-8")
    ck("fixture %s is the pinned file" % name, len(p.read_bytes()) == size, "%d B" % len(p.read_bytes()))
ARCH = (FIX / "MEMORY_ARCHIVE.md").read_text(encoding="utf-8")


def entries(txt, with_archive=True):
    src = txt + ("\n" + ARCH if with_archive else "")
    d = {}
    for line in src.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", line):
            if fn != "MEMORY_ARCHIVE.md":
                d.setdefault(fn, line.strip())
    return d


def loaded(txt, cap=25000, lines=200):
    kept, tot = [], 0
    for line in txt.split("\n"):
        b = len(line.encode("utf-8")) + 2
        if len(kept) >= lines or tot + b > cap:
            break
        kept.append(line)
        tot += b
    return "\n".join(kept)


QA = json.loads((HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json")
                .read_text(encoding="utf-8"))["rows"]
QB = json.loads((HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json")
                .read_text(encoding="utf-8"))
A_all, W_all = entries(raw["02-uncrowded"]), entries(raw["03-written-lines"])
qa = [(r["file"], r["query"]) for r in QA if r["file"] in A_all and r["file"] in W_all]
qb = [(k, v) for k, v in QB.items() if k in A_all and k in W_all and len(v.split()) >= 2]
ck("120 queries per register", len(qa) == 120 and len(qb) == 120, "%d / %d" % (len(qa), len(qb)))
ck("comment says so", *says("120 model-written queries per register"))


def hits(idx, qs):
    bm = BM25(idx) if idx else None
    return [1 if (bm and f in idx and bm.rank(q).index(f) + 1 <= 3) else 0 for f, q in qs]


def boot(x, y, seed=11, n=20000):
    rng = random.Random(seed)
    d = []
    for _ in range(n):
        ii = [rng.randrange(len(x)) for _ in x]
        d.append(sum(y[i] for i in ii) / len(ii) - sum(x[i] for i in ii) / len(ii))
    d.sort()
    return d[int(.025 * n)], d[int(.975 * n)]


# ---- the whole-file measurement the comment opens with
fa, fw = hits(A_all, qa), hits(W_all, qa)
lo, hi = boot(fa, fw)
delta = sum(fw) / len(fw) - sum(fa) / len(fa)
ck("whole-file gain +0.242 [+0.167, +0.317]",
   abs(delta - 0.242) < .005 and abs(lo - 0.167) < .01 and abs(hi - 0.317) < .01,
   "%+.3f [%+.3f, %+.3f]" % (delta, lo, hi))
ck("comment says so", *says("+0.242 recall@3", "[+0.167, +0.317]"))

# ---- what a session actually loads
A, W = entries(loaded(raw["02-uncrowded"]), False), entries(loaded(raw["03-written-lines"]), False)
la, lw = hits(A, qa), hits(W, qa)
ck("on the loaded prefix the same change is worth +0.092",
   abs(sum(lw) / len(lw) - sum(la) / len(la) - 0.092) < .005,
   "%+.3f" % (sum(lw) / len(lw) - sum(la) / len(la)))
ck("comment says so", *says("it was worth +0.092"))
total = len(entries(raw["03-written-lines"], False))
ck("95 of 229 entries, 41%, outside the window",
   total == 229 and total - len(W) == 95 and round(100 * (total - len(W)) / total) == 41,
   "%d of %d outside" % (total - len(W), total))
ck("comment says so", *says("95 of 229 entries \u2014 41% \u2014 were outside the window"))
ck("the file was 42,666 bytes / 248 lines",
   abs(len(raw["03-written-lines"].replace("\n", "\r\n").encode("utf-8")) - 42666) <= 2
   and len(raw["03-written-lines"].splitlines()) == 248,
   "%d B, %d lines" % (len(raw["03-written-lines"].replace("\n", "\r\n").encode("utf-8")),
                       len(raw["03-written-lines"].splitlines())))
ck("comment says so", *says("42,666 bytes / 248 lines"))

# ---- THE CANCELLATION, both halves, because either alone misleads
sa, sw = hits(A, qb), hits(W, qb)
slo, shi = boot(sa, sw)
sdelta = sum(sw) / len(sw) - sum(sa) / len(sa)
ck("second register totals +0.000 [-0.083, +0.083]",
   abs(sdelta) < .005 and abs(slo + 0.083) < .01 and abs(shi - 0.083) < .01,
   "%+.3f [%+.3f, %+.3f]" % (sdelta, slo, shi))
# says() normalises whitespace but NOT the minus sign; TEXT folds U+2212 to ASCII, so the
# check must too, or it looks for a character the compared string no longer contains.
ck("comment says so", *says("+0.000 [-0.083, +0.083]"))
both = [(f, q) for f, q in qb if f in A and f in W]
pa, pw = hits(A, both), hits(W, both)
plo, phi = boot(pa, pw)
pdelta = sum(pw) / len(pw) - sum(pa) / len(pa)
ck("fixed-pool gain +0.207 [+0.086, +0.328]",
   abs(pdelta - 0.207) < .006 and abs(plo - 0.086) < .012 and abs(phi - 0.328) < .012,
   "%+.3f [%+.3f, %+.3f]" % (pdelta, plo, phi))
ck("comment says so", *says("+0.207 [+0.086, +0.328]"))
ck("reachable targets fell 77 to 58",
   sum(1 for f, _ in qb if f in A) == 77 and sum(1 for f, _ in qb if f in W) == 58,
   "%d -> %d" % (sum(1 for f, _ in qb if f in A), sum(1 for f, _ in qb if f in W)))
ck("comment says so", *says("77 \u2192 58"))
ck("BOTH halves are in the comment -- neither may be quoted alone",
   "+0.000" in TEXT and "+0.207" in TEXT)

# ---- the warnings, counted from the transcripts rather than remembered
# THIS SESSION QUOTES THE WARNING STRINGS IN ITS OWN GREPS, and counting it inflated the total from
# 12 to 22. A transcript that contains the evidence of a search for X is not an occurrence of X.
THIS_SESSION = "7dccb956"
pairs, sess = set(), set()
for p in SESSIONS.glob("*.jsonl"):
    if p.name.startswith(THIS_SESSION):
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    for m in set(re.findall(r"MEMORY\.md is ([0-9.]+) ?KB, approaching", t)):
        pairs.add((p.name, m))
        sess.add(p.name)
ck("twelve near-limit warnings across eight sessions", len(pairs) == 12 and len(sess) == 8,
   "%d warnings, %d sessions" % (len(pairs), len(sess)))
ck("comment says so", *says("twelve near-limit warnings across eight sessions in twenty-eight days"))
found = {m for _, m in pairs}
ck("every one of them names a BYTE size, none a line count",
   all(re.fullmatch(r"[0-9.]+", k) for k in found) and len(found) == 10,
   "sizes: %s" % sorted(found, key=float))
ck("comment says so", *says("all naming a byte size"))

# ---- the failed reader arm, quoted honestly
ck("the LLM-reader arm scored 0.067", *says("recall@3 0.067"))
ck("and the comment says WHY it failed", *says("the same three files for unrelated questions"))

# ---- no-overclaim guard
for bad in ("first recall measurement", "nobody has", "we prove", "proves that"):
    ck("no overclaim: %r absent" % bad, bad.lower() not in TEXT.lower())
ck("the private-corpus limit is stated", *says("One private store"))
ck("it ends on a question rather than a result", TEXT.rstrip().endswith("— Rastislav")
   and "Does\nanyone have a way to log" in re.sub(r"[ \t]+", " ", DRAFT.read_text(encoding="utf-8")))

bad = [c for c in checks if not c[1]]
w = max(len(c[0]) for c in checks)
for name, ok, detail in checks:
    print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
print("\n%d/%d checks pass" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if bad else 0)
