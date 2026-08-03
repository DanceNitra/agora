"""How many of your answers change if you ask the same questions in a different order?

A retrieval system whose read path writes -- bumping an access count, a recency clock, or any
per-record score that feeds back into ranking -- answers query N+1 from a store that queries 1..N
already edited. This measures that directly, and it needs no LLM calls.

    take a fixed question set, ask it in several different orders, each time from a FRESH store,
    and count how many answers differ from the canonical-order answer.

8 questions x 8 permutations (the reversal plus 7 rotations) = 64 comparisons per mode. The
permutations are deterministic, so the number can be quoted rather than sampled.

WHY THIS FILE AND NOT THE ONE IN THE LIBRARY'S TEST SUITE. inspeximus's own conformance fixture is
engineered: it holds a deliberate near-tie and an exact 4-way tie, because it exists to test tie
policy, and it reads 64/64 in hybrid. A number measured there invites the obvious objection that
near-tied records flip under any nudge. This corpus has no constructed ties.

It is, however, topically DENSE, and that was a correction rather than a choice. The first version
used 30 unrelated facts, and every arm measured 0/64 including reinforce=True -- because each query
matched exactly one record, so there was nothing for a value bump to reorder. The control caught it:
if the mechanism arm is zero, the pure arm's zero means nothing. The facts now share vocabulary
(audit, review, team, retained, annual) so several records genuinely compete for each query, which is
the realistic case for any store worth ranking. That is a different thing from tuning ties.

The embedder is a deterministic hash, so `semantic` and `hybrid` are really those channels instead of
silently falling back to lexical, and anyone can run this with no model download and no dependency.
`semantic_threshold` is lowered because 30 records would otherwise sit below the routing threshold and
`auto` would resolve to lexical -- an honest environment note, not a thumb on the scale.

CONTROLS, because a sweep that measures nothing also reports zero:
  * the DENOMINATOR is asserted, not assumed -- `changed == 0` is also what an empty sweep returns;
  * the reinforce=False arm must be EXACTLY 0, and this is close to a tautology (with the only
    writing path gone, recall is a pure function of (store, query)) -- it is a wiring check, and is
    reported as one, not as the finding;
  * the reinforce=True arm must be non-zero, or the harness is not exercising the mechanism at all
    and the zero next door means nothing.
"""

import sys

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")

from inspeximus import Inspeximus  # noqa: E402

FACTS = [
    "the annual security audit is scheduled for the third week of November",
    "the annual compliance audit is scheduled for the second week of March",
    "the annual financial audit is scheduled for the first week of June",
    "the annual supplier audit is scheduled for the last week of September",
    "the security review must be completed before the annual audit begins",
    "the compliance review is signed off by the compliance team each quarter",
    "the financial review is signed off by the finance team each quarter",
    "the supplier review is signed off by the procurement team each quarter",
    "invoices above fifty thousand need two signatures from the finance team",
    "invoices above ten thousand need one signature from the finance team",
    "invoices from suppliers need a signature from the procurement team",
    "expense claims need a signature from the line manager within sixty days",
    "the security team reports to the chief technology officer",
    "the compliance team reports to the chief financial officer",
    "the finance team reports to the chief financial officer",
    "the procurement team reports to the chief operating officer",
    "backups are retained for ninety days on the primary cluster",
    "backups are retained for one year on the archive cluster",
    "audit logs are retained for seven years for compliance reasons",
    "access logs are retained for thirty days on the primary cluster",
    "penetration tests are commissioned annually by the security team",
    "vulnerability scans are commissioned quarterly by the security team",
    "supplier assessments are commissioned annually by the procurement team",
    "salary reviews happen once a year in April for every team",
    "performance reviews happen twice a year for every team",
    "the board reviews the audit findings at the last meeting of the year",
    "the board reviews the financial results at the second meeting of each quarter",
    "quarterly results are published on the second Tuesday after the board meets",
    "the incident postmortem is reviewed by the security team within a week",
    "the annual report is published after the financial audit is signed off",
]

