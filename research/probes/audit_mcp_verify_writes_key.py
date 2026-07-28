"""Can a store re-signed with an ATTACKER's key pass the MCP tamper-evidence check?

verify_writes(expected_pubkey=...) is what binds a receipt to the key you expect. The MCP tool takes NO
arguments and calls _MEM.verify_writes() bare, so every MCP caller verifies "signed by SOMEBODY".

The attack modelled here is NOT the operator-holds-the-key case (anchor()'s docstring already owns that,
and it needs an externally witnessed anchor to defeat). It is the cheaper one: someone who can write the
store file, does NOT have the honest key, rewrites the content and re-signs the whole history with a key
of their own. `expected_pubkey` defeats that with nothing but the public key the owner already has --
exactly the third-party check the constructor docstring advertises.

Faithfulness: the tampered store is produced by inspeximus itself under the attacker's key rather than by
me re-implementing the hash chain, so the artifact is what an attacker would actually leave behind.

CONTROLS (a probe with no control is an assertion):
  A. honest store, honest expected_pubkey  -> must be OK   (else the probe is broken, not the product)
  B. tampered store, honest expected_pubkey -> must be CAUGHT (else expected_pubkey is useless anyway
     and the finding is about the core, not the MCP surface)
"""
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.core import new_receipt_keypair  # noqa: E402

HONEST = [
    ("the wire transfer limit for tier-2 accounts is 50000 EUR per day", "limit", "50000"),
    ("the incident escalation contact is the on-call SRE, not the vendor", "escalation", "on-call SRE"),
    ("customer data is retained for 90 days after account closure", "retention", "90 days"),
]
TAMPERED_TEXT = "the wire transfer limit for tier-2 accounts is 5000000 EUR per day"

tmp = tempfile.mkdtemp(prefix="insp_vw_")
path = os.path.join(tmp, "store.json")
sk_honest, pk_honest = new_receipt_keypair()
sk_attack, pk_attack = new_receipt_keypair()


def build(sk, pk, texts):
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    st = Inspeximus(path=path, receipts=True, receipt_key=sk, receipt_pubkey=pk)
    for t, k, o in texts:
        st.remember(t, key=k, object=o)
    return st


def check(label, expected):
    """Reload from disk the way a verifier would, then run both verification modes."""
    st = Inspeximus(path=path, receipts=True)
    bare_ok, bare_probs = st.verify_writes()                       # <- what the MCP tool can reach
    pin_ok, pin_probs = st.verify_writes(expected_pubkey=expected)  # <- what only the library can reach
    keys = {r.get("pubkey") for r in st._receipts}
    print(f"  {label}")
    print(f"     receipt keys on disk : {[ (k or '')[:16] for k in keys ]}")
    print(f"     verify_writes()                 -> ok={bare_ok}   ({len(bare_probs)} problems)")
    print(f"     verify_writes(expected_pubkey=) -> ok={pin_ok}   ({len(pin_probs)} problems)")
    if pin_probs:
        print(f"     first pinned problem: {pin_probs[0][:100]}")
    return bare_ok, pin_ok


print("=== CONTROL A: honest store, honest key ===")
build(sk_honest, pk_honest, HONEST)
a_bare, a_pin = check("untampered", pk_honest)

print("\n=== ATTACK: content rewritten, whole history re-signed with the attacker's key ===")
tampered = [(TAMPERED_TEXT, "limit", "5000000")] + HONEST[1:]
build(sk_attack, pk_attack, tampered)
b_bare, b_pin = check("tampered + re-signed", pk_honest)

st = Inspeximus(path=path, receipts=True)
served = [r["text"] for r in st.items if r.get("key") == "limit"]
print(f"\n  what the store now SERVES for key 'limit': {served}")

print("\n=== VERDICT ===")
ok_control = a_bare and a_pin
print(f"  CONTROL A (honest passes both)        : {'PASS' if ok_control else 'PROBE BROKEN'}")
print(f"  CONTROL B (pinned key catches attack) : {'PASS' if not b_pin else 'expected_pubkey USELESS'}")
if ok_control and not b_pin:
    if b_bare:
        print("  FINDING: the bare call — the ONLY call the MCP tool can make — returns ok=True on a store")
        print("           whose entire history was rewritten and re-signed by a foreign key. The one")
        print("           parameter that catches it is not reachable from the MCP surface.")
    else:
        print("  NO FINDING: the bare call already catches it; expected_pubkey is not load-bearing here.")
shutil.rmtree(tmp, ignore_errors=True)
