"""What shape is the deletion manifest actually? Read it, do not guess its keys.

_erasure_coverage parses the manifest to decide whether every registered target confirmed. It was written
against GUESSED key names ("targets"/"entries", "verified"/"erased"/"still_recoverable"). A coverage
report that silently finds no entries would report `complete: false` forever, or worse, `complete: true`
over an empty list -- the exact shape of defect this whole audit has been closing. So: print the real
structure, for a target that confirms and for one that leaks.
"""
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.deletion_manifest import ErasureTarget  # noqa: E402


class FakeIndex(ErasureTarget):
    """Stands in for the application's own vector index -- the store inspeximus does not manage."""

    def __init__(self, name="app-vector-index", leaky=False):
        self.name = name
        self.leaky = leaky
        self.rows = {}

    def add(self, subject, values):
        self.rows[subject] = list(values)

    def erase(self, subject):
        if not self.leaky:
            self.rows.pop(subject, None)
        return {"deleted": 0 if self.leaky else 1}

    def still_recoverable(self, subject, values):
        return any(v in (self.rows.get(subject) or []) for v in values)


def run(leaky: bool):
    d = tempfile.mkdtemp()
    st = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
    idx = FakeIndex(leaky=leaky)
    st.register_erasure_target(idx)
    st.remember("alice's address is 12 Rose Lane", key="a::addr", object="12 Rose Lane",
                source={"doc": "crm/alice"})
    idx.add("crm/alice", ["12 Rose Lane"])
    res = st.forget_subject("crm/alice", request_id="D1", basis="GDPR Art.17")
    label = "LEAKY target (erase does nothing)" if leaky else "HONEST target (erase works)"
    print(f"=== {label}")
    man = res.get("manifest")
    print("  manifest top-level keys:", list(man) if isinstance(man, dict) else type(man).__name__)
    if isinstance(man, dict):
        for k, v in man.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                print(f"  list field {k!r}: {len(v)} entr(ies), first keys: {list(v[0])}")
                print(f"     first entry: {json.dumps(v[0], ensure_ascii=False, default=str)[:260]}")
    print("  coverage:", json.dumps(res.get("coverage"), ensure_ascii=False)[:320])
    print()


run(leaky=False)
run(leaky=True)
print("A coverage parser must key off the REAL field names above. If `complete` is true for the leaky")
print("target, the parser is reading nothing and the product would certify an erasure that did not happen.")
