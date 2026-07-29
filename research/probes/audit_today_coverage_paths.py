"""Is `coverage` on every erasure path, or only on the one I happened to change?

That question has a bad track record in this codebase. Twice today a fix went into forget_subject while
the sibling destructive paths kept the defect -- and `_resolve_subject`'s own docstring records 1.53.0
making the same mistake before either of us. A caller can only rely on a field that is ALWAYS there; a
field present on one of five erasure entry points is worse than no field, because its absence reads as
"nothing to report" rather than "nobody looked".

Also checks the harder half: does `coverage.complete` ever read TRUE while the data is still recoverable?
That is the (a) class -- a clean verdict about input never examined -- on the surface that answers "did we
erase this person".
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.deletion_manifest import ErasureTarget  # noqa: E402


class Target(ErasureTarget):
    def __init__(self, name="idx", mode="honest"):
        self.name, self.mode, self.rows = name, mode, {}

    def seed(self, s, vals):
        self.rows[s] = list(vals)

    def erase(self, subject):
        if self.mode == "raises":
            raise RuntimeError("target unreachable")
        if self.mode == "honest":
            self.rows.pop(subject, None)
        return {"erased": 1}                     # claims success in every mode, including 'leaky'

    def still_recoverable(self, subject, values):
        if self.mode == "lies":
            return False                          # says it is gone while keeping it
        return any(v in (self.rows.get(subject) or []) for v in values)


def store(**kw):
    d = tempfile.mkdtemp()
    st = Inspeximus(path=os.path.join(d, "s.json"), receipts=True, **kw)
    st.remember("alice's address is 12 Rose Lane", key="a::addr", object="12 Rose Lane",
                source={"doc": "crm/alice"})
    return st


print("=== 1. which erasure paths report coverage at all? ===")
paths = {
    "forget_subject": lambda st: st.forget_subject("crm/alice", request_id="r"),
    "forget(ids=)": lambda st: st.forget(ids=[st.items[0]["id"]], request_id="r"),
    "forget_pii": lambda st: st.forget_pii(subject="crm/alice", request_id="r"),
    "retract_lineage": lambda st: st.retract_lineage("crm/alice"),
}
try:
    from inspeximus.compliance import retention_sweep
    paths["retention_sweep"] = lambda st: retention_sweep(st, 0.0, pii_only=False, apply=True,
                                                          request_id="r")
except Exception:
    pass
for name, call in paths.items():
    st = store()
    try:
        res = call(st)
        has = isinstance(res, dict) and "coverage" in res
        print(f"   {name:18s} coverage present: {has}"
              + ("" if has else "   <- an erasure that says nothing about what it covered"))
    except Exception as e:
        print(f"   {name:18s} raised {type(e).__name__}: {str(e)[:60]}")

print("\n=== 2. can coverage.complete read TRUE while the data survives? ===")
for mode, what in (("honest", "target really erases"),
                   ("leaky", "target reports success, keeps the data"),
                   ("lies", "target reports success AND claims it is unrecoverable"),
                   ("raises", "target throws")):
    st = store()
    t = Target(mode=mode)
    st.register_erasure_target(t)
    t.seed("crm/alice", ["12 Rose Lane"])
    try:
        cov = st.forget_subject("crm/alice", request_id="r").get("coverage", {})
        survives = "12 Rose Lane" in (t.rows.get("crm/alice") or [])
        flag = "  <-- CLEAN VERDICT OVER SURVIVING DATA" if cov.get("complete") and survives else ""
        print(f"   {mode:7s} complete={str(cov.get('complete')):5s}  data survives={survives}"
              f"   {what}{flag}")
    except Exception as e:
        print(f"   {mode:7s} raised {type(e).__name__}: {str(e)[:70]}")

print("\n=== 3. does a subject that is a PREFIX of another reach it? ===")
d = tempfile.mkdtemp()
st = Inspeximus(path=os.path.join(d, "p.json"), receipts=True)
st.remember("alice record", key="a", object="1", source={"doc": "crm/alice"})
st.remember("ali record", key="b", object="2", source={"doc": "crm/ali"})
res = st.forget_subject("crm/ali", request_id="r")
left = sorted((r.get("text") or "") for r in st.items if r.get("status") == "active")
print(f"   forget_subject('crm/ali') erased={res['erased']}  survivors={left}")
print("   -> 'alice record' must survive; if it is gone, a prefix reaches a different subject.")
