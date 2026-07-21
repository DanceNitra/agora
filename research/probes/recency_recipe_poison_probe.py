"""recency_recipe_poison_probe.py — the deterministic "recency wins" recipe is not truth-safe;
inspeximus's layered defense (corroboration gate + unforgeable earned-outcome) is.

CONTEXT. arXiv 2606.01435 ("Don't Ask the LLM to Track Freshness: A Deterministic Recipe for
Memory Conflict Resolution", 2026) resolves conflicting memories deterministically: when the same
item has several versions, KEEP THE ONE WITH THE MOST RECENT TIMESTAMP. That rule is correct and
cheap when writes are TRUSTED (it is exactly inspeximus's bi-temporal keyed ledger). This probe measures
what the recipe does not address: when a write may be ADVERSARIAL, "latest wins" gives the attacker
the write they most want — the LAST one. None of the 2026 conflict/forgetting benchmarks (MemConflict,
Memory-Agent-Bench Fact-Consolidation, From-Recall-to-Forgetting, LongMemEval knowledge-updates)
inject an adversarial later write, so the recipe is never stress-tested the way an attacker uses it.

THREE MEASURED LAYERS (same numeric fixture; a config value the store must keep current):

  A. RECIPE (pure recency, faithful ref-impl of 2606.01435)
        -> a single later write ALWAYS wins. Poison cost = 1 write. No notion of truth.

  B. + CORROBORATION GATE (inspeximus, supersede_requires_corroboration=True, opt-in)
        -> a single UNcorroborated later write is LINKED, not adopted: single-shot poison is held,
           and a genuinely corroborated/earned update is still ADOPTED (not "never change").
        -> BUT this gate is FIRST-MOVER, not truth-aware: an attacker who ESTABLISHES a corroborated
           false value FIRST holds it against a single honest correction. Write-count corroboration is
           Sybil-forgeable (our prior finding: membership-cost-vs-outcome-accountability). So the gate
           raises the single-shot cost; it is NOT a truth guarantee on its own.

  C. + EARNED OUTCOME (inspeximus, credit(ids, outcome) — the UNFORGEABLE channel)
        -> a single correction carrying earned good (a real resolved outcome, which an attacker who can
           only WRITE cannot manufacture) DOES dislodge a corroborated-but-unearned false and restore
           truth. This is the layer the recipe and the corroboration gate both lack.

HONEST FRAMING. Not a new law — a runnable product receipt. That recency is forgeable and that
write-count corroboration is Sybil-forgeable is established (ours + textbook moving-target/Cheng-
Friedman). The contribution is: inspeximus already ships the recipe (trusted keyed path) AND the two
defenses it lacks, and this probe MEASURES exactly where each layer holds and where it breaks —
tied to a recipe the field published this year.
"""
import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from inspeximus import Inspeximus

TRUE_V, FALSE_V, UPDATE_V = 30, 5, 45
def fact(v):  # paraphrase-stable numeric assertion; a numeric clash reliably fires inspeximus's toggle path
    return f"The server request timeout is configured to {v} seconds."


# ── A. faithful reference impl of the deterministic "recency wins" rule (arXiv 2606.01435) ──
class RecencyRecipe:
    def __init__(self): self._latest = {}          # key -> (ts, value); latest ts wins, no gate
    def write(self, v, ts):
        cur = self._latest.get("k")
        if cur is None or ts >= cur[0]: self._latest["k"] = (ts, v)
    def read(self): return self._latest.get("k", (0, None))[1]


def _active_value(m: Inspeximus):
    m.consolidate(dup_threshold=0.6)
    hits = [r for r in m.items if r["status"] == "active" and "timeout" in r["text"]]
    if not hits: return None
    hits.sort(key=lambda r: -r["value"])
    for tok in hits[0]["text"].replace(".", " ").split():
        if tok.isdigit(): return int(tok)
    return None


def _gated_store():
    m = Inspeximus(path=None)                        # in-memory, lexical (no embedder needed)
    m.supersede_requires_corroboration = True   # the opt-in corroboration gate
    return m


# ── A: recipe vs a single later poison write ──
def recipe_single_poison():
    r = RecencyRecipe(); t = time.time()
    r.write(TRUE_V, t); r.write(TRUE_V, t + 1); r.write(FALSE_V, t + 100)
    return r.read()

