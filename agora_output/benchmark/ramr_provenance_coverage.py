"""RAMR metric: PROVENANCE COVERAGE — four numbers that must never be collapsed into one.

The reason this exists is a measurement, not a design taste. Our own production store carries a
populated `source` field on 98.3% of 210,499 records and only **0.01%** whose source resolves to
anything a reader could re-fetch: the field held `agent:scholar`, the identity of the WRITER. A schema
was being reported as a guarantee. safal207 measured the same gap independently on the Causal Memory
Layer corpus (5/5 locators, 1/5 bound to an immutable content identity) and declined to call the 100%
"stale-check coverage" — the discussion is anthropics/claude-code#34556, the contract is CML#270.

    locator_coverage               can the evidence point back to an origin at all?
    refetch_verification_coverage  can that origin be re-read and digest-compared?
    source_enumeration_coverage    can the AUTHORITATIVE source be enumerated, so deletion is
                                   detectable? An index-side scan can NEVER answer this: it reports
                                   what is present, and a deleted document emits exactly one event
                                   that nothing later mentions. Absent an enumerator this is None --
                                   UNKNOWN, not 0.0, because 0.0 is a measurement nobody made.
    environment_binding_coverage   is the record bound to the context in which reuse is safe?

Four numbers because they have four different remedies. A system reporting one number for all four is
not more concise, it is unable to say which repair it needs.

WHAT A SYSTEM MUST IMPLEMENT to appear here: an adapter with `write(text, source)` and `coverage()`.
That is deliberately tiny -- a conformance harness nobody can implement measures nothing.

    python ramr_provenance_coverage.py            # regenerate ramr_provenance_coverage_result.json
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "data", "ramr_chains_v0.1.0.jsonl")
OUT = os.path.join(HERE, "ramr_provenance_coverage_result.json")
sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")


def load_corpus(limit=300):
    rows = []
    with open(CORPUS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


# ── the three source REGIMES, because coverage is a property of how a system is USED, not only of what
# it can do. A library that supports re-fetchable sources still reports 0.01% if its callers write
# writer labels, which is precisely what happened to us. Reporting one regime would flatter whoever
# wrote the harness.
REGIMES = {
    "refetchable_path": lambda i, d: {"doc": os.path.join(d, "fact-%04d.txt" % i)},
    "writer_label": lambda i, d: {"doc": "agent:scholar"},
    "no_source": lambda i, d: None,
}


class InspeximusAdapter:
    name = "inspeximus"

    def __init__(self):
        from inspeximus import Inspeximus
        self._dir = tempfile.mkdtemp()
        self.ix = Inspeximus(os.path.join(self._dir, "store.json"))

    def write(self, i, text, source_fn):
        src = source_fn(i, self._dir)
        if src and not src["doc"].startswith("agent:"):
            with open(src["doc"], "w", encoding="utf-8") as fh:
                fh.write(text)
        self.ix.remember(text, source=src) if src else self.ix.remember(text)

    def coverage(self):
        return self.ix.check_sources()["coverage"]


class NaiveStoreAdapter:
    """A plain list with embeddings-and-text semantics: the shape most agent memories actually are. It
    is here as the FLOOR, so a reader can see what the metrics look like for a system that never
    modelled provenance -- and so a 0.0 in the table is legible rather than alarming."""
    name = "naive_store"

    def __init__(self):
        self.rows = []

    def write(self, i, text, source_fn):
        self.rows.append({"text": text})

    def coverage(self):
        return {"locator_coverage": 0.0, "refetch_verification_coverage": 0.0,
                "source_enumeration_coverage": None, "environment_binding_coverage": 0.0}


def run(adapter_cls, regime_name, rows):
    a = adapter_cls()
    fn = REGIMES[regime_name]
    for i, r in enumerate(rows):
        for fact in r.get("gold_facts") or []:
            a.write(i, fact, fn)
    return a.coverage()


def main():
    rows = load_corpus()
    facts = sum(len(r.get("gold_facts") or []) for r in rows)
    print("RAMR provenance coverage — %d chains, %d facts written per run" % (len(rows), facts))
    print()
    result = {"corpus": os.path.basename(CORPUS), "chains": len(rows), "facts": facts, "systems": {}}

    hdr = "%-14s %-18s %10s %10s %12s %10s" % ("system", "regime", "locator", "refetch", "enumeration",
                                               "env_bind")
    print(hdr)
    print("-" * len(hdr))
    for cls in (InspeximusAdapter, NaiveStoreAdapter):
        for regime in REGIMES:
            cov = run(cls, regime, rows)
            result["systems"].setdefault(cls.name, {})[regime] = cov
            print("%-14s %-18s %10.4f %10.4f %12s %10.4f"
                  % (cls.name, regime, cov["locator_coverage"], cov["refetch_verification_coverage"],
                     "unknown" if cov["source_enumeration_coverage"] is None
                     else "%.4f" % cov["source_enumeration_coverage"],
                     cov["environment_binding_coverage"]))
    print()

    ix = result["systems"]["inspeximus"]
    assert ix["refetchable_path"]["refetch_verification_coverage"] > 0.9, ix
    assert ix["writer_label"]["locator_coverage"] > 0.9, ix
    assert ix["writer_label"]["refetch_verification_coverage"] == 0.0, ix
    print("CONTROL: under `writer_label` the SAME library reports locator %.2f and refetch %.2f."
          % (ix["writer_label"]["locator_coverage"],
             ix["writer_label"]["refetch_verification_coverage"]))
    print("         That gap is the entire point -- it is our own production failure reproduced on a")
    print("         public corpus, and a single collapsed 'provenance coverage' number would have")
    print("         reported this store as 100% covered.")
    print()
    print("NOTE: environment_binding_coverage is 0.0 for every row above because no system here writes")
    print("      an environment binding yet. It is reported rather than omitted so the column exists")
    print("      when one does -- an absent metric reads as 'not applicable'.")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print()
    print("-> %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
