"""Verify the two certificate fixes — honest cases must still pass, tampered ones must be refused."""
import copy
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus, new_source_keypair  # noqa: E402
from inspeximus.core import verify_erasure_certificate as V  # noqa: E402


def build(signed, n_requests=2):
    kw = {"receipts": True}
    if signed:
        priv, _ = new_source_keypair()
        kw["receipt_key"] = priv
    st = Inspeximus(path=None, **kw)
    for i in range(8):
        st.remember(f"subject {i} value-{i}", key=f"k{i}", object=f"v{i}", source={"doc": f"p{i}"})
    for j in range(n_requests):
        st.forget(where=lambda r, j=j: r.get("key") == f"k{j}", request_id=f"DSAR-{j+1}",
                  basis="art17")
    return st, st.erasure_certificate(request_id="DSAR-1"), [dict(r) for r in st.items]


for signed in (False, True):
    st, cert, items = build(signed)
    r = V(cert, store_items=items)
    print(f"=== signed={signed} ===")
    print(f"  honest valid={r['valid']}  signatures_valid={r['checks'].get('signatures_valid')!r} "
          f"signed={r['checks'].get('signed')!r} scope_intact={r['checks'].get('scope_intact')!r}")
    print(f"  problems={len(r['problems'])}  limits={r.get('limits')}")

    bad = copy.deepcopy(cert)
    bad["scope"] = "Full GDPR compliance certification, all systems."
    rs = V(bad, store_items=items)
    print(f"  scope rewritten   -> valid={rs['valid']}  "
          f"{'REFUSED' if not rs['valid'] else '!! ACCEPTED'}")

    bad2 = copy.deepcopy(cert)
    bad2["pubkey"] = "00" * 32
    rp = V(bad2, store_items=items)
    note = "no signatures to check — reported as a LIMIT, not a pass" if not signed else ""
    print(f"  pubkey swapped    -> valid={rp['valid']}  "
          f"{'REFUSED' if not rp['valid'] else 'accepted'}  {note}")

    bad3 = copy.deepcopy(cert)
    bad3["scoped_to"] = None
    rw = V(bad3, store_items=items)
    print(f"  scoped_to widened -> valid={rw['valid']}  "
          f"{'REFUSED' if not rw['valid'] else '!! ACCEPTED'}")
    print()

print("=== the check a DPA reads ===")
_, cert_u, items_u = build(False)
ru = V(cert_u, store_items=items_u)
print(f"  unsigned certificate: signatures_valid={ru['checks']['signatures_valid']!r} "
      f"(was True before this fix, about a document with no signatures)")
print(f"  limits: {ru.get('limits')}")