# ── B1: gate holds a single-shot poison against a standing earned-good fact ──
def gate_single_poison():
    m = _gated_store(); t = time.time()
    a = m.remember(fact(TRUE_V), valid_from=t); b = m.remember(fact(TRUE_V), valid_from=t + 1)
    m.credit([a, b], True)
    m.remember(fact(FALSE_V), valid_from=t + 100)     # single, uncorroborated, later
    return _active_value(m)

# ── B2: gate still ADOPTS a genuine corroborated+earned update (over-block control) ──
def gate_legit_update():
    m = _gated_store(); t = time.time()
    a = m.remember(fact(TRUE_V), valid_from=t); b = m.remember(fact(TRUE_V), valid_from=t + 1)
    m.credit([a, b], True)
    u1 = m.remember(fact(UPDATE_V), valid_from=t + 100)
    u2 = m.remember(fact(UPDATE_V), valid_from=t + 101)
    m.credit([u1, u2], True)                          # persistent + earned
    return _active_value(m)

# ── B3: gate is FIRST-MOVER — a pre-established corroborated FALSE holds vs a single honest correction ──
def gate_firstmover_false(n_false=3, correction_earned=False):
    m = _gated_store(); t = time.time()
    for j in range(n_false):
        m.remember(fact(FALSE_V), valid_from=t + j)   # attacker corroborates the false FIRST
    m.consolidate(dup_threshold=0.6)
    c = m.remember(fact(TRUE_V), valid_from=t + 100)   # single honest correction, later
    if correction_earned:
        m.credit([c], True)                            # C: correction carries UNFORGEABLE earned good
    return _active_value(m)


def main():
    print("=" * 78)
    print("The deterministic 'recency wins' recipe (arXiv 2606.01435) is not truth-safe; inspeximus layers are")
    print("=" * 78)
    print(f"true={TRUE_V}  poison={FALSE_V}  legit-update={UPDATE_V}\n")

    A   = recipe_single_poison()
    B1  = gate_single_poison()
    B2  = gate_legit_update()
    B3  = gate_firstmover_false(correction_earned=False)
    C   = gate_firstmover_false(correction_earned=True)

    def pois(v): return "POISONED" if v == FALSE_V else ("held" if v == TRUE_V else f"?({v})")
    def upd(v):  return "adopted" if v == UPDATE_V else ("over-blocked" if v == TRUE_V else f"?({v})")

    print(f"{'layer / scenario':<52}{'result':<12}{'value'}")
    print("-" * 78)
    print(f"{'A. recipe: 1 later poison write':<52}{pois(A):<12}{A}")
    print(f"{'B1. + corrob gate: 1-shot poison (true stands first)':<52}{pois(B1):<12}{B1}")
    print(f"{'B2. + corrob gate: legit corroborated+earned update':<52}{upd(B2):<12}{B2}")
    print(f"{'B3. + corrob gate: FALSE established first, honest fix':<52}{pois(B3):<12}{B3}")
    print(f"{'C.  + earned outcome: same, correction carries good':<52}{pois(C):<12}{C}")
    print("-" * 78)

    # pre-registered success criteria (stated before reading values):
    ok = {
        "A recipe poisoned by 1 write":                 A  == FALSE_V,
        "B1 gate holds single-shot poison":             B1 == TRUE_V,
        "B2 gate adopts a legit earned update":         B2 == UPDATE_V,
        "B3 gate is first-mover (false holds vs 1 fix)": B3 == FALSE_V,
        "C  earned outcome restores truth":             C  == TRUE_V,
    }
    print("\nPre-registered checks:")
    for k, v in ok.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\nReading:")
    print("  * recency alone: attacker wins with 1 last write (cost = 1).")
    print("  * corroboration gate: raises the single-shot cost, but is FIRST-MOVER, not truth-aware —")
    print("    it protects a standing corroborated value in EITHER direction, including a false one.")
    print("  * earned outcome (credit): the UNFORGEABLE tiebreaker an attacker who can only write cannot")
    print("    manufacture; a single earned correction dislodges a corroborated-but-unearned false.")
    print("\nRECEIPT:", "VALID — all 5 pre-registered checks hold" if all(ok.values())
          else "INVALID — a criterion did not hold; reframe, do not ship")


if __name__ == "__main__":
    main()
