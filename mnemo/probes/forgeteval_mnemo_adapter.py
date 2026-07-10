"""forgeteval_mnemo_adapter.py — measure mnemo, honestly, on the PUBLIC ForgetEval-Adv external subset.

Benchmark: ForgetEval (Yang, "Control-Plane Placement Shapes Forgetting", arXiv:2606.15903; MIT,
WaylandYang/forgeteval-anon-supp). We run the 77 oracle-validated EXTERNAL adversarial cases
(data/hipporag_cases_external.json — the same subset the paper released for cross-system comparison).
Each case: setup_facts -> mutations (purge / supersede / release) -> final_query; PASS iff every
must_contain string is present in the top-k recall blob AND no must_not_contain string is (the paper's
exact deterministic substring rule). No LLM judge.

This is a DETERMINISTIC, no-LLM adapter — the same configuration the paper measures for Lethe / LangGraph
(their deterministic baselines score ~5% on identifier_obfuscation, 0% on cross_lingual because lexical
matching cannot canonicalize surface variants). We expect mnemo to show the SAME structural profile: fine
on lexically-explicit supersession/purge, near-0 on the canonicalization categories that are inherently
LLM-bound. The point is an HONEST measured number + per-category map that quantifies exactly what an
LLM-at-mutation-time layer ("bod 3") would have to recover — not a claim mnemo wins.

ADAPTER (deterministic, disclosed — no per-case tuning):
  remember(fact) for each setup fact (free text; ForgetEval facts carry no app keys).
  purge(target) / release(target): forget() every active memory that CONTAINS the target's distinctive
      tokens (token-containment >= THRESHOLD of the target's non-stopword tokens). Lexical only.
  supersede(old, new): forget() memories matching `old` (same rule), then remember(new).
  final_query: recall(query, k=10, mode='lexical') -> join text -> substring score.
THRESHOLD is a single global constant, swept below to show the number isn't threshold-cherry-picked.
"""
import json, sys, pathlib
from collections import Counter, defaultdict
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mnemo import Mnemo

CASES = pathlib.Path("C:/Users/Danculus/AppData/Local/Temp/claude/C--Users-Danculus-agora/"
                     "912bf97c-41d7-4a8f-9c37-23df5a11bc8f/scratchpad/forgeteval/data/"
                     "hipporag_cases_external.json")
STOP = set("the a an is are was were to of in on at and or for it its his her their he she they "
           "as with be has have had now still call calls called label labels project identifier "
           "currently primary use uses used from also does not".split())


def toks(s):
    return {w for w in "".join(c.lower() if (c.isalnum() or c in "-_@.") else " " for c in s).split()
            if w and w not in STOP}


def _match_ids(m, target, thr):
    """active memory ids whose text contains >= thr of the target's distinctive tokens."""
    tt = toks(target)
    if not tt:
        return []
    out = []
    for r in m.items:
        if r.get("status") != "active":
            continue
        overlap = len(tt & toks(r["text"])) / len(tt)
        if overlap >= thr:
            out.append(r["id"])
    return out


def run_case(case, thr):
    m = Mnemo(path=None)
    for f in case["setup_facts"]:
        m.remember(f)
    for mut in case["mutations"]:
        op = mut[0]
        if op in ("purge", "release"):
            ids = _match_ids(m, mut[1], thr)
            if ids:
                m.forget(ids)
        elif op == "supersede":
            old, new = mut[1], mut[2]
            ids = _match_ids(m, old, thr)
            if ids:
                m.forget(ids)
            m.remember(new)
    # ForgetEval scores the TOP-K RECALL BLOB. mnemo's relevance-filtered recall() returns nothing when the
    # query shares no tokens with the SURVIVING facts (e.g. after the query-matching fact is purged), which
    # would let must_not pass on an EMPTY blob — a false 'forgot it' when the forbidden fact is still stored
    # (caught by the cross_lingual debug: survivors kept 北京/Peking but recall returned ''). The faithful blob
    # for a <=10-fact store is the top-10 = ALL surviving active memories (what the store failed to forget),
    # so must_not actually tests residual content, not query-lexical-overlap.
    hits = m.recall(case["final_query"], k=10, mode="lexical", min_relevance=0.0)
    seen = {h["id"] for h in hits}
    active_rest = [r for r in m.items if r.get("status") == "active" and r["id"] not in seen]
    blob = " ".join([h["text"] for h in hits] + [r["text"] for r in active_rest][:max(0, 10 - len(hits))]).lower()
    ok_contain = all(s.lower() in blob for s in case.get("must_contain", []))
    ok_not = all(s.lower() not in blob for s in case.get("must_not_contain", []))
    return ok_contain and ok_not


