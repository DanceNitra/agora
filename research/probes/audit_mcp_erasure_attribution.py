"""Two erasure gaps on the MCP surface, measured rather than asserted.

GAP 1 -- THE SAFE ESCAPE IS UNREACHABLE. When two sources canonicalise alike, forget_subject refuses:
erasing would hard-delete a third party's records. The core offers TWO ways past the guard:

    allow_ambiguous=True   erase all of them deliberately        <- offered by MCP, and the MCP docstring
                                                                    names it as THE response to the raise
    exact=True             erase only the raw-source-equal set   <- not on the MCP surface at all

So the surface steers the caller to the over-deleting option. core.py's own comment says exact exists
because "an attacker-triggerable denial of a legal obligation is worse than the collision it guards" --
a single hostile write whose source canonicalises onto a victim's makes every later DSAR unperformable.
Over MCP the only way to complete that DSAR deletes the other person too.

GAP 2 -- TOMBSTONES ARE UNATTRIBUTED. `authorized_by` (the authorising principal's public key) and
`authorization` (their signature over the erasure challenge) are written into the tombstone's `auth`
field. Neither is on the MCP tool, so every MCP erasure records THAT a deletion happened and never on
whose authority -- while governance_report is sold as the Art.30 accountability surface.

Both are milder than the key-binding defect: nothing here returns a false clean verdict. They are a
surface that offers the dangerous half of a choice, and an evidence field that is structurally always
empty. CONTROLS: the library path must show the safe behaviour, else the gap is in the core, not the MCP.
"""
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.core import AmbiguousSubject  # noqa: E402

tmp = tempfile.mkdtemp(prefix="insp_er_")


def build():
    """Two sources that canonicalise to one key -- the collision the guard exists for."""
    p = os.path.join(tmp, f"s{build.n}.json")
    build.n += 1
    st = Inspeximus(path=p, receipts=True)
    st.remember("alice's payout account is at bank A", key="alice::payout",
                object="bank A", source={"doc": "crm.example.com/Alice"})
    st.remember("alice asked for a statement in April", key="alice::stmt",
                object="April", source={"doc": "crm.example.com/Alice"})
    st.remember("bob's payout account is at bank B", key="bob::payout",
                object="bank B", source={"doc": "crm.example.com/alice"})
    return st


build.n = 0
SUBJ = "crm.example.com/Alice"


def survivors(st):
    return sorted(r["text"][:28] for r in st.items if r.get("status") == "active")


print("=== GAP 1: which escape does each surface offer? ===")
st = build()
try:
    st.forget_subject(SUBJ)
    print("  no collision raised -- FIXTURE BROKEN, the rest proves nothing")
    raise SystemExit(1)
except AmbiguousSubject as e:
    print(f"  guard fires as designed: {str(e)[:96]}...")

st = build()
st.forget_subject(SUBJ, allow_ambiguous=True)
after_amb = survivors(st)
print(f"\n  allow_ambiguous=True  (the ONLY escape MCP offers)")
print(f"     survivors: {after_amb}")
bob_gone = not any("bob" in s for s in after_amb)
print(f"     bob's record deleted: {bob_gone}")

st = build()
st.forget_subject(SUBJ, exact=True)
after_exact = survivors(st)
print(f"\n  exact=True            (not on the MCP surface)")
print(f"     survivors: {after_exact}")
bob_kept = any("bob" in s for s in after_exact)
alice_gone = not any("alice's payout" in s for s in after_exact)
print(f"     bob's record kept: {bob_kept}   alice erased: {alice_gone}")

print("\n=== GAP 2: is the tombstone attributed? ===")
st = build()
res = st.forget_subject(SUBJ, exact=True, request_id="DSAR-2026-114",
                        basis="GDPR Art.17", authorized_by="ab" * 32, authorization="cd" * 64)
with_auth = [t for t in st._tombstones if t.get("auth")]
print(f"  library call with authorized_by/authorization -> tombstones carrying auth: "
      f"{len(with_auth)}/{len(st._tombstones)}")

st = build()
st.forget_subject(SUBJ, exact=True, request_id="DSAR-2026-115", basis="GDPR Art.17")
mcp_auth = [t for t in st._tombstones if t.get("auth", {}).get("authorized_by")]
print(f"  the MCP-reachable call (basis + request_id only) -> tombstones naming a principal: "
      f"{len(mcp_auth)}/{len(st._tombstones)}")

print("\n=== VERDICT ===")
control = bob_gone and bob_kept and alice_gone
print(f"  CONTROL (library exact protects the third party AND still completes the DSAR): "
      f"{'PASS' if control else 'PROBE BROKEN'}")
if control:
    print("  GAP 1 CONFIRMED: over MCP the only way past the guard erases the third party.")
if len(with_auth) and not len(mcp_auth):
    print("  GAP 2 CONFIRMED: the auth field is reachable from the library and never from MCP.")
shutil.rmtree(tmp, ignore_errors=True)
