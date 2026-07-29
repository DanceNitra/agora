"""Does remember() tell the caller when the guard retired their write? And what does revert() cost?

The audit's claim is that one defect reaches through seven doors: a write the guard demotes is reported to
the caller exactly like a write that landed -- same return type, same shape, an id either way -- so a
legitimate A->B->A reversal silently ends on B. And that `route()`, the other write path, already returns
an explicit {"intent": "echo", "action": "blocked"}, so the signal exists and simply is not on the primary
path.

The second half is worse if true: after revert(), the value the revert retired can never be written again
through remember(), because the guard sees every honest re-write of it as an echo. That is the same wedge
the flip was justified by, in mirror image -- "the store cannot be put right through the surface that broke
it" -- now reachable through revert().

I shipped this default today on the owner's instruction, without measuring either. Measuring now.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store(guard=True):
    st = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"))
    st.echo_guard = guard
    return st


def active(st, key):
    return [r.get("object") for r in st.items if r.get("key") == key and r.get("status") == "active"]


print("=== F1: a legitimate reversal A -> B -> A ===")
for guard in (True, False):
    st = store(guard)
    st.remember("the deploy branch is release-2", key="d::branch", object="release-2")
    st.remember("the deploy branch is main", key="d::branch", object="main")
    rid = st.remember("the deploy branch is release-2 again", key="d::branch", object="release-2")
    rec = next((r for r in st.items if r["id"] == rid), {})
    print(f"   guard={str(guard):5s} 3rd write returned id={rid!r} type={type(rid).__name__}")
    print(f"                 that record's status = {rec.get('status')!r}"
          f"  policy={rec.get('superseded_by_policy')!r}")
    print(f"                 ACTIVE value now = {active(st, 'd::branch')}")
print("   -> if the return is indistinguishable, the caller cannot tell a landed write from a")
print("      retired one, and the store ends on the value the world no longer has.\n")

print("=== does route() already carry the signal remember() lacks? ===")
st = store(True)
st.remember("the deploy branch is release-2", key="d::branch", object="release-2")
st.remember("the deploy branch is main", key="d::branch", object="main")
try:
    out = st.route("the deploy branch is release-2 again", key="d::branch", object="release-2")
    print(f"   route() -> {out}")
except Exception as e:
    print(f"   route() raised {type(e).__name__}: {str(e)[:80]}")

print("\n=== F5: after revert(), can the reverted-away value ever be written again? ===")
for guard in (True, False):
    st = store(guard)
    st.remember("address 4A", key="a::addr", object="4A")
    st.remember("address 3A", key="a::addr", object="3A")
    try:
        st.revert("a::addr")
    except Exception as e:
        print(f"   guard={guard} revert raised {type(e).__name__}: {str(e)[:60]}")
        continue
    after_revert = active(st, "a::addr")
    st.remember("the address really is 3A now", key="a::addr", object="3A")
    print(f"   guard={str(guard):5s} after revert active={after_revert}   "
          f"after honest re-write active={active(st, 'a::addr')}")
print("   -> under the guard, if the re-write is refused the store cannot follow the world back,")
print("      which is the wedge the flip was meant to remove, pointing the other way.")
