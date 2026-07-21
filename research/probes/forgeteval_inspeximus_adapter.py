"""forgeteval_inspeximus_adapter.py — measure inspeximus, honestly, on the PUBLIC ForgetEval-Adv external subset.

Benchmark: ForgetEval (Yang, "Control-Plane Placement Shapes Forgetting", arXiv:2606.15903; MIT,
WaylandYang/forgeteval-anon-supp). We run the 77 oracle-validated EXTERNAL adversarial cases
(data/hipporag_cases_external.json — the same subset the paper released for cross-system comparison).
Each case: setup_facts -> mutations (purge / supersede / release) -> final_query; PASS iff every
must_contain string is present in the top-k recall blob AND no must_not_contain string is (the paper's
exact deterministic substring rule). No LLM judge.

This is a DETERMINISTIC, no-LLM adapter — the same configuration the paper measures for Lethe / LangGraph
(their deterministic baselines score ~5% on identifier_obfuscation, 0% on cross_lingual because lexical
matching cannot canonicalize surface variants). We expect inspeximus to show the SAME structural profile: fine
on lexically-explicit supersession/purge, near-0 on the canonicalization categories that are inherently
LLM-bound. The point is an HONEST measured number + per-category map that quantifies exactly what an
LLM-at-mutation-time layer ("bod 3") would have to recover — not a claim inspeximus wins.

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
from inspeximus import Inspeximus

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
    m = Inspeximus(path=None)
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
    # ForgetEval scores the TOP-K RECALL BLOB. inspeximus's relevance-filtered recall() returns nothing when the
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


INHOUSE = CASES.parent / "hipporag_cases_inhouse.json"


def main():
    cases = json.load(open(CASES, encoding="utf-8"))
    print("=" * 72)
    print(f"inspeximus on ForgetEval-Adv external subset ({len(cases)} oracle-validated cases)")
    print("deterministic no-LLM adapter — the paper's Lethe/LangGraph configuration")
    print("=" * 72)

    # ── VALIDATE / stability check (the gate KILLED the single-number claim here) ──
    # On the full 385-case in-house set the overall score is DOMINATED by the forget-match threshold,
    # so no single headline number is defensible — a critic picks a threshold and gets 23% or 64%.
    if INHOUSE.exists():
        full = json.load(open(INHOUSE, encoding="utf-8"))
        print(f"\n[stability] full {len(full)}-case set — overall by forget-match threshold:")
        for thr in (0.4, 0.5, 0.6, 0.7, 0.8):
            _, tp, tn = evaluate(full, thr)
            print(f"    thr={thr}: {tp}/{tn} = {tp/tn:.1%}")
        print("    => the number is a threshold artifact of THIS adapter, not a store-capability metric.")
        print("    => NOT publishable as 'inspeximus scores X%'. Only threshold-INVARIANT results are honest:")
        print("       compound_fact = 0% at every threshold (deterministic partial-supersede is structurally")
        print("       impossible — drop one fact from a compound sentence, keep the other → needs an LLM).")
        print("    Same limit applies to the paper's own deterministic baselines (single points from their")
        print("    adapters). The benchmark scores the ADAPTER's forget heuristic, not the store alone.\n")

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
    print("\nVERDICT (gate/VALIDATE): the single-number 'inspeximus scores X% on ForgetEval' claim is KILLED --")
    print("the score is threshold-dominated (23-64% on the 385 set), so it measures our adapter's forget")
    print("heuristic, not inspeximus. The only threshold-INVARIANT, honest result is the structural limit")
    print("compound_fact = 0%% (deterministic partial-supersede is impossible). Everything else is not")
    print("robust enough to take outward. The same limit hits the paper's own deterministic baselines")
    print("(single points from their adapters). Two other artifacts this session caught the same class of")
    print("error (v3 inspeximus circular 1.0; the empty-recall false-100%%) — any knob-fed/oracle-fed memory")
    print("number needs a stability check BEFORE it is reported.")


if __name__ == "__main__":
    main()
