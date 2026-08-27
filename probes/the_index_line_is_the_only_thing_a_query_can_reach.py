"""Claude Code auto-memory routes every retrieval through one index line. Does that line carry enough?

THE MECHANISM, as documented: a short always-loaded index file names each topic file in one line, and
the topic files are loaded ON DEMAND -- the agent decides what to open from the index alone. So the
index line is the only surface a future need can reach. A memory whose line does not contain the
words that need will use is, in practice, unreachable: the file exists, is correct, and is never
opened.

THIS STAGE MEASURES THE CORPUS, NOT BEHAVIOUR, on purpose. Generating questions from a memory's body
and then ranking by word overlap would hand the body-arm a victory by construction -- the questions
would carry the body's vocabulary. So stage one asks a question that needs no questions: how much of
each memory's own distinctive vocabulary survives into its index line?

THREE CONTROLS, because a low number here means nothing without them:
  * RANDOM FLOOR -- the same coverage computed against a DIFFERENT memory's index line. If real
    coverage barely exceeds this, the line is not carrying content, it is carrying English.
  * CEILING -- coverage of the body's distinctive terms by the memory's own `description:` field,
    which is what the writer produced when asked to summarise. It bounds what one line could do.
  * POSITIVE CONTROL -- a synthetic memory whose index line repeats its body's rarest terms must
    score ~1.0, and one whose line shares nothing must score ~0.0. If either fails, the metric is
    broken and no number below is usable.

Run: python probes/the_index_line_is_the_only_thing_a_query_can_reach.py [--top 12]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
OUT = pathlib.Path(__file__).with_suffix(".result.json")

# Words that carry no retrieval signal. Deliberately short: an aggressive list would flatter the
# index line by deleting exactly the common words it is full of.
STOP = set("""a an the and or but if then than that this those these is are was were be been being
am do does did doing have has had having i you he she it we they them his her its our their my your
of in on at to for with from by as into over under about after before between during without within
not no nor so such can could would should may might must will shall there here when where which who
whom what why how all any both each few more most other some only own same too very just also""".split())
TOKEN = re.compile(r"[a-z][a-z0-9_-]{2,}")


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def body_of(path: pathlib.Path) -> tuple[str, str, str]:
    """(slug, description, body-without-frontmatter)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    slug = (re.search(r"^name:\s*(\S+)", raw, re.M) or [None, path.stem])[1]
    desc = (re.search(r"^description:\s*(.+)$", raw, re.M) or [None, ""])[1].strip().strip('"')
    body = re.sub(r"^---.*?^---", "", raw, flags=re.S | re.M)
    return slug, desc, body


QUERYABLE = re.compile(r"^[a-z]{4,}$")


def distinctive(terms: list[str], idf: dict, df: dict, top: int) -> list[str]:
    """Terms a future QUESTION could plausibly use, ranked by how specific they are.

    THE FIRST VERSION OF THIS FUNCTION INVALIDATED THE WHOLE MEASUREMENT and the ceiling control is
    what caught it. Ranking by raw idf puts hapax identifiers on top -- `handoff_current_state`,
    `poison_v2_core`, `world-scan-leads-2026-07-12` -- which no one-line summary would ever contain,
    including the writer's own: the ceiling came out at 5.9%. A target no line can reach measures the
    target, not the line. So the vocabulary is restricted to what a question is made of: purely
    alphabetic, four characters or more, and appearing in at least three documents so it is shared
    language rather than a private label.
    """
    seen: dict = {}
    for t in terms:
        if QUERYABLE.match(t) and df.get(t, 0) >= 3:
            seen[t] = seen.get(t, 0) + 1
    return [t for t, _ in sorted(seen.items(), key=lambda kv: (-idf.get(kv[0], 0.0), -kv[1]))[:top]]


