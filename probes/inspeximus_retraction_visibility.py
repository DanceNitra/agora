"""When a retraction arrives and the live value survives, what does a downstream reader see?

yun520-1 asked on DeepSeek-V3#1466: in the keyed substrate, when a retraction arrives and the live
value stays "correct", is there a stale-retraction marker the consumer can see, or is the retraction
invisible to a reader who only looks at the live value? Their framing: does the substrate fail LOUD or
fail QUIET.

The answer is both, depending on how the contradiction arrived, so this measures the two paths side by
side rather than describing them. The consumer being simulated is the least curious one possible: a
plain `recall(query)` with no options, reading the returned dict.

  PATH A  the contradiction arrives as a WRITE and fails the corroboration bar. `consolidate()` links
          it to the standing record and refuses the overturn.
  PATH B  the contradiction arrives through `observe()` as read-path evidence against a key. It never
          writes an authoritative value; it can only REOPEN the settled record for review.

CONTROLS, because "no flag" and "no contradiction" look identical from the outside:
  * a store with NO contradiction must light up none of these surfaces, or every flag below is noise;
  * the live value must still be RETURNED in both paths -- a substrate that hides the contested value
    leaves the agent with nothing, which is a different failure, not a safer one.
"""

import sys

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")

from inspeximus import Inspeximus  # noqa: E402

QUERY = "what is the settlement account for vendor 42"
LIVE = "the settlement account for vendor 42 is IBAN SK11 9999"
RETRACTION = "the settlement account for vendor 42 is not IBAN SK11 9999"


def reader_view(m):
    """Exactly what a consumer who calls recall() and nothing else can observe."""
    hits = [h for h in (m.recall(QUERY, k=3) or []) if h["text"] == LIVE]
    if not hits:
        return None
    h = hits[0]
    return {"returned": True,
            "under_review": h.get("under_review"),
            "review_reason": h.get("review_reason"),
            "stale_derived": h.get("stale_derived"),
            "n_links": len(h.get("links") or [])}


def path_a():
    """A contradicting WRITE that fails the corroboration bar."""
    m = Inspeximus(path=None)
    m.supersede_requires_corroboration = True
    m.remember(LIVE, key="v42::a")
    m.remember(RETRACTION, key="v42::b", source={"doc": "one-actor.internal"})
    m.consolidate()
    return m


def path_b():
    """A contradiction arriving as read-path evidence, twice, from different supports."""
    m = Inspeximus(path=None)
    m.remember(LIVE, key="v42")
    m.observe(RETRACTION, key="v42", support="auditor.pdf")
    m.observe(RETRACTION, key="v42", support="bank.pdf")
    return m


def clean():
    m = Inspeximus(path=None)
    m.remember(LIVE, key="v42")
    return m


def main():
    print("what a plain recall() shows the consumer, per path\n")
    for name, build in (("PATH A  blocked contradicting write", path_a),
                        ("PATH B  observe() reopens the record", path_b),
                        ("CONTROL no contradiction at all", clean)):
        m = build()
        v = reader_view(m)
        extra = f"contradictions()={len(m.contradictions() or [])}  reopened()={len(m.reopened() or [])}"
        print(f"{name}")
        print(f"   {v}")
        print(f"   dedicated surfaces: {extra}")
        with_status = [h for h in (m.recall(QUERY, k=3, with_status=True) or []) if h["text"] == LIVE]
        if with_status:
            print(f"   with_status=True  : convergence={with_status[0].get('convergence')!r}")
        print()

    a, b, c = reader_view(path_a()), reader_view(path_b()), reader_view(clean())
    print("=" * 76)
    print(f"   live value still returned in all three: {a['returned'] and b['returned'] and c['returned']}")
    print(f"   PATH B is LOUD to a plain reader   : under_review={b['under_review']}")
    print(f"   PATH A is QUIET to a plain reader  : under_review={a['under_review']}, and the only")
    print(f"      trace is an unlabelled extra link ({a['n_links']} vs {c['n_links']} on the clean store)")
    print(f"   CONTROL lights up nothing          : {c['under_review'] is None and c['n_links'] == 0}")
    print("=" * 76)
    print("   So: loud when the contradiction came through observe(), quiet when it came as a write")
    print("   that the corroboration bar refused. The information is not lost -- contradictions()")
    print("   returns it -- but a consumer who only reads the live value is not told.")


if __name__ == "__main__":
    main()