QUERIES = [
    "when is the annual audit",
    "who signs invoices",
    "who does the compliance team report to",
    "how long are backups retained",
    "when are reviews signed off",
    "who commissions the tests",
    "when are salaries reviewed",
    "what does the board review",
]

K = 5


def permutations(qs):
    """The reversal plus every rotation. Deterministic, so the failure rate is a number, not a sample."""
    return [list(reversed(qs))] + [qs[r:] + qs[:r] for r in range(1, len(qs))]


SWEEP = len(permutations(list(QUERIES))) * len(QUERIES)


def _embed(text):
    """A deterministic hash embedding, so `semantic` and `hybrid` are really those channels and not a
    silent fallback to lexical, without adding a dependency or a model download. Same text always
    gives the same vector, which is what the sweep needs."""
    import hashlib
    import math
    dim = 64
    v = [0.0] * dim
    for tok in text.lower().split():
        h = hashlib.sha256(tok.encode()).digest()
        for i in range(dim):
            v[i] += (h[i % len(h)] - 127.5) / 127.5
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def build():
    m = Inspeximus(path=None, embed=_embed)
    m.semantic_threshold = 1          # 30 records must reach the semantic/hybrid routing, not sit under it
    for i, f in enumerate(FACTS):
        m.remember(f, key="f%d" % i)
    return m


def ask(store, q, mode, **kw):
    hits = store.recall(q, k=K, mode=mode, **kw) or []
    return tuple(h["text"] for h in hits), (hits[0]["text"] if hits else None)


def sweep(mode, **kw):
    """Returns (changed_top5, changed_top1, total). Every permutation starts from a FRESH store, so
    the only variable is the order the questions were asked in."""
    base_store = build()
    base = {q: ask(base_store, q, mode, **kw) for q in QUERIES}
    c5 = c1 = total = 0
    for perm in permutations(list(QUERIES)):
        store = build()
        got = {q: ask(store, q, mode, **kw) for q in perm}
        for q in QUERIES:
            total += 1
            c5 += got[q][0] != base[q][0]
            c1 += got[q][1] != base[q][1]
    return c5, c1, total


def main():
    print(f"{len(FACTS)} facts, {len(QUERIES)} questions, {len(permutations(list(QUERIES)))} orders, "
          f"k={K} -> {SWEEP} comparisons per arm\n")
    print(f"{'mode':<10}{'arm':<20}{'top-5 changed':>16}{'top-1 changed':>16}")
    rows = {}
    for mode in ("lexical", "semantic", "hybrid", "auto"):
        for label, kw in (("reinforce=True", {"reinforce": True}), ("default (pure)", {})):
            try:
                c5, c1, total = sweep(mode, **kw)
            except Exception as exc:                      # a mode this environment cannot resolve
                print(f"{mode:<10}{label:<20}{'unavailable: ' + type(exc).__name__:>32}")
                continue
            assert total == SWEEP, f"the sweep compared {total} answers, not {SWEEP}"
            rows[(mode, label)] = (c5, c1)
            print(f"{mode:<10}{label:<20}{c5:>8}/{total:<7}{c1:>8}/{total:<7}")

    print("\ncontrols")
    pure_bad = {k: v for k, v in rows.items() if k[1] == "default (pure)" and v != (0, 0)}
    print(f"  every default arm is exactly 0/{SWEEP}: {not pure_bad}"
          + ("" if not pure_bad else f"  VIOLATIONS {pure_bad}"))
    print("     (a wiring check, not the finding: with the only writing path gone, recall is a pure")
    print("      function of (store, query) and this cannot fail)")
    live = [k for k, v in rows.items() if k[1] == "reinforce=True" and v[0] > 0]
    print(f"  at least one reinforce=True arm is non-zero: {bool(live)}  {[k[0] for k in live]}")
    print("     (without this the zeros above measure nothing)")
    print(f"  denominator asserted at {SWEEP} in every cell: True")


if __name__ == "__main__":
    main()
