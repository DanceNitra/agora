"""Check the instrument before believing its verdict — both 'findings' look like MY probe's bugs.

detect_split_view returned {'fork': False, 'inconsistent': True, 'undetermined': False,
'at': ['n_writes']} and my helper looked for keys named split_view/split/divergent, so it scored a
correct answer as MISSED. erasure_certificate's self_check came back falsy and my re-verify call found
no such method, so 'refuses everything' may equally be a probe that called nothing.
"""
import inspect
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store(n=6, receipts=True):
    st = Inspeximus(path=None, receipts=receipts)
    for i in range(n):
        st.remember(f"fact number {i} about the billing system", key=f"k{i}", object=f"v{i}")
    return st


print("=== detect_split_view: read the contract, not my guess at it ===")
print(inspect.getdoc(Inspeximus.detect_split_view)[:900])
a, b = store(), store()
aa, ab = a.anchor(), b.anchor()
same = Inspeximus.detect_split_view(aa, [], aa, [], [])
diff = Inspeximus.detect_split_view(aa, [], ab, [], [])
print(f"\n  same anchor, no cosigs : {json.dumps(same, default=str)[:200]}")
print(f"  diff anchors, no cosigs: {json.dumps(diff, default=str)[:200]}")
print(f"  -> did it notice the difference? {diff != same}")

print("\n=== erasure_certificate: what does it actually return? ===")
st = store(receipts=True)
r = st.forget(where=lambda x: x.get("key") == "k0", request_id="DSAR-1", basis="art17")
print(f"  forget -> {json.dumps(r, default=str)[:160]}")
cert = st.erasure_certificate(request_id="DSAR-1")
print(f"  certificate keys: {sorted(cert)[:12]}")
sc = cert.get("self_check")
print(f"  self_check: {json.dumps(sc, default=str)[:300]}")

verifiers = [n for n in dir(Inspeximus)
             if "certif" in n.lower() or ("verify" in n.lower() and "eras" in n.lower())]
print(f"  certificate-related methods on Inspeximus: {verifiers}")
mod = sys.modules["inspeximus.core"]
free = [n for n in dir(mod) if "certif" in n.lower()]
print(f"  module-level: {free}")