def evaluate(cases, thr):
    by_cat = defaultdict(lambda: [0, 0])
    for c in cases:
        p = run_case(c, thr)
        d = by_cat[c["category"]]
        d[1] += 1
        d[0] += 1 if p else 0
    total_p = sum(v[0] for v in by_cat.values())
    total_n = sum(v[1] for v in by_cat.values())
    return by_cat, total_p, total_n


def main():
    cases = json.load(open(CASES, encoding="utf-8"))
    print("=" * 72)
    print(f"mnemo on ForgetEval-Adv external subset ({len(cases)} oracle-validated cases)")
    print("deterministic no-LLM adapter — the paper's Lethe/LangGraph configuration")
    print("=" * 72)

    # primary threshold + sweep (honesty: the number is not threshold-cherry-picked)
    for thr in (0.5, 0.6, 0.7):
        by_cat, tp, tn = evaluate(cases, thr)
        tag = "  <-- primary" if thr == 0.6 else ""
        print(f"\nthreshold={thr}: OVERALL {tp}/{tn} = {tp/tn:.1%}{tag}")
        if thr == 0.6:
            for cat in sorted(by_cat):
                p, n = by_cat[cat]
                print(f"    {cat:<26} {p}/{n} = {p/n:.0%}")
    # the paper's own systems on the SAME 77 external cases (data/external_subset_results.json)
    print("\nSame 77 cases, paper's reported systems (their adapters):")
    field = [("Lethe (det)", 33.8), ("LangGraph (det)", 32.5), ("Mem0 (det)", 28.6),
             ("Mem0+v3 (det)", 24.7), ("Lethe+LLM", 45.5), ("LangGraph+LLM", 50.6),
             ("A-MEM", 42.6), ("OpenMemory", 50.8), ("Letta+LLM", 80.3)]
    for name, rate in field:
        print(f"    {name:<18} {rate:.1f}%")
    print("\nReading (honest):")
    print("  * mnemo's deterministic no-LLM adapter lands at ~42% (range 30-44% over the forget-match")
    print("    threshold) — at the TOP of the pure-deterministic band (Lethe 33.8 / LangGraph 32.5 /")
    print("    Mem0 28.6), while staying zero-dependency. It is strong on lexically-explicit forgetting")
    print("    (substring_trap 100%, temporal_qualifier 100%, paraphrase_supersession 75%).")
    print("  * The gap to the LLM-hook configs (45-80%) is concentrated in the SURFACE-CANONICALIZATION")
    print("    categories mnemo scores 0/8 on — identifier_obfuscation, cross_lingual_identifier,")
    print("    compound_fact (partial supersede) — which are inherently LLM-at-mutation-time bound.")
    print("    That 0/8 band is exactly what a 'bod 3' LLM adjudicator over mnemo would have to recover.")
    print("\nHONEST CAVEATS (this is NOT an apples-to-apples head-to-head):")
    print("  - This adapter is OURS, not an official ForgetEval adapter; the paper's numbers use the")
    print("    authors' own adapters, so cross-system deltas reflect adapter choices too, not only stores.")
    print("  - 'blob = top-10 = all surviving active facts' (faithful for these <=4-fact cases); an")
    print("    earlier version scored an empty relevance-filtered recall and FALSELY passed the canonical")
    print("    categories 100% (empty blob trivially satisfies must_not) — corrected here.")
    print("  - Threshold 0.6 is a single global constant, reported across a sweep (not per-case tuned).")
    print("  - Publishing any of this outward requires the full validate->storm->audit->verify gate.")


if __name__ == "__main__":
    main()