def coverage(line: str, terms: list[str]) -> float:
    if not terms:
        return float("nan")
    have = set(tokens(line))
    return sum(1 for t in terms if t in have) / len(terms)


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12, help="how many distinctive terms per memory")
    ap.add_argument("--seed", type=int, default=20260819)
    a = ap.parse_args(argv[1:])
    rng = random.Random(a.seed)

    index_text = (MEM / "MEMORY.md").read_text(encoding="utf-8")
    archive = MEM / "MEMORY_ARCHIVE.md"
    if archive.exists():
        index_text += "\n" + archive.read_text(encoding="utf-8")

    # every index line, keyed by the file it points at
    line_for: dict = {}
    for raw in index_text.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", raw):
            line_for.setdefault(fn, raw.strip())

    files = [p for p in sorted(MEM.glob("*.md")) if p.name not in ("MEMORY.md", "MEMORY_ARCHIVE.md")]
    docs = {}
    for p in files:
        slug, desc, body = body_of(p)
        docs[p.name] = dict(slug=slug, desc=desc, body=body, terms=tokens(body))

    # idf over the whole store, so "distinctive" means distinctive HERE
    df: dict = {}
    for d in docs.values():
        for t in set(d["terms"]):
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    idf = {t: math.log(n / c) for t, c in df.items()}

    indexed = [fn for fn in docs if fn in line_for]
    rows = []
    for fn in indexed:
        d = docs[fn]
        terms = distinctive(d["terms"], idf, df, a.top)
        other = line_for[rng.choice([x for x in indexed if x != fn])]
        rows.append(dict(
            file=fn, n_terms=len(terms), terms=terms,
            index_line=line_for[fn],
            cov_index=coverage(line_for[fn], terms),
            cov_random=coverage(other, terms),
            cov_desc=coverage(d["desc"], terms),
            body_words=len(d["terms"])))

    # ---------------- POSITIVE CONTROLS on the metric itself ----------------
    fake_terms = ["zarquon", "blorptastic", "quibbleflux", "mnemophage"]
    ctrl_hi = coverage("- [x](y.md) zarquon blorptastic quibbleflux mnemophage", fake_terms)
    ctrl_lo = coverage("- [x](y.md) nothing in common at all", fake_terms)
    ok = abs(ctrl_hi - 1.0) < 1e-9 and abs(ctrl_lo) < 1e-9
    print("METRIC CONTROLS: full-overlap line scores %.2f (want 1.00), disjoint line scores %.2f "
          "(want 0.00) -> %s" % (ctrl_hi, ctrl_lo, "OK" if ok else "BROKEN, stop reading"))
    if not ok:
        return 2

    def summary(key):
        v = sorted(r[key] for r in rows)
        m = len(v)
        return dict(mean=sum(v) / m, median=v[m // 2], p10=v[int(m * 0.1)], p90=v[int(m * 0.9)],
                    zero=sum(1 for x in v if x == 0.0), n=m)

    print("\n%d memory files, %d of them indexed, %d distinctive terms each"
          % (len(docs), len(indexed), a.top))
    print("\n%-28s %-7s %-7s %-7s %-7s %s" % ("coverage of body terms by", "mean", "median", "p10", "p90", "zero"))
    for label, key in (("the INDEX LINE (the ask)", "cov_index"),
                       ("a RANDOM other line (floor)", "cov_random"),
                       ("its own description (ceiling)", "cov_desc")):
        s = summary(key)
        print("%-28s %-7.3f %-7.3f %-7.3f %-7.3f %d/%d" %
              (label, s["mean"], s["median"], s["p10"], s["p90"], s["zero"], s["n"]))

    si, sr, sd = summary("cov_index"), summary("cov_random"), summary("cov_desc")
    lift = (si["mean"] - sr["mean"]) / sr["mean"] if sr["mean"] else float("inf")
    print("\nindex line over the random floor: %+.1f%%" % (100 * lift))
    print("index line as a share of what the writer's own description reaches: %.0f%%"
          % (100 * si["mean"] / sd["mean"]) if sd["mean"] else "n/a")
    print("memories whose index line reaches NONE of their distinctive terms: %d of %d (%.1f%%)"
          % (si["zero"], si["n"], 100 * si["zero"] / si["n"]))

    worst = sorted(rows, key=lambda r: (r["cov_index"], -r["body_words"]))[:6]
    print("\nleast reachable (line, then the terms it does not carry):")
    for r in worst:
        print("   %.2f  %s" % (r["cov_index"], r["index_line"][:96]))
        print("         misses: %s" % ", ".join(t for t in r["terms"] if t not in set(tokens(r["index_line"])))[:96])

    OUT.write_text(json.dumps(dict(
        top=a.top, files=len(docs), indexed=len(indexed),
        index=si, random_floor=sr, description_ceiling=sd,
        lift_over_floor=lift, rows=rows), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
