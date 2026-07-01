"""Severe-test for mnemo recall(where=) — the metadata pre-filter ('filter before you rank').

Confirms the HARD metadata filter selects the right records (not just the right count) across scalar
equality, list membership, operator conditions ($in/$gte/$lte), top-level fields (valid_from, mtype) vs
meta fields, AND-ing multiple fields, no-filter passthrough, and an unknown-operator guard.

Zero-dependency. Run: python mnemo/probes/recall_where_test.py
"""
import sys, os
try:
    from mnemo import Mnemo
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from mnemo import Mnemo


def _texts(rs):
    return sorted(r["text"] for r in rs)


def main():
    m = Mnemo()
    A = "Caroline went to the support group"
    B = "Mel talked about the marathon"
    C = "Caroline mentioned her new job"
    m.remember(A, mtype="semantic", meta={"speaker": "Caroline"}, valid_from=100.0)
    m.remember(B, mtype="semantic", meta={"speaker": "Mel"}, valid_from=200.0)
    m.remember(C, mtype="episodic", meta={"speaker": "Caroline"}, valid_from=300.0)
    Q = "Caroline Mel support group job marathon"

    checks = []
    def chk(name, got, exp):
        ok = _texts(got) == sorted(exp)
        checks.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {_texts(got)}")

    chk("no filter -> all", m.recall(Q, k=10), [A, B, C])
    chk("scalar meta speaker=Caroline", m.recall(Q, k=10, where={"speaker": "Caroline"}), [A, C])
    chk("list meta speaker in [Mel]", m.recall(Q, k=10, where={"speaker": ["Mel"]}), [B])
    chk("op $in meta speaker", m.recall(Q, k=10, where={"speaker": {"$in": ["Caroline"]}}), [A, C])
    chk("op time-range on top-level valid_from", m.recall(Q, k=10, where={"valid_from": {"$gte": 150.0, "$lte": 250.0}}), [B])
    chk("top-level mtype scalar", m.recall(Q, k=10, where={"mtype": "semantic"}), [A, B])
    chk("AND: Caroline + semantic (excludes episodic)", m.recall(Q, k=10, where={"speaker": "Caroline", "mtype": "semantic"}), [A])
    chk("$ne excludes Mel", m.recall(Q, k=10, where={"speaker": {"$ne": "Mel"}}), [A, C])
    chk("empty filter passthrough", m.recall(Q, k=10, where={}), [A, B, C])

    raised = False
    try:
        m.recall(Q, where={"speaker": {"$weird": 1}})
    except ValueError:
        raised = True
    checks.append(raised)
    print(f"  [{'PASS' if raised else 'FAIL'}] unknown operator raises ValueError")

    n_pass = sum(checks)
    print(f"\nrecall(where=) severe-test: {n_pass}/{len(checks)} passed")
    if n_pass != len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
